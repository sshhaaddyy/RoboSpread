import json
import logging

from exchange.cex_ws_base import CexWSBase
from engine.state import state

logger = logging.getLogger(__name__)


class OkxWS(CexWSBase):
    """OKX v5 public SWAP stream.

    OKX splits the data across two channels that both need to be subscribed:
      - `mark-price`   → frequent push of `markPx` (few ticks/sec per symbol)
      - `funding-rate` → push on settlement / rate change; includes fundingRate,
                        fundingTime (the NEXT settlement), prevFundingTime
                        (from which we derive the per-symbol interval).

    Subscribe envelope is default op/args with two args per symbol:
        {"op":"subscribe","args":[
            {"channel":"mark-price","instId":"BTC-USDT-SWAP"},
            {"channel":"funding-rate","instId":"BTC-USDT-SWAP"}, ...]}

    Keepalive: literal "ping"/"pong" every 20s (CexWSBase default). OKX
    disconnects after 30s of silence.

    Funding is kept in a module-level cache keyed by canonical symbol. Every
    mark-price tick calls state.update_leg with the cached funding triple
    (or None if the first funding-rate message for that symbol hasn't
    arrived yet) — this matches how Bitget/Gate feed funding via a
    discovery-time cache, except OKX's cache is populated at runtime from
    the WS rather than from REST at startup.
    """

    exchange_id = "okx"
    ping_interval_sec = 20.0
    ping_message = "ping"
    pong_message = "pong"
    sub_batch_size = 30  # 60 args per subscribe message (mark + funding per symbol)

    def __init__(self, native_symbols):
        super().__init__(native_symbols)
        self._fr_cache: dict[str, float] = {}
        self._nft_cache: dict[str, float] = {}
        self._interval_cache: dict[str, float] = {}

    def _build_subscribe_message(self, batch: list[str]) -> str:
        args: list[dict] = []
        for native in batch:
            args.append({"channel": "mark-price", "instId": native})
            args.append({"channel": "funding-rate", "instId": native})
        return json.dumps({"op": "subscribe", "args": args})

    def _is_control_message(self, msg: dict) -> bool:
        # OKX data frames have `arg` + `data` and no `event`. Ack/error frames
        # carry `event`. The base-class default (`"event" in msg or "op" in msg`)
        # already handles this correctly.
        return "event" in msg or "op" in msg

    async def _handle_message(self, msg: dict):
        arg = msg.get("arg") or {}
        channel = arg.get("channel")
        data = msg.get("data") or []

        if channel == "funding-rate":
            for item in data:
                native = item.get("instId")
                canonical = self.to_canonical(native) if native else None
                if not canonical:
                    continue

                fr = item.get("fundingRate")
                try:
                    if fr not in (None, ""):
                        self._fr_cache[canonical] = float(fr)
                except (TypeError, ValueError):
                    pass

                ft = item.get("fundingTime")
                try:
                    if ft not in (None, ""):
                        self._nft_cache[canonical] = float(ft) / 1000.0
                except (TypeError, ValueError):
                    pass

                pft = item.get("prevFundingTime")
                try:
                    if ft not in (None, "") and pft not in (None, ""):
                        interval_s = (float(ft) - float(pft)) / 1000.0
                        if interval_s > 0:
                            self._interval_cache[canonical] = interval_s / 3600.0
                except (TypeError, ValueError):
                    pass
            return

        if channel == "mark-price":
            for item in data:
                native = item.get("instId")
                canonical = self.to_canonical(native) if native else None
                if not canonical:
                    continue

                mark = item.get("markPx")
                try:
                    mark_price = float(mark) if mark is not None else 0.0
                except (TypeError, ValueError):
                    continue
                if mark_price <= 0:
                    continue

                state.update_leg(
                    self.exchange_id,
                    canonical,
                    mark_price,
                    funding_rate=self._fr_cache.get(canonical),
                    next_funding_time=self._nft_cache.get(canonical),
                    funding_interval_h=self._interval_cache.get(canonical),
                )
