# WP-061 Completion Report — Language Policy Architecture Alignment

## 1. Objective

Make the project's authoritative language policy (the user-supplied `docs/LANGUAGE_POLICY.md`, correcting the WP-058 architecture review's narrower target-only interpretation) discoverable, authoritative, and consistent across the repository's architecture documents and active implementation instructions. **Architecture/documentation-alignment only - no production code, prompt, or test change; no new language-generation experiment.**

## 2. Authoritative Language Policy

```text
Questions are written in Hebrew.

For every professional/technical/terminological item (anatomical names,
acronyms, symbols, abbreviations, named entities, domain-specific
terminology - not only the target's own name):

    if an English representation exists:
        English MUST be used.

    if no English representation exists:
        Hebrew MAY be used.

This applies to question-stem terminology, target names, correct
answers, distractors, and relevant user-visible generated terminology.

This does NOT require the entire question to be written in English.
```

Source: `docs/LANGUAGE_POLICY.md` (the user-supplied, already-existing document read at the start of this WP - not authored by this WP).

## 3. Documents Audited

`docs/LANGUAGE_POLICY.md`, `docs/MASTER_PROJECT_BRIEF.md`, `docs/ARCHITECTURE.md`, `docs/CLAUDE_HANDOFF.md`, `docs/GPT_HANDOFF.md`, `docs/PROJECT_STATUS.md`, `README.md`, every `implementation/WP-0*.md`/`*_COMPLETION_REPORT.md`/`*_ARCHITECTURE_REVIEW.md` matching a language-related grep, `prompts/generation/question.txt`, `prompts/validation/quality.txt`, `src/exam_generator/generation/generator.py`. Full results: `implementation/WP-061_LANGUAGE_POLICY_AUDIT.md`.

## 4. Conflicting Definitions Found

Two, both stemming from the same source (WP-058's own narrower scoping):

1. `docs/ARCHITECTURE.md`'s WP-058 section - stated the correct-answer/target-name-only scope as settled, current architecture.
2. `implementation/WP-058_ARCHITECTURE_REVIEW.md` - the historical document `docs/LANGUAGE_POLICY.md` itself explicitly names as the problem it corrects.

No other genuine contradiction was found - every other occurrence either already matches the broad policy (e.g. WP-054/056's own historical wording, `implementation/WP-060_ARCHITECT_REVIEW.md`'s own explicit endorsement) or is a looser, non-conflicting restatement (`docs/MASTER_PROJECT_BRIEF.md`).

## 5. Historical vs Active Classification

Full classification (`AUTHORITATIVE_CURRENT`/`HISTORICAL_RECORD`/`STALE_ACTIVE_INSTRUCTION`/`CONSISTENT`/`CONFLICTING`) for every audited document: `implementation/WP-061_LANGUAGE_POLICY_AUDIT.md`'s consistency matrix. Summary: `docs/LANGUAGE_POLICY.md` is `AUTHORITATIVE_CURRENT`; historical WP files (`WP-041.md` through `WP-060.md` and their reports/reviews) are correctly `HISTORICAL_RECORD` and were **not** rewritten (per this WP's own explicit "do not rewrite history" instruction); two real, currently-active/executing artifacts (`prompts/generation/question.txt`, `generation/generator.py`'s `_validate_target_language_compliance()`) are `STALE_ACTIVE_INSTRUCTION`/`CONFLICTING` and are recorded as open enforcement gaps rather than silently fixed.

## 6. Authoritative Document Created/Updated

**Path note**: WP-061 assumed `docs/architecture/LANGUAGE_POLICY.md`; no `docs/architecture/` directory exists in this repository. The real, already-existing, user-supplied document is `docs/LANGUAGE_POLICY.md` (matching this project's established flat `docs/` convention) - used as canonical throughout, per WP-061's own "do not assume the filename if it differs" instruction. **Updated** (not rewritten): added one new section (19a, "Conflict-Resolution Rule") stating explicitly that this document wins on conflict and that Claude must stop and report before implementing a conflicting instruction - the one explicit requirement (WP-061 section 28) the existing document did not yet state in exactly those terms.

## 7. Active Claude Instruction Updated

`docs/CLAUDE_HANDOFF.md`'s "Normal Work Package Rules" section (read and applied for every WP, not only at session start) gained one new bullet: read `docs/LANGUAGE_POLICY.md` before implementing any WP that can affect generation/prompts/target planning/normalization/validation/output/terminology, and stop and report if the WP's own wording conflicts with it. (The session-resume checklist already referenced `docs/LANGUAGE_POLICY.md` at step 3, pre-dating this WP - not introduced here; this WP strengthens it with the per-WP, ongoing check the resume-only mention did not provide.) `docs/GPT_HANDOFF.md` (the architect-side onboarding document, functionally equivalent for the other project role) also received a proportionate pointer update, for consistency - not strictly required by WP-061's own Claude-focused wording, but a natural extension of the same alignment goal, disclosed explicitly here rather than silently done.

## 8. Consistency Matrix

`implementation/WP-061_LANGUAGE_POLICY_AUDIT.md` - full table, every audited document, classification, conflict status, and action taken.

## 9. Tests/Checks

**None added.** No implementation was changed, so no new deterministic test would exercise anything new; the existing WP-041/058 language tests remain valid and unmodified, correctly describing current (narrower, gap-disclosed) behavior. Per WP-061 section 30, tests were required "if the repository already has an appropriate mechanism" for the broader items (acronyms, symbols, distractors) - it does not; building one would be exactly the "large new terminology subsystem" / "production enforcement expansion" WP-061 explicitly reserves for a future, separate, architect-approved WP.

## 10. Regression

```text
.venv/bin/python -m pytest -q
1440 passed, 0 failed
```

Identical to the WP-060 baseline (expected - no production/test code was touched by this WP).

## 11. Production Changes

**NONE.** `git status --short -- src/ tests/ prompts/` shows only the pre-existing, unrelated WP-058 diffs (`generation/generator.py`, `test_generation.py`), confirmed by diff content, not attributable to this WP. This WP touched only `docs/` and `implementation/` files.

## 12. Remaining Enforcement Gaps

Two, both already disclosed in section 5/`implementation/WP-061_LANGUAGE_POLICY_AUDIT.md`:

```text
GAP 1: prompts/generation/question.txt's language section only covers
       the correct answer and in-question target-name reference, not
       distractor terminology, general stem terminology, or
       acronyms/symbols unrelated to the target's own name.

GAP 2: _validate_target_language_compliance() (WP-058) deterministically
       enforces only the same narrower scope, and only for named-entity
       targets - never applied to the (majority) of non-pilot-category
       generation that uses LLM free-text target planning.
```

Both require a separate, architect-approved implementation WP - not addressed here, per WP-061's own explicit scope boundary.

## 13. Final Architecture State

```text
Authoritative language policy:
docs/LANGUAGE_POLICY.md

Question prose:
Hebrew

Professional/technical items:
English whenever an English representation exists

Hebrew:
allowed only when no English representation exists

Whole-question English:
NOT REQUIRED

Acronyms/symbols:
English/international representation when established

Invented English translations:
NOT ALLOWED

New IDENTITY_FIRST mappings:
NONE

Strategy changes:
NONE

Retrieval changes:
NONE

Target-planning changes:
NONE

Schema changes:
NONE

Retry changes:
NONE
```

## 14. Final Conclusion

The repository now has one discoverable, authoritative, explicitly-conflict-resolving language policy document (`docs/LANGUAGE_POLICY.md`), referenced from both the Claude-facing and GPT-facing active handoff instructions, with the one real historical contradiction in `docs/ARCHITECTURE.md` explicitly superseded (not rewritten) and the identical contradiction in the frozen `WP-058_ARCHITECTURE_REVIEW.md` left as an accurate historical record per this project's established "do not rewrite history" discipline. Two genuine, real (not merely documentary) enforcement gaps remain between the new broader policy and the actual production prompt/deterministic-check scope - explicitly disclosed, not silently expanded into during this WP, and left for a future, separate, architect-approved implementation WP.

---

# Required Future-WP Contract

Every future WP affecting generation, prompts, target planning, normalization, validation, output, or terminology must reference `docs/LANGUAGE_POLICY.md` and must not independently redefine the language policy. `docs/CLAUDE_HANDOFF.md`'s "Normal Work Package Rules" now states this explicitly (section 7 above).

---

# Terminal Summary

```text
WP-061 complete.

Objective:
Align repository architecture and active Claude instructions
with the authoritative project-wide language policy.

Authoritative policy:
docs/LANGUAGE_POLICY.md (real path - docs/architecture/LANGUAGE_POLICY.md
does not exist in this repository; deviation documented explicitly)

Question prose:
Hebrew

Professional/technical items:
English whenever English representation exists

Hebrew-only exception:
Preserved

Whole-question English:
NOT REQUIRED

Acronyms/symbols:
English/international representation when established

Documents audited:
~20 (docs/, implementation/, prompts/, README.md, generator.py)

Conflicting active definitions:
2 (docs/ARCHITECTURE.md's WP-058 section; implementation/WP-058_ARCHITECTURE_REVIEW.md)

Historical definitions:
Every implementation/WP-0*.md/_COMPLETION_REPORT.md/_ARCHITECTURE_REVIEW.md
citing the language rule - left unmodified

Authoritative document:
docs/LANGUAGE_POLICY.md (updated with an explicit conflict-resolution rule)

Active Claude instruction updated:
YES - docs/CLAUDE_HANDOFF.md (per-WP check + stop-on-conflict rule);
docs/GPT_HANDOFF.md also updated for consistency

Consistency audit:
implementation/WP-061_LANGUAGE_POLICY_AUDIT.md

Contract/documentation checks:
None added - no implementation changed; existing tests remain valid

Full regression:
1440 passed, 0 failed (unchanged from WP-060 baseline)

Production behavior:
UNCHANGED

Strategy mappings:
UNCHANGED

Target planning:
UNCHANGED

Retrieval:
UNCHANGED

Schemas:
UNCHANGED

Retry budget:
UNCHANGED

Remaining enforcement gaps:
2 - prompts/generation/question.txt's language section, and
_validate_target_language_compliance() (WP-058), both still scoped only
to the correct answer / target-name reference, not the full policy -
left for a future, separate, architect-approved implementation WP.

Completion report:
implementation/WP-061_COMPLETION_REPORT.md

Waiting for architect review.
```
