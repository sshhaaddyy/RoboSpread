import asyncio
import json
import logging
import websockets

from config import EXCHANGES
from exchange.base import ExchangeWS

logger = logging.getLogger(__name__)


class CexWSBase(ExchangeWS):
    """Shared connector skeleton for CEX public WebSocket streams.

    Subclasses must override `_handle_message(msg)` and either:
      - `_subscribe_arg(native)` if the venue uses the op/args shape, OR
      - `_build_subscribe_message(batch)` for a different subscribe envelope.

    Ping model is venue-specific:
      - `enable_app_ping=True`  + `ping_message/pong_message` → app-level string ping loop
      - `enable_app_ping=False` + `websocket_ping_interval=N`  → protocol-level WS pings
    """

    # WebSocket protocol pings (handled by the websockets library)
    websocket_ping_interval: float | None = None

    # App-level string ping (e.g. Bitget "ping"/"pong")
    enable_app_ping: bool = True
    ping_interval_sec: float = 20.0
    ping_message: str = "ping"
    pong_message: str = "pong"

    # Subscription batching
    sub_batch_size: int = 20
    sub_batch_delay: float = 0.05
    subscribe_op: str = "subscribe"

    def _subscribe_arg(self, native: str) -> dict:
        raise NotImplementedError(
            "Override _subscribe_arg() or _build_subscribe_message()"
        )

    def _build_subscribe_message(self, batch: list[str]) -> str:
        """Default envelope: {"op": <op>, "args": [<per-symbol arg>, ...]}.
        Override for venues that use a different shape."""
        args = [self._subscribe_arg(n) for n in batch]
        return json.dumps({"op": self.subscribe_op, "args": args})

    async def _handle_message(self, msg: dict):
        raise NotImplementedError

    def _is_control_message(self, msg: dict) -> bool:
        """Default: treat anything with an `event` or `op` field as an
        ack / control frame. Override for venues where data payloads also
        carry an `event` (e.g. Gate's event="update")."""
        return "event" in msg or "op" in msg

    async def _subscribe(self, ws):
        natives = sorted(self.native_symbols)
        for i in range(0, len(natives), self.sub_batch_size):
            batch = natives[i : i + self.sub_batch_size]
            await ws.send(self._build_subscribe_message(batch))
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

        async with websockets.connect(
            url, ping_interval=self.websocket_ping_interval
        ) as ws:
            logger.info(f"[{self.name}] Connected.")
            await self._subscribe(ws)

            ping_task = (
                asyncio.create_task(self._ping_loop(ws))
                if self.enable_app_ping else None
            )
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
                if ping_task is not None:
                    ping_task.cancel()
