---
name: add-exchange
description: Scaffold a new exchange connector into RoboSpread. Use when the user asks to "add <exchange>" or "integrate <venue>". Scaffold ONLY — run /verify-exchange afterward to confirm it works.
---

# Adding an exchange to RoboSpread

Distilled from Phase 3 (Hyperliquid) through Phase 13 (OKX) and the
2026-04-21 /model-chat redesign. This skill scaffolds the connector.
**Verification is a separate skill** — run `/verify-exchange <id>` after
wiring to catch the silent footguns.

The concrete connector template lives at `backend/exchange/_template_ws.py`
(not a skill prompt — the pragmatist's argument from the debate:
codebase-resident files drift with the code).

## Step 0 — probe before writing code

Every integration failure so far came from trusting docs instead of the wire:

- `curl` the contract/exchangeInfo endpoint. Confirm: native symbol shape,
  quote asset filter, active/trading status field name, whether funding
  interval is on contract metadata or requires a second call.
- **Check for User-Agent blocking.** OKX (and some Cloudflare-fronted
  venues) 403 on Python's default `Python-urllib/3.x`. If the curl works
  but `urllib.request.urlopen` 403s, set
  `headers={"User-Agent": "Mozilla/5.0 RoboSpread/1.0"}`.
- Open the WS with a throwaway probe; log 2-3 messages. Inspect which
  fields are on the tick vs. missing. Specifically check: does the ticker
  carry `funding_rate` + `funding_interval` + `next_funding_time`? Any
  absence changes the archetype.
- **Check geoblocks.** If the exchange geoblocks your region (Kraken
  Futures, Deribit mark channel for US), discovery may 451/403 even with
  a UA. Flag before coding — might need to drop the venue rather than
  fight it.

## Step 1 — choose an archetype (5 patterns)

Pick the closest fit. Reference implementation listed for each:

1. **Bulk stream, Binance-style** — one WS subscription pushes all symbols
   every ~1s in `{stream, data:[...]}`. Inherit `ExchangeWS` directly.
   Ref: `backend/exchange/aster_ws.py`. Used by: Binance, Aster.

2. **Per-symbol op/args CEX** — `{"op":"subscribe","args":[...]}`, one
   arg per symbol, batched. Inherit `CexWSBase`. Override
   `_subscribe_arg(native)`, `_handle_message(msg)`, optionally
   `_is_control_message(msg)`. Ref: `backend/exchange/gate_ws.py`.
   Used by: Bitget, Gate.

3. **Bulk stream + REST funding poll** — WS pushes marks; funding
   rate/interval/next-settle come from a 30s REST poller. Two asyncio
   tasks in `connect()`. **Route funding updates through
   `state.update_leg(...)` with the last-known mark price**, never write
   leg attributes directly. Ref: `backend/exchange/mexc_ws.py`. Used by:
   MEXC, Hyperliquid.

4. **Dual-channel WS + runtime-derived interval** (OKX).
   Two channels per symbol (mark-price + funding-rate). Override
   `_build_subscribe_message(batch)` to emit 2N args per batch.
   Funding interval is **not** on REST — derive from
   `(fundingTime − prevFundingTime) / 3_600_000` on each funding-rate
   push. Cache `_fr_cache`, `_nft_cache`, `_interval_cache` at module
   level keyed by canonical symbol. Ref: `backend/exchange/okx_ws.py`.
   Used by: OKX.

5. **Pure REST poll on bulk endpoint** (NEW — BingX, WhiteBIT). The
   venue exposes ONE endpoint that returns every perp with mark /
   funding rate / funding interval / next-funding-time per row. No WS,
   no sharding, no per-symbol subs. `connect()` = `while True: fetch →
   parse → sleep 3s`. Inherit `ExchangeWS`. Pick this when
   per-symbol WS would require KuCoin-style sharding but REST gives
   you everything under the rate cap. Typical rate-limit math: ~0.33
   req/s easily fits under 100 req/10s public-IP limits.
   Ref: `backend/exchange/bingx_ws.py`. Used by: BingX, WhiteBIT.

## Step 2 — clone the template

```bash
cp backend/exchange/_template_ws.py backend/exchange/<id>_ws.py
```

The template is a commented reference with stubs for archetypes 2, 3,
and 4. Delete the archetypes you don't need. For archetype 1 (bulk
stream) clone from `aster_ws.py` instead — Binance-style envelopes are
simpler than the CEX base.

## Step 3 — discovery module (`<id>_discovery.py`)

- Fetch via `urllib.request` (sync — discovery runs once at startup).
  Timeout 15s. On failure log and return `{}` — never raise.
- **Always set a browser User-Agent.** OKX 403s without one.
- Filter to **USDT-margined**, **trading/active**, **non-delisted** perps.
  Exclude hidden, pre-market, settling. For venues with multiple
  settlement currencies (Hyperliquid USDC/USDH/USDE/USDT0, OKX USDC),
  pick ONE and document the choice.
- Return `dict[canonical: native]`. Canonical is Binance-style `BTCUSDT`.
  Transform `BTC_USDT`, `kPEPE`, `BTC-USDT-SWAP` here — never scatter
  symbol rewrites across the codebase.
- If the ticker stream omits funding interval (Bitget, Gate, Aster):
  fetch it here and expose a module-level `_interval_cache` +
  setter/getter. The WS connector reads from this cache per tick.
- If next-funding-time isn't on the stream (Gate): seed a
  `_next_apply_cache` and add `current_next_funding(canonical)` that
  advances by `interval_h` whenever `now >= seed`.

## Step 4 — wire-up checklist

Every file must be touched. Missing any one silently hides the venue:

1. **`backend/config.py`** — add `EXCHANGES["<id>"]` entry. Required keys:
   `id, name, short_name, icon, color, letter, maker_fee, taker_fee,
   fee_source_url, default_funding_interval_h, ws_url`.
   - Fees are **percent** (0.04 = 0.04%).
   - `fee_source_url` is **enforced at import time** by
     `ExchangeWS.__init_subclass__` — backend refuses to start without it.
     The URL must be the public fee page you copied the numbers from.
     Do NOT invent fee values from memory.
   - `icon`: prefer `https://assets.coingecko.com/markets/images/<id>/small/...`
     (look up the venue on coingecko.com/en/exchanges; the image URL is
     on the page). If no coingecko listing, skip the icon rather than
     guess — the frontend falls back to the `letter` badge.
2. **`backend/exchange/pair_discovery.py`** — import discovery fn, add to
   `_DISCOVERY_FUNCS`. If discovery has side-effect caches, wrap it:
   ```python
   def _discover_X_wrapped():
       natives, intervals = discover_X()
       _X_set_intervals(intervals)
       return natives
   ```
3. **`backend/main.py`** — import the WS class, append one line to the
   `connectors` list in `startup()`.
4. **`backend/exchange/history.py`** — THREE edits in this one file:
   - `_get_client`: add ccxt branch (or a native kline fetcher like
     `_fetch_aster_klines` if ccxt has no adapter).
   - `_ccxt_symbol`: add the exchange id to the tuple for the
     `"BTC/USDT:USDT"` format (most CEXes) or add a custom branch.
   - `_fetch_ohlcv`: add to the mark-price-params tuple if the venue
     supports `params={"price": "mark"}` on OHLCV. If not, it silently
     returns last-price klines — document it.

## Step 5 — verify (separate skill)

Run `/verify-exchange <id>` or directly:

```bash
cd backend && ./venv/bin/python -m scripts.verify_exchange <id> --seconds 60
```

This boots just your connector, streams 60s, and asserts all four leg
fields (`mark_price`, `funding_rate`, `funding_interval_h`,
`next_funding_time`) are populated on BTCUSDT. It also flags the #1
footgun: every symbol stuck on the default 8h interval (= your
discovery cache isn't wired).

Do NOT commit until verify passes.

## Step 6 — changelog + commit

- **Filename is `changelog.md` (lowercase).** There is no `CHANGELOG.md`
  — check with `ls` before appending, not before sure. Phase numbering:
  `grep -c "^## Phase" changelog.md` for the next N, or read the last
  `## Phase` header.
- Phase entry must include: discovery URL, WS URL, subscribe shape,
  tick field list, fees tier (with source URL), count of perps + legs,
  any non-obvious quirk from step 0.
- Commit message: `Phase <N>: <Exchange> connector` + 2-3 line body.

## Pitfalls seen so far

- **OKX / Cloudflare 403 on Python UA**: set
  `User-Agent: Mozilla/5.0 RoboSpread/1.0` on every `urllib.request`.
- **Multi-channel per symbol**: OKX needs 2 args per symbol (mark +
  funding). Override `_build_subscribe_message(batch)`, not
  `_subscribe_arg`. Halve `sub_batch_size` since args-per-batch doubles.
- **Fees from memory**: invented OKX 0.05/0.02 in Phase 13 with no
  source URL. The `fee_source_url` gate now blocks this at import.
- **Symbol-space quirks**:
  - USDC-settled perps (Hyperliquid, some OKX): skip or treat as a
    separate venue — we track USDT-margined only.
  - Dated contracts (Binance quarterlies, BitMEX XBTM25): skip in
    discovery filter.
  - Inverse perps (`BTCUSD_PERP`): skip — we compute USDT-linear edges.
  - `1000XXX` (Binance/Bybit) vs `kXXX` (Hyperliquid) for 1000×
    wrappers — normalize in discovery, not in the connector.
- **Port 8000 in use**: `lsof -ti :8000 | xargs kill -9`.
- **Empty log tail**: use `python -u`; read the log file with the Read
  tool, not a background tail.
- **Writing to `leg.funding_rate` directly** from a REST poller skips
  route recomputation. Always go through `state.update_leg(...)`.
- **Per-symbol subscribe for 800+ MEXC symbols**: don't. Use MEXC's
  `sub.tickers` (plural, no arg) bulk channel.
- **Assumed fields that aren't on the wire**: Gate's ticker does NOT
  include `funding_next_apply`. MEXC's `contract/detail` does NOT
  include `fundingInterval`. Probe before coding.

## Known-unresolved (from the 2026-04-21 model-chat)

- **Geoblocked-venue fallback**: no concrete mechanism. If the exchange
  geoblocks your IP, abandon the integration for now.
- **Fee URL content verification**: the `__init_subclass__` gate checks
  for a URL, not that the URL still shows the declared rates. Manual
  periodic review only.
