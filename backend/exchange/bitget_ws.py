import logging

from exchange.cex_ws_base import CexWSBase
from exchange.bitget_discovery import bitget_interval_map
from engine.state import state

logger = logging.getLogger(__name__)


class BitgetWS(CexWSBase):
    """Bitget v2 public futures ticker stream.

    Subscribe: {"op":"subscribe","args":[{"instType":"USDT-FUTURES","channel":"ticker","instId":"BTCUSDT"}]}
    Keepalive: plain-text "ping" every 30s, server replies "pong". Two minutes
    without a ping → server disconnects.

    Ticker push fields used: instId, markPrice, fundingRate, nextFundingTime.
    Bitget does NOT advertise the funding interval on the ticker channel, so we
    pull the per-symbol `fundInterval` from the REST contracts endpoint during
    discovery and attach it on every update. That value is the live, exchange-
    reported interval — never the config default.
    """

    exchange_id = "bitget"
    ping_interval_sec = 20.0
    ping_message = "ping"
    pong_message = "pong"

    def _subscribe_arg(self, native: str) -> dict:
        return {
            "instType": "USDT-FUTURES",
            "channel": "ticker",
            "instId": native,
        }

    async def _handle_message(self, msg: dict):
        arg = msg.get("arg") or {}
        if arg.get("channel") != "ticker":
            return
        for item in msg.get("data") or []:
            native = item.get("instId")
            canonical = self.to_canonical(native) if native else None
            if not canonical:
                continue

            mark = item.get("markPrice") or item.get("lastPr")
            try:
                mark_price = float(mark) if mark is not None else 0.0
            except (TypeError, ValueError):
                continue
            if mark_price <= 0:
                continue

            funding_rate = item.get("fundingRate")
            try:
                funding_rate = float(funding_rate) if funding_rate is not None else None
            except (TypeError, ValueError):
                funding_rate = None

            next_funding_ms = item.get("nextFundingTime")
            try:
                nft = float(next_funding_ms) / 1000 if next_funding_ms else None
            except (TypeError, ValueError):
                nft = None

            fih = bitget_interval_map().get(canonical)

            state.update_leg(
                self.exchange_id,
                canonical,
                mark_price,
                funding_rate=funding_rate,
                next_funding_time=nft,
                funding_interval_h=fih,
            )
