import asyncio
import logging
from abc import ABC, abstractmethod

from config import WS_RECONNECT_BASE_DELAY, WS_RECONNECT_MAX_DELAY

logger = logging.getLogger(__name__)


class ExchangeWS(ABC):
    def __init__(self, name: str, symbols: list[str]):
        self.name = name
        self.symbols = set(symbols)
        self._reconnect_delay = WS_RECONNECT_BASE_DELAY

    @abstractmethod
    async def connect(self):
        """Connect and start streaming."""
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
