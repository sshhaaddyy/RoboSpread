import asyncio
import json
import logging
import websockets

from config import (
    EXCHANGES,
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

    exchange_id = "bybit"

    async def _subscribe(self, ws):
        symbol_list = sorted(self.native_symbols)
        for i in range(0, len(symbol_list), BYBIT_SUB_BATCH_SIZE):
            batch = symbol_list[i : i + BYBIT_SUB_BATCH_SIZE]
            args = [f"tickers.{s}" for s in batch]
            msg = json.dumps({"op": "subscribe", "args": args})
            await ws.send(msg)
            await asyncio.sleep(BYBIT_SUB_BATCH_DELAY)

        logger.info(f"[Bybit] Subscribed to {len(symbol_list)} tickers")

    async def _ping_loop(self, ws):
        try:
            while True:
                await asyncio.sleep(BYBIT_PING_INTERVAL)
                await ws.send(json.dumps({"op": "ping"}))
        except Exception:
            pass

    async def connect(self):
        url = EXCHANGES[self.exchange_id]["ws_url"]
        logger.info(f"[Bybit] Connecting to {url}")

        async with websockets.connect(url, ping_interval=None) as ws:
            logger.info("[Bybit] Connected. Subscribing to tickers...")

            await self._subscribe(ws)

            ping_task = asyncio.create_task(self._ping_loop(ws))

            try:
                async for raw_msg in ws:
                    try:
                        msg = json.loads(raw_msg)

                        if msg.get("op") in ("pong", "subscribe"):
                            continue

                        topic = msg.get("topic", "")
                        if not topic.startswith("tickers."):
                            continue

                        data = msg.get("data", {})
                        native = data.get("symbol", "")
                        canonical = self.to_canonical(native)
                        if not canonical:
                            continue

                        mark_price = data.get("markPrice")
                        funding_rate = data.get("fundingRate")
                        next_funding_time = data.get("nextFundingTime")
                        funding_interval_min = data.get("fundingInterval")

                        if mark_price:
                            nft = int(next_funding_time) / 1000 if next_funding_time else None
                            fih = int(funding_interval_min) / 60 if funding_interval_min else 8
                            state.update_leg(
                                self.exchange_id,
                                canonical,
                                float(mark_price),
                                funding_rate=float(funding_rate) if funding_rate else None,
                                next_funding_time=nft,
                                funding_interval_h=fih,
                            )

                    except Exception as e:
                        logger.error(f"[Bybit] Parse error: {e}")
            finally:
                ping_task.cancel()
