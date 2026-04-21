import asyncio
import logging
from abc import ABC, abstractmethod
from typing import Iterable, Mapping

from config import EXCHANGES, WS_RECONNECT_BASE_DELAY, WS_RECONNECT_MAX_DELAY

logger = logging.getLogger(__name__)


class ExchangeWS(ABC):
    """Base connector. Subclasses must set `exchange_id` matching an EXCHANGES registry key.

    Accepts either a plain iterable of canonical symbols (identity mapping) or a
    {canonical: native} dict so venues with different naming (e.g. Hyperliquid's
    bare `BTC`, `kPEPE`) can translate in both directions.
    """

    exchange_id: str = ""

    def __init_subclass__(cls, **kwargs):
        # Hard import-time gate on fee provenance. Agreed via /model-chat
        # 2026-04-21: every concrete connector class must resolve to an
        # EXCHANGES entry carrying maker_fee, taker_fee, AND fee_source_url.
        # Intermediate bases (CexWSBase) leave exchange_id empty and are
        # exempt. See model-chat/2026-04-21-add-exchange-skill-redesign.md.
        super().__init_subclass__(**kwargs)
        if not cls.exchange_id:
            return
        entry = EXCHANGES.get(cls.exchange_id)
        if entry is None:
            raise RuntimeError(
                f"{cls.__name__}.exchange_id={cls.exchange_id!r} has no matching EXCHANGES entry"
            )
        # Zero fees (MEXC maker=0.0) are legitimate — only flag missing keys.
        missing = [k for k in ("maker_fee", "taker_fee", "fee_source_url") if k not in entry]
        if missing:
            raise RuntimeError(
                f"{cls.__name__} EXCHANGES[{cls.exchange_id!r}] missing keys: {missing}"
            )
        if not str(entry["fee_source_url"]).startswith(("http://", "https://")):
            raise RuntimeError(
                f"{cls.__name__} EXCHANGES[{cls.exchange_id!r}].fee_source_url must be an http(s) URL"
            )

    def __init__(self, symbols: Iterable[str] | Mapping[str, str]):
        if not self.exchange_id or self.exchange_id not in EXCHANGES:
            raise ValueError(
                f"{self.__class__.__name__}.exchange_id must be set to an EXCHANGES key"
            )
        self.name = EXCHANGES[self.exchange_id]["short_name"]

        if isinstance(symbols, Mapping):
            self._canonical_to_native = dict(symbols)
        else:
            self._canonical_to_native = {s: s for s in symbols}
        self._native_to_canonical = {v: k for k, v in self._canonical_to_native.items()}

        self.symbols = set(self._canonical_to_native.keys())          # canonical
        self.native_symbols = set(self._canonical_to_native.values()) # for subscriptions
        self._reconnect_delay = WS_RECONNECT_BASE_DELAY

    def to_canonical(self, native: str) -> str | None:
        return self._native_to_canonical.get(native)

    def to_native(self, canonical: str) -> str | None:
        return self._canonical_to_native.get(canonical)

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
