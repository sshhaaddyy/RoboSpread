# How Competing Arbitrage Scanners Ingest Prices & Funding Rates

**Date:** 2026-04-21
**Question:** For each previously-surveyed scanner, how does it actually parse prices and funding rates — WebSocket subscribe, REST polling, or hybrid? How does that compare to RoboSpread?

**Method:** 3 parallel agents with chrome-devtools MCP (active click/navigate permission) + source inspection of OSS repos. Observed actual network traffic and page behavior on each scanner while logged out.

---

## RoboSpread baseline (what we're comparing against)

- **Ingest:** per-exchange `ExchangeWS` subclass connects to native WS streams — `wss://fstream.binance.com/stream?streams=!markPrice@arr@1s`, `wss://stream.bybit.com/v5/public/linear`, `wss://api.hyperliquid.xyz/ws`, etc.
- **Aggregation:** every tick flows through a single `state.update_leg(exchange_id, symbol, ...)` write path; routes recomputed on every tick.
- **Funding interval:** read from each exchange's own WS payload (not assumed 8h). Hyperliquid is the one REST exception (30s poll on `/info` — fine since funding changes hourly).
- **Frontend push:** 0.5s batched WS flush from `backend/api/ws_handler.py` to React.

Topology: `Exchange WS → own aggregator → our WS push → browser`. The browser never talks to exchange APIs.

---

## Commercial scanners

| Scanner | Transport | Cadence | Topology | vs RoboSpread |
|---|---|---|---|---|
| **uacryptoinvest.com** | Blazor Server + SignalR over WS (msgpack framing) | Server-pushed; UI throttle 1s/5s/10s/30s | Own aggregator → WS push → browser | **Architectural twin.** SignalR where we use plain WS. |
| **arbitragescanner.io** | REST one-shot on public page; paid tier self-claims "1–4s polling" | 4s (claimed, unverified) | Own aggregator → REST poll → browser | Worse: REST polling loop. |
| **arbitrage-services.com** | REST polling (scanner gated behind login) | 5s (their own marketing copy) | Own aggregator → REST poll → browser | Worse: same pattern, slower. |
| **coinglass.com/ArbitrageList** | Single REST fetch on page load — **no auto-refresh** | Static until manual reload | Own aggregator → one-shot REST → browser | Much worse. |
| **fundingview.app** | Next.js `/api/funding` REST + Socket.IO (stuck in polling-only fallback) | `/api/funding` re-fetched ~15–18s | Own aggregator (Vercel + Railway) → REST + half-broken Socket.IO → browser | Worse freshness; aggregator style matches. |
| **loris.tools** | Server-side-rendered Next.js; WS only for logged-in users | One-shot on navigation; no polling for logged-out visitors | Own aggregator → SSR HTML → browser | Worst freshness (static snapshot per page load). |
| **coinank.com** | Pure REST polling to `api.coinank.com` | `/api/instruments/agg` every ~5s + 5 other endpoints on similar cadence | Own aggregator → REST poll → browser | Worse: 10× our cadence. WS `wss://ws.coinank.com/wsKline` exists but is only for chart klines, not the scanner. |
| **coinalyze.net** | REST only (public API; 40 req/min cap); unclear on frontend | Not pinned in docs | Own aggregator → REST → browser | Worse transport. |

### Key finding
Every commercial scanner runs a **server-side aggregator** (browser never talks to exchanges). Only **uacryptoinvest** matches our WS-push-to-browser model; the other seven REST-poll somewhere in the pipeline.

---

## Open-source scanners

| Repo | Transport | Cadence | Abstraction | Funding math |
|---|---|---|---|---|
| **jose-donato/crypto-futures-arbitrage-scanner** | Pure WS (Go); per-exchange goroutine → buffered channels → central `map[symbol][exchange]` | Event-driven per tick | One file per exchange in `exchanges/`, each spawned as goroutine feeding 3 channels (`priceChan`, `orderbookChan`, `tradeChan`) | **No funding — orderbook-mid only** |
| **hummingbot** (`v2_funding_rate_arb.py` + `PerpetualDerivativePyBase`) | WS via `_orderbook_ds.listen_for_funding_info` → cached `FundingInfo.rate` | Continuous connector stream; strategy ticks on `StrategyV2Base` Clock | Per-venue subclass of `PerpetualDerivativePyBase`; unified `connector.get_funding_info()` API | **Hardcoded interval map**: `{binance_perpetual: 8h, hyperliquid_perpetual: 1h}`, default 8h |
| **kir1l/Funding-Arbitrage-Screener** | REST via `requests.get`; `ThreadPoolExecutor(max_workers=5)` per exchange | One-shot batch | Per-venue subclass in `screeners/`; `main.py` loops `for screener in self.screeners: screener.run()` | None — raw rate per exchange, no annualization |
| **hamood1337/CryptoFundingArb** | REST via **ccxt** (`fetchTickers`, `fetch_funding_rate_history(limit=2)`) | Sequential with `time.sleep(1)` between venues; backoff on rate-limit | Unified ccxt interface via `getattr(ccxt, exchange_id)()` | **Empirical interval inference**: `interval_hours = timestamp.diff() / 3.6e6`, then `365*24 / interval_hours` |
| **hzjken/crypto-arbitrage-framework** | REST only (ccxt) | One-shot snapshot optimization | ccxt unified | None (pure spot price arb) |

### Key findings
- **jose-donato's Go scanner and hummingbot are the only two OSS projects with true WS ingestion.** Both converge on channel/cache patterns equivalent to our `state.update_leg` single-writer.
- **Our funding-interval handling is strictly better than hummingbot's** — they hardcode `{binance: 8h, hyperliquid: 1h}` and default to 8h; we read the interval from the live payload. Hamood1337's empirical inference is clever but has 2-sample latency.
- **Older OSS (hzjken, kir1l)** is REST-only and confirmed obsolete for a live radar.

---

## Cross-product comparison

### Who actually streams (WS push to browser)?
- **RoboSpread** — yes, native exchange WS → our aggregator → 0.5s batched WS to browser
- **uacryptoinvest** — yes, via SignalR/msgpack
- **jose-donato OSS** — yes (but no funding, no UI polish)
- **hummingbot** — yes, but it's a bot, not a radar
- **Everyone else** — no

### Who polls REST?
- arbitragescanner (4s), arbitrage-services (5s), fundingview (~15s), coinank (5s), coinalyze (uncapped), coinglass arb page (manual reload only), loris (SSR snapshot), kir1l (one-shot), hamood1337 (sequential), hzjken (one-shot)

### Freshness ranking (observed)
1. **RoboSpread**: 0.5s batched push on native 1s mark-price ticks
2. **uacryptoinvest**: server-pushed (SignalR), UI throttles to 1s
3. **arbitragescanner / arbitrage-services / coinank**: ~5s REST poll
4. **fundingview**: ~15s REST poll
5. **loris / coinglass arb list**: static per navigation

---

## Implications for RoboSpread

### What's confirmed as a real advantage
- **0.5s WS push is genuinely the freshest observed** among all commercial and OSS scanners except uacryptoinvest (which matches us on architecture, not on advertised cadence).
- **Funding-interval-from-payload is best-in-class.** Hummingbot hardcodes it. Arbitragescanner assumes 8h. Our approach reads it from each exchange's own WS message, so new venues with odd intervals (Hyperliquid 1h, Aster 8h, Gate 8h) just work.
- **Single-writer `update_leg` aggregator pattern** matches what serious projects (hummingbot, jose-donato) converged on independently. Validated by prior art.

### What nobody else does well
- **Auditable freshness provenance** — none of the scanners observed expose per-datum "last polled N seconds ago" timestamps. Our `STALE_THRESHOLD_SEC = 10` logic already tracks this; surfacing it in the UI is cheap and directly attacks everyone's opacity.
- **Sub-second push for a logged-out visitor.** Loris hides its WS behind auth; coinank's WS is klines-only; fundingview's Socket.IO is stuck in polling. We could ship this today.

### Architectural cross-check
Our pipeline topology (`exchange WS → our aggregator → WS to browser`) is the institutional standard. REST polling in the aggregator-to-browser leg is the main competitor foot-gun. Don't adopt it.

---

## Sources

Direct network inspection (chrome-devtools MCP) where pages allowed, plus OSS repo source reads:
- uacryptoinvest.com/arbitrage — Blazor + SignalR confirmed via `/_blazor/negotiate` and `signalr-protocol-msgpack@8.0.0` load
- arbitragescanner.io — `GET https://screener.arbitragescanner.io/api/funding-table` single-shot; paid tier docs claim "every 4 seconds for some endpoints"
- arbitrage-services.com — scanner auth-gated; own backend `arbitrage-services-api.com`; 5s refresh in their own marketing copy
- coinglass.com/ArbitrageList — `GET https://capi.coinglass.com/api/fundingRate/arbitrage-list?exchangeName=all` one-shot, no refresh over 40s idle
- fundingview.app — Next.js `/api/funding` re-fetched every ~15–18s; Socket.IO handshake at `api.fundingview.app/socket.io/?EIO=4&transport=polling` never upgraded to WS
- loris.tools/funding/coin — SSR Next.js, 370KB HTML per navigation; `new WebSocket` in bundle `611-f019d28e40372af9.js` only fires for logged-in users
- coinank.com — `/api/instruments/agg?page=1&size=50` every ~5s plus 5 other endpoints at similar cadence; `wss://ws.coinank.com/wsKline` only used for chart klines
- github.com/jose-donato/crypto-futures-arbitrage-scanner — `main.go` spawns per-exchange goroutines feeding 3 channels
- github.com/hummingbot/hummingbot — `perpetual_derivative_py_base.py::_listen_for_funding_info`; `scripts/v2_funding_rate_arb.py::funding_payment_interval_map`
- github.com/kir1l/Funding-Arbitrage-Screener — `screeners/binance_screener.py` uses `requests.get` + `ThreadPoolExecutor`
- github.com/hamood1337/CryptoFundingArb — ccxt `fetch_funding_rate_history(limit=2)` + pandas timestamp diff
- github.com/hzjken/crypto-arbitrage-framework — ccxt REST snapshot optimizer
