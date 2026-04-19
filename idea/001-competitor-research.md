# 001 — Competitor research agent team

## Goal

Map what already exists in the perp-spread / funding-farm / cross-exchange arbitrage tool space, find what competitors do well and where they leave gaps, and produce a structured comparison against the current version of RoboSpread — so the next phases target real differentiation, not assumed differentiation.

## Flow

1. **Researcher agents (parallel, one per target site)**
   - Each spawned with one competitor URL and the same extraction schema
   - Output: a structured brief with these sections:
     - product pitch (one line)
     - target user (retail trader / quant / institutional)
     - exchange coverage (which CEXs/DEXs, perps only or spot too)
     - core features (table columns, charts, alerts, backtests, auto-exec)
     - data freshness model (REST poll cadence? WS? public or private?)
     - UI quality notes (dense / sparse, dark / light, desktop-first / mobile)
     - pricing (free / tiered / enterprise)
     - standout strengths (≤3 bullets)
     - visible gaps or rough edges (≤3 bullets)
2. **Synthesizer agent (single, serial after researchers)**
   - Ingests all briefs + a snapshot of RoboSpread's current capability list
   - Produces:
     - **Feature matrix**: rows = features, columns = each competitor + RoboSpread, values = ✓ / partial / ✗ / n-a
     - **Gap list**: things every competitor does that RoboSpread doesn't
     - **White-space list**: things nobody does well — potential differentiation
     - **Priority recommendations**: which gaps to close, which white space to claim, ordered by effort × impact
3. **Output lands in `idea/research/<date>/`** — per-competitor briefs + one synthesized summary — kept out of `plan.md` until we commit to acting on anything.

## Candidate competitors (seed list — expand before running)

- CoinGlass — funding rate + liquidations aggregator
- Laevitas — derivatives analytics, funding & basis
- Amberdata — derivatives data API + dashboards
- Paradigm — institutional spreads / RFQ
- Hyperdash — Hyperliquid-native analytics
- CoinAnk — perp analytics
- Velo Data — derivatives dashboards
- any Telegram/Discord bots the user follows (to be listed)

## Implementation sketch

- Kick off as parallel `Agent` calls (subagent_type=`general-purpose` with WebFetch/WebSearch), each with the same structured prompt + a unique URL
- Synthesizer = one serial `Agent` call fed the concatenated briefs + a short "RoboSpread today" snapshot pasted inline from `plan.md` + `CHANGELOG.md`
- Eventually wrap as a slash command `/competitor-scan` that takes a URL list and a RoboSpread snapshot path
- Cadence: re-run quarterly (competitors ship fast in this space)

## Open questions

- Does the synthesizer re-rank the roadmap directly, or just produce a brief the user reworks manually?
- Do we want a "steal from" section calling out specific UI/UX patterns worth copying?
- Do we need a "pricing strategy" pass at all — this tool is local/personal, not a product?
