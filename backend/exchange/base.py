import asyncio
import logging
from abc import ABC, abstractmethod

from config import EXCHANGES, WS_RECONNECT_BASE_DELAY, WS_RECONNECT_MAX_DELAY

logger = logging.getLogger(__name__)


class ExchangeWS(ABC):
    """Base connector. Subclasses must set `exchange_id` matching an EXCHANGES registry key."""

    exchange_id: str = ""

    def __init__(self, symbols: list[str]):
        if not self.exchange_id or self.exchange_id not in EXCHANGES:
            raise ValueError(
                f"{self.__class__.__name__}.exchange_id must be set to an EXCHANGES key"
            )
        self.name = EXCHANGES[self.exchange_id]["short_name"]
        self.symbols = set(symbols)
        self._reconnect_delay = WS_RECONNECT_BASE_DELAY

    @abstractmethod
    async def connect(self):
        """Connect and start streaming. Should run until the connection drops."""
        pass

    async def run_forever(self):
        """Connect with automatic reconnection on failure."""
        while True:
            try:
                self._reconnect_delay = WS_RECONNECT_BASE_DELAY
                await self.connect()
            except Exception as e:
                logger.error(f"[{self.name}] Connection error: {e}")
                logger.info(f"[{self.name}] Reconnecting in {self._reconnect_delay}s...")
                await asyncio.sleep(self._reconnect_delay)
                self._reconnect_delay = min(
                    self._reconnect_delay * 2,
                    WS_RECONNECT_MAX_DELAY,
                )
