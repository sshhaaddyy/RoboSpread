"""WhiteBIT connector — Archetype 5 (pure REST poll on bulk endpoint).

WhiteBIT's `/api/v4/public/futures` returns an array of all perp contracts,
each carrying:
    ticker_id, stock_currency, money_currency, index_price,
    funding_rate, next_funding_rate_timestamp (ms),
    funding_interval_minutes (per-symbol!)
— one HTTP call covers every symbol. No per-symbol WS subs, no funding
poll split.

Important compromise: WhiteBIT's public REST does NOT expose mark price.
We use `index_price` as a mark-price proxy. For arb detection this is
safe — mark = index + f(funding_basis), and the basis is typically
single-digit bps. If WhiteBIT later exposes a dedicated mark-price
endpoint/channel, swap it in here.
"""
import asyncio
import json
import logging
import urllib.request

from config import EXCHANGES
from engine.state import state
from exchange.base import ExchangeWS

logger = logging.getLogger(__name__)

FUTURES_URL = "https://whitebit.com/api/v4/public/futures"
POLL_SECONDS = 3.0


class WhitebitWS(ExchangeWS):
    exchange_id = "whitebit"

    async def connect(self):
        logger.info(f"[{self.name}] Polling {FUTURES_URL} every {POLL_SECONDS}s for {len(self.native_symbols)} symbols")
        while True:
            try:
                items = await asyncio.to_thread(self._fetch_futures)
            except Exception as e:
                logger.error(f"[{self.name}] futures fetch failed: {e}")
                await asyncio.sleep(POLL_SECONDS)
                continue
            self._handle_items(items)
            await asyncio.sleep(POLL_SECONDS)

    def _fetch_futures(self) -> list[dict]:
        req = urllib.request.Request(
            FUTURES_URL,
            method="GET",
            headers={"User-Agent": "Mozilla/5.0 RoboSpread/1.0"},
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            payload = json.loads(resp.read())
        if not payload.get("success"):
            return []
        data = payload.get("result") or []
        if not isinstance(data, list):
            return []
        return data

    def _handle_items(self, items: list[dict]):
        default_fih = EXCHANGES[self.exchange_id]["default_funding_interval_h"]
        updated = 0
        for item in items:
            native = item.get("ticker_id")
            canonical = self.to_canonical(native) if native else None
            if not canonical:
                continue

            # index_price as mark proxy (see module docstring).
            try:
                mark_price = float(item.get("index_price") or 0.0)
            except (TypeError, ValueError):
                continue
            if mark_price <= 0:
                continue

            fr_raw = item.get("funding_rate")
            try:
                funding_rate = float(fr_raw) if fr_raw is not None else None
            except (TypeError, ValueError):
                funding_rate = None

            nft_raw = item.get("next_funding_rate_timestamp")
            try:
                next_funding_time = float(nft_raw) / 1000.0 if nft_raw else None
            except (TypeError, ValueError):
                next_funding_time = None

            fim_raw = item.get("funding_interval_minutes")
            try:
                funding_interval_h = float(fim_raw) / 60.0 if fim_raw else default_fih
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
