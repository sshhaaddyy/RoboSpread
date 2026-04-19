---
name: research
description: Fan-out / fan-in research on any open-ended question. Runs an early-exit check first; if the question is big enough, decomposes into ≥5 angles (user confirms via AskUserQuestion), spawns parallel researcher subagents on sonnet (one per angle, each aware of its siblings), hands the concatenated briefs to a synthesizer on opus that picks the right output template (decision / landscape / explain / timeline), runs a single gap-closing follow-up round if critical gaps remain, and default-saves the brief to `research/<YYYY-MM-DD>-<slug>.md`. Invoke as `/research <question>`.
---

# Research: fan-out → fan-in (v2)

Parallelized investigation with explicit angle approval, template-aware
synthesis, gap closing, failure handling, and default persistence.

## When to invoke

Run this skill when **all** hold:

- The question is **open-ended** — a direct answer would be shallow.
- It has **≥5 defensible angles**.
- The user wants a **decision-support brief**, not a factoid.

## When NOT to invoke

- The question is answerable in ≤2 tool calls (see Step 0).
- The question is about *this codebase* — use the Explore subagent; it's
  faster and doesn't burn web researchers.
- The user wants *implementation*, not research.

---

## Flow

### Step 0 — early-exit check (~30s, no spend)

Before decomposing, ask yourself: **"Could I answer this with ≤2 tool
calls using Grep / Read / WebSearch / WebFetch?"**

If yes → abort the skill, answer directly, and tell the user: *"This was
answerable directly — skipping fan-out. Here's the answer: ..."*

Only proceed to Step 1 if the question genuinely needs parallel angles.

### Step 1 — decompose + self-critique

Draft **≥5 angles** (5–7 sweet spot). Each angle gets a **depth tag**:

| Tag | Word cap | Use for |
|---|---|---|
| `quick` | 200 | Surface scan — "is X a thing?" |
| `standard` | 400 | Normal angle — default |
| `deep` | 700 | Load-bearing technical or strategic angle |

Then **self-critique once** before showing the user:

- Are any two angles >40% overlapping? Merge or sharpen.
- Is the list missing an obvious dimension (risk, historical, adoption,
  cost)? Add it.
- Does each angle produce something the synthesizer can combine? If an
  angle only yields a yes/no, collapse it into another.

### Step 2 — user confirms angles (ONE AskUserQuestion call)

Show the angles to the user via **`AskUserQuestion`** with
`multiSelect: true`. Question shape:

> **Which angles should I research?** (toggle to drop; pick "Other" to
> add one.)
>
> - Angle 1: <title> — <one-line scope> [standard]
> - Angle 2: <title> — <one-line scope> [deep]
> - ...
> - Angle N: <title> — <one-line scope> [quick]
> - **Other** — specify a missing angle

When the user picks, update the list. If they dropped below 5, ask for
one more via the "Other" branch before fanning out. **Only exception to
the ≥5 rule**: if the user explicitly says "4 is enough", respect it.

### Step 3 — fan out (SINGLE message, parallel)

Spawn one `Agent` call per angle in a **single response** (parallel
execution is non-negotiable). Per-agent config:

- `subagent_type: "general-purpose"`
- `model: "sonnet"`
- Word cap matches the angle's depth tag.
- **Prompt includes "Sibling angles" list** — paste the titles + one-
  line scope of the OTHER N−1 angles so each researcher knows what's
  covered elsewhere and doesn't duplicate.
- Tell the researcher to **cite every non-obvious claim** inline
  (`URL` or `file:line`) and to not delegate.

**Researcher prompt template:**

```
Role: You are researching ONE angle of a larger fan-out for a
synthesizer. Stay in your lane.

Overall question: <one sentence>

Your angle: <title> — <scope>
Depth tag: <quick | standard | deep>  → cap: <200 | 400 | 700> words.

Sibling angles being covered in parallel (do NOT duplicate their work):
  - <title 1>: <scope>
  - <title 2>: <scope>
  - ...

Output schema:
## Angle
<one-line restatement>

## Key findings
- <bullet, sourced>
- ...

## Evidence
- <URL or file:line> — <what it supports>
- ...

## Confidence
<high | medium | low> — <why>

## Gaps
- <what you could not determine>

Constraints: cite every non-obvious claim. Do not spawn further agents.
Do not attempt sibling angles.

Tools: <WebSearch, WebFetch> OR <Read, Grep, Glob> — pick based on
whether the angle is web-facing or repo-facing.
```

### Step 4 — failure handling

After the fan-out returns:

- **≥N−1 briefs returned cleanly** → proceed to synthesis.
- **<N−1 returned (multiple failures)** → re-spawn the failed ones
  ONCE (same prompt). If they still fail, proceed with what you have
  and flag "<M> of <N> researchers completed" in the synthesizer's
  reliability note.
- **<4 total briefs even after retry** → stop, tell the user the
  fan-out failed, offer to narrow the angle list and retry.

### Step 5 — synthesize (opus, template-aware)

Spawn **one** `Agent` with `model: "opus"`,
`subagent_type: "general-purpose"`. The synthesizer's first job is to
**pick an output template** based on the question shape:

| Template | When to use | Sections |
|---|---|---|
| **Decision** | "Should we X?" / "X vs Y?" | TL;DR (decision + confidence) · Options with tradeoffs · Recommendation · Gaps · Sources |
| **Landscape** | "What do competitors / alternatives do?" | Feature matrix (rows=features, cols=competitors) · Standouts · White space · Gaps · Sources |
| **Explain** | "What is X?" / "How does X work?" | TL;DR · Key facts · Nuances · Gaps · Sources |
| **Timeline** | "Why / how did X happen?" | Timeline · Root cause(s) · Contributing factors · Unknowns · Sources |
| **Generic** (fallback) | Doesn't fit above | TL;DR · Consensus · Tensions · Gaps · Recommendation · Sources |

**Synthesizer prompt** (paste verbatim):

> You are a synthesizer on opus. You have <N> researcher briefs. Your
> job:
> 1. Pick the single best output template (Decision / Landscape /
>    Explain / Timeline / Generic) for the original question.
> 2. Merge the briefs into that template. Do not browse the web. Do
>    not re-derive findings. If a claim isn't in a brief, mark it as a
>    gap.
> 3. If ≥1 gap is **critical** (i.e., it materially affects the
>    recommendation), tag it `[CRITICAL_GAP]` so the parent can run a
>    follow-up researcher.
> 4. Cap output at 600 words (1000 for Decision template on
>    high-stakes).
> 5. End with a `## Sources` section — flat dedupe of all URLs/paths
>    cited in the briefs.

### Step 6 — gap-closing follow-up (max 1 round)

If the synthesizer's output contains any `[CRITICAL_GAP]` tags:

1. Spawn **one** additional researcher (sonnet, 400-word cap) targeted
   at the most critical gap. Include the same sibling-angle list plus
   the synthesizer's framing of the gap.
2. When it returns, spawn a **short synthesizer addendum** on opus —
   word cap 300 — that takes just the original synthesis + the
   follow-up brief and produces `## Addendum` with updated findings or
   remaining unknowns.
3. **Cap at 1 follow-up round.** No recursive gap-closing — if the
   follow-up also flags critical gaps, report them and stop.

### Step 7 — persist + deliver (default-save)

1. Generate a slug from the original question (kebab-case, ≤40 chars).
2. **Save by default** to
   `research/<YYYY-MM-DD>-<slug>.md` at the repo root. The file should
   contain: original question, angle list, synthesis output, optional
   addendum, and a timestamp footer. Create the `research/` directory
   if it doesn't exist.
3. Show the user:
   - The synthesized brief (inline, readable).
   - The save path (one line): *"Saved to `research/2026-04-19-should-we-retire-ccxt.md`"*.
4. User can opt out by saying "don't save" or similar — **opt-out, not
   opt-in**. The expense of the fan-out justifies default persistence.

---

## Output templates in detail

### Decision
```
## TL;DR
<Decision: go / no-go / conditional> · Confidence: <high/med/low>

## Options considered
- **Option A** · <pros> · <cons> · <cost>
- **Option B** · <pros> · <cons> · <cost>
- ...

## Recommendation
<one paragraph — weighted by confidence, tied to user's stated constraints>

## Gaps
- <what would sharpen this decision if answered>

## Sources
- <flat list>
```

### Landscape
```
## Feature matrix
|                  | Comp A | Comp B | Comp C | Us |
| Feature 1        | ✓      | partial| ✗      | ✓  |
| Feature 2        | ✗      | ✓      | ✓      | ✗  |
| ...

## Standouts
- <thing one competitor does unusually well>

## White space
- <feature nobody does well → potential differentiation>

## Gaps
## Sources
```

### Explain
```
## TL;DR
<2-sentence answer>

## Key facts
- <bullet>

## Nuances
- <bullet — things that look obvious but aren't>

## Gaps
## Sources
```

### Timeline
```
## Timeline
- <YYYY-MM-DD> — <event>
- <YYYY-MM-DD> — <event>

## Root cause(s)
- <primary driver>

## Contributing factors
- <secondary drivers>

## Unknowns
## Sources
```

### Generic (fallback)
```
## TL;DR
## Consensus
## Tensions
## Gaps
## Recommendation
## Sources
```

---

## Anti-patterns

- ❌ Spawning researchers sequentially → loses parallelism.
- ❌ Skipping the AskUserQuestion angle-confirmation step → expensive
  agents fire on angles the user would have redirected.
- ❌ Running fewer than 5 researchers (unless user explicitly approves
  4) → defeats fan-out.
- ❌ Running researchers on opus → burns cost × N.
- ❌ Running synthesizer on sonnet → sacrifices quality on the step
  that matters most.
- ❌ Recursive gap-closing → Step 6 caps at 1 round. Tell the user
  about remaining gaps, don't chase them forever.
- ❌ Forgetting to save → default-save is the rule.
- ❌ Letting researchers browse each other's work → Step 3 uses
  sibling-angle *titles only*, not briefs.
- ❌ Using this for codebase-only questions → Explore subagent is
  faster.

## Tuning knobs

- **Angle count**: 5 minimum (4 only on explicit user approval), 7 max.
- **Depth mix**: default to mostly `standard`; use `deep` for at most 2
  angles; `quick` for ≤2 surface scans.
- **Model**: sonnet for researchers, opus for synthesizer + addendum.
  Override to haiku only for throwaway scans.
- **Word caps**: 200 (quick) / 400 (standard) / 700 (deep) per researcher.
  Synthesizer: 600 default, 1000 for Decision + high stakes. Addendum:
  300.
- **Follow-up rounds**: 1 max (Step 6).

## Example end-to-end

**User:** `/research should we replace ccxt with native REST for discovery + klines?`

**Step 0:** Not answerable in 2 tool calls — proceed.

**Step 1 (decompose, self-critique):** 6 angles drafted:
1. Implementation cost — LOC per venue [standard]
2. Operational benefit — startup time, deps, failure modes [standard]
3. Ongoing maintenance — exchange API drift, does ccxt absorb it? [deep]
4. Ecosystem alternatives — lighter adapter layer? [quick]
5. Risk of regression — features lost (normalization, pagination) [standard]
6. Real-world precedent — others who moved off ccxt, outcomes [quick]

**Step 2 (AskUserQuestion):** user drops "ecosystem alternatives",
keeps 5.

**Step 3 (fan out):** 5 `Agent` calls in one message. Each prompt
includes a "sibling angles" list of the other 4 titles.

**Step 4 (failure handling):** all 5 return — proceed.

**Step 5 (synthesize):** opus picks `Decision` template, outputs 900
words, flags one `[CRITICAL_GAP]`: "concrete LOC estimate for Bybit
native v5 instruments-info — no researcher dug into it."

**Step 6 (gap close):** one sonnet researcher targets that gap, returns
a brief. Opus addendum (300 words) integrates it into the Decision's
"Options considered" column.

**Step 7 (persist):** save to
`research/2026-04-19-retire-ccxt.md`. Show user the synthesis + path.
