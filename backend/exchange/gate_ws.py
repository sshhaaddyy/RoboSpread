import json
import logging
import time

from exchange.cex_ws_base import CexWSBase
from exchange.gate_discovery import gate_interval_map, current_next_funding
from engine.state import state

logger = logging.getLogger(__name__)


class GateWS(CexWSBase):
    """Gate.io v4 USDT-futures public WebSocket.

    Subscribe shape (different from the op/args default):
        {"time": <unix>, "channel": "futures.tickers",
         "event": "subscribe", "payload": ["BTC_USDT", ...]}

    Ticker push fields used: contract, mark_price, funding_rate. Gate's stream
    does NOT include `funding_interval` or `funding_next_apply`, so we read
    both from `/api/v4/futures/usdt/contracts` at discovery and advance the
    next-apply forward algorithmically per-tick (see gate_discovery).
    Update envelope:
        {"time":..., "channel":"futures.tickers", "event":"update", "result":[...]}

    Keepalive: Gate uses protocol-level WebSocket pings (server-driven). The
    websockets library auto-responds, so no app-level ping loop is needed.
    """

    exchange_id = "gate"
    enable_app_ping = False
    websocket_ping_interval = 20.0
    sub_batch_size = 100  # Gate accepts large payload arrays per subscribe

    def _build_subscribe_message(self, batch: list[str]) -> str:
        return json.dumps({
            "time": int(time.time()),
            "channel": "futures.tickers",
            "event": "subscribe",
            "payload": batch,
        })

    def _is_control_message(self, msg: dict) -> bool:
        # Gate data frames carry event="update"; only ack/error are control.
        return msg.get("event") in ("subscribe", "unsubscribe", "error")

    async def _handle_message(self, msg: dict):
        if msg.get("channel") != "futures.tickers":
            return
        result = msg.get("result") or []
        if isinstance(result, dict):
            result = [result]

        for item in result:
            native = item.get("contract")
            canonical = self.to_canonical(native) if native else None
            if not canonical:
                continue

            mark = item.get("mark_price") or item.get("last")
            try:
                mark_price = float(mark) if mark is not None else 0.0
            except (TypeError, ValueError):
                continue
            if mark_price <= 0:
                continue

            try:
                funding_rate = float(item["funding_rate"]) if "funding_rate" in item else None
            except (TypeError, ValueError):
                funding_rate = None

            fih = gate_interval_map().get(canonical)
            nft = current_next_funding(canonical)

            state.update_leg(
                self.exchange_id,
                canonical,
                mark_price,
                funding_rate=funding_rate,
                next_funding_time=nft,
                funding_interval_h=fih,
            )
