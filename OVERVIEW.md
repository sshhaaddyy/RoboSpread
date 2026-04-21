# RoboSpread — Overview

The strategic "why" and "where to" for the project. Technical phases live in `plan.md`. Commercial evidence lives in `research/2026-04-21-arbitrage-scanner-market-research.md` and `model-chat/2026-04-21-robospread-5k-mrr-strategy.md`.

---

## What RoboSpread is

A crypto perpetual-futures **spread radar + local execution tool**. It streams mark prices and funding rates from N exchanges, ranks two opportunities per symbol — an instant price-arbitrage route and a funding-carry route — and (eventually) executes both legs for the user on their own keys.

It is not a bot platform, not a CEX, not a signal group, not custodial. The user's keys stay on the user's machine.

---

## Ultimate goal

**Build the auditable, self-hosted alternative to ArbitrageScanner.io and uacryptoinvest** — and monetize the execution layer that every scanner-only competitor refuses to ship.

Concrete target: **$5,000 MRR within 6 months** via ~50 paying users at $99/mo. Not a venture-scale outcome — a solo-operator outcome that proves the product is real and funds its own future.

---

## Who pays

**Not retail.** Retail churns at ~40%/month on crypto tools and doesn't generate enough slippage for execution to matter.

**ICP**: solo quants, prop-desk juniors, small fund ops, serious individual traders — people running a **$500k+ carry book** on their own VPS or home server, who are willing to:
- Give the tool API keys that stay on their machine
- Instrument their own risk controls
- Pay $99/mo because the alternative is missing a 30-bps trade once a week

If someone asks "can I run this on my phone," they are not the ICP.

---

## Product shape

Two things, not one.

### 1. Free open-source scanner (the funnel)

Everything RoboSpread does today, open-sourced:
- N-exchange price + funding streaming (7 venues on the roadmap)
- Interval-correct funding APR
- Per-leg deposit/withdraw freshness
- Live ranked routes (arb + funding farm)
- Self-hostable, auditable, documented

The scanner competes with uacryptoinvest ($64–80/mo) and Coinglass (free but buried) on transparency and freshness, not on feature count. **Price: $0.** The funnel.

### 2. $99/mo local-execution tier (the business)

BYO-keys, non-custodial, runs on the user's box:
- Pushover / Telegram alerts with sustained-threshold + cooldown logic
- Paper-trading engine with orderbook-depth fills
- Real execution with per-exchange arm/disarm toggle
- Fully automated mode with risk gates (position cap, daily kill switch, per-pair cooldown)

The value prop is **basis points saved per trade**, not "automation." If it doesn't measurably save slippage versus manual clicking, this tier dies at the 3-month churn mark. Must be instrumented.

---

## Where we are now

- v0.1.9 shipped, Phase 8 complete (Binance + Bybit + Hyperliquid live)
- N-exchange architecture proven — adding a venue is one registry entry + one WS subclass
- ~479 pairs tracked with 2+ legs; 176 with 3 legs
- UI is usable: ranked table, detail page, live chart, staleness, D/W badges
- **Zero users, zero distribution, zero auth, zero billing.** Solo-run tool.

## Where we're headed (6 months)

| Window | Technical milestone | Commercial milestone |
|---|---|---|
| **Day 0–30** | Phases 9–13: 4 more CEXs live, ccxt retired | Open-source the scanner; ship local-exec beta to **5 hand-picked design partners** |
| **Day 30–60** | Phases 14–16: SQLite, alerts, deploy-ready | Open a **14-day card-gated trial**; target 20 activations, ≥40% day-30 retention on beta cohort |
| **Day 60–120** | Phases 17–21: multi-route UI, paper engine, exec page | Convert trials; target **25 paid = $2.5k MRR** |
| **Day 120–180** | Phases 22–23: real execution + auto mode | Scale via EN-X + warm Discord/TG intros; target **50 paid = $5k MRR** |

Phase 24 (hardening) rolls through the whole window.

---

## Kill criteria (stop and re-scope)

From the debate, not negotiable:

- **Day 30**: beta cohort day-30 retention **<40%** → product is not sticky, pivot or kill
- **Day 60**: trial cohort yields **<10 paid conversions** → ICP is wrong, re-scope
- **Day 90**: LTV **<3 months** with no measurable slippage savings → price/product mismatch
- **Any month**: exchange API breakage causes **>48h outage** on the primary wedge → operational risk has materialized, must address before growth spend

---

## Open strategic questions

Things the debate surfaced but did not resolve. Owed back to the human:

1. **Which single CEX+DEX funding-carry pair is the wedge?** Room agreed "one wedge," did not pick. Candidates: Binance↔Hyperliquid, Bybit↔Hyperliquid, CEX-cluster↔Aster. Pick by liquidity depth and funding-interval divergence (where interval mismatch creates real APR gap).
2. **Alert tier.** Are Telegram/Pushover alerts free (funnel) or paid (sticky hook under $99)? Default: free. Worth re-testing at month 3.
3. **Distribution.** EN-X is addressable but cold; RU-TG is warmer but scammy. Decide after the first 5 beta partners show whether they came from English or Russian channels.
4. **Support burden.** At 50 paid users running local VPS installs, how many hours/week go to setup support? Unmeasured.

---

## What RoboSpread is NOT

Explicit non-goals — don't let scope drift pull you into these:

- Not a hosted brokerage. Never custodial.
- Not a signal group or Discord-based alpha shop.
- Not an all-in-one ArbitrageScanner clone. One wedge, owned well.
- Not retail. No $29 tier, no free trial without card capture.
- Not a "get-rich-quick" tool. ROI marketing is the competitor's tell, not ours.
- Not cross-platform. Desktop/VPS only. If it doesn't run on Linux, we don't support it.

---

*Sources: `plan.md` · `research/2026-04-21-arbitrage-scanner-market-research.md` · `model-chat/2026-04-21-robospread-5k-mrr-strategy.md`*
