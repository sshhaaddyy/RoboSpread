import json
import logging
import websockets

from config import EXCHANGES
from exchange.base import ExchangeWS
from engine.state import state

logger = logging.getLogger(__name__)


class BinanceWS(ExchangeWS):
    """
    Connects to Binance futures !markPrice@arr@1s stream.
    This single stream pushes ALL futures mark prices every second.
    We filter to only our common pairs.
    """

    exchange_id = "binance"

    async def connect(self):
        url = EXCHANGES[self.exchange_id]["ws_url"]
        logger.info(f"[Binance] Connecting to {url}")

        async with websockets.connect(url, ping_interval=20) as ws:
            logger.info("[Binance] Connected. Streaming mark prices...")

            async for raw_msg in ws:
                try:
                    msg = json.loads(raw_msg)
                    data = msg.get("data", [])

                    for item in data:
                        symbol = item.get("s", "")  # e.g. "BTCUSDT"
                        if symbol not in self.symbols:
                            continue

                        mark_price = float(item.get("p", 0))  # markPrice
                        funding_rate = float(item.get("r", 0))  # lastFundingRate
                        next_funding_time_ms = item.get("T")    # nextFundingTime (ms)

                        # Binance markPrice stream doesn't include funding interval.
                        # Default is 8h; we derive it from consecutive funding times if needed.
                        nft = int(next_funding_time_ms) / 1000 if next_funding_time_ms else None

                        if mark_price > 0:
                            state.update_leg(
                                self.exchange_id,
                                symbol,
                                mark_price,
                                funding_rate=funding_rate,
                                next_funding_time=nft,
                            )

                except Exception as e:
                    logger.error(f"[Binance] Parse error: {e}")
