---
name: consensus
description: Stochastic multi-agent consensus. Spawns N parallel agents (default 10) on the SAME prompt with near-identical variations, each emitting a structured response; aggregates by consensus (mode), splits (factions ≥20%), and outliers (unique ideas). Use for brainstorming with diversity, uncertainty calibration, validation by majority, or ranking from a list. NOT for decomposable research (use `/research`), factual lookups (one agent suffices), deep reasoning (one strong agent wins), or codebase facts (use Explore). Invoke as `/consensus <question>`, optionally `n=<N>`.
---

# Consensus: stochastic multi-agent voting

Parallel sampling of a SINGLE question to surface the mode, splits, and
outliers — not to decompose. For decomposition use `/research`.

## When to invoke

- **Brainstorming** — want diverse ideas, care about both common themes
  and the weird ones.
- **Uncertainty calibration** — a judgment call where you need "how
  much would independent agents agree?"
- **Validation by majority** — is this answer robust, or one model's
  idiosyncrasy?
- **Ranking / choosing** — N agents each pick a winner from options;
  winner = mode, splits expose second choices.

## When NOT to invoke

- **Factual lookups** — sampling variance is noise on facts.
- **Deep reasoning chains** — one strong agent beats N shallow ones.
- **Decomposable research** — use `/research` (different angles per
  agent).
- **Codebase exploration** — use the Explore subagent.

## How this differs from `/research`

| | `/research` | `/consensus` |
|---|---|---|
| Per agent | ONE distinct angle | SAME question, N times |
| Purpose | decompose → merge | vote → expose agreement + outliers |
| Synthesizer | integrates perspectives | buckets same-type responses |
| Model per worker | sonnet | sonnet |
| Synthesizer | opus | opus |

If the user's question is really about distinct angles, say so and
offer to switch to `/research`.

---

## Flow

### Step 1 — parse question + pick a schema

Extract from the invocation:
- The question verbatim.
- `n=<N>` if present. Default 10. Clamp `3 ≤ N ≤ 20`.

Pick a **structured output schema** so the synthesizer can aggregate.
Default schemas by question shape:

| Question shape | Schema |
|---|---|
| "What should I do about X?" | `{recommendation, reasoning, confidence}` |
| "Which of A / B / C?" | `{pick, reasoning}` |
| "Rank these options" | `{ranking: [option], reasoning}` |
| "Generate ideas for X" | `{ideas: [{title, one_line}]}` |
| "Is X correct / safe / …?" | `{verdict: yes/no/partial, reasoning}` |
| "Review this" | `{critical: [...], suggestions: [...], blockers: [...]}` |
| fallback | `{answer, reasoning}` |

State the chosen schema to the user in one line before the fan-out
fires, so they can redirect if it's wrong.

### Step 2 — fan out N agents (SINGLE message, parallel)

Spawn N `Agent` calls in ONE response. Parallel execution is
non-negotiable.

Per agent:
- `subagent_type: "general-purpose"`
- `model: "sonnet"`
- Prompt is **identical across all N** except for the "Sample #K of N"
  preamble. That single variation is the only allowed perturbation —
  it breaks prompt-cache dedupe so each agent samples independently.
  Do **not** inject perspective hints ("from a security lens", "from a
  perf lens") — those bias the pool and destroy the consensus signal.

**Agent prompt template (paste verbatim, substituting `<…>`):**

```
You are Sample #<K> of <N> independently answering one question. Your
answer will be aggregated with <N−1> siblings to find consensus,
splits, and outliers.

Answer as YOU would independently. Do not hedge by trying to guess
what the majority will say — that defeats the whole exercise. Be
decisive.

Question:
<user's question verbatim>

Output schema (emit as a single valid JSON object, no preamble, no
trailing prose):
<schema>

Constraints:
- If the question asks you to pick, pick exactly one.
- Do not answer "it depends" unless the question is literally
  unanswerable without info you don't have — in that case say so
  explicitly in the `reasoning` field.
- Cap reasoning at ~80 words.
- No web browse unless the question literally requires current
  external facts. No file I/O. No delegation.
```

### Step 3 — failure handling

After the fan-out returns:

- `≥⌈N/2⌉` structured responses → proceed to synthesis.
- Fewer than that → abort. Tell the user: *"Fan-out failed — got <M>
  of <N>. Aggregating on a minority is unsound."*
- Do NOT retry individual failures. Unlike `/research`, N is already
  high — 1–2 drops are within tolerance.

### Step 4 — aggregate (opus synthesizer)

Spawn **one** `Agent`:
- `subagent_type: "general-purpose"`
- `model: "opus"`
- Input: all N structured responses concatenated.

**Synthesizer prompt (paste verbatim):**

```
You have <N> independent structured responses to the same question.
Your job is to bucket them and report the distribution — NOT to
re-derive the answer or add your own opinion.

Emit these sections in order:

## CONSENSUS
The modal answer — the position held by ≥⌈N/2⌉ agents. Summarize the
shared position in 1–2 sentences. If no position clears ⌈N/2⌉, say
"No consensus" and proceed directly to SPLITS.

## SPLITS
Minority factions of ≥20% of N (i.e., ≥2 of 10). For each:
- <count>/<N> — <faction's position in one sentence>

Skip factions below 20%.

## OUTLIERS
Unique ideas proposed by exactly 1 agent. List verbatim (these are
often the most interesting — the whole point of fan-out is to surface
them). Format:
- <the outlier position>

If no outliers, omit this section.

## CONFIDENCE
- HIGH if ≥80% agreed on the consensus.
- MEDIUM if 50–80%.
- LOW if <50% (no consensus held).

## DISTRIBUTION
One-line tally: e.g. "Postgres: 7, SQLite: 2, LibSQL: 1 (out of 10)".

Do not browse. Do not re-derive. Use only the N briefs. Cap total
output at 500 words.
```

### Step 5 — deliver

Show the user the synthesizer's output inline. **Do not default-save**
— consensus outputs are usually throwaway probes. If the user says
"save this", persist to
`consensus/<YYYY-MM-DD>-<slug>.md` at the repo root (create the
`consensus/` directory if missing).

---

## Tuning knobs

- **N (default 10)**: `n=3` min — below that, "consensus" is
  meaningless. `n=20` max — cost climbs linearly. Default 10 is the
  sweet spot for mode-finding with room for 1–2 outliers.
- **Model per worker**: `sonnet` default. Drop to `haiku` if the task
  is truly low-stakes and `N ≥ 15`. Never use `opus` per-worker —
  if each chain must be strong, you want `/research`, not
  `/consensus`.
- **Synthesizer**: always `opus`. Bucketing + recognizing semantic
  overlap is exactly where opus earns its cost.
- **Prompt variation**: only "Sample #K of N". No other perturbation.
- **Save**: opt-in (opposite of `/research` which default-saves).

## Anti-patterns

- ❌ Spawning the N agents sequentially → defeats the point.
- ❌ Running without a structured schema → free-form prose is
  near-impossible to aggregate.
- ❌ Biasing prompts with perspective hints → destroys consensus
  signal.
- ❌ Using this to decompose a multi-angle question → that's
  `/research`.
- ❌ Using this on codebase facts ("what does this function do?") →
  sampling variance is pure noise.
- ❌ Synthesizer on sonnet → bucketing + paraphrase-detection is the
  exact capability gap where opus pulls away.
- ❌ Retrying individual failures → N is high, drops are tolerable.
- ❌ Letting the synthesizer add its own opinion → its job is to
  report the distribution, not vote.

## Example

**User:** `/consensus should I use SQLite or Postgres for my MVP?`

**Schema picked:** `{pick, reasoning, confidence}`. Stated inline
before fan-out.

**Fan-out:** 10 sonnet agents in one message, each with "Sample #K of
10" + identical prompt.

**Returns:**
- 7 → Postgres
- 2 → SQLite
- 1 → LibSQL / Turso

**Synthesizer output (opus, 500-word cap):**

> ## CONSENSUS
> Postgres (7/10). Free-tier hosts cover MVP scale, row-level
> security, no migration pain later.
>
> ## SPLITS
> - 2/10 — SQLite: zero ops, single file, fine until concurrent
>   writes matter.
>
> ## OUTLIERS
> - LibSQL/Turso: SQLite protocol + server sync; skip migrations
>   entirely.
>
> ## CONFIDENCE
> MEDIUM (70% agreement — near the HIGH boundary).
>
> ## DISTRIBUTION
> Postgres: 7, SQLite: 2, LibSQL: 1 (out of 10).

## Integration with other skills

- If the question really needs distinct angles → offer to switch to
  `/research`.
- If the question is ambiguous about scope before fan-out even makes
  sense → suggest `/clarify` first.
