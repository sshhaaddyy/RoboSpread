# RoboSpread Changelog

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
