"""BingX connector — Archetype 5 (pure REST poll on bulk endpoint).

BingX's `/openApi/swap/v2/quote/premiumIndex` (no symbol arg) returns an
array of ~675 objects, one per perp, each carrying:
    symbol, markPrice, indexPrice, lastFundingRate, nextFundingTime (ms),
    fundingIntervalHours
— everything we need. One HTTP call every POLL_SECONDS replaces ~675
per-symbol WS subscriptions with zero rate-limit risk (BingX public
unauthenticated: 100 req/10s per IP; we use ~0.33 req/s).

We still inherit `ExchangeWS` so the base-class reconnect/backoff logic
keeps us resilient to transient HTTP failures. `connect()` runs the poll
loop until a fatal exception bubbles; `run_forever()` then reconnects.
"""
import asyncio
import json
import logging
import urllib.request

from config import EXCHANGES
from engine.state import state
from exchange.base import ExchangeWS

logger = logging.getLogger(__name__)

PREMIUM_INDEX_URL = "https://open-api.bingx.com/openApi/swap/v2/quote/premiumIndex"
POLL_SECONDS = 3.0


class BingxWS(ExchangeWS):
    exchange_id = "bingx"

    async def connect(self):
        logger.info(f"[{self.name}] Polling {PREMIUM_INDEX_URL} every {POLL_SECONDS}s for {len(self.native_symbols)} symbols")
        while True:
            try:
                items = await asyncio.to_thread(self._fetch_premium_index)
            except Exception as e:
                logger.error(f"[{self.name}] premiumIndex fetch failed: {e}")
                await asyncio.sleep(POLL_SECONDS)
                continue
            self._handle_items(items)
            await asyncio.sleep(POLL_SECONDS)

    def _fetch_premium_index(self) -> list[dict]:
        req = urllib.request.Request(
            PREMIUM_INDEX_URL,
            method="GET",
            headers={"User-Agent": "Mozilla/5.0 RoboSpread/1.0"},
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            payload = json.loads(resp.read())
        data = payload.get("data") or []
        if not isinstance(data, list):
            return []
        return data

    def _handle_items(self, items: list[dict]):
        default_fih = EXCHANGES[self.exchange_id]["default_funding_interval_h"]
        updated = 0
        for item in items:
            native = item.get("symbol")
            canonical = self.to_canonical(native) if native else None
            if not canonical:
                continue
            try:
                mark_price = float(item.get("markPrice") or 0.0)
            except (TypeError, ValueError):
                continue
            if mark_price <= 0:
                continue

            fr_raw = item.get("lastFundingRate")
            try:
                funding_rate = float(fr_raw) if fr_raw is not None else None
            except (TypeError, ValueError):
                funding_rate = None

            nft_raw = item.get("nextFundingTime")
            try:
                next_funding_time = float(nft_raw) / 1000.0 if nft_raw else None
            except (TypeError, ValueError):
                next_funding_time = None

            fih_raw = item.get("fundingIntervalHours")
            try:
                funding_interval_h = float(fih_raw) if fih_raw is not None else default_fih
            except (TypeError, ValueError):
                funding_interval_h = default_fih

            state.update_leg(
                self.exchange_id,
                canonical,
                mark_price,
                funding_rate=funding_rate,
                next_funding_time=next_funding_time,
                funding_interval_h=funding_interval_h,
            )
            updated += 1
        logger.debug(f"[{self.name}] Updated {updated} legs")
