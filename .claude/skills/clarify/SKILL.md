---
name: clarify
description: Before executing an ambiguous request, batch 2–5 clarifying questions into ONE structured interaction using AskUserQuestion, then proceed with a scoped plan. Invoke when the user types `/clarify <prompt>` (or `/clarify` alone, meaning "ask me questions about what I'm about to request"), or proactively when a request has material scope/approach ambiguity that would cost more to guess wrong on than to ask.
---

# Clarify before executing

Turn a fuzzy request into a sharp one in a single round-trip of questions,
instead of guessing wrong and correcting later, or dripping questions one
at a time.

## When to invoke

Run this skill when the request has **at least one** of:

- **Scope ambiguity** — "the whole backend", "all exchanges", "refactor this"
  (what counts as done? what's in vs out?)
- **Approach ambiguity** — multiple reasonable implementations exist with
  different tradeoffs (fast+shallow vs slow+deep, local vs deploy-ready,
  etc.)
- **Hidden constraint** — performance budget, compat target, deployment
  environment, or deadline not stated
- **Terminology collision** — a word could mean two different things.
  Example from this repo: "move to APIs" = ccxt→native REST vs WS→REST
  polling — opposite answers.
- **Destination ambiguity** — where should output, files, or changes land
  (project-local vs user-global, which branch, which file)
- **Risk threshold unclear** — is this a quick spike or production-bound work?

**Do NOT invoke when:**

- The request is already concrete and unambiguous.
- The ambiguity is trivial and cheaper to decide than to ask (e.g., a
  variable name).
- The user has already answered similar questions earlier in the
  conversation — don't re-ask.
- The user's CLAUDE.md or memory already pins down the preference.

## How to invoke

1. **Restate** the request in one short sentence (≤15 words) so the user
   can redirect early if you've read it wrong.
2. **Identify 2–5 genuine uncertainties**. Pick ones whose answers would
   *change the implementation*, not cosmetic preferences. If only one
   dimension really matters, ask one question — don't pad.
3. **Call `AskUserQuestion` ONCE with all questions batched**. Never drip
   questions across multiple turns.
4. **Each answer option must be concrete**. "The simple approach" is
   useless; "native REST for discovery + kline fetchers; keep ccxt for
   live ticks" is answerable. Options must be mutually exclusive.
5. **Include an "Other" option** on every question so the user can
   volunteer an answer you didn't foresee. Keep `multiSelect: false`
   unless the dimension genuinely allows combinations.
6. **When answers come back**, write a one-paragraph clarified prompt
   back to the user as your action plan — then execute without waiting
   for further confirmation.

## Question-authoring rules

- One uncertainty per question. Don't stack multiple dimensions into one.
- `header` is a ≤12-char tag shown on the question card — make it skimmable
  ("Scope", "Approach", "Target", not "What do you want?").
- `question` is the full natural-language prompt.
- Answer options: 2–4 specific options + "Other". Phrase as things the
  user could pick in <2 seconds of skimming.
- Never ask something you can answer by reading the repo (filenames,
  function signatures, existing config).
- Never ask about preferences already expressed in CLAUDE.md, memory,
  or earlier conversation.
- If the user typed `/clarify <rough prompt>`, treat that string as the
  subject — don't ask them to restate it.
- If the user typed bare `/clarify` with no prompt, respond: "Go ahead —
  what's the request?" and invoke questions on their next message.

## Example

**User says:** `/clarify let's improve the dashboard`

**Restate:** "You want to improve the RoboSpread React dashboard — I need
to scope which part and what kind of change."

**Batched questions via `AskUserQuestion`:**

```
Q1 [Area]:     Which part of the dashboard?
  - Spread table (density, sorting, filters)
  - Pair detail page (chart, leg strip)
  - Alerts / notifications
  - Coin deposit/withdraw badges
  - Other

Q2 [Change]:   Visual polish or new functionality?
  - Visual polish only (spacing, colors, typography)
  - New info surfaces (fields, panels, data I don't see yet)
  - Both
  - Other

Q3 [Target]:   Desktop-only or mobile-responsive?
  - Desktop-only (keep current focus)
  - Mobile-first redesign
  - Both — desktop-first, graceful on mobile
  - Other
```

**Then synthesize:** "OK — going to tighten the spread table with denser
row spacing and a new filter for minimum spread threshold, desktop-only.
Starting now." → proceed.

## Anti-patterns

- ❌ Asking 5 questions in text instead of using AskUserQuestion (no
  structure, user has to re-read every option)
- ❌ Asking questions one at a time across multiple turns
- ❌ Asking "what would you like?" with no options
- ❌ Asking about preferences the user already stated
- ❌ Invoking the skill when the request is already clear (wastes a turn)
- ❌ Including "I'll figure it out" as an option — that defeats the skill

## Integration with AskUserQuestion

The tool signature (load via ToolSearch if not already available):

```
AskUserQuestion({
  questions: [
    {
      header: "<≤12 chars>",
      question: "<full text>",
      multiSelect: false,
      options: [
        {label: "...", description: "..."},
        ...
        {label: "Other", description: "Specify your own answer"},
      ]
    },
    ...  // up to 5 questions
  ]
})
```

One call, all questions. User answers, you proceed.
