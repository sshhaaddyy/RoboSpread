import asyncio
import json
import logging
import urllib.request
import uuid

import websockets

from config import EXCHANGES
from engine.state import state
from exchange.base import ExchangeWS
from exchange.kucoin_discovery import get_interval_h, get_next_funding_time

logger = logging.getLogger(__name__)

BULLET_URL = "https://api-futures.kucoin.com/api/v1/bullet-public"


class KucoinWS(ExchangeWS):
    """KuCoin Futures public WS.

    Two-step connect: POST bullet-public for a one-shot token + WS endpoint,
    then connect to `<endpoint>?token=<t>&connectId=<uuid>`. The
    `/contract/instrument:<sym>[,<sym>...]` topic multiplexes two subjects —
    `mark.index.price` (~1Hz per symbol) and `funding.rate`. Funding interval
    + next-funding-time come from the REST discovery cache.

    Subscription sharding: KuCoin silently caps per-connection symbol traffic
    around ~100 actively streaming symbols. With 500+ perps we'd otherwise
    see only the first ~100 pushing marks. Fix: open N parallel WS sessions,
    each handling a ~80-symbol slice. 6 sessions is well under KuCoin's
    300-connection-per-user cap.
    """

    exchange_id = "kucoin"

    SLICE_SIZE = 80  # symbols per sub-connection
    SUB_BATCH = 80   # symbols per subscribe frame within a connection

    def __init__(self, native_symbols):
        super().__init__(native_symbols)
        self._fr_cache: dict[str, float] = {}

    async def _fetch_bullet(self) -> tuple[str, str, float]:
        def _blocking():
            req = urllib.request.Request(
                BULLET_URL, method="POST",
                headers={"User-Agent": "Mozilla/5.0 RoboSpread/1.0"},
            )
            with urllib.request.urlopen(req, timeout=15) as resp:
                return json.loads(resp.read())

        payload = await asyncio.to_thread(_blocking)
        data = payload.get("data") or {}
        token = data.get("token")
        servers = data.get("instanceServers") or []
        if not token or not servers:
            raise RuntimeError(f"KuCoin bullet returned malformed payload: {payload}")
        server = servers[0]
        return server.get("endpoint"), token, float(server.get("pingInterval") or 18000) / 1000.0

    async def connect(self):
        natives = sorted(self.native_symbols)
        slices = [natives[i : i + self.SLICE_SIZE] for i in range(0, len(natives), self.SLICE_SIZE)]
        logger.info(f"[{self.name}] Sharding {len(natives)} symbols into {len(slices)} connections")
        tasks = [asyncio.create_task(self._connect_slice(i, slc)) for i, slc in enumerate(slices)]
        try:
            await asyncio.gather(*tasks)
        finally:
            for t in tasks:
                if not t.done():
                    t.cancel()

    async def _connect_slice(self, idx: int, symbols: list[str]):
        endpoint, token, ping_interval = await self._fetch_bullet()
        connect_id = str(uuid.uuid4())
        url = f"{endpoint}?token={token}&connectId={connect_id}"

        async with websockets.connect(url, ping_interval=None) as ws:
            await ws.recv()  # welcome
            topic = "/contract/instrument:" + ",".join(symbols)
            await ws.send(json.dumps({
                "id": idx + 1, "type": "subscribe",
                "topic": topic, "response": False,
            }))
            logger.info(f"[{self.name}:{idx}] Subscribed to {len(symbols)} symbols")

            ping_task = asyncio.create_task(self._ping_loop(ws, ping_interval, idx))
            try:
                async for raw in ws:
                    if isinstance(raw, bytes):
                        try:
                            raw = raw.decode()
                        except Exception:
                            continue
                    try:
                        msg = json.loads(raw)
                    except (ValueError, TypeError):
                        continue
                    if msg.get("type") != "message":
                        continue
                    try:
                        self._handle_data(msg)
                    except Exception as e:
                        logger.error(f"[{self.name}:{idx}] Parse error: {e}")
            finally:
                ping_task.cancel()

    async def _ping_loop(self, ws, interval_sec: float, idx: int):
        try:
            while True:
                await asyncio.sleep(max(interval_sec - 2.0, 5.0))
                await ws.send(json.dumps({"id": f"ping-{idx}", "type": "ping"}))
        except Exception:
            pass

    def _handle_data(self, msg: dict):
        topic = msg.get("topic") or ""
        subject = msg.get("subject") or ""
        data = msg.get("data") or {}
        if ":" not in topic:
            return
        native = topic.split(":", 1)[1]
        canonical = self.to_canonical(native)
        if not canonical:
            return

        if subject == "funding.rate":
            fr = data.get("fundingRate")
            if fr is not None:
                try:
                    self._fr_cache[canonical] = float(fr)
                except (TypeError, ValueError):
                    pass
            return

        if subject == "mark.index.price":
            mark = data.get("markPrice")
            if mark is None:
                return
            try:
                mark_price = float(mark)
            except (TypeError, ValueError):
                return
            if mark_price <= 0:
                return
            interval_h = get_interval_h(canonical)
            if interval_h is None:
                interval_h = EXCHANGES[self.exchange_id]["default_funding_interval_h"]
            state.update_leg(
                self.exchange_id,
                canonical,
                mark_price,
                funding_rate=self._fr_cache.get(canonical),
                next_funding_time=get_next_funding_time(canonical),
                funding_interval_h=interval_h,
            )
