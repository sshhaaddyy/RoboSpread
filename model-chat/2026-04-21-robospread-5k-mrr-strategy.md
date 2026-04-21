# RoboSpread $5k MRR strategy — 5-agent debate

**Topic:** How should RoboSpread reach $5k MRR — which market, which feature bundle, which distribution?

**Date:** 2026-04-21
**Rounds:** 5 (hard cap). K=2 stability early-stop not triggered.
**Roster:** Skeptic · Domain expert (crypto trading / fintech) · User advocate · Pragmatist · Synthesizer (opus)

---

## Final synthesis

### Consensus

Two-tier product (free OSS scanner + $99/mo local-execution tier with BYO-keys, non-custodial), targeting solo quants / prop-desk juniors managing a ~$500k+ carry book, via a beta-first rollout to 5 design partners before opening a card-gated trial. **Stabilized at Round 4** (3 of 4 non-synth agents aligned; Skeptic held conditional dissent).

### Remaining disagreements

- **Proceed only under retention instrumentation** — held by Skeptic. Without measured 30-day depositor retention ≥40%, the business is not sticky and should pivot or kill rather than scale spend.
- **Open trial with card capture upfront** — held by Expert. Trial friction must gate tire-kickers immediately; 50 × $99 beats 200 × $29 only if activation is qualified at day 0.
- **No middle tier ever** — held by User advocate. $29 is a retention trap (40%/mo churn); anyone who won't pay $99 is not the ICP.
- **Beta-before-trial sequencing** — held by Pragmatist. Exchange API breakage is the #1 operational risk; 5 design partners must prove stability before any public trial.

### Open questions surfaced

- What slippage savings (bps per round-trip) does local-exec actually deliver vs manual execution? LTV hinges on this and is unmeasured.
- Is EN-X reachable solo without an existing following, or does RU-TG (warmer but scammy) become necessary?
- Which single CEX+DEX funding-carry pair is the defensible wedge (the room agreed on "one wedge" but did not pick it)?
- What is the per-user VPS/home-server support burden at 50 paid users?
- How does the product survive a major exchange API break mid-demo?

### Round-over-round notes

- **Token stabilization:** 2-tier free+$99 consensus first formed in **Round 3** and held through Rounds 4–5. K=2 early-stop not triggered because Skeptic's conditional dissent persisted.
- **Flips:**
  - **Skeptic** moved from `KILL_AUTOEXEC` (R1) to conditional acceptance (R2) once BYO-keys/non-custodial framing was introduced — liability vector shifted from product to user.
  - **User advocate** moved from `NEED_EXECUTION` (R1) to `BYO_ORCHESTRATION` (R2) — accepted that "orchestration, not custody" satisfies the execution demand.
  - **Expert** stripped unconfirmed distribution channels in R3 after Skeptic's challenge on arb-audience sizing.
  - **Pragmatist** held `SINGLE_WEDGE` / beta-first across all five rounds.

### Prioritized action plan

**30-day MVP scope**
- Ship free OSS scanner (current N-exchange + funding APR + D/W status) publicly.
- Ship local-exec beta (BYO-keys, non-custodial, runs on user's VPS/home server) to **5 design partners** hand-picked from solo-quant / prop-desk-junior ICP.
- Instrument from day 1: 30-day depositor retention, daily-active, exchange-API-uptime per leg, slippage-saved-per-trade.
- Pick and commit to **one** CEX+DEX funding-carry wedge (room did not pick; decision owed).

**6-month path to $5k MRR**
- **Day 0–30** — beta to 5 partners, ≥3 running daily by day 30.
- **Day 30–60** — open card-gated 14-day trial; target **20 activations**, ≥40% day-30 retention on beta cohort.
- **Day 60–120** — convert trials; target **25 paid × $99 = $2.5k MRR**.
- **Day 120–180** — scale via EN-X + warm Discord/TG intros; target **50 paid × $99 = $5k MRR**.

**Kill criteria**
- Day-30 depositor retention **<40%** on beta cohort → pivot or kill (Skeptic).
- Day 60: **<10 paid conversions** from trial cohort → ICP is wrong, re-scope.
- Day 90: **LTV <3 months** with no measurable slippage savings → pricing/product mismatch (User advocate).
- Any month where exchange API breakage causes **>48h outage** on primary wedge → operational risk has materialized (Pragmatist).

---

## Full transcript (rounds 1–5)

### Round 1 — initial stances

- **Skeptic** — `KILL_AUTOEXEC`. Auto-execution kills the product: regulatory/liability bomb, custody implications, users blame tool for losses. ArbitrageScanner's "manual only" is not marketing theater, it's the legal posture.
- **Expert** — `WEDGE_FUNDING_CARRY`. Single wedge (CEX+DEX funding carry radar) beats all-in-one. All-in-one is undifferentiated from Coinglass. One defensible wedge > five shallow features.
- **User advocate** — `NEED_EXECUTION`. Real traders want execution, not more tables. Scanner-only is a commodity; the pain is the last mile.
- **Pragmatist** — `SINGLE_WEDGE`. Solo builder cannot maintain all-in-one across CEX + spot-DEX + perp-DEX. Pick ONE wedge, own it.
- **Synthesizer** — `UNRESOLVED`. Three active tensions: (a) execution vs liability, (b) wedge vs all-in-one, (c) EN-X vs RU-TG distribution.

### Round 2 — BYO-keys reframe

- **Skeptic** — `BYO_KEYS_OK`. Conditionally accepts auto-exec IF keys stay on user's machine and product is explicitly non-custodial. Liability vector shifts from product to user.
- **Expert** — `WEDGE_WITH_BYO_EXEC`. Confirms funding-carry wedge stands; BYO-keys local execution is the premium upsell. Signal + orchestration, never custody.
- **User advocate** — `BYO_ORCHESTRATION`. Shifts: "orchestration IS the product". Good scanners are free; users pay to not miss the trade.
- **Pragmatist** — `SINGLE_WEDGE`. Held. Warns BYO-keys adds per-user support burden.
- **Synthesizer** — `PARTIAL_CONSENSUS`. BYO-keys path resolves liability tension; wedge-vs-all-in-one still open.

### Round 3 — distribution math attack

- **Skeptic** — `DISTRIBUTION_UNVERIFIED`. EN-X has 50M+ crypto Twitter but arb audience is ~0.1%; solo builder with no following. RU-TG is warmer but saturated/scam-heavy.
- **Expert** — `WEDGE_FUNDING_CARRY_REVISED`. Strips unconfirmed channels (DeFi Llama, Bankless, Delphi). Narrows to: Twitter/X funding-rate-trader subgraph + prop-desk Discord warm intros.
- **User advocate** — `KILL_29_TIER`. Retail $29 users churn at 40%/mo; pros pay $99+ and stick. Middle tier is a retention trap.
- **Pragmatist** — `API_RISK_TOP`. Exchange API breakage is the #1 operational risk. Must instrument per-leg uptime from day 1.
- **Synthesizer** — `FREE_OSS_PLUS_99`. Two-tier consensus forming: free OSS + $99 local-exec.

### Round 4 — ICP and sequencing

- **Skeptic** — `RETENTION_GATE`. Proceed but instrument 30-day depositor retention. <40% active at day 30 = not sticky.
- **Expert** — `LOCAL_EXEC_99_ICP`. ICP = solo quant / prop-desk junior with home server or VPS, managing $100k–$1M carry book. 50 × $99 = $5k MRR, tractable via X + Discord/TG warm intro.
- **User advocate** — `KILL_MIDDLE_TIER`. Confirms: kill $29. LTV 3 months unless meaningful slippage savings.
- **Pragmatist** — `BETA_FIRST`. Ship beta to 5 design partners before public trial. Prove stability before scale.
- **Synthesizer** — `TWO_TIER_CONSOLIDATED`. Consensus on 2-tier + beta-first + $99 local-exec.

### Round 5 — final

- **Skeptic** — `CONDITIONAL_LIVE_HIGH_CHURN_RISK`. Proceed conditionally. 30-day depositor retention is the gate. <40% active day 30 → pivot or kill.
- **Expert** — `LOCAL_EXEC_99_TRIAL_GATE`. 14-day trial with card capture upfront. 50 × $99 more achievable than 200 × $29. ICP = solo quant or prop desk junior with VPS/home server.
- **User advocate** — `FREE_OSS_PLUS_99_LOCAL_NO_MIDDLE`. Kill $29 tier entirely. ICP is small prop desk or fund ops with $500k+ carry. LTV 3 months unless meaningful slippage savings.
- **Pragmatist** — `TWO_TIER_BETA_FIRST`. 2 tiers (free OSS + $99 local-exec); ship beta first then trial card-gate. Biggest risk = exchange API breakage killing demos.
- **Synthesizer** — `TWO_TIER_TRIAL_GATED_BETA`. Day 0–30 OSS scanner + local-exec beta to 5 design partners; Day 30–60 open trial with card-gate (20 activations target); Day 60–180 50 paid × $99 = $5k MRR.

---

*Generated 2026-04-21 via `/model-chat` skill. Debate input: research/2026-04-21-arbitrage-scanner-market-research.md.*
