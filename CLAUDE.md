# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

RoboSpread is a personal crypto perpetual-futures spread radar. It streams mark prices + funding rates from multiple exchanges, ranks arbitrage and funding-farm routes per symbol, and surfaces them in a live React dashboard. Runs local, single-user. See `plan.md` for the full phased roadmap (currently at v0.1.9, Phase 7 N-exchange refactor in progress).

## Running the app

```bash
./run.sh                                     # starts backend (:8000) + frontend (:5173)
./backend/venv/bin/python backend/main.py    # backend only (reload enabled)
cd frontend && npm run dev                   # frontend only
cd frontend && npm run build                 # production build
cd frontend && npm run lint                  # eslint
```

There is no test suite yet. The backend venv lives at `backend/venv/` (use it directly — `pip install -r backend/requirements.txt` to rebuild).

## Architecture

### N-exchange leg model (read this before touching state or math)

The core data model is **N-exchange, not pairwise**. A `PairState` holds a `legs: dict[exchange_id, ExchangeLeg]`, and every route is derived on demand from that dict. Binance/Bybit are currently the only legs populated, but all code paths assume arbitrary N — do not reintroduce hardcoded `a`/`b` fields.

- `backend/config.py` → `EXCHANGES` registry is the single source of truth for fees, WS URLs, funding intervals, icons, colors. **Adding a new exchange = one new entry + one new `ExchangeWS` subclass.** No other code should hardcode exchange identities.
- `backend/engine/state.py` → `AppState.update_leg(exchange_id, symbol, ...)` is the single write path; every connector calls it. It recomputes `best_arb` and `best_funding` routes and appends a `PriceSnapshot` to the in-memory history ring.
- `backend/engine/spread_calc.py` → `Route`, `compute_route`, `all_routes(legs)`, `best_arb_route(legs)` (max `instant_edge_pct`), `best_funding_route(legs)` (max `funding_apr_pct - round_trip_fee_pct`). Funding APR normalizes by each leg's own `funding_interval_h` — never assume 8h or 3×/day.

### Connector pattern

Every connector subclasses `backend/exchange/base.py::ExchangeWS` and sets `exchange_id` matching an `EXCHANGES` key. The base class provides `run_forever()` with exponential-backoff reconnect; subclasses implement `connect()` which streams until the socket dies. All parsed ticks flow into `state.update_leg(...)`.

- Binance uses one global `!markPrice@arr@1s` stream and filters client-side.
- Bybit requires batched per-symbol `tickers.<SYM>` subscriptions + a 20s app-level ping.
- Funding interval + next-funding-time are already in both exchanges' existing streams — do not add extra REST polling for them.

### History: in-memory + historical join

- `PairState.history` is a `deque(maxlen=3600)` of `PriceSnapshot{timestamp, prices: {exchange_id: price}}`, appended on every tick from any exchange.
- `GET /api/history/{symbol}?timeframe=...` returns raw in-memory ring when `tf=1s`; for other timeframes, `backend/exchange/history.py` fetches per-exchange mark-price klines via ccxt (`params={"price": "mark"}`), outer-joins timestamps across exchanges, and the endpoint merges live ticks newer than the last historical candle.
- The frontend chart computes spread from the `prices` map on each snapshot — backend does not serialize precomputed spreads for charting.

### Frontend push pipeline

- `backend/api/ws_handler.py` maintains a set of connected clients, buffers `state.on_update` callbacks into `_pending` keyed by symbol, and flushes a single JSON frame every `FRONTEND_PUSH_INTERVAL` (0.5s). Known footgun: `_pending` and `_clients` must be declared `global` inside `_push_loop` — missing it caused v0.1.7.
- New clients first receive `{type: "snapshot", pairs: [...]}`, then a stream of `{type: "update", pairs: [...]}` deltas.
- `frontend/src/hooks/useWebSocket.js` keeps `pairsRef.current` as the authoritative map and shallow-copies into React state on each frame.

### Frontend shape

- `SpreadTable` + `SpreadRow` render from `pair.best_arb_route` and `pair.legs`. The global **flip** button swaps In/Out direction for the table and detail page — see `frontend/src/utils/routes.js::inOutFromRoute` for the canonical semantics (Out = forward spread in the best-arb direction; In = reverse).
- `PairDetail` + `SpreadChart` read the same `legs` dict; the chart uses `lightweight-charts` v5 (`addSeries(LineSeries)` — the old `addLineSeries` API is gone).
- Exchange icons, colors, and short names come from the backend's `EXCHANGES` payload via `coin_status` + leg metadata — the frontend has no hardcoded exchange list.

### Coin deposit/withdraw status

`backend/exchange/asset_status.py` polls Binance's public `bapi` endpoint every 60s for per-coin deposit/withdraw flags. `base_coin_candidates(symbol)` handles the multiplier-prefix quirk (`1000PEPEUSDT` → try `1000PEPE` then `PEPE`) since exchanges disagree on whether the prefix is part of the spot coin name. Attached to each pair payload as `coin_status`.

## Conventions worth knowing

- Symbols are always the Binance-style id (`BTCUSDT`) at the backend boundary; per-exchange normalization happens inside each connector. The roadmap's 3+-exchange expansion will route through a central normalizer — don't scatter symbol rewrites.
- Fees in `EXCHANGES` are in **percent** (e.g. `0.04` means 0.04%). `round_trip_fee_pct(long, short)` returns `2 * (taker_long + taker_short)`.
- Staleness: a leg is stale after `STALE_THRESHOLD_SEC` (10s) without an update; a pair is stale if it has fewer than 2 live legs or any live leg is stale. The frontend grays stale rows.
- Pairs with no computed route (`best_arb is None`) are omitted from `/api/pairs` and snapshots — always guard for that on the frontend.

## Lab notes — things not to try next time

A running log of dead ends, failed approaches, and traps that previous Claude instances fell into on this project. Append to this list whenever you spend meaningful time on something that turned out to be wrong, whenever the user corrects you, or whenever you catch yourself about to repeat a mistake documented below. Keep entries terse: one line of what, one line of why it was wrong.

Format: `- YYYY-MM-DD — <what was tried>. Why not: <root cause or correction>.`

<!-- Add new entries at the TOP of this list so the most recent lessons are seen first. -->

- _(no entries yet — first future instance that hits a wall should start the log)_

