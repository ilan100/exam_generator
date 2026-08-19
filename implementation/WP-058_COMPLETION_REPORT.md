# WP-058 Completion Report — English-Only Generation Compliance

## 1. Objective

Determine where the project's English-first language requirement currently exists, why the real generation pipeline can still produce Hebrew when an English representation exists, and implement the smallest general mechanism that reliably enforces the requirement - triggered by the WP-057 live verification's accepted question `"איזה מהמבנים הבאים הוא Globus Pallidus?"`, which the WP-057 architecture review characterized as non-compliant.

## 2. Existing Language-Rule Location(s) (OBSERVED)

Three distinct layers were traced, none invented for this WP:

1. **`docs/MASTER_PROJECT_BRIEF.md`** ("Question Requirements"): *"Questions are in Hebrew... Preserve natural terminology conventions from historical exams. English anatomical terms, or Hebrew and English terms used together, should remain where appropriate rather than being mechanically translated."* This is the project's own authoritative source document. It states Hebrew as the base language and **explicitly sanctions mixed Hebrew/English terminology** - it does not state "the entire question must become English whenever any term has an English form."
2. **`prompts/generation/question.txt`** (WP-041): the base rule is *"the question text and all four answer choices must be written in Hebrew... except when the 'Target-language requirement' below explicitly specifies English for this target; that requirement takes precedence over this general default for the correct answer choice and for any reference to the target's own name within the question, **and for nothing else**."* The "Target-language requirement" section itself states: *"This requirement governs only the two things named above - it does not change the general Hebrew-language requirement for the rest of the question and the other three (incorrect) answer choices."*
3. **`prompts/formatting.py`'s `format_target_language_requirement()`** (WP-041): renders `TARGET LANGUAGE = English` (requiring the target's own English text, verbatim, for the correct answer and any in-question reference to the target by name) whenever `target.named_entity_target` and `target.topic` is English-representable (`_is_english_representable()`, a pure-ASCII check) - identically scoped to (2).

**All three sources agree, unambiguously: the documented, deliberately-scoped project rule requires English for exactly two items (the correct answer; any in-question reference to the target's own name), never the entire question.** No document anywhere in this repository states a "whole question becomes English" requirement.

## 3. WP-041 Findings Relevant to Language Enforcement (OBSERVED, re-read from `implementation/WP-041_COMPLETION_REPORT.md` and `docs/ARCHITECTURE.md`)

- WP-041's own investigation (section 2) found the base prompt's pre-WP-041 rule was **"the question text and all four answer choices must be written in Hebrew... but do not write the question or the answer choices in English"** - a hard, general Hebrew rule with no carve-out at all. WP-041's own explicit fix was a **precise carve-out for exactly two items**, not a general lift of the Hebrew requirement.
- WP-041's own live pilot achieved **9/9 (100%) compliance with this exact narrow scope** ("every accepted question where the target required English produced a fully English (ASCII) correct answer, zero Hebrew answers where English was required") - purely via prompt instruction. **"No validator was modified"** - WP-041 deliberately left this unenforced by any deterministic check, relying entirely on LLM instruction-following.
- **Conclusion: WP-041 did not "fail" or cover a narrower scope than intended - it correctly solved exactly the problem it defined, and its own documentation (both the completion report and the architecture record) has always been explicit that the general Hebrew rule for the rest of the question was deliberately preserved, not an oversight.**

## 4. WP-057 Reproduction/Evidence (OBSERVED)

The exact WP-057 output, re-examined:

```text
Question: "איזה מהמבנים הבאים הוא Globus Pallidus?"
Correct answer: "Globus Pallidus"
```

Checked against the documented WP-041 scope (section 2/3 above): the correct answer (`"Globus Pallidus"`) is fully English. The in-question reference to the target (`"Globus Pallidus"`, appearing literally in the question text) is also fully English. **The observed WP-057 output is fully compliant with the current, documented, deliberately-scoped project language rule.** The Hebrew portion of the question (`"איזה מהמבנים הבאים הוא"` - "which of the following structures is") is ordinary Hebrew question-stem prose, exactly the kind of text the base Hebrew rule (and the Master Project Brief's own "Questions are in Hebrew" requirement) both require to remain Hebrew, and exactly the kind of "Hebrew and English terms used together" the Master Project Brief explicitly sanctions.

**This is the single most important diagnostic finding of this WP**: the WP-057 architecture review's characterization of this output as a "genuine language-policy violation" applied a standard - the entire question must become English whenever any of its terms have an English form - that is not documented anywhere in this project, contradicts the Master Project Brief's own explicit terminology-mixing allowance, and contradicts WP-041's own explicitly-scoped, previously-reviewed implementation. Per WP-058 section 56's own instruction ("If WP-058 reveals that an earlier WP covered a narrower language invariant than currently understood, document that fact... Do not retroactively alter historical reports"), this is documented here rather than silently accepted or used to justify an unscoped implementation.

## 5. Root-Cause Classification

**PARTIAL_VALIDATION**, for the narrow scope WP-041 actually defines - not for the broader scope the WP-057 review assumed (which is not a defect, because it was never the project's rule).

Specifically: WP-041's own documented, approved requirement (correct answer + in-question target reference must be English when English-representable) was, until this WP, enforced **only** as an LLM prompt instruction, with zero deterministic verification - unlike the structurally analogous WP-040 answer-identity requirement, which WP-047 already hardened with a deterministic post-generation check (`_validate_target_answer_identity()`). This is a real, general, previously-undocumented enforcement gap, independent of Globus Pallidus or identity-first.

Investigating further: `_validate_target_answer_identity()` (WP-047) already requires the correct answer to **contain** the target's own English topic text when `named_entity_target` is true - which, as an emergent, previously-undocumented side effect, already makes a *purely*-Hebrew correct answer structurally impossible to accept (a Hebrew string cannot contain an ASCII substring). The one residual gap that check's own deliberate "incidental surrounding text is allowed" design (WP-046/WP-047, needed for legitimate cases like `"The Basillar artery"`) does not exclude: an answer that satisfies containment while **also** carrying an accompanying non-English rendering alongside the required English text (e.g. `"גלובוס פאלידום Globus Pallidus"`). This exact shape has never been observed in this project's real data (confirmed by inspecting every recorded live-pilot output referenced across WP-036 through WP-057) but is reachable in principle and was not excluded by any existing check.

## 6. Compliance-Boundary Definition (explicit, per section 11's instruction not to silently assume a scope)

```text
IN SCOPE (deterministically enforced by this WP):
  - the correct answer choice text, when target.named_entity_target
    and target.topic is English-representable: must not contain any
    non-ASCII character.

OUT OF SCOPE (deliberately, for reasons stated in section 7 below):
  - the question stem's general prose (governed by the base Hebrew rule,
    unchanged since before WP-041)
  - the three incorrect answer choices (same)
  - "in-question reference to the target's own name" as an independently
    checkable item (see section 7 - not deterministically verifiable
    without techniques this project has repeatedly and explicitly
    prohibited)
  - any notion of "the entire question becomes English" (not the
    project's documented rule at all - see sections 2-4)
```

## 7. English-Exists Determination Mechanism (OBSERVED, reused unchanged)

`target.named_entity_target` (bool) + `target.topic` (str), via a small, local, pure-ASCII check (`_target_topic_requires_english()`, `generation/generator.py`) - deliberately re-implementing, not importing, `prompts.formatting._is_english_representable()`'s identical logic, following this module's own established precedent (`_normalize_answer_text()`'s docstring) for a small local duplicate over a cross-module private import. **No new terminology database, no new model field, no new configuration was introduced** - this is the exact same data source WP-041 already established and WP-054/056/057 already reused for the strategy mapping's own unrelated purposes.

**Why the "in-question reference" half of WP-041's rule was not made independently deterministic**: detecting whether the question text "refers to the target in Hebrew instead of English" requires knowing the space of possible Hebrew transliterations/renderings of the target - an open-ended, unbounded string-matching problem. This project has repeatedly and explicitly rejected exactly this class of technique (WP-038's own investigation explicitly ruled out transliteration/fuzzy/semantic matching as unsafe; WP-058 section 13 itself repeats this prohibition: "Do not use a naive 'no Hebrew characters exist' rule... without first establishing whether the project permits Hebrew-only items," and section 55: "Do not use broad world knowledge such as 'Surely this Hebrew phrase has an English translation.'"). No project data source exists that would let this be checked safely and deterministically; inventing one was explicitly out of scope (sections 14, 55). This is reported as a known, permanent limitation (section 20 below), not silently omitted.

## 8. Implementation Decision

Add one new deterministic post-generation check, `_validate_target_language_compliance()` (`src/exam_generator/generation/generator.py`), called from `QuestionGenerator.generate_candidate_question()` alongside the three existing WP-044/046/047 checks - same pattern, same error type (`InvalidGeneratedOutputError`), same "consumes this attempt, no new retry loop" semantics. **General, not Globus-Pallidus-specific or identity-first-specific**: it fires for any `named_entity_target=True` target with an English-representable topic, regardless of category or strategy preference.

No prompt file was modified (WP-041's existing prompt guidance already correctly states the rule; the gap was enforcement, not instruction) - matching section 9's explicit instruction not to start with a prompt rewrite, and section 29's "prompt guidance improves generation probability; deterministic enforcement protects correctness" principle exactly.

## 9. Files Changed

**Modified (production):**
- `src/exam_generator/generation/generator.py` - one new deterministic check (`_validate_target_language_compliance()`, plus its `_target_topic_requires_english()` helper and a module-level `_NON_ASCII_PATTERN`), wired into the existing check sequence; two docstring updates (module-level check-list and `generate_candidate_question()`'s own docstring).

**Modified (tests):**
- `tests/unit/test_generation.py` - 8 new tests (section 12 below).

**Untouched:** `prompts/generation/question.txt`, `prompts/formatting.py`, `prompts/context.py`, all five validators, `production/producer.py`, retrieval, `models/target.py`, `generation/strategy.py` (WP-054/057 strategy mapping), schemas, config.

## 10. Production Behavior Changed

Exactly one: a `named_entity_target=True` candidate whose target has an English-representable topic, and whose correct answer contains any non-ASCII character, is now rejected as a generation-contract failure (consuming a retry attempt) rather than potentially reaching the five validators. This can only ever make acceptance *stricter* for a narrow, well-defined case that was already supposed to be impossible per the existing prompt instruction and was already substantially (but not completely) prevented by the pre-existing WP-047 check.

## 11. Tests Added

8 new tests in `tests/unit/test_generation.py`, "WP-058: deterministic target-language compliance check" section:
- `test_pure_english_correct_answer_is_accepted` - the exact WP-057-observed shape (Hebrew question stem, English target reference, English correct answer) is accepted, confirming this WP does not regress the real, already-compliant behavior.
- `test_hebrew_decorated_english_answer_is_rejected` - the one real residual gap (section 5) is now closed.
- `test_pure_hebrew_answer_still_rejected_by_existing_identity_check` - confirms the new check coexists with, and does not mask, WP-047's own pre-existing rejection reason.
- `test_hebrew_only_topic_exception_is_permitted` - a synthetic, explicitly-labeled-as-structural test (not a claimed real project item, per section 20's explicit instruction) proving the Hebrew-only exception path still works.
- `test_non_named_entity_target_never_triggers_language_compliance_check`
- `test_language_compliance_check_never_consumes_a_second_llm_call`
- `test_language_compliance_check_is_deterministic_never_an_llm_validator` (source-inspection, matching the established WP-044/046/047 pattern)
- `test_language_compliance_check_coexists_with_target_answer_identity_check`

## 12. Test Matrix

| Input | English exists? | Language used | Expected | Actual |
|---|---:|---|---|---|
| `Globus Pallidus` (correct answer, target `Globus Pallidus`) | YES | English | PASS | **PASS** |
| `גלובוס פאלידום Globus Pallidus` (correct answer, target `Globus Pallidus`) | YES | Hebrew + English | FAIL | **FAIL (new check)** |
| `גלובוס פאלידום` (correct answer, target `Globus Pallidus`) | YES | Hebrew only | FAIL | **FAIL (pre-existing WP-047 check)** |
| `עצם הצדע` (correct answer, synthetic Hebrew-only target `עצם הצדע`) | NO | Hebrew | PASS/allowed | **PASS** |
| `corticospinal   tract` (correct answer, target `Corticospinal Tract`) - pre-existing WP-047 test | YES | English (case/whitespace variant) | PASS | **PASS** (pre-existing test, unaffected) |
| Non-named-entity target, Hebrew-only answer | N/A (rule does not apply) | Hebrew | PASS/allowed | **PASS** |

## 13. End-to-End Verification (OBSERVED, no new live API call - offline replay per section 42's cost-discipline instruction)

Per WP-058 section 42 ("No API Cost Escalation... prefer deterministic local checks") and section 17's explicit allowance ("If reproducing the exact LLM output is stochastic, do not require the same output every time. Instead document the WP-057 observed evidence and reproduce the structural condition using the smallest reliable test"), the new check was replayed **directly against the real, already-recorded WP-057 live output** (`evaluation/live_outputs/wp057_verification_record.json`) rather than spending a new API call:

```text
real recorded question: איזה מהמבנים הבאים הוא Globus Pallidus?
real recorded correct answer: Globus Pallidus
RESULT: PASS - the new WP-058 check does not reject the real WP-057 accepted output
```

This directly confirms (a) the new check is correctly wired to accept real, already-compliant production output, and (b) the WP-057 output was never actually a policy violation under the project's real, documented rule. The **negative** end-to-end path (a language-violating candidate cannot become the final accepted output) is verified via `test_hebrew_decorated_english_answer_is_rejected` (section 11) using a mocked `LLMProvider` at the `QuestionGenerator` level - the real integration point, not a bare unit test of the check function in isolation.

**Real-data substantiation of the Hebrew-only-exception claim**: a fresh, direct scan of all three pilot categories' concept inventories (`extract_concept_inventory()`, zero LLM calls) found **0 non-ASCII concepts among 141 total** (`גרעיני הבסיס`: 63, `אספקת דם`: 47, `מסילות עצביות`: 31) - confirming WP-041's own invariant ("every pilot-category target is pure-ASCII, by construction") still holds today, and confirming section 20's required disclosure honestly: **no verified Hebrew-only item exists in the current project data** for a genuine positive Hebrew-exception example beyond the synthetic structural test.

## 14. Regression Result

```text
.venv/bin/python -m pytest -q
1440 passed, 0 failed
```

Baseline (end of WP-057): 1432 passed. Delta: +8 (section 11).

## 15. API Calls

**Zero.** No new LLM/API call was made anywhere in this WP - the diagnostic phase used only existing documentation and a deterministic corpus scan (`extract_concept_inventory()`, local TF-IDF retrieval, no network); the end-to-end verification used offline replay against already-recorded WP-057 evidence (section 13); the full regression suite uses only mocked `LLMProvider` instances, as established throughout this project.

## 16. Retry Behavior

Unchanged. The new check raises `InvalidGeneratedOutputError`, caught by `QuestionProducer` exactly like the three pre-existing WP-044/046/047 checks - consumes one of the existing 3 attempts, no new retry loop, no configuration change (`generation.max_generation_attempts` untouched).

## 17. Language-Rule Compliance

The documented, deliberately-scoped rule (correct answer + in-question target reference must be English when English-representable) now has both prompt instruction (WP-041, unchanged) **and** deterministic enforcement (this WP, for the correct-answer half) - matching section 45's own target architecture exactly. The in-question-reference half remains prompt-instruction-only, for the reason stated in section 7 (no safe deterministic mechanism exists without techniques this project has repeatedly prohibited) - reported as a known limitation, not silently omitted.

## 18. Non-English Exception Handling

Preserved exactly, per the Master Project Brief and WP-041's own second branch: a target whose topic is not English-representable (no real pilot-category example currently exists, confirmed section 13) is legitimately permitted a Hebrew correct answer; the new check is a no-op for such a target (`_target_topic_requires_english()` returns `False`), verified by `test_hebrew_only_topic_exception_is_permitted`.

## 19. Architectural Conclusion

**PARTIALLY_COMPLETE**, for the reason stated precisely below - not because the implementation is incomplete relative to the project's actual rule, but because the WP-057 review's own framing of the problem included a scope the project has never actually adopted.

1. **The WP-057-observed output was never a violation of any documented project rule.** It fully complied with the Master Project Brief's own explicit terminology-mixing allowance and with WP-041's own explicitly-scoped, previously-approved implementation.
2. **A real, general, previously-undocumented enforcement gap did exist** for the narrower, actually-documented WP-041 scope (LLM-instruction-only, no deterministic check) - this WP closes it with one small, general, non-target-specific deterministic check, mirroring the established WP-044/046/047 pattern exactly.
3. **A broader "the entire question becomes English whenever any term has an English form" policy is NOT implemented**, because (a) it is not the project's documented rule, (b) it would contradict the Master Project Brief's own explicit language, and (c) no project data source exists that could determine "English representation exists" at the sentence/prose level without either inventing unsupported heuristics or adding a translation mechanism - both explicitly prohibited by this WP's own instructions (sections 30, 37, 55).

## 20. Known Limitations

- The "in-question reference to the target's own name must be English" half of WP-041's own rule remains enforced only by prompt instruction - no safe deterministic check exists for it without transliteration/fuzzy matching, which this project has repeatedly and explicitly rejected (WP-038 and others).
- No verified Hebrew-only pilot-category item exists in current project data (0/141 concepts across all three categories) - the Hebrew-only-exception test is necessarily synthetic/structural, not a real-data positive example. If a genuinely Hebrew-only item is ever encountered in production, this code path has never been exercised against real data.
- The residual gap this WP closes (a Hebrew-decorated English answer) has never been observed in this project's real historical data - it was closed pre-emptively based on a real, precisely-identified structural possibility, not a reproduced live failure.
- If the architect wants the broader "entire question becomes English" policy, that is a genuine, new policy decision requiring either new project terminology data (sentence-level canonical English representations, which do not currently exist) or an explicit, narrower redefinition of what "sentence has an English equivalent" means in a way that is actually checkable from existing project data - neither was invented here, per this WP's own explicit prohibition on inventing terminology/data.

## 21. Recommendation for Next Step

No further action is required for the narrow, already-documented WP-041 scope - it is now both instructed and deterministically enforced, general across every named-entity target. **An explicit architect decision is recommended** on exactly one question: does the project want to adopt a broader English-language policy than the one documented in the Master Project Brief and implemented since WP-041? If yes, the next WP should first define what data source would determine "an English representation exists" at the sentence/prose level (not merely per-term), since none currently exists, before any implementation is attempted. If no, the WP-057 architecture review's characterization of the observed output as non-compliant should be understood as a scope misunderstanding, now corrected by this report, and no further work is needed on this thread.

---

# Required Diagnostic Table

| Layer | Existing mechanism | Problem found | WP-058 action |
|---|---|---|---|
| Prompt | `format_target_language_requirement()` (WP-041) instructs English for correct answer + in-question target reference only | None - correctly scoped, matches Master Project Brief | None (preserved unchanged) |
| Target terminology | `target.named_entity_target` + `target.topic` (ASCII check) | None - confirmed still 100% ASCII across all 141 real pilot-category concepts | None (reused unchanged) |
| Candidate model | `GeneratedQuestionResponse.answers`/`.correct_answer` | None | None |
| Normalization | None exists (no language normalization step anywhere) | N/A - not needed, enforcement is reject-not-repair | None |
| Validation | Five LLM validators (grounding/MCQ/category/quality/textbook) - `QualityValidator` tolerates "Hebrew or standard English/Latin" (WP-041 finding), never a language-policy check | Correct-answer language was enforced only by prompt instruction, no deterministic check (real gap, for the WP-041-scoped rule only) | Added `_validate_target_language_compliance()`, a new deterministic pre-validator check (not a new validator, matching the WP-044/046/047 precedent) |
| Final output | `CandidateQuestion`/`ExamQuestion` | None - the new check runs before `CandidateQuestion` construction, so a violating candidate never reaches final output | None further needed |

# Required Compliance Table

| Case | English exists | Output language | Expected | Actual |
|---|---:|---|---|---|
| English identity question (real WP-057 evidence) | YES | English (correct answer) | PASS | **PASS** |
| Hebrew identity question (correct answer itself in Hebrew) | YES | Hebrew | FAIL | **FAIL** (pre-existing WP-047 check) |
| Mixed Hebrew/English correct answer | YES | Mixed | FAIL | **FAIL** (new WP-058 check) |
| Hebrew-only item (synthetic, no real example exists) | NO | Hebrew | ALLOW | **ALLOW** |
| English technical term in English prose (correct answer, whitespace/case variant) | YES | English | PASS | **PASS** |

# Required Production-Change Table

| Area | Changed? | Reason |
|---|---|---|
| Language prompt guidance | NO | WP-041's existing guidance already correctly scoped; no rewrite needed |
| Language compliance mechanism | YES | New deterministic post-generation check, general across all named-entity targets |
| QuestionGenerator | YES (minimal) | One new check call + two docstring updates; no structural change |
| QuestionProducer | NO | Existing retry/attempt handling already correctly consumes any `InvalidGeneratedOutputError` |
| Validators | NO | No validator modified; new check is a pre-validator, mirroring WP-044/046/047 |
| Retrieval | NO | Not applicable to language compliance |
| Strategy mapping | NO | WP-057's mapping unchanged |
| Target representation | NO | `QuestionTarget` gained no new field |
| Schemas | NO | No schema file touched |
| Retry budget | NO | 3 attempts, unchanged |
| Output model | NO | `CandidateQuestion`/`ExamQuestion` unchanged |

---

# Terminal Summary

```text
WP-058 complete.

Objective:
Establish reliable English-first generation compliance.

Observed WP-057 issue:
Hebrew generated/accepted despite English representation existing -
found, on investigation, to already be fully compliant with the
project's actual, documented, WP-041-scoped rule (correct answer +
in-question target reference only, never the whole question).

WP-041 mechanism:
Correctly and deliberately scoped to two items (correct answer;
in-question target reference); 100% compliant in its own live pilot;
enforced only via prompt instruction, never a deterministic check.

Root cause:
PARTIAL_VALIDATION (for the narrow, actually-documented scope only -
LLM-instruction-only enforcement, no deterministic check existed)

Compliance boundary:
Correct answer text must be entirely ASCII/English when
named_entity_target and topic is English-representable. Question-stem
prose and the three distractors remain governed by the general Hebrew
rule, unchanged since before WP-041, per the Master Project Brief's own
explicit terminology-mixing allowance.

English-exists source:
target.named_entity_target + target.topic (ASCII check) - the same
source WP-041/054/057 already established and reused; no new
terminology data invented.

Implementation:
One new deterministic check, _validate_target_language_compliance()
(generation/generator.py), general across every named-entity target,
mirroring the existing WP-044/046/047 pre-validator-check pattern.

Deterministic language tests:
8 new tests, all passing.

English-compliant cases:
PASS (real WP-057 evidence replayed offline; new check does not reject
already-compliant output)

Hebrew-when-English-exists cases:
FAIL correctly - both the pre-existing pure-Hebrew case (WP-047) and the
new Hebrew-decorated-English case (WP-058) are rejected.

Hebrew-only exception:
PASS (synthetic/structural test only - no real Hebrew-only project item
exists, confirmed by a fresh 141-concept scan across all three pilot
categories)

End-to-end verification:
Offline replay against real WP-057 recorded output (PASS) + mocked
negative-path test at the QuestionGenerator integration level (rejects
correctly). No new live API call was made.

Full regression:
1440 passed, 0 failed (1432 pre-existing + 8 new)

Production changes:
One new deterministic pre-validator check in generation/generator.py;
no prompt, validator, retrieval, schema, or strategy-mapping change.

WP-057 strategy mapping:
UNCHANGED

Retry budget:
UNCHANGED

Retrieval:
UNCHANGED

Target representation:
UNCHANGED

Conclusion:
PARTIALLY_COMPLETE - the documented, deliberately-scoped WP-041 rule is
now fully enforced (instruction + deterministic check); a broader
"entire question becomes English" interpretation is explicitly not
implemented, because it is not the project's documented rule, would
contradict the Master Project Brief's own explicit language, and no
project data source exists to determine it safely and deterministically.

Known limitations:
In-question target-name-reference language cannot be deterministically
verified without prohibited transliteration/fuzzy-matching techniques;
no real Hebrew-only project item currently exists to validate that
exception path against real data.

Completion report:
implementation/WP-058_COMPLETION_REPORT.md

Waiting for architect review.
```
