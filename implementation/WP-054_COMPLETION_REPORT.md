# WP-054 Completion Report — Narrow Permanent Identity-First Strategy Implementation

## 1. Objective

Convert WP-053's experimentally-validated identity-first result into a permanent production mechanism, scoped to exactly the two approved (category, target) pairs: `גרעיני הבסיס` + `Caudate Nucleus`, and `גרעיני הבסיס` + `Nucleus Accumbens`. Explicitly not a general strategy-selection system, not a sparse-evidence classifier, not a target-filtering mechanism.

## 2. Architecture Used Before WP-054 (OBSERVED)

- `QuestionTarget` (WP-025, `models/target.py`) carries WHAT to test - `topic`, `category`, `factual_focus`, plus several deterministic booleans (`named_entity_target`, `is_source_role`, `is_enumeration_member`) each backed by its own `format_target_*()` prompt-formatting function (WP-040/043/044).
- `QuestionGenerator.generate_candidate_question()` (`generation/generator.py`) resolves the canonical category, retrieves evidence, deterministically extracts a `QuestionRelationship` (`extract_relationship()`, WP-030) and `CompetitorCandidate`s (`discover_competitors()`, WP-031), builds a `GenerationPromptContext`, renders the production prompt, makes exactly one `LLMProfile.GENERATION` call, then runs several deterministic post-generation consistency checks (`_validate_target_role_consistency`, `_validate_distractor_containment`, `_validate_target_answer_identity`) before constructing `CandidateQuestion`.
- `GenerationPromptContext.render_variables()` (`prompts/context.py`) is the single place that assembles every prompt variable from already-resolved information; each `format_target_*()` function in `prompts/formatting.py` follows an established, consistent pattern: an honest "no requirement applies" sentinel for the ordinary case, and an explicit instructional block otherwise - never a silent omission.
- `QuestionProducer.produce_question()` (`production/producer.py`) holds `category`/`generation_mode`/`target` fixed across up to `max_attempts` (3) generation+validation attempts; strategy resolution needed to live entirely inside generation, with zero changes to this retry loop.
- WP-053's own experiment used a separate, in-memory-only `PromptRepository`/`PromptTemplate` to append an experimental instruction block - explicitly a prototype mechanism, never written to `prompts/generation/question.txt`.

## 3. Implementation Design

Followed the existing `format_target_*()` pattern exactly, adding one new deterministic input (the resolved strategy preference) rather than inventing a new mechanism:

```text
QuestionTarget (category, topic)
        v
resolve_strategy_preference(category, topic)      generation/strategy.py (new)
        v
GenerationStrategyPreference                        models/strategy.py (new)
        v
GenerationPromptContext.strategy_preference          prompts/context.py (new field)
        v
format_target_strategy_requirement()                 prompts/formatting.py (new)
        v
target_strategy_requirement prompt variable           prompts/generation/question.txt (new placeholder)
        v
LLM
```

Strategy resolution happens inside `QuestionGenerator.generate_candidate_question()`, immediately after canonical-category resolution and immediately before context construction - the same point `extract_relationship()`/`discover_competitors()` already run, per WP-054 section 24's "close to generation orchestration, before the generation prompt is rendered" guidance. No validator, retrieval, historical-repository, PDF-extraction, or category-resolver code was touched.

## 4. Strategy Model

`GenerationStrategyPreference(str, Enum)` (`src/exam_generator/models/strategy.py`): `DEFAULT`, `IDENTITY_FIRST`. Placed in `models/` (not `generation/`) for the same reason `QuestionRelationship` lives in `models/relationship.py` while its computation (`extract_relationship()`) lives in `generation/relationship.py`: `exam_generator.prompts` already imports from `exam_generator.models` but cannot import from `exam_generator.generation` (which itself imports `exam_generator.prompts`) without a circular import - `prompts/formatting.py`'s new `format_target_strategy_requirement()` needed the enum type directly. `QuestionTarget` gained **no new field** - strategy is intentionally kept structurally separate from the target (WP-054 section 13), verified by a new regression test (`test_question_target_gained_no_strategy_field`).

## 5. Strategy Resolver

`resolve_strategy_preference(*, category: str, topic: str) -> GenerationStrategyPreference` (`src/exam_generator/generation/strategy.py`) - a pure function over two strings, no I/O, no LLM call, no historical-workbook read at request time (verified by a dedicated regression test asserting the module's own source contains no `HistoricalQuestionRepository`/`.xlsx`/`openpyxl` reference). Looks up `category` in a small, explicit, in-code table (`_IDENTITY_FIRST_TARGETS_BY_CATEGORY`) and checks `topic` for exact (case-sensitive, no fuzzy/substring) membership - mirroring the existing precedent of `generation/relationship.py`'s `_RELATIONSHIP_KEYWORDS` table for a narrow, explicit, hand-reviewed mapping.

`QuestionGenerator.generate_candidate_question()` calls it as `resolve_strategy_preference(category=canonical_category, topic=target.topic)` - using the already-resolved canonical category (not the caller-supplied raw category string, and not `target.category` before it has been validated against the canonical category), so the strategy lookup can never key off an alias or a not-yet-validated mismatch.

## 6. Exact Approved Mappings

```text
גרעיני הבסיס + Caudate Nucleus       -> IDENTITY_FIRST
גרעיני הבסיס + Nucleus Accumbens     -> IDENTITY_FIRST
everything else                       -> DEFAULT
```

`_IDENTITY_FIRST_TARGETS_BY_CATEGORY = {"גרעיני הבסיס": frozenset({"Caudate Nucleus", "Nucleus Accumbens"})}` - the entire mapping, exactly the two approved pairs, no others.

## 7. Prompt Integration

`prompts/generation/question.txt` gained one new instructional section ("Generation strategy preference") and one new placeholder (`{target_strategy_requirement}`), positioned immediately after the existing enumeration-member section - the same position in both the instructions and the rendered-variables block. `GenerationPromptContext.render_variables()` renders it via the new `format_target_strategy_requirement(preference, target)` (`prompts/formatting.py`):

- `DEFAULT` -> an honest sentinel ("No additional generation-strategy preference applies to this target - follow the general guidance above...") - never a silent omission, matching every other `format_target_*()` function's established convention.
- `IDENTITY_FIRST` -> an explicit preference (not an exclusive requirement) for a question whose correct answer is determined by the target's own identity/name, with an explicit statement that it does not relax, replace, or override the answer-identity, target-language, target-evidence-role, or enumeration-member requirements, or the general single-best-answer/grounding requirements.

The blueprint self-check checklist (the prompt's own final "review your own blueprint against this checklist" paragraph) was extended with one clause ("and the question honors the generation-strategy preference stated below, if any") for consistency with every other per-target note already listed there - this is the one place outside the new section/placeholder itself that was touched, and it is a direct extension of the same, already-existing checklist mechanism, not new scope.

This satisfies WP-054 section 22's prompt-isolation requirement: the default (on-disk) template text is a single, immutable file; the actual per-generation content difference is produced entirely by which string `render_variables()` substitutes into the existing `{target_strategy_requirement}` placeholder - never by mutating a template object, never by string concatenation onto a `PromptTemplate.text` at generation time. A dedicated test (`test_strategy_preference_does_not_alter_any_unrelated_prompt_section`) confirms the rendered text is byte-identical outside the "Generation strategy preference:" ... "Possible competing concepts:" span between the `DEFAULT` and `IDENTITY_FIRST` conditions for the same target.

## 8. Language-Rule Handling

The English-first rule (`format_target_language_requirement()`, WP-041) is untouched and orthogonal to this WP - it already governs the correct-answer/target-name language independently of which strategy preference applies. The new `format_target_strategy_requirement()` instruction text itself uses only the target's own already-decided `topic` string (never inventing or translating a name) and does not restate or override the language requirement. See section 17 (Language Verification) below for the live-observed result.

## 9. Tests Added

- `tests/unit/test_strategy.py` (new, 16 tests): the six required WP-054 section 20 scope cases (Cases 1-6) plus an unknown-category case, exact-match/case-sensitivity/partial-match/blank-topic negative cases, determinism, a pure-signature check, a "never reads the historical workbook" source-inspection check, and `GenerationStrategyPreference` model checks.
- `tests/unit/test_prompts.py` (+5 new tests, +7 existing `GenerationPromptContext(...)` call sites updated with an explicit `strategy_preference=GenerationStrategyPreference.DEFAULT`): required-variable presence, `IDENTITY_FIRST` prompt content, `DEFAULT` honest sentinel, prompt-isolation (no unrelated section changes), and `format_target_strategy_requirement()` purity.
- `tests/unit/test_generation.py` (+9 new tests): the WP-054 section 38 integration test (identity-first context reaches the LLM call, using a mock provider, no real API call) for both approved targets; the mandatory Globus Pallidus safety regression (section 35); the other-target-in-category regression (section 37); the cross-category regression (section 36); a no-second-LLM-call check; a check that existing deterministic post-generation checks (WP-047) remain active for an identity-first target; and two scope guards confirming neither `QuestionTarget` nor `CandidateQuestion` gained a `strategy`-named field.

## 10. Integration Test Result

`test_caudate_nucleus_generation_reaches_the_llm_with_identity_first_instruction` / `test_nucleus_accumbens_generation_reaches_the_llm_with_identity_first_instruction`: **PASS** - using a mocked `LLMProvider`, the rendered user-message content sent to `generate_structured()` contains `GENERATION STRATEGY = IDENTITY_FIRST` within the "Generation strategy preference:" section for both approved targets, with zero real API calls. `test_globus_pallidus_generation_never_receives_the_identity_first_instruction` / `test_other_target_in_basal_nuclei_never_receives_the_identity_first_instruction` / `test_caudate_nucleus_outside_basal_nuclei_never_receives_the_identity_first_instruction`: **PASS**.

## 11. End-to-End Results (OBSERVED, real OpenAI API, one fresh run, no reruns)

Script: `implementation/wp054_verification.py` (not production code - mirrors WP-053's own live-pilot script, using the real, unmodified, now-permanent `QuestionGenerator`/`QuestionProducer`/all five real validators/`PromptRepository.from_default_location()`). Full record: `evaluation/live_outputs/wp054_verification_records.json`.

| Target | Resolved strategy | Accepted | Attempts | First accepted question shape |
|---|---|---:|---:|---|
| Caudate Nucleus | IDENTITY_FIRST | Yes | 1 | "איזה מבנה במערכת העצבים המרכזית נקרא Caudate Nucleus?" - pure identity/naming question |
| Nucleus Accumbens | IDENTITY_FIRST | Yes | 2 | Attempt 1 rejected (grounding: bare classification-membership shape, all 4 answers equally valid basal-nuclei members); attempt 2 accepted - "איזה מבנה מהגרעינים הבסיסיים נקרא Nucleus Accumbens?" - identity/naming question |
| Globus Pallidus | DEFAULT | No | 3 | All 3 attempts rejected on grounding, each a classification-membership-ambiguity shape ("איזה מבנה הוא חלק מגרעיני הבסיס...") - the same, already-disclosed WP-045/048 failure family for this target, not a new or worsened failure |

## 12. Globus Pallidus Safety Result (OBSERVED)

`resolved_strategy` was `DEFAULT` for every Globus Pallidus attempt (confirmed both by the deterministic resolver call recorded in the script's own log line and, structurally, by the unit-test suite's `test_globus_pallidus_generation_never_receives_the_identity_first_instruction`). All three rejections are the pre-existing classification-ambiguity family already documented in WP-045/046/048 (`Globus Pallidus`'s own dominant, still-unresolved failure mode) - not a regression introduced by this WP, and not evidence that DEFAULT strategy is "worse": Globus Pallidus was never guaranteed to succeed within budget even before WP-054, and section 40 explicitly instructs not to force a property-based result. The identity-first instruction was never accidentally applied.

## 13. Other-Target/Category Scope Test Results

All PASS - see the required scope-test table below (section 20).

## 14. Regression Test Result

Full suite before this WP: 1396 passed (verified by running `pytest -q` immediately after WP-053, before any WP-054 code change). Full suite after this WP: 1426 passed, 0 failed (1396 pre-existing + 30 new WP-054 tests: 16 in `test_strategy.py`, 5 in `test_prompts.py`, 9 in `test_generation.py` = 30, matching the observed delta exactly). Every pre-existing `GenerationPromptContext(...)` construction site was updated (never deleted or weakened) to supply the new required `strategy_preference` field explicitly.

## 15. Schema Verification

`CandidateQuestion` gained no field (verified: `test_candidate_question_carries_no_strategy_field`). `QuestionTarget` gained no field (verified: `test_question_target_gained_no_strategy_field`, and the pre-existing `test_question_target_gained_no_new_field` in `test_relationship.py` continues to pass unchanged). No input/output JSON schema file under `schemas/` was touched. The strategy preference exists only as generation-internal metadata (a `GenerationPromptContext` field and a rendered prompt string) and never reaches product output.

## 16. Retry-Budget Verification

`QuestionProducer`/`production/producer.py` was not modified at all (`git diff` for this WP touches no file under `src/exam_generator/production/`). `max_attempts` (3, from `config/app.yaml`) is unchanged; strategy resolution happens once per generation attempt, inside `QuestionGenerator`, exactly like every other deterministic pre-generation computation already there (`extract_relationship`, `discover_competitors`) - it does not add, remove, or special-case any attempt.

## 17. Source-Authority Verification

`resolve_strategy_preference()` reads no data source at all - not the student-summary corpus, not `course_book.pdf`, not the historical Excel workbook - it is a pure function of two caller-supplied strings against a fixed in-code table. Student summaries remain the sole factual grounding authority for the generated question itself; `course_book.pdf` remains a secondary consistency check (`textbook.status` unaffected, confirmed `CONSISTENT` in every live round above); the historical Excel workbook remains a style/structure/terminology reference only, never runtime strategy authority (confirmed by `test_resolve_strategy_preference_never_reads_the_historical_workbook`).

## 18. Language Verification

```text
Language rule:
If an English representation exists, use English.
Use Hebrew only when no English representation exists.

Verification:
PASS. All three live-observed correct answers (Caudate Nucleus, Nucleus
Accumbens x2 attempts, Globus Pallidus x3 attempts) used the exact
English target name verbatim, per WP-041's pre-existing, unmodified
format_target_language_requirement() mechanism. The new
format_target_strategy_requirement() text itself is pure English
instructional prose (as every other formatting function's instructional
text already is) and never asserts or overrides a language choice - it
only ever echoes target.topic, which is already required to be the
target's own English text by WP-041.

Generated examples:
"...נקרא Caudate Nucleus?" -> correct answer text: "Caudate Nucleus" (English, verbatim)
"...נקרא Nucleus Accumbens?" -> correct answer text: "Nucleus Accumbens" (English, verbatim)

Existing validator/prompt support:
format_target_language_requirement() (WP-041) unmodified; unaffected by
this WP's new section (the new placeholder sits after target-language
and target-evidence-role in the prompt, subordinate to both by explicit
statement in its own text).

Any remaining language issue:
None observed in this live run. Note (INFERENCE, not proven at scale):
WP-053's own architecture review flagged Hebrew-around-English-name
phrasing ("...הנקרא Caudate Nucleus?") as a distinct concern from the
correct-answer text itself - the *question wording* around the target
name may legitimately mix Hebrew narration with the English target name
(e.g. "...נקרא Caudate Nucleus?" = "...called Caudate Nucleus?"), which
is exactly what format_target_language_requirement() already permits:
its own requirement is scoped only to "the correct answer choice, and
any place within the question where you refer to the target by name" -
the English name itself was used verbatim in-question in both live
rounds above, satisfying that existing rule. No new language issue was
introduced or observed; this WP made no change to
format_target_language_requirement() itself.
```

## 19. Documentation/Decision Updates

`docs/ARCHITECTURE.md`: new "Narrow Permanent Identity-First Strategy (WP-054)" section recording the strategy model, resolver, exact mapping, and the explicit "this is intentionally narrow, not a general sparse-evidence strategy" statement (WP-054 section 47). `docs/PROJECT_STATUS.md`: updated "Next WP Context" with the WP-054 summary and outcome, per this project's established rolling-checkpoint convention.

## 20. Files Changed

**New:**
- `src/exam_generator/models/strategy.py`
- `src/exam_generator/generation/strategy.py`
- `tests/unit/test_strategy.py`
- `implementation/wp054_verification.py` (not production code)
- `evaluation/live_outputs/wp054_verification_records.json` (live verification record)
- `implementation/WP-054_COMPLETION_REPORT.md` (this file)

**Modified:**
- `src/exam_generator/models/__init__.py` (export `GenerationStrategyPreference`)
- `src/exam_generator/generation/__init__.py` (export `resolve_strategy_preference`)
- `src/exam_generator/generation/generator.py` (resolve and thread strategy preference into `GenerationPromptContext`)
- `src/exam_generator/prompts/formatting.py` (new `format_target_strategy_requirement()`)
- `src/exam_generator/prompts/context.py` (new `strategy_preference` field + rendered variable)
- `prompts/generation/question.txt` (new instructional section, placeholder, checklist clause)
- `tests/unit/test_prompts.py` (new tests + required-field updates to existing `GenerationPromptContext(...)` sites)
- `tests/unit/test_generation.py` (new integration tests)
- `docs/ARCHITECTURE.md`, `docs/PROJECT_STATUS.md`

**Untouched (explicitly verified):** `production/producer.py`, all five validators (`validation/*.py`), `retrieval/*.py`, `historical/*.py`, `planning/*.py` (target planning/coverage), every schema under `schemas/`, `config/*.yaml`.

## 21. Final Architecture

| Category | Target | Strategy | Reason | Scope |
|---|---|---|---|---|
| גרעיני הבסיס | Caudate Nucleus | IDENTITY_FIRST | WP-052 + WP-053 evidence | Approved |
| גרעיני הבסיס | Nucleus Accumbens | IDENTITY_FIRST | WP-052 + WP-053 evidence | Approved |
| גרעיני הבסיס | Globus Pallidus | DEFAULT | Property generation remains valuable | Explicit exclusion |
| גרעיני הבסיס | Any other target | DEFAULT | Not experimentally validated | Default |
| Any other category | Any target | DEFAULT | Not experimentally validated | Default |

## 22. Required Scope-Test Table

| Test | Expected | Actual | Pass |
|---|---|---|---|
| Basal nuclei + Caudate Nucleus | IDENTITY_FIRST | IDENTITY_FIRST | Yes |
| Basal nuclei + Nucleus Accumbens | IDENTITY_FIRST | IDENTITY_FIRST | Yes |
| Basal nuclei + Globus Pallidus | DEFAULT | DEFAULT | Yes |
| Basal nuclei + another target (Putamen) | DEFAULT | DEFAULT | Yes |
| Other category + Caudate Nucleus | DEFAULT | DEFAULT | Yes |
| Other category + Nucleus Accumbens | DEFAULT | DEFAULT | Yes |

## 23. Known Limitations (INFERENCE/DECISION, disclosed honestly)

- **Nucleus Accumbens attempt 1 still reverted to a bare-classification shape** even under `IDENTITY_FIRST` (rejected by grounding), succeeding only on attempt 2 - consistent with WP-054 section 15's own framing ("a preference, not IDENTITY_ONLY"): the mechanism reduces but does not guarantee first-attempt success. This is an OBSERVED result, not a defect - the retry budget (3 attempts, unchanged) already exists precisely to absorb this.
- **Globus Pallidus's own classification-ambiguity failure family (WP-045/048) remains genuinely unresolved** - this WP does not address it and was never scoped to. A single live round exhausting all 3 attempts is within its previously-observed behavior, not a new regression.
- **Sample size remains small** (one fresh end-to-end round per target, plus WP-053's own n=2-per-condition experiment) - this WP implements the reviewed decision from WP-053's architecture review; it does not add further statistical confirmation beyond what WP-053 already established.
- No diagnostic logging was added for the resolved strategy (WP-054 section 45 makes this conditional on "the existing architecture already support[ing] appropriate diagnostic logging" - this codebase has no logging infrastructure at all, confirmed by inspection; adding one was correctly out of this WP's narrow scope).

## 24. Future Generalization Boundary

Extending `_IDENTITY_FIRST_TARGETS_BY_CATEGORY` to any other target or category requires its own dedicated evidence-gathering WP (mirroring WP-052's retrospective-analysis step) followed by its own controlled experiment (mirroring WP-053) - never a direct code change based on a chunk-count heuristic, a historical failure count, an LLM judgment, or analogy to these two targets. This boundary is stated both in code comments (`generation/strategy.py`'s module docstring) and here.

## 25. Regression Result

**PASS.** `.venv/bin/python -m pytest -q` -> `1426 passed` (0 failed). No static/lint tool is configured anywhere in this repository (no `ruff`/`mypy`/`flake8` config found by inspection) - per WP-054 section 42's own "do not introduce a new formatting/linting system" instruction, none was run or added.

## 26. Recommendation for WP-055

Two candidate directions, neither committed to here:
1. Investigate `Globus Pallidus`'s own still-unresolved classification-ambiguity family directly (the same open thread WP-045/046/048 already left explicitly unresolved) - now cleanly isolated from the identity-first question, since WP-054 confirms it is untouched by this change.
2. If a future WP wants to consider expanding identity-first beyond these two targets, it should first run a WP-052-style retrospective classification for the candidate target/category, then a WP-053-style controlled live experiment, before any permanent code change - this WP's own resolver table is deliberately structured (a simple dict literal) to make such an addition mechanically trivial once evidence justifies it.

---

# Terminal Summary

```text
WP-054 complete.

Objective:
Implement the smallest permanent, explicit, testable generation-strategy
preference causing identity-first generation only for the two approved
target/category pairs.

Permanent strategy:
GenerationStrategyPreference (DEFAULT, IDENTITY_FIRST), resolved by
resolve_strategy_preference(category, topic) and threaded into the
generation prompt via a new target_strategy_requirement variable.

Approved mappings:
גרעיני הבסיס + Caudate Nucleus -> IDENTITY_FIRST
גרעיני הבסיס + Nucleus Accumbens -> IDENTITY_FIRST

Explicit exclusions:
Globus Pallidus
all other targets
all other categories

Implementation:
models/strategy.py (enum) + generation/strategy.py (pure resolver) +
prompts/formatting.py/context.py (rendering) + one new prompt placeholder.
QuestionGenerator resolves the preference once per call, right after
category resolution, and threads it through GenerationPromptContext.

Prompt integration:
New "Generation strategy preference" section/placeholder in
prompts/generation/question.txt, following the existing honest-sentinel
formatting convention; default template on disk is immutable, only the
rendered variable differs per call.

Language compliance:
PASS - verified live; English target names used verbatim in both
approved-target correct answers, per WP-041's unmodified mechanism.

Scope tests:
6/6 PASS (see section 22 table).

Integration tests:
PASS (mock LLM, no real API call; identity-first content reaches the
prompt only for the two approved targets).

End-to-end Caudate:
PASS - accepted on attempt 1, clean identity-shaped question, all
validators pass.

End-to-end Nucleus Accumbens:
PASS - accepted on attempt 2 (attempt 1 reverted to bare classification
and was correctly rejected), clean identity-shaped question on
acceptance, all validators pass.

Globus Pallidus safety:
PASS - resolved DEFAULT every attempt; no identity-first contamination;
rejections match the pre-existing, already-disclosed classification-
ambiguity family, not a new regression.

Validators:
UNCHANGED - no file under src/exam_generator/validation/ modified.

Retry budget:
UNCHANGED - 3 attempts; production/producer.py not modified.

Schemas:
UNCHANGED - no file under schemas/ modified; CandidateQuestion and
QuestionTarget both verified to carry no new field.

Coverage:
UNCHANGED - no file under planning/ modified.

Full regression:
1426 passed, 0 failed (1396 pre-existing + 30 new).

Files changed:
See section 20 above.

Completion report:
implementation/WP-054_COMPLETION_REPORT.md

Recommended WP-055:
Either (a) investigate Globus Pallidus's own still-unresolved
classification-ambiguity family, now cleanly isolated from this change,
or (b) if further identity-first expansion is desired, run a fresh
WP-052/WP-053-style evidence+experiment pair for any new candidate
target before any code change.

Waiting for architect review.
```
