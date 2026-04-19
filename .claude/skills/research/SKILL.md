---
name: research
description: Fan-out / fan-in research on any question, topic, or idea. Decomposes the subject into at least 5 angles, spawns parallel researcher subagents on sonnet (one per angle), then spawns a single synthesizer subagent on opus that merges their findings into a structured brief with consensus, disagreements, gaps, and recommendations. Invoke as `/research <question>` or `/research` (then prompt).
---

# Research: fan-out → fan-in

Parallelizes investigation of a single question across N independent
researchers, then collapses their output through a synthesizer. Use when
the question is too broad for one sweep and has multiple reasonable
angles of attack.

## When to invoke

Run this skill when **all** of these hold:

- The question/topic is genuinely **open-ended** — a direct answer would
  be shallow or incomplete.
- It has **multiple defensible angles** (market / technical / product /
  risk / historical / competitive / etc.).
- The user wants a **decision-support brief**, not a one-shot factoid.

**Do NOT invoke when:**

- The question has a single authoritative answer discoverable in ≤2 tool
  calls. Just answer it.
- The question is about *this codebase* — use Explore subagent, not research
  (the research subagents don't need to spin up web access to read the repo).
- The user wants *implementation*, not research. This skill produces briefs,
  not code.

## Flow

### Step 1 — decompose (≤30s of your own thinking)

Restate the subject in one sentence, then propose **at least 5 research
angles** (5–7 is the sweet spot) as distinct sub-questions. Angles
should be:

- **Orthogonal** — each explores different ground; minimize overlap.
- **Concrete** — "how do funding-farm tools price their alerts?" beats
  "alerts in general".
- **Answerable in isolation** — a researcher reading only their angle
  (no sibling context) should be able to make progress.

Typical angle templates (pick the 3–5 that fit):

| Template | Use for |
|---|---|
| **State of the art** | What do best-in-class tools/approaches look like? |
| **Competitor / prior art** | Who has done this, how, and what did they learn? |
| **Technical constraint** | Feasibility, tradeoffs, performance, compat |
| **User / adoption** | Who uses this, pain points, willingness to pay |
| **Risk / failure modes** | What breaks? What's been abandoned and why? |
| **Historical / precedent** | How has thinking evolved on this? |

### Step 2 — fan out (SINGLE message, parallel Agents)

Spawn one `Agent` tool call **per angle** in a **single response** so
they run in parallel. Critical rules:

- **Minimum 5 researchers.** If you think 4 suffices, add one more
  angle — fewer than 5 defeats the point of the skill.
- Use `subagent_type: "general-purpose"` (has WebFetch/WebSearch).
- **Set `model: "sonnet"` on every researcher Agent call.** Sonnet is
  the right cost/capability point for parallel scouting work. The
  synthesizer is different — see Step 3.
- Each researcher gets the **same output schema** (see below) but a
  **unique angle prompt**.
- Each researcher is told: "Only research your assigned angle. Do not
  try to answer the full question. Do not delegate to other agents."
- Tell each researcher to **cite sources** inline (URLs for web, file
  paths for code).
- Set a **word cap** (200–400 words per brief) — synthesis drowns in
  long outputs.

**Researcher output schema** (paste verbatim into every prompt):

```
## Angle
<one-line restatement of what you investigated>

## Key findings
- <bullet, ≤15 words, sourced>
- <bullet>
- <bullet>

## Evidence
- <source URL / file:line> — <what it supports>
- ...

## Confidence
<high | medium | low> — <why>

## Gaps
- <what you couldn't determine and why>
```

### Step 3 — fan in (single synthesizer, serial)

After all researchers return, spawn **one** `Agent` with
`subagent_type: "general-purpose"` and **`model: "opus"`**. Pass it:

- The original subject (one sentence)
- The **concatenated researcher briefs** verbatim
- The synthesis schema (below)

**Why opus for the synthesizer:** this is the step where reasoning
quality matters most — weighing tensions between briefs, spotting
hidden gaps, producing a defensible recommendation. There is only one
synthesizer call, so the cost delta vs sonnet is small and worth it.
Researchers can be sonnet because they do narrow, parallel scouting.

**Synthesizer instructions** (paste verbatim):

> You are a synthesizer. You have N researcher briefs attached. Your job
> is to merge them — not to do original research. Do not browse the web.
> Do not re-derive findings. If a claim isn't in a brief, mark it as a
> gap. Produce the output below in ≤600 words.

**Synthesizer output schema:**

```
## TL;DR
<2-sentence answer to the original question>

## Consensus
- <things ≥2 researchers independently found>

## Tensions / disagreement
- <where researchers' findings conflict, with both sides>

## Gaps
- <what no researcher answered — needs follow-up>

## Recommendation
<1 paragraph: what the user should do, weighted by confidence>

## Sources
- <flat dedupe of all cited URLs/paths from the briefs>
```

### Step 4 — deliver

Show the synthesized brief to the user. **Do not paste the individual
researcher briefs** unless asked — they're intermediate artifacts.

If the topic warrants it (competitor scans, architectural bake-offs,
recurring research), offer to persist the output to
`research/<date>/<topic-slug>.md` — but only if the user opts in. Don't
silently create files.

## Question-authoring for researchers

Each researcher prompt should contain, in order:

1. **Role** — "You are researching one angle of a larger question for a
   synthesizer."
2. **Overall subject** — one sentence of what the full question is, so
   the angle makes sense.
3. **Your angle** — one clear sub-question. Exactly one.
4. **Output schema** — verbatim from above.
5. **Constraints** — word cap, sourcing requirements, no delegation.
6. **Tools allowed** — usually `WebSearch`, `WebFetch` (for web-facing
   topics) or `Read`, `Grep`, `Glob` (for repo-facing). Tell them which
   to use.

**Example researcher prompt (abridged):**

```
Role: You are researching ONE angle of a larger question for a
synthesizer agent. Stay in your lane.

Overall question: "Should RoboSpread build a SQLite history store, or
keep the in-memory ring forever?"

Your angle: Technical constraint. What are the operational costs of
running SQLite for a 7-exchange, 650-symbol, 1Hz write workload on a
local machine — disk growth, write amplification, read latency, and
crash recovery?

Output schema: [paste schema]

Constraints: ≤300 words. Cite every non-obvious claim with a URL or
file:line. Do not investigate other angles (UX, competitor behavior,
alert latency) — those are other researchers' jobs. Do not spawn
further agents.

Tools: WebSearch, WebFetch.
```

## Anti-patterns

- ❌ Spawning researchers sequentially instead of in one message → loses
  the parallelism that's the whole point.
- ❌ Asking one researcher to "cover everything" → that's just a regular
  Agent call, not fan-out.
- ❌ Letting the synthesizer browse the web → it drifts into original
  research and the structure breaks.
- ❌ Pasting all 5 briefs to the user → they asked for an answer, not a
  pile of raw notes.
- ❌ Running fewer than 5 researchers → defeats the purpose of
  fan-out; below 5, just do a single Agent call.
- ❌ Running 8+ researchers → diminishing returns past 7; synthesis
  quality drops as input grows.
- ❌ Omitting `model: "sonnet"` on researchers → burns cost if parent
  is opus, and slows the parallel fan-out tier.
- ❌ Running the synthesizer on sonnet → the integrative step is where
  quality matters most; synthesizer must be opus.
- ❌ Using this for codebase questions → Explore subagent is faster.

## Tuning knobs

- **Angle count**: **5 minimum** (hard floor), 7 maximum. Use 5 for tight
  questions, 6–7 for broad or high-stakes ones.
- **Model**: **sonnet** for researchers (parallel scouting, cheap), **opus**
  for the synthesizer (single integrative call, quality matters). Non-
  negotiable default. Only override both to haiku for throwaway scans
  the user explicitly asks for.
- **Researcher word cap**: 200 for quick scans, 400 for deep dives.
- **Synthesizer word cap**: 600 is the default sweet spot. Raise to
  1000 only for decisions with real stakes.
- **Tool allowlist per researcher**: restrict to what the angle actually
  needs. A competitor-analysis researcher needs web tools; a
  historical-precedent researcher needs web + maybe Read for local
  notes.

## Example end-to-end

**User:** `/research should we replace ccxt with native REST for discovery + klines?`

**You (Step 1 decompose, shown to user before fanning out):**

> Researching: ccxt retirement for RoboSpread's discovery + kline fetch.
> Angles:
> 1. Implementation cost — LOC + per-venue complexity
> 2. Operational benefit — startup time, dependency weight, failure
>    modes we've hit with ccxt
> 3. Ongoing maintenance — how often do exchange API shapes drift, and
>    does ccxt absorb that work for us?
> 4. Ecosystem alternatives — is there a lighter adapter layer worth
>    using instead of ccxt?
> 5. Risk of regression — what features do we lose (symbol normalization,
>    pagination, retry) and what's the replacement plan?
>
> Fanning out 5 researchers on sonnet now.

**[Agent ×5 in one message, all with `model: "sonnet"`]** → parallel
execution.

**[Agent ×1 synthesizer with `model: "opus"`]** → reads the 5 briefs,
outputs the structured synthesis.

**You:** present TL;DR + recommendation + sources to the user.
