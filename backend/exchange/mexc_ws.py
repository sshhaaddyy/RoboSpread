import asyncio
import json
import logging

import aiohttp
import websockets

from config import EXCHANGES
from exchange.base import ExchangeWS
from engine.state import state

logger = logging.getLogger(__name__)

FUNDING_POLL_URL = "https://contract.mexc.com/api/v1/contract/funding_rate"
FUNDING_POLL_SEC = 30
MEXC_PING_INTERVAL = 15


class MexcWS(ExchangeWS):
    """MEXC Futures public WebSocket + REST funding poll.

    Dual-source because MEXC's streams split the data across channels:
      - `sub.tickers` (bulk, no symbol arg) → one channel pushes `fairPrice`
        for every symbol at once. ~1 Hz, far cheaper than 800+ sub.ticker
        subscriptions.
      - `GET /api/v1/contract/funding_rate` → array of every symbol's
        `fundingRate`, `collectCycle` (interval in hours), `nextSettleTime`.
        Polled every 30s. Per-tick sub.ticker *does* carry fundingRate but
        omits interval and nextSettleTime, so the REST poll is load-bearing.

    Ping: `{"method":"ping"}` every 15s; server replies `{"channel":"pong"}`.
    No ping for ~60s drops the connection.
    """

    exchange_id = "mexc"

    async def _ping_loop(self, ws):
        try:
            while True:
                await asyncio.sleep(MEXC_PING_INTERVAL)
                await ws.send(json.dumps({"method": "ping"}))
        except Exception:
            pass

    async def _funding_poll(self):
        async with aiohttp.ClientSession() as session:
            while True:
                try:
                    async with session.get(
                        FUNDING_POLL_URL,
                        timeout=aiohttp.ClientTimeout(total=15),
                    ) as resp:
                        resp.raise_for_status()
                        payload = await resp.json()
                    for row in payload.get("data") or []:
                        native = row.get("symbol")
                        canonical = self.to_canonical(native) if native else None
                        if not canonical:
                            continue
                        try:
                            funding_rate = float(row.get("fundingRate") or 0)
                        except (TypeError, ValueError):
                            funding_rate = 0.0
                        try:
                            cycle = float(row.get("collectCycle") or 8)
                        except (TypeError, ValueError):
                            cycle = 8.0
                        nst_ms = row.get("nextSettleTime")
                        try:
                            nft = float(nst_ms) / 1000 if nst_ms else None
                        except (TypeError, ValueError):
                            nft = None

                        # Route funding updates through state.update_leg using
                        # the last-known mark price, so best_arb / best_funding
                        # get recomputed and the WS frontend sees fresh numbers
                        # without waiting for the next mark-price tick.
                        pair = state.pairs.get(canonical)
                        leg = pair.legs.get(self.exchange_id) if pair else None
                        if leg is None or leg.mark_price <= 0:
                            continue
                        state.update_leg(
                            self.exchange_id,
                            canonical,
                            leg.mark_price,
                            funding_rate=funding_rate,
                            funding_interval_h=cycle,
                            next_funding_time=nft,
                        )
                except Exception as e:
                    logger.warning(f"[MEXC] funding poll error: {e}")
                await asyncio.sleep(FUNDING_POLL_SEC)

    async def connect(self):
        url = EXCHANGES[self.exchange_id]["ws_url"]
        logger.info(f"[MEXC] Connecting to {url}")

        async with websockets.connect(url, ping_interval=None) as ws:
            logger.info("[MEXC] Connected.")
            await ws.send(json.dumps({"method": "sub.tickers", "param": {}}))
            logger.info(
                f"[MEXC] Subscribed to sub.tickers; tracking {len(self.symbols)} symbols"
            )

            ping_task = asyncio.create_task(self._ping_loop(ws))
            poll_task = asyncio.create_task(self._funding_poll())

            try:
                async for raw in ws:
                    try:
                        msg = json.loads(raw)
                    except (ValueError, TypeError):
                        continue
                    channel = msg.get("channel")
                    if channel in ("pong", "rs.sub.tickers"):
                        continue
                    if channel != "push.tickers":
                        continue
                    data = msg.get("data")
                    if not isinstance(data, list):
                        continue
                    for item in data:
                        native = item.get("symbol")
                        canonical = self.to_canonical(native) if native else None
                        if not canonical:
                            continue
                        mark = item.get("fairPrice") or item.get("lastPrice")
                        try:
                            mark_price = float(mark) if mark is not None else 0.0
                        except (TypeError, ValueError):
                            continue
                        if mark_price <= 0:
                            continue
                        # funding_rate may also be on sub.ticker (per-symbol) but
                        # we rely on the 30s REST poll for it + interval + next
                        # settle. Do not override with a partial.
                        state.update_leg(
                            self.exchange_id,
                            canonical,
                            mark_price,
                        )
            finally:
                ping_task.cancel()
                poll_task.cancel()
