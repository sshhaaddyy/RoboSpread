---
name: add-exchange
description: Wire a new exchange connector into RoboSpread (REST discovery → WS connector → config → pair_discovery → history → CHANGELOG). Use when the user asks to "add <exchange>" or "integrate <venue>".
---

# Adding an exchange to RoboSpread

Distilled from wiring Hyperliquid, Bitget, Gate, MEXC, and Aster. Skip steps
you've verified are irrelevant for the target venue — but touch every file
listed under "wire-up checklist" or the exchange won't appear at startup.

## Step 0 — investigate before writing code

Probe the venue's API **before** writing any files. Every mistake so far
came from trusting docs instead of the wire:

- `curl` the contract/exchangeInfo endpoint. Confirm native symbol format,
  quote asset filter, active/trading status field, and whether funding
  interval lives on the contract metadata or requires a second call.
- Open the WS with a throwaway Python probe (see `backend/exchange/aster_ws.py`
  probe snippet in commit history). Log 2-3 messages and inspect which fields
  are on the tick vs. missing.
- Specifically check: does the ticker carry `funding_rate` + `funding_interval`
  + `next_funding_time`? If any are absent, plan a REST discovery cache
  (Bitget pattern) or a REST poller (MEXC pattern) or an algorithmic advance
  (Gate's `current_next_funding` pattern).

## Step 1 — choose a connector archetype

Three patterns exist; pick the closest fit:

1. **Bulk stream, Binance-style** (Binance, Aster): one WS subscription pushes
   all symbols every 1s in `{stream, data:[...]}` envelope. Inherit
   `ExchangeWS`, not `CexWSBase`. Reference: `backend/exchange/aster_ws.py`.

2. **Per-symbol op/args CEX** (Bitget, Gate): subscribe with
   `{"op":"subscribe","args":[...]}` or a payload-array equivalent, one
   arg per symbol, batched. Inherit `CexWSBase` — it handles reconnect,
   batching, app-level ping, control-frame filtering. Override hooks:
   `_subscribe_arg(native)`, `_build_subscribe_message(batch)` (only if
   the envelope differs from op/args), `_is_control_message(msg)`,
   `_handle_message(msg)`. Reference: `backend/exchange/gate_ws.py`.

3. **Bulk stream + REST funding poll** (MEXC, Hyperliquid): WS pushes mark
   prices in a single bulk channel; funding rate / interval / next-settle
   come from a 30s REST poll. Two asyncio background tasks inside
   `connect()`. **Route funding updates through `state.update_leg()` with
   the last-known mark price** so `best_arb` / `best_funding` recompute
   on each poll — don't write leg attributes directly. Reference:
   `backend/exchange/mexc_ws.py`.

## Step 2 — discovery module (`<exchange>_discovery.py`)

- Fetch via `urllib.request` (sync, no aiohttp — discovery runs once at
  startup). Timeout 15s. Log and return `{}` on failure; never raise.
- Filter to **USDT-margined**, **trading/active**, **non-delisted** perps.
  Exclude hidden/pre-market/settling listings.
- Return `dict[canonical: native]`. Canonical is Binance-style `BTCUSDT`.
  If the venue uses `BTC_USDT` or `kPEPE`, transform here — never scatter
  symbol rewrites across the codebase.
- **If the ticker stream omits funding interval** (Bitget, Gate, Aster):
  fetch it in discovery and expose a module-level `_interval_cache` plus
  setter/getter. The WS connector will read from this cache per tick.
- **If next-funding-time isn't on the stream** (Gate): seed a
  `_next_apply_cache` at discovery and add a `current_next_funding(canonical)`
  helper that advances forward by `interval_h` whenever `now >= seed`.

## Step 3 — WS connector module (`<exchange>_ws.py`)

- Set `exchange_id` to match the `EXCHANGES` key. Never use free strings.
- Canonicalize with `self.to_canonical(native)` — base class handles the
  {canonical:native} dict that `pair_discovery` produces.
- Always guard `if mark_price <= 0: continue` before calling `update_leg`.
  Stale/zero prices corrupt `best_arb` routes.
- Pass `funding_rate`, `funding_interval_h`, `next_funding_time` to
  `state.update_leg(...)` on every tick where you have them. `state`
  recomputes `best_arb` + `best_funding` and appends history.
- **Funding rate semantics**: we publish the *predicted next-settlement*
  rate across all venues. If the venue also ships a "last paid" field
  (Gate's `funding_rate` vs `funding_rate_indicative`), always prefer the
  predicted/indicative variant with fallback to the settled field.

## Step 4 — wire-up checklist

Every file below must be touched. Missing any one silently hides the venue:

1. `backend/config.py` → add `EXCHANGES["<id>"]` entry. Required keys:
   `id, name, short_name, icon, color, letter, maker_fee, taker_fee,
   default_funding_interval_h, ws_url`. Fees are **percent** (0.04 = 0.04%).
2. `backend/exchange/pair_discovery.py` → import discovery fn, add to
   `_DISCOVERY_FUNCS`. If discovery has side-effect caches (intervals,
   next-applies), wrap it: `def _discover_X_wrapped(): natives, intervals = discover_X(); _X_set_intervals(intervals); return natives`.
3. `backend/main.py` → import the WS class, append to the `connectors` list
   in `startup()`.
4. `backend/exchange/history.py` → add a ccxt client branch in `_get_client`
   **or** a native kline fetcher if ccxt doesn't ship an adapter
   (`_fetch_aster_klines` is the template). Add the exchange id to the
   `_ccxt_symbol` translation tuple and the mark-price params tuple if it
   supports a mark-price OHLCV param.

## Step 5 — verify end-to-end

Before committing, boot the backend and confirm **on the wire**, not just
in logs:

```bash
# in a second shell, after the backend shows "Application startup complete":
curl -s http://localhost:8000/api/exchanges | python3 -c "import json,sys; print(list(json.load(sys.stdin).keys()))"
curl -s http://localhost:8000/api/pairs | python3 -c "
import json,sys
pairs=json.load(sys.stdin)
btc=next((p for p in pairs if p['symbol']=='BTCUSDT'),None)
for ex,leg in btc['legs'].items():
    print(f'{ex}: mark={leg[\"mark_price\"]} fr={leg[\"funding_rate\"]} fih={leg[\"funding_interval_h\"]} nft={leg[\"next_funding_time\"]}')
"
```

All four fields (`mark_price`, `funding_rate`, `funding_interval_h`,
`next_funding_time`) must be non-zero/non-null on BTCUSDT within ~30s of
boot (allow for REST-poll venues to fire their first cycle). If
`funding_interval_h` is defaulted to 8.0 for every symbol, your discovery
interval cache isn't wired — go back to step 2.

Also verify a non-8h symbol picks up its real interval (Aster's
`0GUSDT=1h`, `1000BONKUSDT=4h`, Bitget's `XTZUSDT=4h`). Silent fall-through
to the default funding interval is the #1 footgun.

## Step 6 — CHANGELOG + commit

- Append a Phase entry to `CHANGELOG.md` with: discovery URL, WS URL,
  subscribe shape, field list, fees tier, count of perps + legs, and any
  non-obvious quirk found in step 0.
- Commit message: `Phase <N>: <Exchange> connector` + 2-3 line body.
- The user's memory says every `git push` must append an entry to
  changelog.md — that's the same `CHANGELOG.md` file, handled as part of
  the phase entry. No separate push log.

## Pitfalls seen so far

- **Port 8000 in use after a crash**: `lsof -ti :8000 | xargs kill -9`.
- **Empty log tail**: use `python -u` for unbuffered output and read the
  log file with the Read tool; don't trust background bash tails.
- **Assumed fields from docs that weren't on the wire**: Gate's ticker
  does NOT include `funding_next_apply` despite docs implying it does.
  MEXC's `contract/detail` does NOT include `fundingInterval` — it's on
  `funding_rate` instead. Probe before coding.
- **Per-symbol subscribe for 800+ MEXC symbols**: don't. MEXC's
  `sub.tickers` (plural, no arg) bulk channel is the right answer.
- **Writing to `leg.funding_rate` directly** from a REST poller skips
  route recomputation. Always go through `state.update_leg(...)`.
