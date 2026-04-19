import json
import logging

import websockets

from config import EXCHANGES
from exchange.base import ExchangeWS
from engine.state import state
from exchange.aster_discovery import aster_interval_map

logger = logging.getLogger(__name__)


class AsterWS(ExchangeWS):
    """Aster Futures `!markPrice@arr@1s` stream.

    Aster is a Binance-fapi fork — mark-price tick format is byte-identical
    to Binance: `{e,E,s,p,P,i,r,T}` per item, combined-stream envelope
    `{"stream":..., "data":[...]}`. Funding interval is NOT on the tick,
    so we attach `funding_interval_h` from the discovery cache (see
    `aster_discovery.discover_aster`).

    Server pings every 5m, disconnects after 15m silence; the websockets
    library auto-pongs, so `ping_interval=None` is fine here.
    """

    exchange_id = "aster"

    async def connect(self):
        url = EXCHANGES[self.exchange_id]["ws_url"]
        logger.info(f"[Aster] Connecting to {url}")

        async with websockets.connect(url, ping_interval=None) as ws:
            logger.info("[Aster] Connected. Streaming mark prices...")
            intervals = aster_interval_map()

            async for raw in ws:
                try:
                    msg = json.loads(raw)
                except (ValueError, TypeError):
                    continue
                data = msg.get("data")
                if not isinstance(data, list):
                    continue
                for item in data:
                    native = item.get("s")
                    canonical = self.to_canonical(native) if native else None
                    if not canonical:
                        continue
                    try:
                        mark_price = float(item.get("p") or 0)
                    except (TypeError, ValueError):
                        continue
                    if mark_price <= 0:
                        continue
                    try:
                        funding_rate = float(item.get("r") or 0)
                    except (TypeError, ValueError):
                        funding_rate = 0.0
                    nft_ms = item.get("T")
                    try:
                        nft = int(nft_ms) / 1000 if nft_ms else None
                    except (TypeError, ValueError):
                        nft = None
                    fih = intervals.get(canonical)

                    state.update_leg(
                        self.exchange_id,
                        canonical,
                        mark_price,
                        funding_rate=funding_rate,
                        funding_interval_h=fih,
                        next_funding_time=nft,
                    )
