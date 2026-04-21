# Add-exchange skill redesign — 5-agent debate

**Date:** 2026-04-21
**Topic:** How should we redesign the RoboSpread `/add-exchange` skill so it best fits the project?
**Rounds:** 3 (user-requested override)
**Roster:** Skeptic · Domain expert (connector-pattern / Python skill authoring) · User advocate · Pragmatist · Synthesizer (opus)

## Invocation context

Used the current `.claude/skills/add-exchange/SKILL.md` to wire OKX (Phase 13). 14 concrete gaps surfaced:

1. Dual-channel WS + runtime-derived funding interval is a 4th archetype, not documented.
2. Python default User-Agent gets 403'd by OKX — not in pitfalls.
3. No guidance for N-channel-per-symbol subscribe (had to override `_build_subscribe_message`).
4. No source-of-truth for fees — invented OKX 0.05%/0.02% from memory.
5. Icon URL guessed; no fallback.
6. `history.py` requires 3 separate edits in one file.
7. No verification helper — step 5 is manual curl + python one-liners.
8. No deposit/withdraw status guidance (Binance-bapi-only right now).
9. Phase N commit requires looking up last N.
10. Discovery is serial (~38s startup for 8 exchanges).
11. `CHANGELOG.md` vs `changelog.md` case mismatch.
12. No geoblocked-venue fallback.
13. No "clone existing connector" subflow (Aster ≈ Binance).
14. Symbol-space quirks (USDC-settled, inverse, dated contracts) not enumerated.

---

## Consensus

All 5 agents converged on **`split-into-scaffold-plus-verify`**: a two-skill split (`add-exchange` scaffold + `verify-exchange`) backed by a hard runtime fee-source-URL gate in `ExchangeWS.__init_subclass__`. Stabilized at **Round 3** with unanimous agreement.

## Remaining disagreements

No remaining disagreements. Minor unresolved emphasis differences (not conclusion-level):

- Pragmatist wants the scaffold delivered as a codebase-resident file (`backend/exchange/_template_ws.py`) rather than skill-narrated prose.
- Expert argues Archetype 4 remains a named archetype in docs; no one explicitly ratified this.
- User advocate insists async discovery must be baked into the template now, not deferred.

## Open questions surfaced

- What exactly triggers the `__init_subclass__` assertion — a `fee_source_url` class attribute, a registry lookup into `EXCHANGES`, or both?
- How does the verify helper validate that the URL content actually matches the declared fee (vs. just that a URL is present)?
- Geoblocked-venue fallback (gap #12): no concrete mechanism proposed.
- `CHANGELOG.md` vs `changelog.md` case mismatch (gap #11): never explicitly addressed.
- Symbol-space quirks enumeration (gap #14): mentioned in prompt, not resolved.
- Phase N commit lookup (gap #9): not addressed.
- Whether the four archetypes get named in the scaffold skill or only in the template file.

## Round-over-round notes

- **Conclusion token stabilized:** Round 3 (5/5 on `split-into-scaffold-plus-verify`).
- **Round 1 tally:** 3 split, 1 monolithic (Pragmatist), 1 `other:split-with-enforced-fee-gate` (Skeptic).
- **Round 2 flips:**
  - *Pragmatist* flipped `keep-monolithic` → `split`. Reason: proposed `__init_subclass__` runtime assertion, which made split+gate concrete enough to adopt.
  - *Skeptic* held, named threshold: "verify script must have fail mode for fee/source-URL mismatch."
- **Round 3 flip:**
  - *Skeptic* flipped `other:split-with-enforced-fee-gate` → `split`. Reason: layered enforcement (import-time `__init_subclass__` + CI test) met the named threshold; grep alone would have been insufficient (wrong number + correct comment still passes).
- Synthesizer dropped the CI test in round 3 (no CI exists in RoboSpread), leaving `__init_subclass__` as the hard gate and `verify_exchange.py` as dev UX.

## Actionable next steps

1. **`backend/exchange/base.py`** — add `fee_source_url` class attribute requirement on `ExchangeWS`; implement `__init_subclass__` that asserts `EXCHANGES[exchange_id]` has `maker_fee`, `taker_fee`, AND a non-empty `fee_source_url`. Fail at import time.
2. **`backend/exchange/_template_ws.py`** — codebase-resident connector template covering all 4 archetypes (including Archetype 4: dual-channel WS + runtime-derived funding interval). Bake in async discovery to kill the ~38s serial startup (gap #10).
3. **`backend/scripts/verify_exchange.py`** — dev-UX helper: runs a connector for N seconds, verifies ticks flow into `state.update_leg`, echoes fee-source URL for human eyeball, checks deposit/withdraw status wiring.
4. **`.claude/skills/add-exchange/SKILL.md`** — single entry-point scaffold skill. Points at template file, enumerates 4 archetypes, covers gaps 2/3/5/6/11/12/13/14.
5. **`.claude/skills/verify-exchange/SKILL.md`** — wraps `verify_exchange.py` with usage guidance and deposit/withdraw status validation (gap #8).

---

## Full transcript

### Round 1

**Skeptic** — `other:split-with-enforced-fee-gate`
> Split the skill, but splitting alone won't prevent invented-fee recurrence. Need a machine-readable fact-sheet (yaml) of fees + source URLs per exchange. A prose skill can't stop you from making up 0.05%/0.02% again.

**Expert** — `split-into-scaffold-plus-verify`
> Two skills: `add-exchange-scaffold` (clone template, wire files, probe) + `verify-exchange` (automated end-to-end check). Archetype 4 documented. Fees live in `config.py` with a comment citing source URL — reviewable in PR.

**User advocate** — `split-into-scaffold-plus-verify`
> Time-to-working-exchange is what matters. Scaffold skill should take <10 min. Verify script gives confidence without manual curl. Fee provenance via `config.py` comments is lightweight enough.

**Pragmatist** — `keep-monolithic-with-additions`
> Splitting adds skill-switching overhead. One `SKILL.md` with Archetype 4, pitfalls section expanded, and a `verify.py` helper covers 90% of the pain. Three skills = three places to update when Phase 14 drifts.

**Synthesizer** — `split-into-scaffold-plus-verify`
> Scaffold + verify is the natural split — one 'do the work', one 'prove it works'. Third skill (`claim-fees`) is overkill. Fee-gate enforcement is the valid Skeptic concern to resolve in round 2.

### Round 2

**Skeptic** — `other:split-with-enforced-fee-gate` (holding)
> Pragmatist's 'config.py comments' still allows me to write a comment with a wrong number. `verify_exchange.py` must assert fee values against YAML with checksums, not just check presence. Named threshold: I'll converge only if the verify script has a fail mode for fee/source-URL mismatch.

**Expert** — `split-into-scaffold-plus-verify`
> Absorbed Skeptic's concern: `verify_exchange.py` fails if `config.py` exchange entry lacks `# source: <url>` comment next to `maker_fee`/`taker_fee`. No yaml needed; comment discipline + grep check is sufficient.

**User advocate** — `split-into-scaffold-plus-verify`
> YAML pre-fills fees in scaffold — still takes 30 min total with verify. Fee-gate addressed by comment + grep. Keep it simple for future-me.

**Pragmatist** — `split-into-scaffold-plus-verify` (FLIPPED from monolithic)
> Runtime assertion in `ExchangeWS.__init_subclass__` checks that `EXCHANGES[self.exchange_id]` has `maker_fee`/`taker_fee` AND a source-URL comment in the config file. Fails at import time. No yaml, no external fact-sheet.

**Synthesizer** — `split-into-scaffold-plus-verify`
> Converging. Minimum artifact set: (a) `add-exchange-scaffold` skill, (b) `verify_exchange.py` script, (c) `test_exchanges_config.py` CI test for fee-source-URL provenance. Third skill unnecessary. Skeptic's concern collapses into the CI test.

### Round 3

**Skeptic** — `split-into-scaffold-plus-verify` (FLIPPED)
> Named threshold met by `__init_subclass__` runtime enforcement (hard import-time gate) + CI test combination. Grep alone was insufficient (wrong number with correct comment still passes). Change_justification: Pragmatist introduced `__init_subclass__` — a hard gate I had not seen proposed before.

**Expert** — `split-into-scaffold-plus-verify`
> `__init_subclass__` is primary enforcement: no test suite exists, startup imports all connectors eagerly, failing import louder than failing grep. Archetype 4 stays named (feature-block decomposition cognitively heavier for one-person codebase). OKX's dual-channel + runtime-derived interval is genuinely distinct enough to warrant Archetype 4.

**User advocate** — `split-into-scaffold-plus-verify`
> 3 artifacts fine IF scaffold skill is the single entry point. `<30 min` from Exchange #9 POV. `test_exchanges_config.py` hidden until CI catches regression — that's fine. Bake async discovery into template now; don't defer it to a separate optimization that never ships.

**Pragmatist** — `split-into-scaffold-plus-verify`
> Scaffold template is a FILE, not a skill prompt. `backend/exchange/_template_ws.py` — a real file devs copy, not a skill-narrated clone flow. Codebase-resident files drift with the code naturally. Two artifacts to maintain vs. fourteen gaps to rediscover on every exchange add.

**Synthesizer** — `split-into-scaffold-plus-verify`
> Commit to layered enforcement: `__init_subclass__` (hard gate) + `verify_exchange.py` (dev UX). Skip CI test — redundant with (a) and RoboSpread has no CI. Artifact tree: `.claude/skills/add-exchange/SKILL.md`, `.claude/skills/verify-exchange/SKILL.md`, `backend/scripts/verify_exchange.py`, `backend/exchange/base.py` (add `fee_source_url` attr + `__init_subclass__` assertion).
