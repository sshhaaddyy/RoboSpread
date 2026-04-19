# RoboSpread — Unified Roadmap

Personal crypto-perp spread radar + paper/real execution tool. Runs local, single-user, keys in `.env.local`.

## Current state (shipped)

- **Exchanges**: Binance + Bybit, pairwise A/B model
- **Data**: `!markPrice@arr@1s` (Binance) + per-symbol tickers (Bybit), ~468 common USDT perps
- **Math**: spread both directions w/ 0.19% round-trip fees, funding-APR normalized by each exchange's own interval
- **UI**: sortable table, pair-detail page with flip, spread chart (lightweight-charts v5), 1s/1m/5m/15m/1h/4h/1d timeframes, hot-row highlighting, staleness detection, reconnect w/ backoff
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

### Phase 7 — N-exchange core refactor (foundation)
**Goal**: Restructure state + math from A/B to N-leg without regressing Binance/Bybit.

- `config.py`: `EXCHANGES` registry — id, display name, icon, maker/taker fees, default funding interval
- `engine/state.py`: replace per-exchange A/B fields with `PairState.legs` dict; update all read/write paths
- `engine/spread_calc.py`: new `best_arb_route(legs) → Route` + `best_funding_route(legs) → Route` + `all_routes(legs) → list[Route]`
- `exchange/base.py`: tighten connector protocol (`connect`, `subscribe(symbols)`, `on_tick`, `reconnect`)
- Frontend: `SpreadRow` renders from `legs[best_long]` / `legs[best_short]` (auto-picked); detail page reads from legs dict
- Binance + Bybit behave identically after refactor — this is the acceptance criterion

### Phase 8 — Hyperliquid
**Why first**: Highest-liquidity new venue and structurally most different (single WS, on-chain coin names). Forces the adapter interface to be truly generic.

- `exchange/hyperliquid_ws.py`: connect to `wss://api.hyperliquid.xyz/ws`, subscribe `webData2` or `allMids`
- Symbol normalizer: `"BTC" → "BTCUSDT"` (hyperliquid uses bare base tickers, USDC-settled)
- Extend `pair_discovery.py` to include Hyperliq universe; flip symbol filter to **3+ exchanges**
- `EXCHANGES["hyperliquid"]` with fees (0.035% taker / 0.01% maker at base tier)
- Detail page: Hyperliq exchange box + icon

### Phase 9 — Multi-route detail page
**Goal**: User explicitly requested — when a pair is clicked, show the chart + an exchange selector + a table of all alternative routes below.

- Exchange selector chip row above chart: `[Binance] [Bybit] [Hyperliq]` — click two chips = long/short for chart; chart re-renders
- Routes panel below chart:
  - Columns: `Long / Short | Price Spread % | Funding APR | Breakeven h | Liquidity`
  - Rank toggleable: by Instant Edge | Funding APR | Hybrid
  - Click a row → that route becomes the chart
- Still only one chart visible at a time (keeps DOM light, 1s tick rate)

### Phase 10 — SQLite persistence
- DB at `~/.robospread/robospread.db`
- Tables: `spreads_1m` (minute-aggregated history per route), `trades`, `paper_trades`, `positions`, `alerts_sent`
- `backend/db/connection.py` + migrations
- Background flusher every 5s (batched inserts)
- `/api/history/:symbol?tf=1m` reads SQLite for ≥1m timeframes; 1s stays in-memory ring
- Survives restarts

### Phase 11 — Alerts (Telegram + Pushover)
- `alerts/telegram.py`: bot sends DMs; token + chat_id in `.env.local`
- `alerts/pushover.py`: user key + app token in `.env.local`
- `alerts/engine.py`: rule evaluator
  - **Opportunity rule** (Telegram): `instant_edge > T` for **≥30s sustained** → fire, then 15min cooldown per `(symbol, long_ex, short_ex)`. Quiet-hours config.
  - **Funding-farm rule** (Telegram): `funding_APR > T` AND `breakeven_h < 24` sustained ≥60s → fire
  - **Critical rule** (Pushover): trade fill, WS drop > 30s, kill-switch trip, backend crash
- Settings panel in frontend (thresholds, quiet hours, per-channel on/off)
- Persist firing history in `alerts_sent` for dedup across restarts

### Phase 12 — Bitget + Gate + MEXC (CEX batch)
**Shared helper**: `exchange/cex_ws_base.py` — handles common patterns (subscribe-batched, ping/pong, reconnect w/ resubscribe).

- `exchange/bitget_ws.py` — wss://ws.bitget.com/v2/ws/public, `ticker` + `mark-price` channels
- `exchange/gate_ws.py` — wss://fx-ws.gateio.ws/v4/ws/usdt, `futures.tickers`
- `exchange/mexc_ws.py` — wss://contract.mexc.com/edge, `sub.ticker`
- Per-exchange fee tiers in `config.py`
- Symbol normalization per exchange

### Phase 13 — Aster
- DEX-adjacent (BNB chain). Investigate WS availability; REST polling fallback at 2s interval if no stable WS
- `exchange/aster_ws.py` or `exchange/aster_rest.py` conforming to same adapter protocol

### Phase 14 — Funding Farm page
**Goal**: Dedicated view for carry-trade hunting; powerful once 7 exchanges are live.

- Route rows: `(symbol × long_ex × short_ex)` — ALL viable permutations
- Rank: `funding_APR − entry_cost_annualized`
- Columns: Symbol | Long | Short | Funding APR | Entry Spread | Breakeven h | Next Funding Countdown | Liquidity Tier
- Filters: min APR, max breakeven, exchange include/exclude, min liquidity tier
- Click → same detail page as Arbitrage, opened on that route

### Phase 15 — On-demand orderbook depth
**Prereq for full-realism paper fills.**

- Each adapter grows `subscribe_depth(symbol)` / `unsubscribe_depth(symbol)` (top-20)
- `engine/orderbook_manager.py`: tracks hot set = (open paper/real positions ∪ currently-viewed chart symbol). Subscribes only those
- Frontend WS messages: `{type: "open_chart", symbol}` / `{type: "close_chart"}` to signal hot-set changes
- Depth stored in `PairState.legs[ex].orderbook` (bids/asks lists)

### Phase 16 — Paper trading engine + risk
- `trading/paper_engine.py`:
  - `open(route, size_usd)` walks orderbook on both legs to compute VWAP fill, applies maker/taker fees, records partial fills if depth insufficient
  - Continuous mark-to-market from live prices
  - Funding accrual: check each leg's next-funding-time, apply payment to paper balance, respect per-exchange interval
- `trading/position.py`: `Position(route, entry_fills, current_mtm, funding_earned, fees_paid)` + live P&L
- `trading/risk.py`:
  - `position_size_usd` cap (static or % of paper equity)
  - `max_concurrent_positions` hard cap
  - `daily_loss_limit_pct` → trip kill switch, refuse new entries, push Pushover alert
  - `per_pair_cooldown_minutes` after close
  - Every `open()` call gates through `risk.validate()`
- SQLite tables: `paper_trades`, `positions`, `daily_pnl`

### Phase 17 — Execution page (paper-only)
- `frontend/src/pages/Exec.jsx`
- Opportunity feed: top-N routes from either strategy matching user's entry filters
- Size input + "Paper Execute" button per row
- Open positions panel: row per position with live unrealized P&L, funding earned, funding countdown, close button
- Risk dashboard strip: daily P&L, equity, kill-switch status, active cooldowns
- Trade blotter (SQLite-backed history, filterable)

### Phase 18 — Real execution (manual, per-exchange REST)
**Gate**: only after paper engine has run a week without surprises.

- `exchange/binance_rest.py`, `bybit_rest.py`, etc — `place_order`, `cancel_order`, `get_position`, `get_balance`
- Keys optional per exchange: missing key → paper-only for that exchange
- Per-exchange "Arm Real Money" toggle in settings (stored locally, never synced)
- Exec page: same UI, but button label swaps to "REAL EXECUTE" when armed; confirmation modal first time per session
- Two-leg order placement: fire both in parallel, rollback if one fails

### Phase 19 — Fully automated mode
- `trading/auto_engine.py`: loop evaluates live opportunities against user's auto-rules, opens/closes without human
- Master arm/disarm switch; cannot arm unless all risk limits are configured AND last daily P&L > −X%
- Safety: auto-mode respects same `risk.validate()` path as manual
- Pushover on every auto-executed fill

### Phase 20 — Hardening
- Reconnection stress test per exchange (simulated drops)
- Unit tests on risk gate + paper fill math
- Integration test: price feed → route ranker → alert fire end-to-end
- README, run.sh updates, `.env.local.example`

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
| 9 | Detail page: clicking any two exchange chips redraws the chart; routes table populated and sortable |
| 10 | Restart backend → frontend restores last 24h of spread history from SQLite |
| 11 | Fake a spread spike → Telegram message arrives once; second spike within 15min is suppressed |
| 12 | 6 exchanges streaming; symbol count > 500 after 3+ filter |
| 13 | 7 exchanges live |
| 14 | Funding Farm page ranks routes correctly for a known high-funding pair |
| 15 | Opening a chart triggers a depth subscribe on the relevant exchanges; closing unsubscribes |
| 16 | Paper trade opened on a 2-leg route shows live MtM + funding accrual within 0.1% of hand-calc |
| 17 | Full paper lifecycle: open → hold through funding → close → P&L reconciles to blotter |
| 18 | Manual real execute on smallest-allowed size on testnet first, then $10 mainnet |
| 19 | Auto-mode opens + closes a paper position against pre-written rules, end-to-end |
| 20 | 72h soak test, zero unhandled exceptions |
