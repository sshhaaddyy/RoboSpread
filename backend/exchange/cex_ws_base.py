import asyncio
import json
import logging
import websockets

from config import EXCHANGES
from exchange.base import ExchangeWS

logger = logging.getLogger(__name__)


class CexWSBase(ExchangeWS):
    """Shared connector skeleton for CEXs whose public WS uses op/args pubsub
    with per-symbol channels and an app-level string-ping keepalive.

    Subclasses must override:
      - `_subscribe_arg(native)`  — the per-symbol arg dict sent with op=subscribe
      - `_handle_message(msg)`    — parse one inbound JSON message (may call state.update_leg)

    Subclasses may override:
      - `ping_message` / `pong_message` / `ping_interval_sec`
      - `sub_batch_size` / `sub_batch_delay`
      - `subscribe_op`  — the op string (default "subscribe")
      - `_is_control_message(msg)` — filter sub/ack/pong frames before parse
    """

    ping_interval_sec: float = 20.0
    ping_message: str = "ping"
    pong_message: str = "pong"
    sub_batch_size: int = 20
    sub_batch_delay: float = 0.05
    subscribe_op: str = "subscribe"

    def _subscribe_arg(self, native: str) -> dict:
        raise NotImplementedError

    async def _handle_message(self, msg: dict):
        raise NotImplementedError

    def _is_control_message(self, msg: dict) -> bool:
        return "event" in msg or "op" in msg

    async def _subscribe(self, ws):
        natives = sorted(self.native_symbols)
        for i in range(0, len(natives), self.sub_batch_size):
            batch = natives[i : i + self.sub_batch_size]
            args = [self._subscribe_arg(n) for n in batch]
            await ws.send(json.dumps({"op": self.subscribe_op, "args": args}))
            await asyncio.sleep(self.sub_batch_delay)
        logger.info(f"[{self.name}] Subscribed to {len(natives)} channels")

    async def _ping_loop(self, ws):
        try:
            while True:
                await asyncio.sleep(self.ping_interval_sec)
                await ws.send(self.ping_message)
        except Exception:
            pass

    async def connect(self):
        url = EXCHANGES[self.exchange_id]["ws_url"]
        logger.info(f"[{self.name}] Connecting to {url}")

        async with websockets.connect(url, ping_interval=None) as ws:
            logger.info(f"[{self.name}] Connected.")
            await self._subscribe(ws)
            ping_task = asyncio.create_task(self._ping_loop(ws))
            try:
                async for raw in ws:
                    if isinstance(raw, bytes):
                        try:
                            raw = raw.decode()
                        except Exception:
                            continue
                    if raw == self.pong_message:
                        continue
                    try:
                        msg = json.loads(raw)
                    except (ValueError, TypeError):
                        continue
                    if self._is_control_message(msg):
                        continue
                    try:
                        await self._handle_message(msg)
                    except Exception as e:
                        logger.error(f"[{self.name}] Parse error: {e}")
            finally:
                ping_task.cancel()
