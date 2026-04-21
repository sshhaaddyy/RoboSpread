"""
Connector template — DO NOT import this file. It is not a live connector.

Copy this to `<exchange_id>_ws.py` and delete the archetypes you don't need.
Agreed via /model-chat 2026-04-21: the template lives in the codebase (not
in a skill prompt) so it drifts naturally as the connector pattern evolves.

5 archetypes seen in the wild — pick the closest fit:

    Archetype 1: BULK STREAM (Binance, Aster)
        One WS subscription pushes all symbols every ~1s in a
        {stream, data:[...]} envelope. Inherit ExchangeWS directly.
        Reference: backend/exchange/aster_ws.py

    Archetype 2: CEX op/args PER-SYMBOL (Bitget, Gate)
        {"op":"subscribe","args":[...]} with one arg per symbol.
        Inherit CexWSBase — it handles reconnect, batching, app ping,
        control-frame filtering. Override `_subscribe_arg(native)`,
        `_handle_message(msg)`, optionally `_is_control_message`.
        Reference: backend/exchange/gate_ws.py

    Archetype 3: BULK STREAM + REST FUNDING POLL (MEXC, Hyperliquid)
        WS pushes mark prices; funding rate/interval/next-settlement come
        from a 30s REST poll. Two asyncio tasks in connect(). Funding
        updates MUST route through state.update_leg(...) with the last
        known mark price — do not write leg attributes directly.
        Reference: backend/exchange/mexc_ws.py

    Archetype 4: DUAL-CHANNEL WS + RUNTIME-DERIVED INTERVAL (OKX)
        Two WS channels per symbol (e.g. mark-price + funding-rate).
        Override `_build_subscribe_message(batch)` for 2N args per batch.
        Funding interval NOT published by REST; derive from WS payload
        (fundingTime − prevFundingTime) / 3_600_000 and cache per symbol.
        Reference: backend/exchange/okx_ws.py

    Archetype 5: PURE REST POLL ON BULK ENDPOINT (BingX, WhiteBIT)
        The venue exposes one REST endpoint that returns EVERY perp in
        one call with mark + funding rate + funding interval +
        next-funding-time per row. No WS involved. `connect()` is a
        `while True: fetch → parse → sleep` loop. Inherit ExchangeWS;
        the base's run_forever() still handles reconnect on fatal errors.
        Pick this when WS would require per-symbol sub sharding (KuCoin-
        style) but REST gives you everything in one call under rate limits.
        Reference: backend/exchange/bingx_ws.py

Common rules for every archetype:
    • Set `exchange_id` to match the EXCHANGES registry key.
    • Canonicalize via `self.to_canonical(native)` — base class holds the
      {canonical: native} dict from pair_discovery.
    • Always guard `if mark_price <= 0: continue` before update_leg.
    • Pass funding_rate / funding_interval_h / next_funding_time to
      state.update_leg on every tick where available. Do NOT write to
      leg attributes directly — that skips route recomputation.
    • Prefer predicted/indicative funding over last-paid when the venue
      ships both (Gate: funding_rate_indicative > funding_rate).
"""
import asyncio
import json
import logging

from exchange.base import ExchangeWS
from exchange.cex_ws_base import CexWSBase
from engine.state import state

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════
# Archetype 2 template (most common). Delete the others when copying.
# ═══════════════════════════════════════════════════════════════════════
class TemplateCexWS(CexWSBase):
    """Rename to <Exchange>WS. Delete this archetype if not applicable."""

    exchange_id = ""  # REQUIRED — match an EXCHANGES key.

    # Ping model. Pick ONE:
    #   (a) app-level string ping (Bitget, OKX): enable_app_ping=True + ping_message/pong_message
    #   (b) protocol ping (most CEXes): enable_app_ping=False + websocket_ping_interval=20
    enable_app_ping = True
    ping_interval_sec = 20.0
    ping_message = "ping"
    pong_message = "pong"

    sub_batch_size = 20
    subscribe_op = "subscribe"

    def _subscribe_arg(self, native: str) -> dict:
        # Single-channel per symbol. For multi-channel (Archetype 4),
        # override _build_subscribe_message instead.
        return {"channel": "<channel>", "instId": native}

    async def _handle_message(self, msg: dict):
        # Walk msg["data"] (or vendor-specific field), canonicalize each
        # item, guard mark > 0, call state.update_leg.
        data = msg.get("data") or []
        for item in data:
            native = item.get("<native-key>")
            canonical = self.to_canonical(native) if native else None
            if not canonical:
                continue
            try:
                mark_price = float(item.get("<mark-key>") or 0.0)
            except (TypeError, ValueError):
                continue
            if mark_price <= 0:
                continue
            state.update_leg(
                self.exchange_id,
                canonical,
                mark_price,
                funding_rate=None,           # fill if on-stream
                next_funding_time=None,      # fill if on-stream (seconds since epoch)
                funding_interval_h=None,     # fill from discovery cache or runtime derivation
            )


# ═══════════════════════════════════════════════════════════════════════
# Archetype 4 — dual-channel + runtime-derived interval (OKX-style).
# ═══════════════════════════════════════════════════════════════════════
class TemplateDualChannelWS(CexWSBase):
    """Two channels per symbol. Funding interval derived at runtime from
    consecutive `fundingTime` fields, not from REST discovery.
    Reference implementation: backend/exchange/okx_ws.py."""

    exchange_id = ""
    sub_batch_size = 30  # 2 args per symbol → 60 args per subscribe

    def __init__(self, native_symbols):
        super().__init__(native_symbols)
        self._fr_cache: dict[str, float] = {}
        self._nft_cache: dict[str, float] = {}
        self._interval_cache: dict[str, float] = {}

    def _build_subscribe_message(self, batch: list[str]) -> str:
        args: list[dict] = []
        for native in batch:
            args.append({"channel": "<mark-channel>", "instId": native})
            args.append({"channel": "<funding-channel>", "instId": native})
        return json.dumps({"op": "subscribe", "args": args})

    async def _handle_message(self, msg: dict):
        channel = (msg.get("arg") or {}).get("channel")
        if channel == "<funding-channel>":
            # Cache fr + nft; derive interval from fundingTime − prevFundingTime.
            pass
        elif channel == "<mark-channel>":
            # Call state.update_leg with cached funding triple.
            pass


# ═══════════════════════════════════════════════════════════════════════
# Archetype 3 — bulk stream + REST funding poll (MEXC-style).
# ═══════════════════════════════════════════════════════════════════════
class TemplateBulkPlusPollWS(ExchangeWS):
    """WS pushes marks; a background asyncio task polls funding REST."""

    exchange_id = ""

    async def _funding_poll_loop(self):
        while True:
            # Fetch funding rates via REST, call state.update_leg for each
            # symbol using the LAST KNOWN mark_price (read from the leg).
            # Do NOT write leg.funding_rate directly — goes via update_leg
            # so best_arb / best_funding recompute.
            await asyncio.sleep(30)

    async def connect(self):
        poll_task = asyncio.create_task(self._funding_poll_loop())
        try:
            # Open WS, read ticks, call state.update_leg on each mark.
            pass
        finally:
            poll_task.cancel()
