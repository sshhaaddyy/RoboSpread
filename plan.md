# RoboSpread — Unified Roadmap

Personal crypto-perp spread radar + paper/real execution tool. Runs local, single-user, keys in `.env.local`.

## Current state (shipped)

- **Exchanges**: Binance + Bybit + Hyperliquid, N-exchange leg model
- **Data**: `!markPrice@arr@1s` (Binance) + per-symbol tickers (Bybit) + `allMids` WS + `metaAndAssetCtxs` funding poll (Hyperliquid); ~479 pairs at the 2+ filter, 176 of them 3-legged
- **Math**: spread both directions w/ per-exchange fees, funding-APR normalized by each leg's own interval (HL = 1h, BN/BB = 8h)
- **UI**: sortable table, pair-detail page with flip + legs strip (all exchanges visible), spread chart (lightweight-charts v5), 1s/1m/5m/15m/1h/4h/1d timeframes, hot-row highlighting, staleness detection, reconnect w/ backoff, exchange metadata fetched from `/api/exchanges`
- **Backend push**: 500ms batched WS frames

## Target architecture (north star)

```
 Binance ─┐
 Bybit   ─┤
 Hyperliq├─► Adapter layer ─► N-exchange state ─┬─► Price-Arb route ranker  ─► Arbitrage page
 Bitget  ─┤    (unified WS)       (PairState.legs)│                                    │
 Gate    ─┤                                       ├─► Funding-Farm ranker    ─► Funding Farm page
 MEXC    ─┤                                       │                                    │
 Aster   ─┘                                       └─► Alert engine           ─► Telegram / Pushover
                                                          │
                                                  (Orderbook depth on-demand for hot symbols)
                                                          │
                                                  Paper trading engine ─► Risk gate ─► Exec page
                                                                                       │
                                                                                Real REST adapters
                                                                                       │
                                                                                   Auto loop
```

## Locked decisions

| | |
|---|---|
| Data model | N-exchange matrix; `PairState.legs: dict[exchange_id, ExchangeLeg]` |
| Symbol coverage | Pairs listed on **3+ exchanges** (~600 symbols) |
| Rollout order | Hyperliquid → Bitget → Gate → MEXC → Aster |
| Pages | **Arbitrage** (price spread lens) + **Funding Farm** (carry lens) |
| Detail page | Exchange selector for chart + full route table below chart |
| Alerts | Telegram = opportunities, Pushover = critical (fills/errors/drops) |
| Alert logic | threshold + ≥30s sustained + 15min per-symbol cooldown + quiet hours |
| Paper trading | Full realism: orderbook-depth fills, fees, slippage, partial fills, continuous funding accrual |
| Risk controls | position size + max concurrent + daily kill switch + per-pair cooldown |
| Orderbook | Top-20 levels, on-demand only for hot symbols (open chart or open position) |
| Persistence | SQLite at `~/.robospread/robospread.db` |
| Funding Farm ranking | `funding_APR − entry_cost_annualized` (no hard filter) |
| Runtime | Local only, keys in `.env.local` |

## Route model (math)

For any `(symbol, long_exchange, short_exchange)` triple:

```
instant_edge_%   = (price_short − price_long) / price_long × 100 − round_trip_fees_%
funding_APR_%    = (funding_short − funding_long) × payments_per_year × 100     (per-exchange interval aware)
breakeven_hours  = round_trip_fees_% / (funding_APR_% / 8760)
hybrid_score     = instant_edge_% + funding_APR_% × expected_hold_hours / 8760
```

- **Arbitrage page** sorts by `instant_edge` (highlighted when > threshold)
- **Funding Farm page** sorts by `funding_APR − entry_cost_annualized`
- Detail page surfaces all three metrics for every route on the symbol

## Data contracts

### `ExchangeLeg`
```
{
  exchange_id: str,       # "binance" | "bybit" | "hyperliquid" | ...
  mark_price: float,
  funding_rate: float,    # instantaneous
  funding_interval_h: float,
  next_funding_time: int, # unix ms
  last_update: int,
  stale: bool
}
```

### `PairState`
```
{
  symbol: str,
  legs: dict[exchange_id, ExchangeLeg],
  history: deque[Snapshot]   # in-memory 1s ring; long-term lives in SQLite
}
```

### `Route` (derived on demand)
```
{
  long_ex: str, short_ex: str,
  instant_edge_%: float,
  funding_apr_%: float,
  breakeven_h: float,
  liquidity_tier: int   # depth-derived; 1=best, 4=thin
}
```

---

## Phased implementation

**Guiding principles for everything below**:
1. **Backend must be deploy-ready before any frontend phase resumes.** The current dashboard already renders N legs, so every new connector lights up automatically — we press the backend to completion first.
2. **Native APIs only.** Every new connector talks directly to the exchange's native WS/REST. No ccxt, no generalized wrappers. Direct parse paths are faster and give us full control over tick-to-state latency. Phase 13 retires ccxt from BN/BB/history too.
3. **Live data for everything, always.** Funding rate AND funding interval must be read off every tick — exchanges change both (8h → 4h → 1h) without warning. Never trust the config default once a live value is available. Spreads appear for seconds; we have to be the fastest.
4. **API-key insertion points are called out explicitly.** Every phase is tagged `PUBLIC` (no keys) or `🔑 KEY NEEDED` with exactly which secret and where it lives.

### Key-insertion summary
| Phase | What needs a key | Where it lives |
|---|---|---|
| 9–13 | nothing — public WS/REST only | — |
| 14 | nothing — local SQLite | — |
| 15 | Telegram bot token + chat_id, Pushover user_key + app_token | `.env.local` |
| 16 | nothing — deploy plumbing | — |
| 17–21 | nothing — paper trading only | — |
| 22 | per-exchange API key + secret (HL: wallet signing key) | `.env.local`, per-exchange `ARM_REAL_<EX>` toggle |

### Phase 7 — N-exchange core refactor (foundation)  ✅ shipped
**Goal**: Restructure state + math from A/B to N-leg without regressing Binance/Bybit.

- `config.py`: `EXCHANGES` registry — id, display name, icon, maker/taker fees, default funding interval
- `engine/state.py`: replace per-exchange A/B fields with `PairState.legs` dict; update all read/write paths
- `engine/spread_calc.py`: new `best_arb_route(legs) → Route` + `best_funding_route(legs) → Route` + `all_routes(legs) → list[Route]`
- `exchange/base.py`: tighten connector protocol (`connect`, `subscribe(symbols)`, `on_tick`, `reconnect`)
- Frontend: `SpreadRow` renders from `legs[best_long]` / `legs[best_short]` (auto-picked); detail page reads from legs dict

### Phase 8 — Hyperliquid  ✅ shipped
**Why first**: Highest-liquidity new venue and structurally most different (single WS, on-chain coin names). Forces the adapter interface to be truly generic.

- `exchange/hyperliquid_ws.py`: `wss://api.hyperliquid.xyz/ws` `allMids` for prices; REST `/info metaAndAssetCtxs` polled every 30s for funding
- Symbol normalizer: `"BTC" → "BTCUSDT"`, `"kPEPE" → "1000PEPEUSDT"` — HL ships `kXXX` for 1000x wrappers
- `pair_discovery.discover_pairs()` returns `(common, per_exchange_map)`; `MIN_EXCHANGES_PER_PAIR = 2` for now
- `/api/exchanges` endpoint exposes registry metadata; frontend `useExchanges()` hook

---

### Phase 9 — CEX shared base + Bitget connector  `PUBLIC`
**Goal**: Stand up `exchange/cex_ws_base.py` (the shared abstraction the remaining CEXs will inherit) and prove it with Bitget.

- `exchange/cex_ws_base.py`: common connector skeleton — batched subscribe, app-level ping/pong with per-exchange framing, reconnect-with-resubscribe, symbol translation via `to_canonical` / `to_native`, structured ingest that funnels into `state.update_leg`
- `exchange/bitget_ws.py`: native connector at `wss://ws.bitget.com/v2/ws/public`. Subscribe to `ticker` channel for mark-price + `fundingRate` + `nextFundingTime` + `fundingInterval` — all live, parsed per tick (no config defaults, no REST polling)
- `exchange/bitget_discovery.py`: native REST `GET /api/v2/mix/market/contracts?productType=USDT-FUTURES` → canonical `BTCUSDT` mapping. **No ccxt.**
- `EXCHANGES["bitget"]`: base-tier fees confirmed against bitget.com/en/fee schedule at PR time (taker 0.06% / maker 0.02% is current as of last check — re-verify); `default_funding_interval_h` kept as the fallback only, live tick always wins
- **Acceptance**: `/api/pairs` shows Bitget legs; kill the socket mid-run → `cex_ws_base` resubscribes cleanly; funding interval for at least one 4h contract (e.g. some alts) reads as `4` not `8`

### Phase 10 — Gate connector  `PUBLIC`
- `exchange/gate_ws.py`: `wss://fx-ws.gateio.ws/v4/ws/usdt`, `futures.tickers` channel (includes `funding_rate`, `funding_next_apply`, `funding_interval`). Live parse per tick.
- `exchange/gate_discovery.py`: native REST `GET /api/v4/futures/usdt/contracts` → canonical. Gate ships `BTC_USDT` natively → normalize to `BTCUSDT`.
- `EXCHANGES["gate"]`: base-tier taker 0.05% / maker 0.02% (verify against gate.com fee page at PR time)
- Shake-test: confirm `cex_ws_base` handled Gate's ping frames; adjust if protocol differs

### Phase 11 — MEXC connector  `PUBLIC`
- `exchange/mexc_ws.py`: `wss://contract.mexc.com/edge`, `sub.ticker` channel. Funding: the ticker payload exposes `fundingRate` + `nextSettleTime`; funding interval comes from `GET /api/v1/contract/detail` cached once per symbol at startup. If MEXC adds live interval to the ticker, switch to that.
- `exchange/mexc_discovery.py`: native REST `GET /api/v1/contract/detail` → canonical. MEXC ships `BTC_USDT` natively.
- `EXCHANGES["mexc"]`: base-tier taker 0.02% / maker 0.00% (verify at PR time)
- **Note**: MEXC public futures WS does not require auth (as of 2026-Q1); if this changes, flag it and add `MEXC_API_KEY` to the key-insertion table
- 6 exchanges live — if 3-leg coverage > 300 symbols, bump `MIN_EXCHANGES_PER_PAIR` to 3 in the same PR

### Phase 12 — Aster connector  `PUBLIC`
- Target is **asterdex.com** (perp DEX on BNB chain, not the Aster L1).
- Investigate their WS docs first; if no stable WS, REST poll at 2s
- `exchange/aster_ws.py` or `exchange/aster_rest.py` conforming to `ExchangeWS` protocol
- `exchange/aster_discovery.py`: their native REST contracts endpoint
- `EXCHANGES["aster"]`: base-tier fees from their docs at PR time; funding interval from live data
- **Exit criterion**: 7 exchanges streaming, `/api/exchanges` returns all 7

### Phase 13 — Retire ccxt; native REST everywhere  `PUBLIC`
**Why now**: Phases 9–12 introduced native discovery per exchange. Finish the job for Binance + Bybit + Hyperliquid so the whole codebase is uniform and ccxt is dropped from `backend/requirements.txt`. Measurable goal: cold startup discovery time down, per-tick parse budget unchanged.

- Rewrite `_discover_binance` → `GET /fapi/v1/exchangeInfo`
- Rewrite `_discover_bybit` → `GET /v5/market/instruments-info?category=linear`
- `exchange/history.py`: replace ccxt kline fetches with each exchange's native kline REST (`/fapi/v1/markPriceKlines`, `/v5/market/mark-price-kline`, HL's `candleSnapshot`, plus the four new CEXs). Each history source returns `(ts, o, h, l, c)` normalized.
- Drop `ccxt` from `backend/requirements.txt`; remove the `_canonical_to_ccxt` map in history
- **Acceptance**: all 7 exchanges' pair discovery returns same counts (within ±1) as the previous ccxt path; every timeframe on every exchange renders in the chart

### Phase 14 — SQLite persistence  `PUBLIC`
**Still backend-only.** Dashboard survives restarts; unlocks alert dedup and paper-trade history.

- DB at `~/.robospread/robospread.db`
- Full schema laid down now so Phases 15/18 don't need follow-up migrations:
  - `spreads_1m(symbol, long_ex, short_ex, ts, instant_edge_pct, funding_apr_pct)` — minute-aggregated per route
  - `alerts_sent(rule_id, symbol, long_ex, short_ex, fired_at)` — dedup ledger
  - `paper_trades`, `positions`, `daily_pnl` — created now, written to from Phase 18
- `backend/db/connection.py` + `backend/db/migrations/` (plain SQL files, applied on boot)
- Background flusher every 5s — aggregates in-memory ring to 1m **before** inserting (do not store every tick)
- `/api/history/:symbol?tf=1m` reads SQLite for ≥1m timeframes; 1s stays in-memory ring
- **Acceptance**: restart backend → historical chart for any symbol survives, no ccxt fallback needed for ≥1m

### Phase 15 — Alerts engine (Telegram + Pushover)  🔑 KEY NEEDED
**External-service keys.** No exchange keys.

Required in `.env.local`:
- `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`
- `PUSHOVER_USER_KEY`, `PUSHOVER_APP_TOKEN`

Implementation:
- `alerts/telegram.py`: bot send
- `alerts/pushover.py`: push send
- `alerts/engine.py`: rule evaluator
  - **Opportunity rule** (Telegram): `instant_edge > T` sustained ≥30s → fire, 15min cooldown per `(symbol, long_ex, short_ex)`. Quiet-hours config.
  - **Funding-farm rule** (Telegram): `funding_APR > T` AND `breakeven_h < 24` sustained ≥60s → fire
  - **Critical rule** (Pushover): WS drop > 30s, backend crash, kill-switch trip (trade fills land in Phase 18+)
- Rule config via `config.py` for now (no settings UI yet — that lands with the frontend stretch). Thresholds + quiet hours in `.env.local`.
- Persist firing history in `alerts_sent` for dedup across restarts

### Phase 16 — Backend deploy-ready  `PUBLIC`
**Goal**: Make the backend a long-running service you can `start`/`stop`/`restart` and walk away from. This is the gate before we touch frontend.

- `launchd` plist template at `deploy/com.robospread.plist` (macOS-native — no Docker for a single-user local tool) with auto-restart on crash
- `deploy/run-service.sh`: venv activation + `uvicorn backend.main:app --host 127.0.0.1 --port 8000` with structured logs to `~/.robospread/logs/backend.log`, rotated
- `backend/main.py`: `/health` endpoint returns `{status, uptime_s, exchanges: [{id, connected, last_tick_s_ago}]}` — lets the service monitor itself
- Graceful shutdown: SIGTERM → close WS sockets → flush SQLite → exit
- `.env.local.example` lists every env var with a comment: all 7 exchange key slots (empty for now), Telegram/Pushover, thresholds, log level
- `deploy/README.md`: install, start, stop, tail logs, update
- **Acceptance**: `launchctl load` then reboot the machine → service comes back up, `/health` returns 200, all 7 connectors streaming within 30s

---

**Frontend resumes here.** 7 exchanges live, SQLite persisted, alerts firing, service auto-restarts. Frontend phases can now safely add UI without the backend being in flux.

### Phase 17 — Multi-route detail page
- Exchange selector chip row above chart: click two chips = long/short for chart; chart re-renders
- Routes panel below chart: `Long / Short | Price Spread % | Funding APR | Breakeven h | Liquidity`
- Rank toggleable: Instant Edge | Funding APR | Hybrid
- Click a row → that route becomes the chart
- Still only one chart visible at a time

### Phase 18 — Funding Farm page
- Route rows: `(symbol × long_ex × short_ex)` — ALL viable permutations
- Rank: `funding_APR − entry_cost_annualized`
- Columns: Symbol | Long | Short | Funding APR | Entry Spread | Breakeven h | Next Funding Countdown | Liquidity Tier
- Filters: min APR, max breakeven, exchange include/exclude, min liquidity tier
- Click → same detail page as Arbitrage, opened on that route

### Phase 19 — On-demand orderbook depth
**Prereq for full-realism paper fills.**

- Each adapter grows `subscribe_depth(symbol)` / `unsubscribe_depth(symbol)` (top-20) — native WS channels per exchange
- `engine/orderbook_manager.py`: tracks hot set = (open paper/real positions ∪ currently-viewed chart symbol). Subscribes only those
- Frontend WS messages: `{type: "open_chart", symbol}` / `{type: "close_chart"}`
- Depth stored in `PairState.legs[ex].orderbook`

### Phase 20 — Paper trading engine + risk
- `trading/paper_engine.py`:
  - `open(route, size_usd)` walks orderbook on both legs for VWAP fill, applies maker/taker fees, records partial fills
  - Continuous mark-to-market from live prices
  - Funding accrual respects per-exchange live interval
- `trading/position.py`: `Position(route, entry_fills, current_mtm, funding_earned, fees_paid)` + live P&L
- `trading/risk.py`: position size cap, max concurrent, daily loss limit, per-pair cooldown; every `open()` gates through `risk.validate()`
- Writes to `paper_trades`, `positions`, `daily_pnl` (schema already laid down in Phase 14)

### Phase 21 — Execution page (paper-only)
- `frontend/src/pages/Exec.jsx`
- Opportunity feed + size input + "Paper Execute"
- Open positions panel, risk dashboard strip, trade blotter

### Phase 22 — Real execution  🔑 KEY NEEDED
**Gate**: paper engine has run a week without surprises.

Required in `.env.local` (per exchange, all optional — missing → that exchange stays paper-only):
- `BINANCE_API_KEY`, `BINANCE_API_SECRET`
- `BYBIT_API_KEY`, `BYBIT_API_SECRET`
- `HYPERLIQUID_WALLET_ADDRESS`, `HYPERLIQUID_PRIVATE_KEY` (signing key, treat like a cold secret)
- `BITGET_API_KEY`, `BITGET_API_SECRET`, `BITGET_API_PASSPHRASE`
- `GATE_API_KEY`, `GATE_API_SECRET`
- `MEXC_API_KEY`, `MEXC_API_SECRET`
- `ASTER_API_KEY`, `ASTER_API_SECRET` (TBD — depends on Phase 12 findings)

Implementation:
- `exchange/<ex>_rest.py` for each venue — native REST: `place_order`, `cancel_order`, `get_position`, `get_balance`
- Per-exchange "Arm Real Money" toggle (local state, never synced anywhere)
- Button label swaps to "REAL EXECUTE" when armed; confirmation modal first time per session
- Two-leg order placement: fire both in parallel, rollback if one fails

### Phase 23 — Fully automated mode
- `trading/auto_engine.py`: evaluates live opportunities against user's rules, opens/closes without human
- Master arm/disarm; cannot arm unless all risk limits configured AND last daily P&L > −X%
- Auto-mode uses the same `risk.validate()` path as manual
- Pushover on every auto-executed fill

### Phase 24 — Hardening
- Reconnection stress test per exchange (simulated drops)
- Unit tests on risk gate + paper fill math
- Integration test: price feed → route ranker → alert fire end-to-end
- README, run.sh updates, `.env.local.example` finalized

---

## Gotchas / risks

- **Symbol normalization across 7 exchanges**: Hyperliq `BTC`, MEXC `BTC_USDT`, Gate `BTC_USDT`, Binance `BTCUSDT`, Aster TBD. Central normalizer is load-bearing.
- **Funding interval divergence**: already handled pairwise; must generalize across all 7 when computing funding APR per route.
- **Fees across VIP tiers**: config assumes base-tier taker. User's actual tier may differ — surface in settings later if it becomes material.
- **Paper/real divergence**: orderbook simulation can't model queue position for maker orders. Paper P&L will be optimistic for maker strategies. Document, don't try to fake it.
- **Hyperliq / Aster as DEX-adjacent**: slower block-time, different fill semantics. Real execution there needs careful thought — maybe keep manual-only until proven.
- **SQLite write amplification**: 600 symbols × 21 routes × 60 flushes/hour could bloat fast. Aggregate at 1m before inserting, not per-tick.

## Verification gates per phase

| Phase | Pass criteria |
|---|---|
| 7 | BN+BB behave identically to v0.1.9 on the refactored N-leg shape |
| 8 | Hyperliq prices stream live; a 3-way symbol (e.g. BTCUSDT) shows legs for all three |
| 9 | Bitget legs in `/api/pairs`; forced socket drop resubscribes cleanly; live funding interval propagates (4h contract not mislabeled as 8h) |
| 10 | Gate streaming; `BTC_USDT ↔ BTCUSDT` normalization both directions; live funding interval correct |
| 11 | MEXC streaming; 6 exchanges live; `MIN_EXCHANGES_PER_PAIR=3` reviewed |
| 12 | Aster streaming (or REST-polled); all 7 exchanges present in `/api/exchanges` |
| 13 | ccxt removed from `requirements.txt`; all 7 discoveries return same counts (±1); chart renders every timeframe for every venue |
| 14 | Restart backend → historical chart survives, 1m+ reads from SQLite; full schema migrated |
| 15 | Fake a spread spike → Telegram arrives once; second spike within 15min suppressed; WS drop > 30s → Pushover fires |
| 16 | `launchctl load` + reboot → service auto-starts; `/health` returns 200 with all 7 connectors within 30s |
| 17 | Detail page: clicking any two exchange chips redraws the chart; routes table populated and sortable |
| 18 | Funding Farm page ranks routes correctly for a known high-funding pair |
| 19 | Opening a chart triggers a depth subscribe on the relevant exchanges; closing unsubscribes |
| 20 | Paper trade opened on a 2-leg route shows live MtM + funding accrual within 0.1% of hand-calc |
| 21 | Full paper lifecycle: open → hold through funding → close → P&L reconciles to blotter |
| 22 | Manual real execute on smallest-allowed size on testnet first, then $10 mainnet |
| 23 | Auto-mode opens + closes a paper position against pre-written rules, end-to-end |
| 24 | 72h soak test, zero unhandled exceptions |
