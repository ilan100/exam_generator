# WP-061 Language Policy Consistency Audit

Methodology: repository-wide search for language-policy wording (`grep -ri "hebrew\|english\|language"` across `docs/`, `implementation/`, `prompts/`, `README.md`, plus targeted inspection of `src/exam_generator/generation/generator.py` and `prompts/validation/quality.txt`). No external search, no LLM call.

## Path Note (WP-061 section 27's own "do not assume the filename if it differs")

WP-061 assumed the canonical document would live at `docs/architecture/LANGUAGE_POLICY.md`. **No `docs/architecture/` directory exists in this repository.** The actual, already-existing, user-supplied authoritative document is `docs/LANGUAGE_POLICY.md`, at the project's flat `docs/` convention (alongside `ARCHITECTURE.md`, `MASTER_PROJECT_BRIEF.md`, `CLAUDE_HANDOFF.md`, `GPT_HANDOFF.md`, `PROJECT_STATUS.md`). **`docs/LANGUAGE_POLICY.md` is used as the canonical path throughout this WP** rather than creating a new subdirectory or a duplicate file - this is documented explicitly here rather than silently assumed.

## Consistency Matrix

| Source / Document | Current Wording (summary) | Classification | Conflict? | Action Taken |
|---|---|---|---|---|
| `docs/LANGUAGE_POLICY.md` | The full, broad, mandatory English-whenever-available rule, applying to every professional/technical item throughout a question (stem, answer, distractors), not only the target's own name | `AUTHORITATIVE_CURRENT` | No (this is the standard) | Strengthened with an explicit conflict-resolution rule (new section 19a); used as canonical at its real path |
| `docs/MASTER_PROJECT_BRIEF.md` ("Question Requirements") | "Questions are in Hebrew... Preserve natural terminology conventions... English anatomical terms, or Hebrew and English terms used together, should remain where appropriate rather than being mechanically translated" | `AUTHORITATIVE_CURRENT` (root product spec) | No - looser/softer phrasing, but not contradictory; does not claim a narrower scope than `LANGUAGE_POLICY.md` | None - not rewritten (root spec, not a historical WP; still accurate, just less specific than the now-elaborated policy) |
| `docs/GPT_HANDOFF.md` ("Question requirements") | Same original looser wording as the master brief, no pointer to the language policy | `STALE_ACTIVE_INSTRUCTION` (active onboarding document for the architect role, no conflicting claim, just missing the pointer) | No direct conflict, but incomplete | **Updated**: added an explicit pointer to `docs/LANGUAGE_POLICY.md` with a one-paragraph summary of the current rule |
| `docs/CLAUDE_HANDOFF.md` (resume checklist, step 3) | Already instructed session-start reading of `docs/LANGUAGE_POLICY.md` (present before this WP - not introduced by WP-061) | `CONSISTENT` but incomplete (session-start only, no per-WP or conflict-stop rule) | No | **Updated**: added an explicit per-WP check ("if the WP can affect generation/prompts/target planning/normalization/validation/output/terminology, read `docs/LANGUAGE_POLICY.md` first... if conflict, stop and report") to the "Normal Work Package Rules" section, which applies to every WP, not only session start |
| `docs/ARCHITECTURE.md`, WP-041 section | Documents WP-041's own historical implementation: English required for correct answer + in-question target reference only | `HISTORICAL_RECORD` (accurately describes what WP-041 built, at the time) | No direct conflict - does not itself claim to be the current global policy statement | None - accurate historical record of WP-041's own scope, left unmodified |
| `docs/ARCHITECTURE.md`, WP-058 section | States the correct-answer-only scope as the settled, current architecture ("it does not change the general Hebrew-language requirement for the rest of the question... never the rest of the question") | `CONFLICTING` (this is exactly the narrower interpretation `docs/LANGUAGE_POLICY.md` itself names and supersedes) | **Yes** | **Updated**: added an explicit "Superseded (WP-061)" bullet immediately after the existing content, pointing to `docs/LANGUAGE_POLICY.md` as now-authoritative - the original historical description of what WP-058 built was preserved unmodified, only the claim about policy *scope* was corrected |
| `implementation/WP-058_ARCHITECTURE_REVIEW.md` | Contains the narrower "target-only" interpretation `docs/LANGUAGE_POLICY.md` itself explicitly names as the problem it corrects (`LANGUAGE_POLICY.md` section 1) | `HISTORICAL_RECORD` (a completed, dated architecture review) | Yes, by `LANGUAGE_POLICY.md`'s own explicit statement | None - not rewritten, per WP-061 section 12/36's explicit "do not rewrite historical WP definitions merely to make history look consistent"; superseded via the `docs/ARCHITECTURE.md` annotation instead, not by editing this file |
| `implementation/WP-041.md`, `WP-041_COMPLETION_REPORT.md`, `WP-053.md`, `WP-054.md`, `WP-055.md`, `WP-056.md`, `WP-056_ARCHITECTURE_REVIEW.md`, `WP-057.md`, `WP-057_ARCHITECTURE_REVIEW.md`, `WP-058.md`, `WP-060.md` | Various citations of the general "if English exists, use English; Hebrew only when none exists" rule (the broad form) as WP-specific context/history | `HISTORICAL_RECORD` | No - consistent with, and in most cases directly supportive of, the current broad policy (WP-061 section 17's own observation) | None - accurate historical records, left unmodified |
| `implementation/WP-060_ARCHITECT_REVIEW.md` | Already explicitly cites and endorses the current, broad `docs/LANGUAGE_POLICY.md` definition (its own section 19, "Relationship to Language Policy") | `CONSISTENT` | No | None needed - already aligned |
| `prompts/generation/question.txt` (real, active, production generation prompt) | Base rule: "the question text and all four answer choices must be written in Hebrew... except when the Target-language requirement... explicitly specifies English"; the target-language section itself: "this requirement governs only the two things named above [correct answer; in-question target reference] - it does not change the general Hebrew-language requirement for the rest of the question and the other three (incorrect) answer choices" | `STALE_ACTIVE_INSTRUCTION` / `CONFLICTING` (this is real, live, currently-executing instruction text, not documentation) | **Yes** - narrower than `docs/LANGUAGE_POLICY.md`'s scope (does not require English for professional terminology appearing in distractors or elsewhere in the stem beyond the target's own name) | **Not modified** - per WP-061's own explicit "do not automatically build enforcement... any production enforcement expansion must be a separate architect-approved WP" instruction. Recorded as an **ENFORCEMENT GAP** requiring a future WP (see below) |
| `src/exam_generator/generation/generator.py`, `_validate_target_language_compliance()` (WP-058) | Deterministically rejects a non-ASCII correct answer only when `target.named_entity_target` and `target.topic` is English-representable - covers the correct answer only, never distractors, the question stem, or non-named-entity targets | `STALE_ACTIVE_INSTRUCTION` / `CONFLICTING` (real, deterministic, currently-executing code) | **Yes** - same narrower scope as the prompt | **Not modified** - same reasoning; recorded as an **ENFORCEMENT GAP** |
| `prompts/validation/quality.txt` | "...anatomical terminology (Hebrew or standard English/Latin) used correctly and consistently" | `CONSISTENT` but non-enforcing (permissive - never rejects a compliant answer, never enforces the mandatory-English rule either) | No conflict, but does not enforce | None - out of scope for a documentation-alignment WP; noted for completeness |
| `README.md` | One generic descriptive sentence ("Generates Hebrew neuroanatomy multiple-choice exams...") - not a policy statement | `N/A` | No | None |
| `tests/unit/test_prompts.py`, `tests/unit/test_generation.py` (WP-041/058 language tests) | Test the current (narrower-scope) implementation behavior, which is unchanged by this WP | `CONSISTENT` with current code (not with the broader policy target-state) | No - tests correctly reflect current, unmodified behavior | None - implementation unchanged, so no test change is warranted; these tests will need extension whenever a future WP closes the enforcement gap |

## Enforcement Gaps (WP-061 section 22 - explicitly recorded, not fixed in this WP)

```text
GAP 1: prompts/generation/question.txt only instructs English for the
       correct answer and in-question target-name reference - not for
       distractor terminology, general question-stem terminology, or
       acronyms/symbols unrelated to the target's own name.

GAP 2: _validate_target_language_compliance() (generation/generator.py,
       WP-058) only deterministically enforces the correct answer's
       language for named-entity targets - the same narrower scope,
       and it never applies to non-named-entity targets at all (the
       majority of non-pilot-category generation, per WP-060's own
       finding that most categories still use LLM free-text planning).

Both gaps are the SAME underlying scope limitation (WP-058's own
narrower interpretation, now superseded by docs/LANGUAGE_POLICY.md),
present in two different layers (prompt instruction + deterministic
check). Closing them is explicitly out of WP-061's own scope
("architecture/documentation alignment... any production enforcement
expansion must be a separate architect-approved WP") and is left as
the concrete recommendation for a future implementation WP.
```

## Historical Contradictions Discovered (WP-061 section 12)

The only genuine textual contradiction found (not merely "less specific") is between `docs/LANGUAGE_POLICY.md` and (a) `docs/ARCHITECTURE.md`'s own WP-058 section and (b) `implementation/WP-058_ARCHITECTURE_REVIEW.md` - both stated the correct-answer/target-name-only scope as settled, current architecture. (a) was corrected via an explicit superseding annotation (not a rewrite); (b) is a historical, dated review document and was left untouched, per WP-061's own explicit instruction not to rewrite historical WP records.
