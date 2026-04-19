import asyncio
import json
import logging
import time

import aiohttp
import websockets

from config import EXCHANGES, HYPERLIQUID_FUNDING_POLL_SEC
from exchange.base import ExchangeWS
from engine.state import state

logger = logging.getLogger(__name__)


class HyperliquidWS(ExchangeWS):
    """Streams mid prices from Hyperliquid's `allMids` WS channel and polls the
    `info` REST endpoint for funding rates. Funding only changes hourly, so 30s
    polling is plenty — no need for an extra WS subscription per symbol.

    Symbol mapping: HL uses bare bases (BTC) and a `kXXX` prefix for 1000x
    wrappers. `pair_discovery` gives us {canonical: native} so we translate
    both directions here.
    """

    exchange_id = "hyperliquid"

    async def _funding_poll(self):
        info_url = EXCHANGES[self.exchange_id]["info_url"]
        interval_h = EXCHANGES[self.exchange_id]["default_funding_interval_h"]
        async with aiohttp.ClientSession() as session:
            while True:
                try:
                    async with session.post(
                        info_url,
                        json={"type": "metaAndAssetCtxs"},
                        timeout=aiohttp.ClientTimeout(total=15),
                    ) as resp:
                        resp.raise_for_status()
                        payload = await resp.json()

                    meta, asset_ctxs = payload[0], payload[1]
                    universe = meta.get("universe", [])
                    for i, coin in enumerate(universe):
                        if i >= len(asset_ctxs):
                            break
                        native = coin.get("name", "")
                        canonical = self.to_canonical(native)
                        if not canonical:
                            continue
                        ctx = asset_ctxs[i]
                        try:
                            funding_rate = float(ctx.get("funding") or 0)
                        except (TypeError, ValueError):
                            funding_rate = 0.0
                        try:
                            mark_px = float(ctx.get("markPx") or 0)
                        except (TypeError, ValueError):
                            mark_px = 0.0

                        # HL funding pays hourly on the hour.
                        now = time.time()
                        next_hour = (int(now // 3600) + 1) * 3600

                        if mark_px > 0:
                            state.update_leg(
                                self.exchange_id,
                                canonical,
                                mark_px,
                                funding_rate=funding_rate,
                                next_funding_time=float(next_hour),
                                funding_interval_h=float(interval_h),
                            )
                except Exception as e:
                    logger.warning(f"[Hyperliquid] funding poll error: {e}")
                await asyncio.sleep(HYPERLIQUID_FUNDING_POLL_SEC)

    async def connect(self):
        url = EXCHANGES[self.exchange_id]["ws_url"]
        logger.info(f"[Hyperliquid] Connecting to {url}")

        async with websockets.connect(url, ping_interval=20) as ws:
            await ws.send(json.dumps({
                "method": "subscribe",
                "subscription": {"type": "allMids"},
            }))
            logger.info(
                f"[Hyperliquid] Subscribed to allMids; tracking {len(self.symbols)} symbols"
            )

            poll_task = asyncio.create_task(self._funding_poll())

            try:
                async for raw_msg in ws:
                    try:
                        msg = json.loads(raw_msg)
                        if msg.get("channel") != "allMids":
                            continue
                        mids = msg.get("data", {}).get("mids", {})
                        for native, price_str in mids.items():
                            canonical = self.to_canonical(native)
                            if not canonical:
                                continue
                            try:
                                price = float(price_str)
                            except (TypeError, ValueError):
                                continue
                            if price > 0:
                                state.update_leg(
                                    self.exchange_id,
                                    canonical,
                                    price,
                                )
                    except Exception as e:
                        logger.error(f"[Hyperliquid] Parse error: {e}")
            finally:
                poll_task.cancel()
