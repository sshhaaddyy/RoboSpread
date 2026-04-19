# RoboSpread Changelog

## 2026-04-19 — `/clarify` + `/research` skills

- **`.claude/skills/clarify/SKILL.md`**: `/clarify <prompt>` batches 2–5 structured clarifying questions via `AskUserQuestion` before executing an ambiguous request. Position-invariant — the `/clarify` token can appear anywhere in the user's message. Motivated by the "move all exchanges to APIs" incident where ccxt→native and WS→REST were both plausible readings.
- **`.claude/skills/research/SKILL.md`**: `/research <question>` fan-out/fan-in. Decomposes into ≥5 angles, user confirms via `AskUserQuestion`, spawns parallel researcher subagents on **sonnet** (one per angle, each aware of its siblings), synthesizer on **opus** picks an output template (Decision / Landscape / Explain / Timeline / Generic), runs a single gap-closing follow-up round if the synthesizer flags `[CRITICAL_GAP]`, default-saves to `research/<YYYY-MM-DD>-<slug>.md`. v2 applied 8 self-critique improvements over v1: early-exit check, angle approval, sibling awareness, failure handling, depth tags (200/400/700 word caps), templates, gap-closing, default persistence.
- **Pushed** commits `6583138`, `135a1f5`, `ef45279`, `85fb07f`, `042e1a6`, `f5b2463` to origin/master.

## 2026-04-19 — Gate funding semantics + project skills

- **Gate funding rate**: switched from `funding_rate` (Gate's "rate paid at the PREVIOUS settlement") to `funding_rate_indicative` (live-predicted rate for the NEXT settlement). Every other venue already publishes predicted-next-settle — Gate was the odd one out and would lag during a rate shift. Falls back to `funding_rate` if the indicative field is missing on a given tick.
- **`.claude/skills/add-exchange/SKILL.md`**: project-level skill capturing the end-to-end recipe for wiring a new exchange (REST discovery, WS connector archetypes, wire-up checklist, verification protocol, pitfalls seen across the 5 venues added so far). Invocable via `/add-exchange`.
- **Pushed** commits `7e1471d` (Phase 11 MEXC), `d1d2acc` (Phase 12 Aster), and this one to origin/master. Live exchange count now 7: binance, bybit, hyperliquid, bitget, gate, mexc, aster.

## 2026-04-19 — Phase 12: Aster connector (7 exchanges live)

- `backend/exchange/aster_discovery.py`: native REST `GET /fapi/v3/exchangeInfo` (symbols with `contractType=PERPETUAL`, `status=TRADING`, `quoteAsset=USDT`) + `GET /fapi/v3/fundingInfo` (per-symbol `fundingIntervalHours`). Aster is Binance-fapi compatible — canonical == native (`BTCUSDT`). 350 trading perps, interval mix: 259 at 1h, 174 at 8h, 58 at 4h, 3 at 2h.
- `backend/exchange/aster_ws.py`: combined-stream `wss://fstream.asterdex.com/stream?streams=!markPrice@arr@1s`. Tick format is byte-identical to Binance's `markPriceUpdate` (`{e,E,s,p,P,i,r,T}`). `funding_interval_h` attached from the discovery cache (not on tick). Server-driven pings every 5min; library auto-pongs.
- `backend/config.py`: `EXCHANGES["aster"]` with taker 0.035% / maker 0.01%.
- `backend/exchange/history.py`: native kline fetch via `/fapi/v1/markPriceKlines` (ccxt doesn't ship an Aster adapter). Binance-compatible response shape, converted to ccxt tuple format for the existing outer-join logic.
- `backend/main.py` + `backend/exchange/pair_discovery.py`: wired through startup + discovery. Total exchange count = 7.
- Verified: 654 symbols listed on 2+ venues. BTCUSDT shows **all 7 legs live** with mark price, funding rate, interval, and next-funding-time populated. Aster's per-symbol interval variety confirmed (`0GUSDT=1h`, `1000BONKUSDT=4h`, `BTCUSDT=8h`) — no default-interval reliance.

## 2026-04-19 — Phase 11: MEXC connector

- `backend/exchange/mexc_discovery.py`: native REST `GET https://contract.mexc.com/api/v1/contract/detail`. Returns `{canonical: native}` only — `BTC_USDT → BTCUSDT`. Filters by `quoteCoin=="USDT"`, `state==0` (trading), skips `isHidden` / `preMarket`. MEXC's contract detail does **not** carry funding interval, so no interval cache is seeded at discovery.
- `backend/exchange/mexc_ws.py`: public WS at `wss://contract.mexc.com/edge`. Uses the **bulk** `sub.tickers` channel (no symbol arg) — one subscription pushes `fairPrice` for every symbol at ~1 Hz, far cheaper than 800+ per-symbol subs. Standalone connector (does not inherit `CexWSBase`) because of the bulk subscribe + protocol-level ping shape. Ping = `{"method":"ping"}` every 15s; drop after ~60s silence.
- Funding rate / interval / next settle come from a **separate REST poll** (`GET /api/v1/contract/funding_rate`, 30s cadence). Per-tick `sub.ticker` does carry `fundingRate` but omits `collectCycle` + `nextSettleTime`, so the REST poll is load-bearing. Funding updates are routed through `state.update_leg(...)` with the last-known mark price so `best_arb` / `best_funding` recompute and the frontend sees fresh numbers without waiting for the next price tick.
- `backend/config.py`: `EXCHANGES["mexc"]` with taker 0.02% / maker 0.00% (public tier — MEXC is the cheapest venue we track).
- `backend/main.py` + `backend/exchange/pair_discovery.py` + `backend/exchange/history.py`: MEXC wired through startup, discovery, and ccxt kline fallback.
- Verified: backend boots with **6 exchanges**, 643 pairs total. BTCUSDT shows all 6 live legs with mark price, funding rate, interval, and next-funding-time populated. MEXC contributes 573 legs (of 755 discovered perps). Funding poll delivers live interval (`collectCycle=8`) per symbol — no default-interval reliance.

## 2026-04-19 — Phase 10: Gate connector

- `backend/exchange/gate_discovery.py`: native REST `GET /api/v4/futures/usdt/contracts`. Returns `{canonical: native}` + `{canonical: funding_interval_h}` + `{canonical: funding_next_apply_unix}`. `BTC_USDT → BTCUSDT` canonical translation. Gate's perp universe = 667 USDT-settled (350 at 8h, 311 at 4h, 6 at 1h).
- `backend/exchange/gate_ws.py`: Gate v4 USDT-futures public WS at `wss://fx-ws.gateio.ws/v4/ws/usdt`, `futures.tickers` channel. Subscribe envelope is `{time,channel,event:"subscribe",payload:[...]}` (no op/args shape), so `CexWSBase._build_subscribe_message` was generalized to let subclasses override the envelope. Gate relies on server-driven protocol pings — `enable_app_ping=False`, `websocket_ping_interval=20`, library auto-responds.
- Gate's ticker push omits `funding_interval` and `funding_next_apply` (confirmed on the wire — only `funding_rate` and `funding_rate_indicative` are there). `gate_discovery.current_next_funding(canonical)` advances the REST-seeded `funding_next_apply` forward by `funding_interval` on each tick so the frontend countdown stays correct without re-polling.
- `backend/exchange/cex_ws_base.py`: added `websocket_ping_interval` + `enable_app_ping` knobs, generalized `_build_subscribe_message(batch)` hook, default `_is_control_message` left on Bitget-style (Gate overrides to keep event="update" frames).
- `backend/config.py`: `EXCHANGES["gate"]` with taker 0.05% / maker 0.02% (base tier), default 8h interval.
- `backend/main.py` + `backend/exchange/pair_discovery.py` + `backend/exchange/history.py`: Gate wired through startup, discovery, and ccxt kline fallback.
- Verified: 575 pairs across 5 exchanges (binance=548, bybit=484, hyperliquid=187, bitget=501, gate=526). BTCUSDT shows all 5 live legs. AIXBTUSDT Gate leg reports 4h interval (live, not defaulted).

## 2026-04-19 — Phase 9: CEX shared base + Bitget

- `backend/exchange/cex_ws_base.py`: new `CexWSBase` shared connector. Handles batched subscribe, string-ping keepalive, reconnect-with-resubscribe (via parent `run_forever`), and control-frame filtering. Subclasses override `_subscribe_arg(native)` + `_handle_message(msg)`. Gate/MEXC/Aster will inherit from this — Bybit left on its own path for now.
- `backend/exchange/bitget_discovery.py`: native REST `GET /api/v2/mix/market/contracts?productType=USDT-FUTURES` (no ccxt). Returns `{canonical: native}` plus `{canonical: funding_interval_h}` parsed from the exchange's own `fundInterval` field — 363 symbols on 4h, 169 on 8h, 5 on 1h. Cached so the WS connector can read it per tick.
- `backend/exchange/bitget_ws.py`: v2 public WS at `wss://ws.bitget.com/v2/ws/public`, `ticker` channel per symbol. Live `markPrice` + `fundingRate` + `nextFundingTime` per tick; `funding_interval_h` attached from the discovery cache since Bitget's ticker payload doesn't ship it. Ping/pong is plain-text "ping"/"pong" at 20s (server disconnects after 2min).
- `backend/config.py`: `EXCHANGES["bitget"]` with taker 0.06% / maker 0.02% (base tier).
- `backend/exchange/pair_discovery.py`: wired `_discover_bitget_wrapped` into `_DISCOVERY_FUNCS`; populates the interval cache as a side effect.
- `backend/exchange/history.py`: ccxt `bitget` client added for kline fetches (will be retired in Phase 13 along with the rest).
- `backend/main.py`: `BitgetWS` added to the startup connector list.
- Verified: discovery returns 537 Bitget perps with correct per-symbol intervals (BTC=8h, XTZ/AXS=4h, SIREN=1h). Full backend boots with 540 pairs across 4 exchanges; BTCUSDT shows 4 live legs; XTZUSDT's Bitget leg reports 4h as expected (not defaulted to 8h).

## 2026-04-19 — Planning: API-first pivot

- Reworked `plan.md` for phases 9–24 around four guiding principles: (1) backend-deploy-ready before any frontend phase resumes; (2) native exchange APIs only — ccxt retired in Phase 13; (3) live funding rate **and** live funding interval pulled off every tick (never trust config defaults, intervals shift 8h ↔ 4h ↔ 1h at exchange discretion); (4) API-key insertion points called out explicitly per phase (no keys until Phase 15 alerts, no exchange keys until Phase 22 real execution).
- New deploy-readiness phase (16) added before frontend resumes: `launchd` plist, `/health` endpoint, log rotation, graceful shutdown, `.env.local.example` covering all 7 exchanges.
- Scope lock: Bitget → Gate → MEXC → Aster → ccxt removal → SQLite → alerts → deploy. Frontend phases (17+) do not start until the whole backend is running as a long-lived service.

## 2026-04-19

### Phase 8 — Hyperliquid integration
- `backend/exchange/hyperliquid_ws.py`: new connector. WS `allMids` subscription for live mid prices + REST `/info metaAndAssetCtxs` polled every 30s for funding rate / mark-px / hourly countdown.
- `backend/exchange/pair_discovery.py`: rewritten as `discover_pairs() -> (canonical_symbols, per_exchange_map)`. Hyperliquid universe fetched directly from `/info {"type":"meta"}` (ccxt drops the `kXXX` prefix). Mapping `kPEPE → 1000PEPEUSDT`, `BTC → BTCUSDT` etc.
- `backend/exchange/base.py`: connectors accept `dict[canonical: native]` as well as a plain list; new `to_canonical()` / `to_native()` helpers let Binance/Bybit (identity) and Hyperliquid (bare/k-prefixed) share one code path.
- `backend/exchange/binance_ws.py`, `bybit_ws.py`: translate native→canonical via base helpers before writing state. Bybit now subscribes with native symbols (identity on its side).
- `backend/engine/state.py`: `init_pairs(per_exchange_map)` only creates legs for exchanges that list the pair. `PairState.is_stale` relaxed to "≥2 fresh legs" so a single laggy venue doesn't gray out a 3-leg pair.
- `backend/exchange/history.py`: per-exchange canonical→ccxt-symbol mapping (adds `BTC/USDC:USDC` for Hyperliquid, reverses `1000PEPE → kPEPE`). History endpoint outer-joins up to N legs.
- `backend/main.py`: wires `HyperliquidWS` into startup. Adds `GET /api/exchanges` exposing the registry metadata (id, name, icon, color, fees, funding interval).
- `frontend/src/hooks/useExchanges.js`: module-cached fetch of `/api/exchanges`.
- `frontend/src/components/PairDetail.jsx`: drops hardcoded `EXCHANGE_META`; reads icons/colors/names from the backend registry. New `LegsStrip` renders every exchange leg for the pair above the long/short boxes so the Hyperliquid leg is visible even when the best arb is Binance↔Bybit.
- `frontend/src/index.css`: styles for `.legs-strip` chips.
- Verified: 479 pairs total, 176 of them 3-legged. BTCUSDT streams live legs for binance/bybit/hyperliquid; `1000PEPEUSDT` correctly pulls from HL's `kPEPE`. 5m history endpoint returns all 3 legs outer-joined.

## 2026-04-16

### v0.1.9 — Funding interval + countdown timer
- Extracted `nextFundingTime` and `fundingInterval` from existing Binance (`T`, `i` fields) and Bybit (`nextFundingTime`, `fundingInterval` fields) WebSocket streams — zero extra API calls
- Each exchange box now shows a live countdown timer (HH:MM:SS) until next funding payment
- Funding interval displayed as a tag badge (e.g. "8h", "4h", "1h") next to the timer
- Fixed `calc_funding_spread_apr` to normalize each exchange's rate by its actual interval instead of assuming 3x/day for both
- `PairState` now stores `next_funding_time_*` and `funding_interval_h_*` per exchange

### v0.1.8 — Detail page redesign + exchange icons + direction arrows
- Restructured pair detail layout: IN + exchange data grouped in left column, OUT + exchange data in right column (Funding Spread APR stays full-width)
- Added token icon next to symbol name (loaded from CDN, text fallback)
- Added exchange icons (Binance/Bybit logos from CoinGecko CDN) in each exchange box header
- Added direction arrows: green up-arrow for Long, red down-arrow for Short — shown in direction bar and exchange box headers
- Full exchange names everywhere ("Binance" / "Bybit" instead of "BN" / "BB") for future multi-exchange support
- Exchange data now renders dynamically from `EXCHANGE_META` map — adding a new exchange only requires one new entry
- Updated table column headers: "Fund Binance" / "Fund Bybit"

## 2026-04-15

### v0.1.7 — Fix live updates not streaming to frontend
- **Root cause**: `global _clients` missing in `_push_loop()` — Python treated `_clients` as local variable due to `_clients -= dead` assignment, causing `UnboundLocalError` crash on first tick
- Removed threading Lock from AppState (unnecessary in asyncio, was blocking event loop)
- Push loop now confirmed working: snapshot + continuous updates every 500ms
- Added debug logging to WebSocket handler

### v0.1.6 — 1s chart + chart update fixes
- Added **1s timeframe** — uses in-memory live data collected since backend started
- Fixed chart not updating: added `flipped` to component key so chart remounts on flip
- Fixed live data updates not appending after history load
- Backend now returns in-memory data for `timeframe=1s`, exchange klines for everything else

### v0.1.5 — Flip direction on detail page + chart In/Out
- Added direction bar on pair detail page showing current direction (e.g. "Long BN / Short BB")
- Added flip button on detail page to reverse In/Out direction
- In/Out values shown in large prominent boxes below direction bar
- Chart lines renamed to In (green) and Out (red), respond to flip state
- Chart data swaps spread_ab/spread_ba when flipped
- Replaced Entry/Exit labels in header with single Net Spread display

### v0.1.4 — In/Out columns + flip direction
- Replaced Direction, Spread A→B, Spread B→A columns with **In** and **Out**
- In = entry cost (spread against you when entering position)
- Out = exit spread (what you capture when closing)
- Added **flip button** (↕) to reverse In/Out direction globally
- Flip button highlights blue when reversed

### v0.1.3 — Historical spread charts + timeframe selector
- Added historical kline fetching from Binance and Bybit via ccxt
- Spread chart now loads real historical data (not just since backend started)
- Added timeframe selector: 1m, 5m, 15m, 1h, 4h, 1d
- Merged historical + live data seamlessly on chart
- Added loading state while fetching history

### v0.1.2 — Frontend redesign (taste-skill) + chart crash fix
- Redesigned entire frontend using taste-skill design principles
- Deep dark palette (#050508 base), Outfit + Geist Mono fonts
- Fixed crash on ticker click: lightweight-charts v5 API change (`addSeries(LineSeries)` instead of `addLineSeries`)
- Added timestamp guards to prevent update errors
- Sticky table headers, custom scrollbar, mobile responsive
- RoboSpread header now clickable to return to main table
- Added pulse animation on live connection indicator

### v0.1.1 — Full data pipeline + web dashboard
- Pair discovery: 468 common USDT perpetual pairs (Binance + Bybit)
- Real-time mark prices + funding rates via WebSockets
- Binance: single `!markPrice@arr@1s` stream for all symbols
- Bybit: per-symbol ticker subscriptions with batched subscribe + ping/pong
- Spread calculation both directions with fee deduction (0.19% round-trip)
- FastAPI backend with REST + WebSocket endpoints
- React frontend: sortable/filterable table, dark theme
- Pair detail view with exchange info boxes + spread chart
- Hot row highlighting (>5% red, >2% warm)
- Stale data detection (grayed out if >10s without update)
- Auto-reconnection with exponential backoff
- Batched frontend push (500ms throttle)

### v0.1.0 — Project init
- Created project structure under ~/main/projects/RoboSpread/
- Set up Python + FastAPI backend, React + Vite frontend
- Implementation plan documented in plan.md
