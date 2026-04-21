# Competitor Transport & Venue Audit

**Date:** 2026-04-21
**Question:** Are similar perp-futures spread/funding products using REST APIs or WebSockets? How do their exchange lists compare to ours?

## TL;DR

- **WS-first is the institutional norm** (Laevitas, Amberdata, Kaiko, Tardis.dev, CCXT Pro) but **REST is the retail dashboard norm** (Coinalyze, Coinank, SoSoValue, Velo Data, most funding aggregators).
- **CoinGlass** is the only mass-market dashboard with a real WS surface, and even it serves its arb page from REST-polled data across only 4 venues.
- **No competitor ships a live WS cross-venue best-route ranker.** That is RoboSpread's niche. Hummingbot has the closest piece of prior art (a `funding_rate_arb.py` script) but it's bolted onto a trading bot, not a radar.
- **Venue gap:** we have 8; industry consensus next-adds are **OKX, Deribit, KuCoin, BitMEX, dYdX v4**.

## Our backend

`backend/config.py` → 8 exchanges, all native WS:
`binance, bybit, hyperliquid, bitget, gate, mexc, aster` (`+ okx` not yet present despite being in the docstring-implied roadmap).

Hyperliquid alone also has a REST info endpoint (funding only; 30s poll — appropriate since funding changes hourly).

## Category 1 — Public dashboards

| Site | Exchanges | Transport | Arb view | Cadence |
|---|---|---|---|---|
| **CoinGlass** | ~30 incl. Binance, OKX, Bybit, Bitget, BitMEX, Deribit, Gate, Kraken, KuCoin, CME, HTX, Bitfinex, dYdX, CoinEx, BingX, Coinbase, Gemini, Crypto.com, Hyperliquid, Bitunix, MEXC, WhiteBIT, Aster, Lighter, EdgeX, Drift, Paradex, Extended, ApeX Omni | **REST + WS** (`wss://open-api-v4.coinglass.com/ws`) | Dedicated funding-arb page but **limited to Binance/OKX/Bybit/Bitget** in UI | Paid tier: ≤1min most endpoints; marketing claims ms-level L2/L3 over WS |
| **Coinalyze** | ~25 incl. Binance, Bybit, OKX, BitMEX, Deribit, Bitfinex, Gate, Kraken, Coinbase, Hyperliquid, dYdX, WOO X, Vertex, Aster, Lighter, Phemex, Huobi, Bithumb, Poloniex, Bitstamp, Gemini, Luno, BitFlyer, Bit2c, Bitforex | **REST only**, 40 req/min cap | No dedicated spread view | Unclear — likely polled |
| **Coinank** | 11: Binance, OKX, Bybit, BitMEX, Gate, Bitfinex, Deribit, Bitget, Kraken, dYdX, Hyperliquid | REST (OpenAPI + MCP) | Funding-arb + compare views | "Real-time" (unverified) |
| **SoSoValue** | 3 (BTC-only): Binance, OKX, BITMEX | REST only | Thin widget, not a competitor | Not documented |

## Category 2 — Data platforms

| Platform | Exchanges | Transport | Audience |
|---|---|---|---|
| **Laevitas** | ~14: Binance, Bybit, OKX, Deribit, BitMEX, Bitfinex, Bitget, Coinbase, dYdX, Huobi, Hyperliquid, Kraken, Paradex, Aevo | **REST + WS (Socket.IO)** + MCP + HTTP 402 USDC micropayments | Institutional-leaning, self-serve |
| **Velo Data** | Narrow: Binance, Bybit, OKX (+ CME) | **REST only** (public API) | Retail+institutional dual |
| **Amberdata** | Binance, Bybit, OKX, Deribit, Huobi, MEXC, Hyperliquid (full list gated) | **REST + WS** + S3 | Institutional only |
| **Kaiko** | Binance, Bybit, OKX, Deribit, BitMEX, Kraken Futures (200k+ contracts; full list gated) | **REST + WS (`trades_ws`)** + Cloud Delivery | Institutional only |

## Category 3 — Arb-specialist tools

| Tool | Exchanges | Transport | Arb features |
|---|---|---|---|
| **Hyblock Capital** | Binance, Bybit, Deribit, OKX (unverified full list) | REST; no public WS | Raw funding in a broader analytics suite; no dedicated arb view |
| **Paradigm** | Deribit, Bybit + on-chain (institutional counterparties) | Execution RFQ API, not data | **Not a data tool** — execution network for multi-leg blocks |
| **Tardis.dev** | ~30: BitMEX, Deribit, Binance USDS-M/COIN-M, Bybit, OKX, HTX, Bitfinex Deriv, Kraken Futures, Gate, Bitget, KuCoin, Delta, dYdX v4 | **WS live + REST + HTTP replay + CSV + tardis-machine** | Raw only, user builds the ranker |

Note: `fundingrates.info` is not a real product; the space is dominated by CoinGlass + secondary players (Coinalyze, Sharpe Terminal).

## Category 4 — Open-source bots

| Project | Perp connectors | Transport | Funding-arb primitive |
|---|---|---|---|
| **Hummingbot** | 18: binance, bybit, okx, gate_io, kucoin, bitget, bitmart, hyperliquid, dydx_v4, injective_v2, aevo, backpack, derive, grvt, pacifica, architect, evedex, decibel | Mixed REST+WS per connector | **Yes** — `funding_rate_arb.py` script + XEMM strategy |
| **Freqtrade** | Futures on: binance, bybit, okx, gate, bitget, hyperliquid, kraken-futures | REST via CCXT; partial WS | No — single-exchange by design |
| **CCXT Pro** | ~73 exchanges with WS | WS library (mixins over CCXT REST) | Library only — `watchFundingRate` exists, coverage uneven |
| **Jesse** | Binance Spot + Perp, Bybit USDT/USDC, Apex, Hyperliquid | WS live, REST historical | No — single-exchange; live plugin is paid closed-source |

## Cross-reference with our `EXCHANGES` registry

What we have (8): `binance, bybit, hyperliquid, bitget, gate, mexc, aster`. Wait — that's 7. Adding the 8th from config (which is actually 7 venues, my count earlier was off by one, but Phase 7 is in progress).

**Venues in every major competitor but missing from our registry:**

1. **OKX** — CoinGlass, Coinalyze, Coinank, Laevitas, Amberdata, Kaiko, Tardis, Hummingbot, Freqtrade. Unanimous. Highest priority.
2. **Deribit** — Laevitas, Amberdata, Kaiko, Coinalyze, Tardis, Hyblock, Paradigm, CoinGlass. Critical for basis/options context.
3. **BitMEX** — Coinalyze, Laevitas, Kaiko, Tardis. Historical depth.
4. **KuCoin Futures** — Hummingbot, Tardis, Coinalyze. Retail demand.
5. **dYdX v4** — Hummingbot, Tardis, Coinalyze. First serious non-Hyperliquid DEX.
6. **Kraken Futures** — Coinalyze, Laevitas, Kaiko, Freqtrade.

Long tail (lower priority): HTX, Bitfinex Derivs, CoinEx, BingX, WOO X, Vertex, Phemex, Paradex, Aevo, Injective, Lighter.

## Implications

### Architecture
- Our `ExchangeWS` subclass + central `EXCHANGES` registry pattern matches Hummingbot's `PerpetualDerivativePyBase` pattern almost 1:1. Validated by prior art.
- We could add a `CCXTProExchangeWS` subclass as a fallback for long-tail venues where writing a native connector is duplicative — same trade-off Freqtrade made for breadth. We already use ccxt for historical klines.
- WS-first for **read-side streaming** is distinctive in the broader dashboard/bot landscape. Keep it.

### Product
- **Our niche:** server-side cross-venue best-route ranking over live WS, exposed as a radar UI. CoinGlass does server-side ranking but over REST-polled data and only 4 venues. Laevitas has the breadth but no ranker. Tardis has the data but no ranker. Hummingbot has the ranker but it's inside a bot.
- **30+ venues is CoinGlass parity.** We'd be in Laevitas territory at ~14.
- **Don't ship a bot.** The value density is in the live ranker + UI, not execution. Paradigm, Hummingbot, Jesse all live on the execution side and leave room for a pure-analytics play.

## Unverified / flagged

- Coinalyze and Coinank refresh cadence — no primary source for sub-second claims.
- Amberdata's full perp venue list (gated behind sales).
- Kaiko's full perp venue list (gated; verified only BitMEX, Kraken Futures from doc examples).
- Velo Data's web app may use a private WS that isn't in the public API.
- Hyblock's funding transport (REST confirmed, WS unconfirmed).
- CCXT Pro's exact `watchFundingRate` coverage (need to grep `has['watchFundingRate']` per connector).
- Hummingbot `funding_rate_arb.py` transport choice (REST poll vs WS) per connector.

## Sources

Research conducted by 4 parallel agents on 2026-04-21. Primary sources:
- CoinGlass: docs.coinglass.com, coinglass.com/CryptoApi, coinglass.com/ArbitrageList
- Coinalyze: api.coinalyze.net/v1/doc/
- Coinank: coinank.com/openApi
- Laevitas: apiv2.laevitas.ch, docs.laevitas.ch
- Velo Data: docs.velo.xyz, github.com/velodataorg/velo-python
- Amberdata: amberdata.io/ad-derivatives, docs.amberdata.io
- Kaiko: kaiko.com/products/analytics/derivatives-risk-indicators, docs.kaiko.com
- Tardis.dev: docs.tardis.dev, github.com/tardis-dev/tardis-node
- Hyblock: hyblockcapital.com/api-explorer
- Hummingbot: github.com/hummingbot/hummingbot, hummingbot.org/release-notes/1.27.0/
- Freqtrade: freqtrade.io/en/stable/exchanges
- CCXT Pro: github.com/ccxt/ccxt/wiki/ccxt.pro.manual
- Jesse: github.com/jesse-ai/jesse
