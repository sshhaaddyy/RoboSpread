# /model-chat skill design — fan-out/fan-in research brief

**Question:** How should I design a /model-chat skill that spawns 5+
Claude instances into a shared conversation room with round-robin
turns and parallel execution within each round, for debate and
convergence on solutions?

**Angles researched (3):**
- Persona differentiation [deep] — 700-word cap
- Convergence + termination [deep] — 700-word cap
- Prior art — debate research [standard] — 400-word cap

Angle count is below the skill's default ≥5 minimum because the user
narrowed the angle list at the confirmation step. Two additional
angles (transcript state architecture, output synthesis) were handled
as design inferences during synthesis.

---

## Decision

Build `/model-chat` as a **5-agent, role-differentiated, broadcast-
revise loop** with hard-capped rounds, parallel-within-round
execution, and structured anti-sycophancy guards. Round-robin turn
*ordering* is preserved for deterministic logging, but all agents in
a given round generate **simultaneously against the frozen prior-
round transcript** — this is the MAD (Du et al.) pattern, not
sequential handoff.

## Core architecture

**Roster (5 peers, no meta-judge):**
1. Skeptic / falsifier — stake: "find the failure mode"
2. Domain expert (scoped) — bound to named subdomain to prevent
   authority dominance
3. User / stakeholder advocate — stake: end-user outcome
4. Pragmatist / implementer — stake: "you maintain this for 3 years"
5. Synthesizer / integrator — peer agent, not judge (reduces
   authority asymmetry)

Each persona carries a **stake, not just a viewpoint** — "you are
the engineer who maintains this code" beats "you are a skeptic" for
actionable objections.

**Turn protocol per round:**
1. All 5 agents receive the same frozen transcript of round N−1.
2. All 5 generate in parallel (async fan-out).
3. Outputs are appended to the shared room in fixed round-robin
   order for readability.
4. Round N+1 begins once all 5 complete (barrier sync).

Broadcast-revise > sequential handoff — prevents early-anchor bias.

**Stopping rule (composite):**
- Hard cap: **N = 5 rounds** with per-round timeout.
- Early-stop: if the **conclusion token** is stable across all
  agents for **K = 2 consecutive rounds**, terminate.
- Final synthesizer pass must **enumerate remaining disagreements**;
  empty list ⇒ converged, non-empty ⇒ surface them.

Expect ~70–80% of quality lift by round 2; round 4+ rarely flips a
round-3 consensus.

## Anti-sycophancy guards (non-negotiable)

Same-model ensembles collapse to false consensus by round 2–3
because RLHF penalizes persistent disagreement. Required mitigations:

1. **Original-position re-read** (Liang et al.): before each round,
   every agent is shown its own round-1 stance and must justify any
   change explicitly.
2. **Anti-capitulation prompt**: "Do not update your position unless
   presented with a **new argument you have not yet addressed**."
3. **Devil's-advocate stopping rule**: skeptic argues against
   majority until it can articulate what evidence would change its
   view.
4. **Asymmetric priors over temperature variance**: give agents
   different framings of the same facts.

## Implementation notes

- **Shared state**: a single append-only transcript (the "room").
  Each agent's context = system prompt + full transcript + their
  own round-1 stance pinned.
- **Message schema**: structured — `{round, agent_id, stance,
  argument, conclusion_token}` — not freeform. Prevents context
  bloat at 5 × 5 = 25 messages.
- **Turn selection**: fixed round-robin ordering for v1. AutoGen's
  `GroupChatManager` (LLM-selected next speaker) is a later upgrade.
- **Parallelism**: spawn all 5 Agent calls in ONE message per round;
  barrier on round boundary.
- **Output**: final synthesizer message + enumerated remaining
  disagreements + full transcript as collapsible artifact.

## Rejected alternatives

- **Sequential round-robin** — causes early-anchor bias.
- **Meta-judge agent** — judge sycophancy is recursive; peer
  synthesizer with explicit disagreement enumeration is more robust.
- **Temperature-varied homogeneous agents** — produces style variance
  not position variance; collapses fastest.
- **Semantic (embedding) convergence detection** — agents rephrase
  the same disagreement in different words; fragile. Conclusion-
  token stability is the practical proxy.
- **Unbounded rounds with dynamic stopping only** — adversarial
  prompts stall stability checks; hard cap is non-negotiable.

## Gaps

- **[CRITICAL_GAP]** No published data on convergence dynamics or
  homogeneity collapse rates with **5+ same-model agents**
  specifically. All cited prior art (MAD, Liang, AutoGen) studied
  2–3 agents. Mitigation: ship with 5-round cap + strong anti-
  capitulation; instrument round-over-round position-change rate;
  prepared to drop to 4 if collapse rate exceeds ~40% by round 2.
- **[CRITICAL_GAP]** Optimal K for stability early-stop at 5-agent
  cardinality is unknown. K=2 is a reasonable default but untested.
- Claude-specific homogeneity collapse rate vs other models is
  untested.
- No prior art addresses persistent shared-state rooms across
  invocations — treat v1 as single-shot.
- Anti-capitulation prompt wording has no controlled-study backing.

Both critical gaps require **empirical testing** (build-then-measure),
not more research — gap-closing round skipped.

## Ship criteria for v1

- 5 role-stake personas, hardcoded; synthesizer as peer.
- Parallel broadcast-revise loop, 5-round hard cap, K=2 conclusion-
  token early-stop.
- Original-position pinning + anti-capitulation prompt on every
  agent.
- Final output: synthesizer message + remaining-disagreements list +
  full transcript.
- Instrument: position-change rate per round, round at first
  stability, total tokens.

## Sources
- https://arxiv.org/abs/2305.14325 — Du et al. 2023 (MAD)
- https://arxiv.org/abs/2305.19118 — Liang et al. 2023
- https://arxiv.org/abs/2307.04986 — Liang et al. (tit-for-tat)
- https://arxiv.org/abs/2308.08155 — AutoGen
- https://arxiv.org/abs/2303.17760 — CAMEL
- https://arxiv.org/abs/2308.00352 — MetaGPT
- https://arxiv.org/abs/2212.08073 — Constitutional AI
- https://www.anthropic.com/research/constitutional-ai
- https://microsoft.github.io/autogen/

---

*Saved: 2026-04-19 · Slug: model-chat-design*
