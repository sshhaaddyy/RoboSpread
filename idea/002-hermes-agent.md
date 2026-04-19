# 002 — Hermes agent

## Status

Stub — needs clarification before it can become a real draft.

## Prompt from user

> install Hermes agent

## Open questions

- **Which Hermes?** The name collides with several things — not sure which one was meant:
  - An existing agent/tool published somewhere (npm / pypi / GitHub) that should be installed into this repo or into `~/.claude/agents/`? If so, link please.
  - A custom subagent to author from scratch (a messenger-role agent, Hermes = Greek messenger god → maybe the alerts/notifier for Phase 15)?
  - A local tool renamed, e.g. the paper-trading executor?
- **Where should it live?** User-global (`~/.claude/agents/hermes.md`) vs. project-local (`.claude/agents/hermes.md`)?
- **What's its job?** One-line role description. Without that, can't pick tools or write the system prompt.

## Once clarified

- Author `hermes.md` with YAML frontmatter (`name`, `description`, `tools`) per the Claude Code subagent format
- Add to the available-skills list if it should be user-invocable via `/hermes`
- Document its trigger conditions in this file
