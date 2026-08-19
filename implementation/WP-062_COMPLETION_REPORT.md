# WP-062 Completion Report — Language Policy Runtime Enforcement

## 1. Objective

Align runtime generation (prompt) and runtime validation (deterministic post-generation checks) with the authoritative, project-wide language policy established in `docs/LANGUAGE_POLICY.md` (WP-061), closing the two enforcement gaps identified by `implementation/WP-061_ARCHITECTURE_REVIEW.md`:

1. `prompts/generation/question.txt` instructed English-first only for the correct answer and the target's own in-question reference (the narrower WP-058/WP-041 scope), not for stem or distractor terminology generally.
2. `_validate_target_language_compliance()` deterministically checked only `response.answers[response.correct_answer - 1]`, never the three distractors, the stem, or non-named-entity targets.

## 2. Authoritative Language Policy

Per `docs/LANGUAGE_POLICY.md` (re-read in full at the start of this WP, as required by `docs/CLAUDE_HANDOFF.md`):

- Hebrew is the question's base/grammatical language.
- Every professional/technical/terminological item (anatomical names, acronyms, symbols, named entities) must use its established English representation whenever one exists; Hebrew is permitted only when no English representation exists.
- This applies to the question stem, target names, correct answers, and distractors alike — not only the target's own name.
- This never requires the whole question to be written in English.

## 3. Repository Architecture Inspected

Per WP-062 section 4/31, inspected before making any change:

- `src/exam_generator/models/target.py` (`QuestionTarget`, `named_entity_target`, `topic`) — the only field carrying a deterministic English-representation guarantee.
- `src/exam_generator/generation/generator.py` — the four deterministic pre-validator checks, especially `_validate_target_language_compliance()`, `_target_topic_requires_english()`, `_NON_ASCII_PATTERN`, `_normalize_answer_text()`.
- `src/exam_generator/prompts/formatting.py` — `format_target_language_requirement()` (WP-041's per-target renderer, deliberately left unchanged this WP).
- `prompts/generation/question.txt` — the full generation prompt template.
- `src/exam_generator/generation/competitors.py` and `src/exam_generator/models/competitor.py` — `CompetitorCandidate`, investigated as a possible second terminology source.
- `src/exam_generator/planning/concept_inventory.py` / `concept_anchor.py` — the deterministic concept-inventory mechanism (WP-035/WP-060), investigated for reusable terminology data.
- Existing language-related tests in `tests/unit/test_generation.py` (WP-058's language-compliance tests) and `tests/unit/test_prompts.py` (WP-041's target-language-requirement tests).
- `implementation/WP-061_COMPLETION_REPORT.md` and `implementation/WP-061_LANGUAGE_POLICY_AUDIT.md`.

## 4. Existing Terminology Sources

The key design question (WP-062 section 4): *how can the project enforce English for professional/technical items without rejecting ordinary Hebrew prose?*

Findings:

- `QuestionTarget.topic` combined with `QuestionTarget.named_entity_target` is the **only** repository data that deterministically guarantees an item is (a) a specific professional/technical entity and (b) has an established English representation — this is exactly the mechanism WP-041 already built and WP-058 already used.
- `CompetitorCandidate.concept` (`src/exam_generator/models/competitor.py`) was investigated as a possible second source. It is disqualified: it is raw, mixed-language evidence text extracted from student summaries, with no guarantee it is in English, so treating it as an authoritative English label would risk enforcing an unverified, possibly-Hebrew string as if it were the "correct" English form.
- Concept inventories (`extract_concept_inventory()` / `refine_concept_inventory()`, WP-035/WP-060) only exist for the three `PILOT_CATEGORIES` and are used for deterministic target selection, not as a general terminology-lookup table for arbitrary stem/distractor text; reusing them here would require extending them into a role they were never designed or validated for, well beyond this WP's scope.
- No other structured source (historical Excel, source evidence chunks, question/answer models) attaches a verified English representation to arbitrary terminology.

**Conclusion:** the only reliable, existing, deterministic terminology source remains the target's own `topic`. This satisfies WP-062 section 5 ("prefer existing project information; do not duplicate an existing terminology source") without introducing anything new.

## 5. Enforcement Design Decision

Two layers, kept structurally separate per WP-062 section 15:

- **Prompt (instruction only, broad):** broadened to state the full policy scope — Hebrew prose throughout, English for every professional/technical term wherever the evidence shows an established English/Latin form, applying to the stem and all four answer choices, not only the correct answer or the target's own name.
- **Validator (deterministic, narrow):** kept scoped to exactly the one case the repository can reliably verify — the assigned target's own name — but broadened from checking only the correct answer to checking **all four** answer choices, since a distractor containing a Hebrew-decorated rendering of the target's own name is just as reliably detectable as the same problem in the correct answer.

This directly follows WP-062 section 13's validator boundary ("reject only when the validator can establish: specific professional/technical item + established English representation exists + Hebrew representation was used") and section 16's fail-closed boundary (enforce what is reliably identifiable; do not fabricate certainty for the rest — documented in `implementation/WP-062_LANGUAGE_ENFORCEMENT_COVERAGE.md`).

No external terminology system, LLM terminology classification, or new subsystem was introduced (WP-062 sections 6/7), and no STOP condition was triggered — full reliable enforcement of the target-name case was achievable with the existing architecture.

## 6. Prompt Changes

`prompts/generation/question.txt`, three edits:

1. **Base language rule** (was line 5): broadened from "the correct answer choice and any reference to the target's own name... and for nothing else" to a full statement that Hebrew is the question's primary grammatical language and every professional/technical term throughout the stem and all four answer choices must use its established English/Latin form when the evidence shows one, explicitly noting this never requires the whole question to be English.
2. **Target-language-requirement closing line** (was line 27): removed the sentence stating the requirement "governs only the two things named above... it does not change the general Hebrew-language requirement for the rest of the question and the other three (incorrect) answer choices." Replaced with a line clarifying that the deterministic per-target decision covers only the target's own name (the one case that can be decided in advance), and that it does **not** exempt any other terminology anywhere in the question or in any answer choice — the same underlying English-when-established-otherwise-Hebrew principle applies to that other terminology via the model's own judgment from the evidence.
3. **Blueprint self-check checklist** (line 82): added a checklist item requiring the model to verify, before finalizing, that every professional/technical term in the stem and all four answers — not only the correct answer — uses its established English/Latin form where the evidence shows one, Hebrew otherwise.

`format_target_language_requirement()` in `src/exam_generator/prompts/formatting.py` (the WP-041 per-target renderer) was **not modified** — it remains the one deterministic, narrow decision for the target's own name; only the surrounding instructions that govern the rest of the question (by the model's own judgment) were broadened.

Verified via `grep -rn "does not change the general Hebrew\|for nothing else\|governs only the two things"` across `tests/`, `src/`, `prompts/` — zero remaining references to the superseded narrow-scope wording.

## 7. Validator Changes

`src/exam_generator/generation/generator.py`, `_validate_target_language_compliance()`:

- Previously inspected only `response.answers[response.correct_answer - 1]`.
- Now loops `for position, answer_text in enumerate(response.answers, start=1)` and, for each of the four answers, checks whether the answer's normalized text contains the normalized target topic (`_normalize_answer_text`); if it does, and it contains a non-ASCII character (`_NON_ASCII_PATTERN`), the candidate is rejected — regardless of whether that answer is the correct answer or a distractor.
- Answers that do not name the target at all are skipped — this check remains scoped only to the one reliable case (the target's own name), never a general terminology scan.
- The gating condition (`target.named_entity_target` and `_target_topic_requires_english(target)`) is unchanged from WP-058.
- Docstring rewritten to cite `docs/LANGUAGE_POLICY.md` and explain the deliberate scope boundary (target's own name only, now across all four answers).
- The one-line reference to this check in `generate_candidate_question()`'s own docstring updated to note the scope was broadened to all four answer choices in WP-062.

No other deterministic check (`_validate_target_role_consistency`, `_validate_distractor_containment`, `_validate_target_answer_identity`) was modified.

## 8. Test Changes

**`tests/unit/test_generation.py`** — 10 new tests appended after the pre-existing WP-058 language-compliance tests, under a new `# WP-062: language-policy runtime enforcement broadened to all four answers` section:

- `test_hebrew_grammatical_prose_with_english_correct_answer_is_accepted`
- `test_hebrew_decorated_target_name_used_as_a_distractor_is_rejected` — the real new capability: a Hebrew-decorated rendering of the target's own name in a **distractor** position is now rejected (was previously undetected).
- `test_answer_choice_not_naming_the_target_is_never_checked_for_language`
- `test_english_acronym_target_correct_answer_accepted`
- `test_hebrew_expansion_of_english_acronym_target_is_rejected`
- `test_entire_english_candidate_is_not_rejected_by_language_policy_alone`
- `test_language_compliance_check_now_scoped_to_all_four_answers_source_inspection` (source-inspection: confirms `response.answers` + `enumerate` in the check's source)
- `test_disclosed_limitation_pure_hebrew_transliteration_distractor_not_caught`
- `test_disclosed_limitation_non_named_entity_target_language_not_deterministically_enforced`
- `test_disclosed_limitation_question_stem_terminology_never_inspected` (source-inspection: confirms `response.question` is never read by the check)

The three "disclosed limitation" tests exist per WP-062 section 16 — proving each known gap is real and undetected, rather than silently omitting coverage or implying false certainty.

**`tests/unit/test_prompts.py`** — 5 new tests appended after the existing WP-041 target-language-requirement section, under `# WP-062: broadened language-policy runtime enforcement (prompt wording)`:

- `test_base_language_rule_now_covers_the_stem_and_all_four_answers`
- `test_target_language_section_no_longer_exempts_other_terminology`
- `test_blueprint_checklist_now_covers_all_four_answers_not_only_correct_answer`
- `test_superseded_narrow_scope_wording_no_longer_present_anywhere_in_the_prompt`
- `test_target_language_requirement_rendering_itself_is_unchanged_by_wp062` — semantic contract test (WP-062 section 18) confirming `format_target_language_requirement()`'s own output is byte-identical to before, only the surrounding instructions changed.

## 9. Enforcement Coverage

See `implementation/WP-062_LANGUAGE_ENFORCEMENT_COVERAGE.md` for the full required table (Question prose, Professional stem terminology, Target name, Correct answer, Distractors, Acronyms, Symbols, Non-named-entity targets — Policy Applies / Runtime Enforcement / Prompt Enforcement / Tests / Limitation).

## 10. Known Limitations

Explicitly disclosed, not silently assumed away (each has a dedicated test):

1. Question-stem terminology unrelated to the target is never deterministically inspected — prompt instruction only.
2. Distractor (or any answer) terminology unrelated to the assigned target is never deterministically inspected — prompt instruction only.
3. A pure Hebrew transliteration of the target's own name, with no embedded ASCII substring of the target's English text, is not detected by the validator — closing this would require transliteration/fuzzy matching, which this project has repeatedly and explicitly rejected as a safety principle (WP-038 and reaffirmed in multiple subsequent WPs).
4. Non-named-entity targets have no deterministic language enforcement at all — no existing repository data source attaches a verified English representation to their free-text `topic`.
5. Symbol-shaped terminology has no dedicated runtime test because no symbol-shaped target exists in the current pilot-category data to exercise it; covered only by prompt instruction.

## 11. Production-Change Verification

`git status --short -- src/ tests/ prompts/` shows exactly:

```
 M prompts/generation/question.txt
 M src/exam_generator/generation/generator.py
 M tests/unit/test_generation.py
 M tests/unit/test_prompts.py
```

No other production, prompt, or test file was touched.

## 12. Regression Result

Full suite: `.venv/bin/python -m pytest -q` → **1455 passed, 0 failed** (up from 1440 before this WP: +10 in `test_generation.py`, +5 in `test_prompts.py`).

## 13. Strategy Verification

`GenerationStrategyPreference`, `resolve_strategy_preference()`, and `_IDENTITY_FIRST_TARGETS_BY_CATEGORY` in `src/exam_generator/generation/strategy.py` were not read or modified by this WP. No new IDENTITY_FIRST mapping was added.

## 14. Target-Planning Verification

`QuestionTargetPlanner`, `extract_concept_inventory()`, and `refine_concept_inventory()` were inspected only as part of the section-4 feasibility investigation (to check whether they could serve as a terminology source) and were not modified.

## 15. Retrieval Verification

No retrieval code (evidence chunk selection, source-evidence formatting) was modified.

## 16. Source-Authority Verification

The student-summary/course-book/historical-Excel authority hierarchy is unchanged. The factual-authority section of `prompts/generation/question.txt` (lines 84-89) was not touched.

## 17. Recommended Next Step

Per `implementation/WP-062_LANGUAGE_ENFORCEMENT_COVERAGE.md`, the remaining gaps (stem terminology, unrelated-distractor terminology, non-named-entity targets, pure transliteration) all trace back to the same root cause: the repository has no structured, verified terminology source beyond the assigned target's own name. Closing any of them further would require either a new terminology mechanism (out of scope per WP-062 section 6, would need explicit architect approval) or fuzzy/transliteration matching (already rejected as a safety principle). No further runtime-enforcement WP is recommended until the architect decides whether such an expansion is justified; in the meantime, prompt-level instruction remains the only coverage for these cases, which is an accepted, documented trade-off rather than an oversight.

## 18. Final Architectural Conclusion

Runtime behavior is now aligned with `docs/LANGUAGE_POLICY.md` to the full extent the existing repository architecture can reliably support: the generation prompt no longer contradicts the broad policy, and the deterministic validator's scope was broadened from one answer to all four for the one case it can verify without inventing new infrastructure. The prompt/validator division (broad instruction vs. narrow deterministic enforcement) is preserved, Hebrew ordinary prose is never rejected, and every case the validator cannot reliably cover is explicitly documented and tested as a known limitation rather than silently assumed solved.

---

## Terminal Summary

```text
WP-062 complete.

Objective:
Align runtime generation and validation with
docs/LANGUAGE_POLICY.md.

Authoritative policy:
docs/LANGUAGE_POLICY.md

Question prose:
Hebrew

Professional/technical terminology:
English whenever English representation exists

Whole-question English:
NOT REQUIRED

Existing terminology source:
QuestionTarget.topic (named_entity_target=True) - the only repository
data with a guaranteed English representation; CompetitorCandidate and
concept inventories investigated and found unsuitable/out of scope.

Enforcement architecture:
Prompt broadened to full policy scope (instruction only); deterministic
validator broadened from correct-answer-only to all four answer choices,
still scoped to the target's own name only.

Generation prompt:
ALIGNED

Runtime validator:
PARTIALLY ALIGNED (aligned for the target-name case across all four
answers; stem/unrelated-distractor/non-named-entity-target terminology
remains prompt-instructed only, explicitly documented)

Question-stem terminology:
Prompt-instructed only; not deterministically enforced (disclosed limitation)

Target names:
Deterministically enforced across all four answer choices

Correct answers:
Deterministically enforced (unchanged mechanism, now shares the all-answer loop)

Distractors:
Deterministically enforced for the target's-own-name case; not enforced
for unrelated terminology or pure transliteration (disclosed limitations)

Acronyms:
Enforced when the acronym is the assigned target's own topic; not
enforced elsewhere (same scope as target names generally)

Symbols:
Prompt-instructed only; no runtime test exercised (no symbol-shaped
target exists in current data)

Non-named-entity targets:
Not deterministically enforced; disclosed limitation, explicitly tested

Tests:
10 new tests in tests/unit/test_generation.py, 5 new tests in
tests/unit/test_prompts.py, including 3 explicit disclosed-limitation tests

Known limitations:
Stem terminology, unrelated-distractor terminology, pure Hebrew
transliteration of the target, and non-named-entity targets are not
deterministically enforced - documented in
implementation/WP-062_LANGUAGE_ENFORCEMENT_COVERAGE.md

New IDENTITY_FIRST mappings:
NONE

Strategy changes:
NONE

Target-planning changes:
NONE

Retrieval changes:
NONE

Source authority:
UNCHANGED

Full regression:
1455 passed, 0 failed

Enforcement coverage:
implementation/WP-062_LANGUAGE_ENFORCEMENT_COVERAGE.md

Completion report:
implementation/WP-062_COMPLETION_REPORT.md

Architectural status:
Runtime aligned with docs/LANGUAGE_POLICY.md to the full extent the
existing architecture can reliably support, without introducing an
external terminology system or fuzzy/transliteration matching.

Waiting for architect review.
```
