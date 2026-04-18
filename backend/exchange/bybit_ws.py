import asyncio
import json
import logging
import time
import websockets

from config import (
    BYBIT_WS_URL,
    BYBIT_SUB_BATCH_SIZE,
    BYBIT_SUB_BATCH_DELAY,
    BYBIT_PING_INTERVAL,
)
from exchange.base import ExchangeWS
from engine.state import state

logger = logging.getLogger(__name__)


class BybitWS(ExchangeWS):
    """
    Connects to Bybit v5 linear (futures) WebSocket.
    Subscribes to tickers for each symbol individually (batched).
    Requires ping every 20s to keep connection alive.
    """

    def __init__(self, symbols: list[str]):
        super().__init__("Bybit", symbols)

    async def _subscribe(self, ws):
        """Subscribe to tickers in batches of BYBIT_SUB_BATCH_SIZE."""
        symbol_list = sorted(self.symbols)
        for i in range(0, len(symbol_list), BYBIT_SUB_BATCH_SIZE):
            batch = symbol_list[i : i + BYBIT_SUB_BATCH_SIZE]
            args = [f"tickers.{s}" for s in batch]
            msg = json.dumps({"op": "subscribe", "args": args})
            await ws.send(msg)
            await asyncio.sleep(BYBIT_SUB_BATCH_DELAY)

        logger.info(f"[Bybit] Subscribed to {len(symbol_list)} tickers")

    async def _ping_loop(self, ws):
        """Send ping every BYBIT_PING_INTERVAL seconds."""
        try:
            while True:
                await asyncio.sleep(BYBIT_PING_INTERVAL)
                await ws.send(json.dumps({"op": "ping"}))
        except Exception:
            pass  # Connection closed, ping loop exits

    async def connect(self):
        logger.info(f"[Bybit] Connecting to {BYBIT_WS_URL}")

        async with websockets.connect(BYBIT_WS_URL, ping_interval=None) as ws:
            logger.info("[Bybit] Connected. Subscribing to tickers...")

            await self._subscribe(ws)

            # Start ping loop in background
            ping_task = asyncio.create_task(self._ping_loop(ws))

            try:
                async for raw_msg in ws:
                    try:
                        msg = json.loads(raw_msg)

                        # Skip pong and subscription confirmations
                        if msg.get("op") in ("pong", "subscribe"):
                            continue

                        topic = msg.get("topic", "")
                        if not topic.startswith("tickers."):
                            continue

                        data = msg.get("data", {})
                        symbol = data.get("symbol", "")

                        if symbol not in self.symbols:
                            continue

                        mark_price = data.get("markPrice")
                        funding_rate = data.get("fundingRate")
                        next_funding_time = data.get("nextFundingTime")
                        funding_interval_min = data.get("fundingInterval")

                        if mark_price:
                            nft = int(next_funding_time) / 1000 if next_funding_time else None
                            fih = int(funding_interval_min) / 60 if funding_interval_min else 8
                            state.update_price(
                                "bybit",
                                symbol,
                                float(mark_price),
                                float(funding_rate) if funding_rate else None,
                                next_funding_time=nft,
                                funding_interval_h=fih,
                            )

                    except Exception as e:
                        logger.error(f"[Bybit] Parse error: {e}")
            finally:
                ping_task.cancel()
