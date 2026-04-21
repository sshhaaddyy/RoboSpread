# Crypto Arbitrage Scanner / Spread Radar — Market Research

**Original question:** Competitive and market research on crypto arbitrage scanner / spread radar products similar to RoboSpread — what competitors lack, what we can do better, what we miss.

**Research date:** 2026-04-21

**Method:** Fan-out / fan-in research (`/research` skill). 6 parallel sonnet researchers on distinct angles → opus Landscape synthesis → 1 gap-closing follow-up (chrome-devtools MCP inspection of uacryptoinvest) → opus addendum.

**Angles researched:**
1. Named 4 competitors deep-dive (uainvest, arbitragescanner.io, arbitrage-services.com, uacryptoinvest) — deep
2. Global data leaders (Coinglass, CoinAnk, Laevitas, Hyblock, Velo, Coinalyze) — standard
3. RU/UA arbitrage market (Telegram ecosystem, P2P dominance, scam landscape) — standard
4. Open-source scanners (Hummingbot, Freqtrade, GitHub CCXT projects) — quick
5. DEX-CEX & cross-chain arb (FundingView, Loris Tools, Hyperliquid) — quick
6. Pricing & business-model patterns across segments — standard

---

## Executive summary

The crypto perpetual-futures arbitrage scanner market splits into four competitive categories. **(1) Global derivatives data leaders** (Coinglass, Coinalyze, Laevitas, CoinAnk) sell broad dashboards where arbitrage is one view among many; only Coinglass ships a true ranked cross-exchange funding-rate arb scanner. **(2) Commercial arb-scanner suites** (ArbitrageScanner.io, arbitrage-services.com, uacryptoinvest.com) are subscription products that bundle CEX-CEX, CEX-DEX, funding, and sometimes P2P scanners, priced $33–$795/mo with a RU/UA-heavy marketing footprint. **(3) DEX-native and CEX+DEX hybrid tools** (FundingView, Loris Tools) are small, free or referral-funded, and thinly tooled but growing fast around Hyperliquid. **(4) Open-source** (jose-donato's scanner, Hummingbot, hzjken framework) covers fragments but no single project combines live WS data, both price and funding arb, interval-normalized APR, deposit/withdraw status, and a ranked UI.

Against this landscape, RoboSpread's current feature set is unusually tight for a personal project: sub-second WebSocket ingest, N-exchange leg model, per-exchange funding-interval normalization, and live deposit/withdraw status. **However — critical finding from gap-close: uacryptoinvest.com (Ukrainian, $64–$80/mo) already implements all three of these correctly.** Funding APR is verified interval-correct (ASTEROID/ARIA/SIREN arithmetic matches true intervals to within rounding); per-leg deposit/withdraw indicators are shown across ~17 venues, not just Binance; and symbol coverage reaches 41 legs per symbol. RoboSpread's original claimed wedge has substantially collapsed.

The revised positioning opportunity is narrower: **auditable, local, sub-second, open-source**. The $15–25/mo commercial slot is no longer viable — uacryptoinvest dominates that band on breadth. Pivot the value prop to "self-hosted radar with source-visible APR math, no vendor trust required, 0.5s push latency." Top roadmap priority remains adding Hyperliquid as the first DEX leg, but now to match rather than exceed uacryptoinvest's footprint. See Addendum for the full revision.

## Competitor profiles

**Coinglass** — The closest conceptual match among global data leaders. `/ArbitrageList` ships two dedicated views: "Arbitrage Between Spot and Perpetual" and "Different Funding Rates Cross Exchanges," both with PNL/APR columns. Exchange coverage includes Binance, OKX, Bybit, Bitget, and others. Web UI has a free tier; API tiers run $29–$699/mo. Near-real-time UI with iOS+Android apps.

**ArbitrageScanner.io** — Broadest commercial suite: 80+ CEX, 25+ DEX across 40+ chains, 1–4s refresh, covering CEX-CEX spot, futures-futures, spot-futures, funding (0.15%/8h advertised), CEX-DEX, DEX-futures. Telegram alerts at most tiers. No API, no auto-trading. Pricing: START $99 / BUSINESS $195 / PLATINUM $397 / ENTERPRISE $795 monthly; 6–15mo bundles up to WHALE $9,990; white-label $19,999–$199,999. Marketing claims "10–15% monthly returns" and "15–25% per round-trip"; Trustpilot 3.9, ScamAdviser medium-risk, anonymous ownership. Sets the ceiling of retail arb-scanner pricing.

**arbitrage-services.com** — Cleaner, Russian-language scanner with 24 CEX for inter-exchange, 13 chains / 10 CEX / 8 DEX aggregators for DEX-CEX. Covers spot-spot, futures-futures, spot-futures, DEX-CEX, DEX-futures. Meaningful differentiator: pre-checks deposit/withdrawal availability and network compatibility before surfacing a route. 5s refresh, 6,000+ coins. Browser push + Telegram alerts, no API. Pricing Week $33 / Month $75 / Lifetime $390 USDT (inter-exchange only). Strong YouTube tutorial channel, more credible claims than ArbitrageScanner.

**uacryptoinvest.com/arbitrage** — The closest live analog to RoboSpread, and the most important competitor. Real-time perp-perp funding+price scanner over Binance, Bybit, MEXC, Gate, KuCoin, OKX, WhiteBIT, and ~10 more venues. Configurable refresh (Live/1s/5s/10s/30s). Free tier shows 15 symbols; symbols on premium show 2–41 legs each (median 9, max 41). Material Design web app, EN+UA, sortable table with 1d/7d/30d cumulative APR, funding spread APR, open spread. Alerts Premium-gated. Pricing: free tier + Premium $64–$80/mo depending on term ($768/yr at 12mo). **Gap-close finding: funding APR is interval-correct, not 8h-assumed; per-leg deposit/withdraw status shown across all venues.** No ROI marketing language — a notable positive trust signal.

**uainvest.com.ua** — Not a scanner. Ukrainian retail finance portal with a `/arbitrage` page that is an affiliate-link hub plus editorial. An internal automation bot exists but is gated by application, not a product. Relevance: category anchor for "referral-funded content site" business model, not a product competitor.

**FundingView** (fundingview.app) — 12+ perp DEXs (Hyperliquid, Paradex, Backpack, Orderly, Lighter), delta-neutral surfacing for 150+ pairs, completely free on a referral-revenue model. Does NOT cover CEX. Demonstrates that a CEX+DEX hybrid radar is a genuine market gap.

**Loris Tools** — Scans DEX-CEX funding pairs (Binance vs Hyperliquid, OKX vs Drift) with interval normalization. Smallest footprint of any named tool but the *structurally* closest to RoboSpread — same interval-aware APR philosophy, extended to DEX.

**Coinalyze** (coinalyze.net) — 15–25 derivatives exchanges, multi-exchange funding overlays + alerts on spread thresholds. No ranked arb table. Core data free; ad-free subscription is paid. Strong free-tier baseline to beat.

**jose-donato/crypto-futures-arbitrage-scanner** — Closest OSS structural analog: Go+JS, WS feed from 9 exchanges (incl. Hyperliquid, OKX, Kraken, Paradex), live matrix, lightweight-charts. Gaps: no funding rates, 4 symbols only, no interval normalization, no deposit/withdraw status. 126⭐ and maintenance unclear.

**P2P Army** ($95–$319/mo) — Category anchor for RU/UA P2P scanners. Irrelevant to RoboSpread's perp focus but critical context: the RU/UA arb market is dominated by P2P, not perp-futures, which means RoboSpread's adjacent audience has scanner-purchase habits but different product expectations.

## Feature matrix

| Feature | Coinglass | ArbitrageScanner | Arbitrage-Services | uacryptoinvest | FundingView | Loris Tools | Coinalyze | jose-donato OSS | **RoboSpread** |
|---|---|---|---|---|---|---|---|---|---|
| CEX-CEX price (spread) arb | ✓ (spot-perp) | ✓ | ✓ | ✓ | ✗ | ✗ | partial | ✓ | ✓ |
| CEX-CEX funding arb | ✓ | ✓ | ✓ | ✓ | ✗ | partial | partial (overlay) | ✗ | ✓ |
| DEX-CEX arb | ✗ | ✓ | ✓ | ✓ (premium) | partial | ✓ | ✗ | partial | ✗ |
| Multi-exchange funding interval normalization | partial | ✗ (8h assumed) | unclear | ✓ (verified) | N/A | ✓ | ✗ | ✗ | ✓ |
| Live WS sub-second | partial | ✓ (1–4s) | ✗ (5s) | ✓ (configurable) | unclear | unclear | ✓ | ✓ | ✓ (0.5s push) |
| Per-coin deposit/withdraw status | ✗ | ✗ | ✓ | ✓ (multi-venue) | ✗ | ✗ | ✗ | ✗ | ✓ (Binance only) |
| Ranked scanner UI | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✗ | ✓ | ✓ |
| Alerting (TG/push) | partial | ✓ | ✓ | ✓ (premium) | ✗ | unclear | ✓ | ✗ | ✗ |
| API access | ✓ ($29–$699) | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | N/A (self-host) | ✗ |
| Mobile app | ✓ (iOS+Android) | ✗ | ✗ | partial (responsive) | ✗ | ✗ | ✗ | ✗ | ✗ |
| Self-host | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✓ | ✓ |
| Open source | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✓ | ✗ [opportunity] |

## Standouts — what specific competitors do unusually well

- **Coinglass** — ranked scanner is genuinely clean and the only one of the global-data leaders that commits to arb as a first-class view, not an overlay. Worth borrowing: dual-view split (spot-perp vs cross-exchange funding) as distinct tabs.
- **uacryptoinvest** — deep symbol coverage (2–41 legs per symbol) + cumulative 1d/7d/30d funding APR columns. Interval-correct APR math (verified). Refreshingly no ROI marketing. Their table design is the best retail-facing example of a perp funding radar in the landscape.
- **arbitrage-services.com** — pre-flight check of deposit/withdrawal availability *and network compatibility* before surfacing a route. RoboSpread has the data (per-coin deposit/withdraw status) but should escalate it into route filtering, not just a UI badge.
- **ArbitrageScanner** — breadth (80+ CEX, 25+ DEX) and the 50% recurring affiliate program. The affiliate design is the real moat; it funds influencer distribution that smaller tools can't match.
- **FundingView** — proves a referral-revenue free product can cover 12+ DEXs and 150+ pairs sustainably. Evidence that exchange-referral economics alone can fund a credible tool.
- **Coinalyze** — monetizes API, not UI. Core data fully free forever is an aggressive positioning move against paid dashboards.
- **jose-donato OSS** — uses lightweight-charts for the live matrix (same stack as RoboSpread) and covers 9 exchanges including Hyperliquid, Paradex, Kraken. Proof that the technical scope is achievable for one developer.

## White space — gaps in the market

- **Unified CEX+DEX funding-farm radar.** FundingView is DEX-only, Coinglass is CEX-only, arbitrage-services and ArbitrageScanner treat DEX-CEX as spot arb not funding carry. Nobody ranks a CEX-perp vs DEX-perp funding carry route in one table. uacryptoinvest has DEX behind premium only.
- **Documented freshness / auditable methodology.** Every paid scanner is a black box — no timestamped source links, no explicit polling cadence display, no source-visible APR math. uacryptoinvest's deposit/withdraw status icons have no refresh timestamp. A scanner that surfaces "last polled 14s ago" per datum and publishes its computation is differentiated.
- **Open-source core + hosted premium** (the Grafana/Metabase pattern). Zero players execute this in this niche.
- **API-first, no-UI tier.** Coinglass bundles dashboard with API. Raw low-latency WS feed per symbol/exchange has no occupant.
- **BYO exchange keys → personalized executable spread.** No scanner uses the user's own VIP fee tier to show their actual net edge. All use flat taker assumptions.

## Gaps — what RoboSpread is missing vs. competitors

- **Exchange breadth.** 2 legs (Binance+Bybit) vs. competitors at 7–80+. Even uacryptoinvest free tier hits 7 CEX and premium reaches ~17.
- **No DEX legs.** Hyperliquid alone represents ~70% of perp DEX volume at $10B+/day. Low-cost to add given N-exchange architecture.
- **No alerting.** Table stakes above $30/mo.
- **No API.** Table stakes at the $299+ Coinglass tier.
- **No mobile app.** Coinglass has iOS+Android; uacryptoinvest is responsive.
- **No historical depth beyond 3600-tick ring.** Competitors show 1d/7d/30d cumulative APR (uacryptoinvest) and 5+ years history (Laevitas).
- **No cumulative funding APR column.** uacryptoinvest's 1d/7d/30d rollups are a UX standard RoboSpread doesn't meet.
- **Deposit/withdraw status only from Binance.** uacryptoinvest shows it across ~17 venues; extending to per-venue status is now a parity feature, not a differentiator.
- **No auth / multi-tenant.** Irrelevant for personal use but blocks commercialization.
- **No distribution.** Competitors run Telegram+YouTube+affiliate funnels; RoboSpread has none.

## Positioning recommendation for RoboSpread

**Original positioning wedge ("honest perp funding radar — interval-correct APR, transferable coins only, CEX+DEX in one table") is dead.** The gap-close revealed uacryptoinvest already ships interval-correct APR, multi-venue deposit/withdraw status, and 2–41-leg symbol coverage. See Addendum below for the revised recommendation.

---

## Addendum

**What changed.** All three technical differentiators in the original positioning recommendation collapsed under gap-close. uacryptoinvest.com already ships interval-correct funding APR (verified against ASTEROID/ARIA/SIREN to within rounding), per-leg deposit/withdraw status across ~17 venues (not just Binance), and N-exchange coverage up to 41 legs per symbol. The "honest perp funding radar" wedge as written is dead.

**Revised wedge.** What survives is narrower and less marketable: (1) **documented freshness provenance** — RoboSpread's 60s `bapi` poll is explicit; uacryptoinvest exposes no refresh timestamp. (2) **self-hosted / local-single-user** — no paywall, no rate limits, no trust-the-vendor on methodology (source-visible APR math). (3) **latency floor** — 0.5s push loop on a local WS beats any hosted scanner's polling cadence for a single user watching a handful of pairs. Lead with "auditable, local, sub-second" — not "honest" or "interval-correct" (table stakes now).

**Roadmap reshuffle.**
1. **Hyperliquid leg — still #1, but reframed.** No longer "expand N"; now "add the one major venue uacryptoinvest's coverage thins out on" and the highest-volume on-chain perp. Verify uacryptoinvest's HL depth before committing.
2. **New #2: deposit/withdraw freshness + provenance surface** — timestamped per-venue D/W, source link, poll-cadence display. The one dimension where uacryptoinvest is demonstrably opaque. Cheap to ship, directly attacks their weakest flank.
3. **Alerting — demote to #3.** Uacryptoinvest likely has this on paid tiers; it's not a wedge, it's parity.

**Commercialization.** The $15–25/mo slot is no longer viable as a thin-feature discount play — uacryptoinvest at $64–80 already dominates on breadth. Drop paid SaaS ambitions. Pivot to **open-source / self-hosted** (GitHub, BYO-API-keys, optional Docker). Monetization, if any, is donations or a hosted-convenience tier at $5/mo, not a competitor to uacryptoinvest.

---

## Evidence footnotes — gap-close arithmetic

Verification that uacryptoinvest computes funding APR interval-correctly (not 8h-assumed):

- **ASTEROID** (Mexc 4h / Gate 4h): displayed F Spread APR = 1051.86%. Expected at true 4h: (0.50% − 0.02%) × (24/4) × 365 = 1051.2%. Match within rounding.
- **ARIA** (Mexc 4h / Kucoin 1h): displayed = −1298.67%. Kucoin annual at 1h: −0.15% × 24 × 365 = −1314%. Under 8h assumption: −164.25% (off ~8×).
- **SIREN** (Mexc 4h / Gate 1h): displayed = 569.18%. Mixed-interval computation gives ~591% (≈ within fee drag); 8h assumption would yield ~77%.

Leg-count distribution (15 free-tier symbols on uacryptoinvest): [2, 41, 9, 6, 9, 7, 17, 22, 7, 8, 2, 9, 8, 40, 13]. Median 9, max 41 (RAVE), total 200 legs across 15 symbols (avg ~13 per symbol).

Deposit/withdraw icons: `check_circle` (open) / `do_not_disturb_on` (paused). 39 open / 9 paused across 200 legs in the free-tier sample. No refresh timestamp exposed in the UI.

---

## Sources

- https://uainvest.com.ua/
- https://uainvest.com.ua/arbitrage
- https://uainvest.com.ua/crypto-arbitrage-bot
- https://arbitragescanner.io/
- https://arbitragescanner.io/plans
- https://arbitragescanner.io/white-label-arbitrage
- https://arbitrage-services.com/
- https://www.youtube.com/@Arbitrage_Services
- https://uacryptoinvest.com/arbitrage
- https://uacryptoinvest.com/premium
- https://www.coinglass.com/
- https://www.coinglass.com/ArbitrageList
- https://www.coinglass.com/pricing
- https://coinank.com/
- https://apps.apple.com/us/app/coinank-live-crypto-tracker/id6444732071
- https://laevitas.ch/
- https://app.laevitas.ch/assets/perpswaps/btc/funding
- https://spread.laevitas.ch/section/concepts
- https://hyblockcapital.com/
- https://hyblockcapital.com/pricing
- https://academy.hyblockcapital.com/product-announcements/trade-to-access-free-hyblock
- https://velodata.app/
- https://docs.velo.xyz/
- https://docs.velo.xyz/web-app/market
- https://coinalyze.net/
- https://www.bitget.com/academy/coinalyze-crypto-too
- https://p2p.army/
- https://argop2p.com/
- https://p2p-surfer.com/
- https://p2pmachine.io/
- https://monetory.io/
- https://arbitrage-radar.com/
- https://arbitrage.expert/
- https://koinknight.com/
- https://fundingview.app/
- https://loris.tools/
- https://github.com/hummingbot/hummingbot
- https://hummingbot.org/strategies/v1-strategies/spot-perpetual-arbitrage/
- https://github.com/freqtrade/freqtrade
- https://github.com/jose-donato/crypto-futures-arbitrage-scanner
- https://github.com/hzjken/crypto-arbitrage-framework
- https://github.com/kir1l/Funding-Arbitrage-Screener
- https://github.com/hamood1337/CryptoFundingArb
- https://github.com/StepanTita/crypto-trading
- https://dev.to/foxyyybusiness/i-built-a-free-7-exchange-funding-rate-arbitrage-scanner
- https://hyperliquid.xyz/
- https://eigenphi.io/
- https://www.bitsgap.com/pricing
- https://cryptoarbitragescreener.com/
- https://www.gunbot.com/
- https://www.trustpilot.com/review/arbitragescanner.io
- https://www.scamadviser.com/check-website/arbitragescanner.io
- https://www.scam-detector.com/validator/arbitragescanner-io-review/
- https://habr.com/ru/companies/jetinfosystems/articles/893838/
- https://vc.ru/money/2306543-telegram-ak-arbitrazh-razoblachenie-moshennichestva
- https://vc.ru/money/2216484-luchshie-skany-dlya-arbitrazha-kriptovalyut
- https://vc.ru/crypto/1136272-novyi-skaner-dlya-mezhbirzhevogo-arbitrazha-kriptovalyuty-i-imya-emu-arbitrage-radar
- https://profinvestment.com/p2p-arbitrage-scam/
- https://profinvestment.com/p2p-arbitrage/
- https://cyberleninka.ru/article/n/arbitrazh-kriptovalyut-i-protsessing-platezhey-riski-ugolovnogo-presledovaniya
- https://atomicwallet.io/academy/articles/perpetual-dexs-2025
- https://saasworthy.com/product/arbitragescanner-io

---

_Generated 2026-04-21 via `/research` skill (6-angle fan-out + 1 gap-close round)._
