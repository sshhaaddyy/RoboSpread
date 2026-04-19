# Project skills

Project-scoped Claude Code skills for RoboSpread. Skills declared here become
user-invocable via `/<skill-name>` in any session rooted at this repo.

## Format

One directory per skill, containing a `SKILL.md` with YAML frontmatter:

```markdown
---
name: <skill-name>
description: <one-line description of when this skill applies>
---

<skill body — instructions the model follows when the skill is invoked>
```

## Skills in this folder

- `add-exchange/` — end-to-end recipe for wiring a new exchange connector
  (REST discovery, WS connector, config registry, pair-discovery, history,
  CHANGELOG). Distilled from the 5 venues added so far (Hyperliquid, Bitget,
  Gate, MEXC, Aster).

## Authoring new skills

- Keep the SKILL.md body terse — it loads into context on invocation, so
  every line should be load-bearing.
- Capture *earned* knowledge: patterns that took real investigation to
  uncover (undocumented WS behavior, semantic mismatches between APIs,
  quirks that burned you once and shouldn't burn you again).
- Don't duplicate what CLAUDE.md already says; reference it instead.
