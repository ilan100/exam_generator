# WP-033 Completion Report — Category Question Set API

## 1. Objective and Scope

WP-032 established the project's new primary capability: "Generate Next Question For Category." WP-033 replaces its request/response contract with a *permanent* one - a "Category Question Set" (the category, every question already belonging to it, and generation options) - using exactly one question representation (the production schema) throughout, instead of the internal, pre-acceptance shape WP-032's own contract used. This is an architectural, contract-only work package: no prompt, validator, retrieval, relationship, competitor, planner, or diversity-improvement change of any kind was made (section 11's exclusions followed exactly).

## 2. New Request Contract

`CategoryQuestionSetRequest` (`category_generation/models.py`, immutable, `extra="forbid"`):

```python
category: NonBlankStr
generation_mode: GenerationMode
existing_questions: tuple[ExamQuestion, ...] = ()
generation_options: CategoryGenerationOptions = CategoryGenerationOptions()
```

- `existing_questions` may legitimately hold 0, 1, 2, 3, or any other count (section 2) - no assumption about count is made anywhere in the implementation, verified by parametrized tests over `[0, 1, 2, 3]`.
- Every existing question is an `ExamQuestion` - WP-002's already-established, already-schema-exported production question contract, reused directly rather than duplicated (section 3). Passing a `CandidateQuestion` (the internal shape) is rejected by validation - confirmed by test.
- `generation_options` reuses `CategoryGenerationOptions` unchanged (`difficulty`/`style`, still unused by every pipeline component today).
- `generation_mode` remains a required, caller-supplied field, for the same reason documented on `CategoryGenerationRequest` (WP-032): mode alternation is a plan-level policy `ExamOrchestrator.build_exam_plan()` owns, fixed per planned position regardless of any later question-local failure; inferring it from `existing_questions` would silently drift from that policy. This priority (section 12/WP-032's precedent: "identical retry behavior... unchanged" over section 2's illustrative, non-binding example) is documented explicitly in the model's own docstring.

## 3. New Response Contract

`CategoryQuestionSetResponse` (`category_generation/models.py`, immutable, `extra="forbid"`):

```python
accepted: StrictBool
question: ExamQuestion | None = None          # the production-schema question, number=None
production: QuestionProductionResult | None = None   # WP-013's full audit trail, reused unchanged
duplicate_replacement_attempts: NonNegativeIntStrict = 0
duplicate_productions: tuple[QuestionProductionResult, ...] = ()
failure_type: NonBlankStr | None = None
failure_message: NonBlankStr | None = None
failure_attempts: tuple[QuestionAttempt, ...] = ()
```

with a `model_validator` enforcing exactly one of the accepted (`question`+`production` both set) / failed (`failure_type`+`failure_message` set, `question`/`production` both unset) shapes, and a derived `attempts: int` `@property`.

- **The generated question uses exactly the same schema as every existing question** (section 4): `question: ExamQuestion`, confirmed by test (`isinstance(response.question, ExamQuestion)`) and by the field-content mapping (question/answers/correct_answer/category all match the accepted candidate).
- **`question.number` is always `None`** - generation is responsible only for the question content (section 4); the orchestration layer assigns `number` when it is not already available. Confirmed by test on every accepted response.
- **`production` is retained alongside `question`**, not removed - `ExamOrchestrator` still needs the underlying `CandidateQuestion`/full attempt history to build `QuestionProductionRecord`/`FailedPlannedQuestion` (WP-014/WP-023, both untouched); `question` and `production.candidate` always describe the same accepted candidate, never two different representations of two different questions.

## 4. Reused Models (Section 3 - "Do Not Create a Duplicate Model")

`ExamQuestion` (`models/question.py`, WP-002) is reused literally - not a lightweight/parallel type. The only change to it: `number: PositiveIntStrict | None = None` (previously required). This is the smallest change that allows literal reuse while satisfying section 4's "generation assigns no runtime identifier." `candidate_to_exam_question(candidate, number=None)` gained the same default. Every other `ExamQuestion` field (`question`/`answer1..4`/`correct_answer`/`category`) is unchanged, and every field is preserved on every existing question passed through the request (section 3: "every field must be preserved, even if currently unused").

`ExamOutput`'s own contiguous-numbering validator (`models/exam.py`) was **not** relaxed - a question actually inserted into a real exam must still carry a real, unique, contiguous number; this is enforced exactly as before (a `None` number inside `ExamOutput.questions` still fails loudly). The optionality only ever applies to a question in transit through the `CategoryQuestionSetService` response, before `ExamOrchestrator` assigns its real number.

## 5. Service Responsibility

`CategoryQuestionSetService` (`category_generation/service.py`): "receive a category question set, return one additional question - nothing more" (section 5). Identical underlying behavior to `CategoryGenerationService` - same injected `QuestionTargetPlanner`/`QuestionProducer`, same target-planning-with-`count=1`, same bounded duplicate-replacement loop, same question-local/system-level error classification. Differs only in its request/response contract.

**No duplicated decision logic**: `_run_generation_cycle()` (new, `category_generation/service.py`) contains the actual target-planning/production/duplicate-replacement/error-classification logic exactly once. Both `CategoryGenerationService.generate_next()` (WP-032, refactored to call it) and `CategoryQuestionSetService.generate_next()` (WP-033, new) call this one shared function and build their own response shape from its result (`_GenerationCycleOutcome`, a small internal dataclass). This was a deliberate design choice to satisfy "WP-033 changes the contract only" (section 6's closing line) as literally as possible - the two services are guaranteed to behave identically by construction, not merely by convention.

## 6. Internal Pipeline (Section 6)

`existing_questions` is passed through unchanged - used for exactly one thing: the existing WP-014 exact-duplicate-text check (`_normalize_question_text()` applied to `.question`). No summarization, concept extraction, diversity computation, coverage computation, or relationship computation was added - confirmed by code inspection and by a regression test asserting no `generate_structured`/embedding reference exists anywhere in `category_generation/service.py`.

## 7. Backward Compatibility (Section 7)

- **`CategoryGenerationRequest`/`CategoryGenerationResponse`/`CategoryGenerationService` remain fully present and functional**, unchanged in observable behavior - directly tested (not merely assumed) in `tests/unit/test_category_question_set.py`: constructing a `CategoryGenerationService` and exercising both its accepted-candidate path and its question-local-failure-classification path after the WP-033 refactor, confirming identical results to before.
- **`ExamOrchestrator` now builds `CategoryQuestionSetRequest` and calls `CategoryQuestionSetService`** - the CLI required zero changes (it already only calls `ExamOrchestrator.from_default_configuration()`/`.generate_exam(request)`), transitively satisfying section 7's "the CLI should transparently build the new request model."
- **Existing behavior (from the CLI/orchestrator's perspective) is unchanged**: same plan construction, same renumbering, same `QuestionProductionFailedError`/`FailedPlannedQuestion` shapes and semantics, same acceptance policy, same retry bounds - verified by the full regression suite (all pre-existing exam-level tests pass, now driving `ExamOrchestrator` through a mocked `CategoryQuestionSetService`).

## 8. Tests

- New `tests/unit/test_category_question_set.py` (26 tests): request model (existing-questions counts 0/1/2/3, frozen, `extra=forbid`, defaults); existing/generated question contract (an `ExamQuestion` is required - a `CandidateQuestion` is rejected; a supplied existing question may carry a real number or `None`; the generated question `isinstance(..., ExamQuestion)` with `number is None`); response model consistency (accepted requires both `question`+`production`, failed requires neither); service configuration validation; target-planning-with-`count=1`; zero-targets failure; attempt-exhaustion and question-local-error-type classification (parametrized over `QUESTION_LOCAL_ERROR_TYPES`); system-level-failure propagation; duplicate-replacement mechanics (exact match, exhaustion); and explicit backward-compatibility tests exercising the still-unchanged `CategoryGenerationService`.
- `tests/unit/test_orchestration.py` updated: `_service`/`_accepted_response`/`_make_orchestrator` helpers now build `CategoryQuestionSetResponse`/mock `CategoryQuestionSetService`; the existing-questions-accumulate-within-category test updated to assert `ExamQuestion` objects (via `candidate_to_exam_question`) rather than `CandidateQuestion`. All 28 tests still pass unchanged in intent.
- `tests/integration/test_end_to_end_pipeline.py`/`test_structured_output_recovery.py`: `ExamOrchestrator` construction sites updated to build a `CategoryQuestionSetService` first, then pass it as `category_question_set_service=`.
- **Full regression suite: 1179 passed, 0 failed** (up from 1153 before this WP), zero network access, no `OPENAI_API_KEY` required.
- `scripts/generate_schemas.py` re-run: `schemas/exam_output.schema.json` **changed** (expected, disclosed) - `ExamQuestion.number` is no longer in `required`, now `"anyOf": [{"gt": 0, "type": "integer"}, {"type": "null"}]` with `"default": null`. `schemas/exam_request.schema.json`/`exam_audit.schema.json` are byte-identical (unaffected, as expected - neither `ExamRequest` nor `ExamAudit` was touched).

## 9. Evaluation (Architectural Smoke Test, Section 9)

One category (`אספקת דם`), four sequential `CategoryQuestionSetService.generate_next()` calls with 0, then 1, then 2, then 3 `existing_questions` (each round's `existing_questions` being exactly what was accepted in every prior round):

| Scenario | Existing questions | Mode | Accepted | Attempts | `question.number is None` |
|---|---|---|---|---|---|
| A | 0 | STYLE_SIMILAR | Yes | 1 | Yes |
| B | 1 | INDEPENDENT | Yes | 1 | Yes |
| C | 2 | STYLE_SIMILAR | Yes | 1 | Yes |
| D | 3 | INDEPENDENT | Yes | 1 | Yes |

**4/4 accepted.** API behaves correctly, generation succeeds at every `existing_questions` size, and every response's `question` field is a valid `ExamQuestion` (the production schema) with `number=None` in every case - satisfying section 9's stated goal exactly (not a diversity evaluation, per its own scope note). All four generated questions tested the same underlying fact ("which artery supplies the superior surface of the cerebellum," reworded four times) - the identical target-planning-granularity convergence WP-032's acceptance run already found and disclosed. This is **not a new finding**: WP-033 does not touch target planning, relationship extraction, competitor discovery, or any diversity-related logic at all (section 11 explicitly excludes "analyze existing questions"/"compute coverage"/"improve diversity"), so an unchanged convergence pattern is exactly what should be expected, not evaluated further here. Raw results: `evaluation/live_outputs/wp033_evaluation_results.json`.

## 10. Acceptance Run

**No full-scale (e.g. 20-category × 2-question) acceptance run was performed for WP-033.** Unlike WP-032, which had an explicit "Section 11: Acceptance Run" requiring one, WP-033's own spec has no equivalent section - only "Section 9: Evaluation" (the four-scenario architectural smoke test above, explicitly framed as "only an architectural smoke test") and "Section 10: Acceptance Criteria" (a bullet list of success conditions - identical generation quality/validation/retry behavior/output schema - not a mandate to run a live 40-question test). Running one anyway would have been unrequested scope and API cost for a WP whose own text repeatedly emphasizes it changes the contract only. The terminal "Acceptance run" summary below reports the four-scenario evaluation's result, which is the only live-test evidence WP-033 itself calls for.

Acceptance criteria (section 10) are satisfied:
- **Identical generation quality**: same `QuestionGenerator`/prompts/relationship/competitor logic, completely untouched.
- **Identical validation**: same five validators, completely untouched.
- **Identical retry behavior**: same `QuestionProducer`/`QuestionTargetPlanner`, same bounded attempt/duplicate-replacement loops, now literally shared via `_run_generation_cycle()` between both the WP-032 and WP-033 contracts.
- **Identical output schema**: `ExamQuestion` reused directly; `ExamOutput`'s own contiguous-numbering guarantee for real exams is unchanged.

## 11. Confirmations

- No prompt file was modified.
- No validator was modified.
- No retrieval/chunking/TF-IDF logic was modified.
- No relationship/competitor logic was modified.
- No target-planning/coverage/diversity logic was modified or added.
- `CategoryQuestionSetRequest`/`CategoryQuestionSetResponse` reuse `ExamQuestion`/`QuestionAttempt`/`QuestionProductionResult` wholesale - no duplicate model was introduced for any of them.
- `CategoryGenerationService`/`CategoryGenerationRequest`/`CategoryGenerationResponse` (WP-032) remain unmodified in observable behavior and fully functional, directly tested.
- Full regression suite passes: **1179/1179**.

## 12. Files Created/Modified

**Created:**
- `tests/unit/test_category_question_set.py`

**Modified:**
- `src/exam_generator/models/question.py` (`ExamQuestion.number` optional; `candidate_to_exam_question()` default)
- `src/exam_generator/category_generation/models.py` (new `CategoryQuestionSetRequest`/`CategoryQuestionSetResponse`)
- `src/exam_generator/category_generation/service.py` (extracted `_run_generation_cycle()`/`_GenerationCycleOutcome`; refactored `CategoryGenerationService`; new `CategoryQuestionSetService`)
- `src/exam_generator/category_generation/__init__.py` (export list updated)
- `src/exam_generator/orchestration/orchestrator.py` (constructs `CategoryQuestionSetRequest`, calls `CategoryQuestionSetService`)
- `tests/unit/test_orchestration.py` (mocks `CategoryQuestionSetService`)
- `tests/integration/test_end_to_end_pipeline.py`/`test_structured_output_recovery.py` (construction sites updated)
- `schemas/exam_output.schema.json` (regenerated - `number` no longer required)
- `docs/ARCHITECTURE.md` (new "Category Question Set Contract" section)
- `docs/PROJECT_STATUS.md` (Tests count, new Live Evaluation Baseline section, Next WP Context updated)
- `evaluation/live_outputs/README.md` (new row)

---

WP-033 complete.

Tests:
1179 passed, 0 failed

Acceptance run:
4/4 scenarios accepted (A/B/C/D - 0/1/2/3 existing questions) via CategoryQuestionSetService; no full-scale acceptance run required by this WP's own spec (see section 10)

Completion report:
implementation/WP-033_COMPLETION_REPORT.md

Waiting for architect review.
