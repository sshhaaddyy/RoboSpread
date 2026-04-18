# RoboSpread — Implementation Plan

## Context
Ronnie wants a personal crypto futures spread/arbitrage radar that scans all USDT perpetual pairs common to Binance and Bybit, calculates real-time price spreads + funding rates, and displays them in a web dashboard with charts. Alerts for spreads > 5%. Telegram and auto-trading come later.

## Architecture

```
Binance WS (markPrice@arr@1s) ──┐
                                 ├─► state.update_price() ─► spread_calc ─► spread_history
Bybit WS (tickers.{symbol}) ───┘                                              │
                                                                               ▼
                                                                     FastAPI WS → Browser
                                                                               │
                                                                    ┌──────────┴──────────┐
                                                                    SpreadTable        SpreadChart
```

## Project Structure

```
projects/RoboSpread/
├── backend/
│   ├── main.py                  # FastAPI entry, starts WS connections + serves API
│   ├── config.py                # Constants: fees, thresholds, WS URLs
│   ├── exchange/
│   │   ├── __init__.py
│   │   ├── base.py              # Abstract WS connector
│   │   ├── binance_ws.py        # Binance futures WS (single !markPrice@arr@1s stream)
│   │   ├── bybit_ws.py          # Bybit futures WS (per-symbol tickers, batched)
│   │   └── pair_discovery.py    # ccxt: find common USDT perp pairs
│   ├── engine/
│   │   ├── __init__.py
│   │   ├── spread_calc.py       # Spread math with fee deduction
│   │   ├── state.py             # In-memory state + spread history (deque per symbol)
│   │   └── alerts.py            # Threshold checking
│   ├── api/
│   │   ├── __init__.py
│   │   ├── routes.py            # GET /api/pairs, GET /api/history/{symbol}
│   │   └── ws_handler.py        # WS /ws endpoint, pushes updates to frontend
│   └── requirements.txt
├── frontend/
│   ├── index.html
│   ├── package.json
│   ├── vite.config.js
│   └── src/
│       ├── main.jsx
│       ├── App.jsx              # WS connection, routing
│       ├── components/
│       │   ├── SpreadTable.jsx  # Sortable table of all pairs
│       │   ├── SpreadRow.jsx    # Single row
│       │   ├── SpreadChart.jsx  # lightweight-charts (red/green lines)
│       │   └── PairDetail.jsx   # Detail view with exchange info + chart
│       ├── hooks/
│       │   └── useWebSocket.js
│       └── utils/
│           └── format.js
├── run.sh                       # One-command launcher
└── .gitignore
```

## Key Design Decisions

**Binance `!markPrice@arr@1s`**: Single stream pushes ALL mark prices every 1s — no per-symbol subscription needed. Parse only common pairs, discard rest.

**Bybit per-symbol tickers**: Must subscribe individually. Max 10 args per subscribe message → batch with 50ms delay. Requires ping every 20s.

**Spread calculation**: `raw_spread = ((price_A - price_B) / price_B) * 100`. Round-trip fees = `2 * (0.04% + 0.055%) = 0.19%`. Net spread = raw - 0.19%. Calculate both directions (long A/short B and long B/short A).

**Funding Spread APR**: `(funding_rate_A - funding_rate_B) * 3 * 365 * 100`

**In-memory storage**: `deque(maxlen=3600)` per symbol = ~1hr of 1s snapshots. ~200 pairs × 3600 × 100 bytes ≈ 72MB. Fine for local.

**Frontend throttling**: Batch updates every 500ms to avoid flooding React with 200 updates/sec.

**Staleness**: Track `last_update_timestamp` per exchange per symbol. Mark as STALE if > 10s old.

## Tech Stack

**Backend**: Python, FastAPI, uvicorn, websockets, ccxt, aiohttp, pydantic
**Frontend**: React 19, Vite 6, lightweight-charts 4.2 (TradingView)
**Charts**: Two line series per pair — red (short A / long B), green (short B / long A), with In/Out horizontal markers

## Implementation Order

### Phase 1 — Data engine skeleton
1. `config.py` — all constants
2. `exchange/pair_discovery.py` — discover common pairs via ccxt
3. `engine/spread_calc.py` — core spread math
4. `engine/state.py` — in-memory state with update + history
5. `main.py` — bare FastAPI app, runs discovery on startup

### Phase 2 — Exchange WebSockets
6. `exchange/base.py` — abstract base
7. `exchange/binance_ws.py` — connect, parse markPrice stream
8. `exchange/bybit_ws.py` — connect, subscribe tickers, handle ping/pong
9. Wire into main.py as background tasks
10. Test: verify prices flowing, print spreads to console

### Phase 3 — Backend API
11. `api/routes.py` — REST endpoints
12. `api/ws_handler.py` — WS endpoint for frontend (with 500ms batching)
13. Wire into main.py, add CORS middleware

### Phase 4 — Frontend table view
14. Scaffold React app with Vite
15. `useWebSocket.js` hook
16. `SpreadTable.jsx` + `SpreadRow.jsx` — sortable table, dark theme
17. `App.jsx` — connect everything
18. Dark theme CSS matching reference screenshots

### Phase 5 — Detail view + charts
19. `PairDetail.jsx` — side-by-side exchange info boxes
20. `SpreadChart.jsx` — lightweight-charts with red/green spread lines
21. History endpoint for chart backfill
22. Click-to-detail navigation

### Phase 6 — Polish
23. `engine/alerts.py` + row highlighting for > 5%
24. `run.sh` launcher script
25. Reconnection logic (exponential backoff)
26. `.gitignore`, README

## Gotchas
- **Symbol normalization**: Compare base+quote from ccxt markets, not raw strings (e.g., `1000SHIBUSDT` vs `SHIBUSDT`)
- **Bybit ping/pong**: Must send ping every 20s or connection drops
- **Binance reconnect**: Subscription is in the URL, just reconnect. Bybit: must re-subscribe all symbols
- **CORS**: Dev mode needs FastAPI CORS middleware for localhost:5173
- **Price staleness**: If one exchange WS drops, spreads show stale data — must detect and flag

## Verification
1. Run `python backend/main.py` — should print discovered common pairs
2. After Phase 2: console should show live price updates and calculated spreads
3. After Phase 3: `wscat -c ws://localhost:8000/ws` should show streaming JSON
4. After Phase 4: browser at localhost:5173 shows live-updating spread table
5. After Phase 5: clicking a pair shows detail view with live chart
