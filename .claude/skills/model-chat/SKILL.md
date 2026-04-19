---
name: model-chat
description: Multi-agent debate room. Spawns 5 role-differentiated Claude instances (Skeptic, Domain-expert, User-advocate, Pragmatist, Synthesizer) that debate a topic over up to 5 rounds using broadcast-revise (all agents see frozen prior-round transcript, all generate in parallel within the round — NOT sequential handoff). Architecture based on MAD (Du et al. 2023) + Liang et al. anti-sycophancy mitigations. Hard-capped rounds with conclusion-token stability early-stop. Use for design decisions with real tradeoffs, risk assessment / pre-mortems, hard judgment calls where surfacing disagreement matters more than speed. NOT for factual lookups, decomposable research (use /research), vote-counting (use /consensus), or codebase facts (use Explore). Triggers on `/model-chat`, "model chat", "multi model debate", "agent debate", "spawn a chat room". Pass the topic as arguments. Optional `rounds=N` override (clamp 2–7).
---

# Model-chat: 5-agent debate room

Five role-differentiated Claude instances debate a topic in a shared
transcript. Parallel-within-round (broadcast-revise), hard-capped
rounds, anti-sycophancy guards, peer synthesizer (not a judge).

Design grounded in the fan-out/fan-in research brief at
`research/2026-04-19-model-chat-design.md` — read it for the
full rationale; this file is the operational recipe.

## When to invoke

- Design decisions with real tradeoffs, no obvious winner.
- Risk assessment / pre-mortem on a plan or architecture.
- Hard judgment calls where surfacing disagreement matters more
  than speed.
- Any topic where you want adversarial pressure on an idea.

## When NOT to invoke

- Factual lookups — debate is noise on facts.
- Narrow implementation tasks — one strong agent + tests wins.
- Decomposable research — use `/research`.
- Vote-counting on a clean choice — use `/consensus`.
- Codebase exploration — use the Explore subagent.

---

## The 5 roles (fixed)

Each role's prompt must bake in a **stake**, not just a viewpoint.
Generic contrarianism produces generic output. Stakes produce
actionable disagreement.

| # | Role | Stake baked into system prompt |
|---|---|---|
| 1 | **Skeptic / falsifier** | "Find the failure mode. Your reputation is on the line if an edge case ships broken." |
| 2 | **Domain expert** (scoped) | Bound to the named subdomain — outside it, defer. Prevents authority dominance. |
| 3 | **User / stakeholder advocate** | "You're the end user. Will this actually help you?" |
| 4 | **Pragmatist / implementer** | "You maintain this code for 3 years. Every choice compounds." |
| 5 | **Synthesizer / integrator** | Tracks positions across agents. Surfaces common ground AND unresolved disputes. **Peer, not judge** — does not rule. |

---

## Flow

### Step 1 — parse topic + bind domain

From the invocation, extract:
- The **topic** — the debate subject, verbatim.
- The **domain** for Role 2. Infer from the topic; if genuinely
  ambiguous, ask ONE clarifying question.
- Optional `rounds=N` override. Default 5, clamp 2–7.

State the roster + inferred domain in one line before spawning
round 1, so the user can redirect early.

### Step 2 — round 1 (parallel fan-out)

Spawn 5 `Agent` calls in ONE message:
- `subagent_type: "general-purpose"`
- `model: "sonnet"` for Roles 1–4
- `model: "opus"` for Role 5 (synthesizer reasoning is
  load-bearing)

Prompt each agent with:
- Role + stake
- Topic verbatim
- Output schema (see below)
- Anti-capitulation directive (see below)
- "This is round 1 — state your initial position."

### Step 3 — rounds 2..N (parallel broadcast-revise)

For each round K ∈ {2..N}:

1. Build the **frozen transcript** of rounds 1..K−1 as structured
   JSON records (not freeform chat).
2. Spawn 5 `Agent` calls in ONE message. Each prompt contains:
   - The role + stake (repeat)
   - The frozen transcript of rounds 1..K−1
   - **The agent's OWN round-1 stance pinned at the top** ("Your
     original position was: <X>. You may update, but justify any
     change by naming the specific new argument that changed your
     mind.")
   - Anti-capitulation directive
   - "This is round K. You may refine, concede, or hold your
     position — justify either way."

3. **Early-stop check** after parsing the 5 responses:
   - Extract each agent's `conclusion_token`.
   - If all 5 agree AND all 5 also agreed in round K−1 (so K ≥ 3),
     terminate the loop.
   - Otherwise, proceed to round K+1 or to final synthesis if
     K = N.

### Step 4 — final synthesis (opus)

After the loop exits (early-stop OR round N hit), spawn ONE more
`Agent` call on opus with the full transcript:

```
You are the final synthesizer for a 5-agent debate that just
concluded. You have the full transcript of all rounds.

Produce:

## Consensus
The position held by ≥⌈5/2⌉ = 3 agents at the final round. State it
in 1–2 sentences, and the round it stabilized (if earlier than the
last).

## Remaining disagreements
List every position that has ≥1 agent still holding it but differs
from the consensus. Format:
- <position> — held by <agent names>, core argument: <1 sentence>

If empty, state "No remaining disagreements".

## Open questions surfaced
Questions the debate raised but did NOT resolve — worth following
up separately.

## Round-over-round notes
- Round at which conclusion-token first stabilized (if ever).
- Whether any agent flipped position between rounds, and why.

Cap: 600 words. Do not add your own opinion — you are reporting the
debate, not adjudicating it.
```

### Step 5 — deliver

Show the user:
- **Final synthesis** (inline, readable).
- **Remaining disagreements / open questions** (even if empty —
  explicitly saying "no remaining disagreements" is useful signal).
- **Full transcript** as a collapsible / indented block — this is
  the "room".

**Default-save** the transcript + synthesis to
`model-chat/<YYYY-MM-DD>-<slug>.md` at the repo root (create the
directory if missing). User can opt out with "don't save".

---

## Message schema (structured, not freeform)

Every agent MUST emit exactly this JSON shape — no preamble, no
trailing prose:

```json
{
  "round": <int>,
  "agent": "skeptic" | "expert" | "user_advocate" | "pragmatist" | "synthesizer",
  "stance": "<one-line summary of position>",
  "argument": "<supporting reasoning, ≤120 words>",
  "conclusion_token": "<the discrete answer — e.g. 'go', 'no-go', 'Option A' — or null if the topic has no discrete answer>",
  "changed_from_last_round": <bool>,
  "change_justification": "<if changed_from_last_round=true, name the specific new argument; else null>"
}
```

Structured schemas prevent context bloat at 5 × 5 = 25 messages and
make conclusion-token early-stop mechanical.

---

## Anti-sycophancy directive (paste verbatim into every round ≥ 2)

> **Your original round-1 position was:** <pinned stance>
>
> Do NOT update your position unless you can point to a **new
> argument or evidence in this round that you had not addressed
> before**. Surface-level majority pressure is not a reason to
> change. If you DO update, state explicitly in
> `change_justification`: "I am updating because <new argument>."
>
> If you are the **Skeptic**, you may only converge once you can
> articulate what evidence would change your view. Without that
> named threshold, keep pressing.

---

## Parallelism model

"Parallel execution within each round" = **one message with 5
`Agent` tool calls**. Claude Code executes independent tool calls in
the same assistant turn concurrently. Do NOT spawn rounds as
separate messages with sequential Agent calls — that loses the
parallelism that prevents early-anchor bias.

Barrier: wait for all 5 responses before building round K+1's
transcript. If one agent times out or errors, drop to 4 for that
round and log — do NOT block the barrier waiting on a dead agent.

---

## Tuning knobs

- **Rounds**: 5 default, clamp 2–7. Most quality lift lands by
  round 2; round 4+ rarely flips a round-3 consensus. Override via
  `rounds=N` in the invocation.
- **Early-stop K**: 2 consecutive stable rounds. Untested at this
  cardinality — instrument the round at which stability first hits
  and tune empirically.
- **Per-round timeout**: 60s per agent call budget. If one agent
  times out, drop to 4 that round, log, continue.
- **Model allocation**: sonnet for Roles 1–4, opus for Role 5 + the
  final synthesis. If cost-constrained, drop Role 5 to sonnet too
  — but expect shallower synthesis.
- **Anti-capitulation strength**: if by round 2 ≥4 of 5 agents have
  flipped to the same position without citing new arguments in
  `change_justification`, that's false convergence — the
  synthesizer should flag it and the debate should NOT early-stop.

---

## Anti-patterns

- ❌ **Sequential round-robin** (each agent sees prior agents'
  same-round output) → early-anchor bias. Broadcast-revise is
  non-negotiable.
- ❌ **Meta-judge agent** separate from peers → recursive sycophancy.
  Synthesizer is a peer, not a judge.
- ❌ **Temperature variation** instead of role stakes → style
  variance, not position variance. Collapses fastest.
- ❌ **Free-form chat messages** → context bloat, can't mechanically
  check conclusion-token stability.
- ❌ **Embedding-similarity convergence** → agents rephrase the same
  disagreement in different words; fragile. Use conclusion-token
  stability.
- ❌ **Unbounded rounds with dynamic stopping only** → adversarial
  prompts stall stability checks. Hard cap is non-negotiable.
- ❌ **Running Role 5 / final synthesis on sonnet** → synthesis is
  the load-bearing step that differentiates this from raw parallel
  sampling.
- ❌ **Skipping original-position pinning** → sycophantic collapse
  by round 3.
- ❌ Using this for facts / simple implementation / votes — see
  "When NOT to invoke".

---

## Known gaps (carried from research)

- **No prior art on 5+ same-model agents.** All cited research
  (MAD, Liang, AutoGen) used 2–3 agents. 5 may amplify sycophantic
  collapse (more social pressure) OR improve coverage (more role
  slots). Ship v1, instrument position-change rate per round, tune.
- **K=2 for stability early-stop is untested** at 5-agent
  cardinality.
- **Anti-capitulation prompt wording** has no controlled-study
  backing. Iterate after real runs.

---

## Prior art this is built on

- **Du et al. 2023 (MAD)** — https://arxiv.org/abs/2305.14325 —
  broadcast-revise architecture, 2–3 rounds sufficient.
- **Liang et al. 2023** — https://arxiv.org/abs/2305.19118 —
  sycophantic capitulation + original-position re-read.
- **AutoGen (Wu et al.)** — https://arxiv.org/abs/2308.08155 —
  GroupChat managers, turn routing.
- **CAMEL** — https://arxiv.org/abs/2303.17760 — role-playing
  persona discipline.
- **MetaGPT** — https://arxiv.org/abs/2308.00352 — structured
  message schemas.
- **Constitutional AI** — https://arxiv.org/abs/2212.08073 —
  dedicated critic role.

Full synthesis + evidence in
`research/2026-04-19-model-chat-design.md`.

---

## Example end-to-end

**User:** `/model-chat should we ship the new payments flow behind a feature flag or dark-launch to 1% of users first?`

**Setup announcement:**
> Roster: Skeptic · Domain expert (feature-flag rollout / phased
> deploys) · User advocate · Pragmatist · Synthesizer. 5 rounds
> max, K=2 stability early-stop. Starting round 1.

**Round 1 (parallel, 5 agents):** each states initial position.
Example: skeptic → `{stance: "feature flag", conclusion_token:
"flag", argument: "dark-launch skips integration testing"}`;
pragmatist → `{stance: "dark-launch", conclusion_token: "dark",
argument: "flag debt accumulates"}`.

**Rounds 2–5:** each round broadcasts the prior round; each agent
re-reads its original stance; updates only on new arguments.
Conclusion tokens evolve: `{flag, dark, flag, flag, flag}` →
round 2 majority-to-all shift → check round 3 for K=2 stability.
If all 5 agree two rounds running, early-stop.

**Final synthesis (opus, ≤600 words):** consensus = feature flag;
minority = Skeptic holds out citing integration-test concern →
listed as remaining disagreement + open question.

**Save:** `model-chat/2026-04-19-payments-flag-vs-dark.md`.

---

## Integration with other skills

- Topic ambiguous before debate even makes sense? → `/clarify`
  first.
- Want distinct research angles rather than debate on one? →
  `/research`.
- Want a vote-distribution from N samples of the SAME prompt? →
  `/consensus`.
