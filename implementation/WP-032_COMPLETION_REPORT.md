# WP-032 Completion Report — Category Generation Architecture Refactoring

## 1. Architectural Changes

WP-032 changes the project's *primary API surface*, not its generation behavior. No prompt, validator, retrieval, relationship, competitor, or acceptance-policy logic was touched (WP-032 section 13's exclusions were followed exactly).

- **V1 (WP-006 through WP-031): Generate Exam → Generate Question.** `ExamOrchestrator.generate_exam(request) -> ExamGenerationResult` was the top-level capability; one question's production (`QuestionProducer.produce_question()`) was an implementation detail nested inside the orchestrator's own loop. Duplicate-detection state and target-planning batching both lived at the exam level.
- **V2 (WP-032 onward): Generate Next Question For Category → Generate Exam.** `CategoryGenerationService.generate_next(CategoryGenerationRequest) -> CategoryGenerationResponse` (new `src/exam_generator/category_generation/` package) is now the top-level capability: given a category and every question already accepted for that category so far, produce one additional accepted question or an honest failure. `ExamOrchestrator.generate_exam()` is now exactly the loop WP-032 section 7 specifies: "for each category: for each planned question: call `CategoryGenerationService`" - no generation logic remains inside exam orchestration.
- **Why the abstraction changed**: the project's own trajectory (WP-025 target planning, WP-030 relationship extraction, WP-031 competitor discovery) has steadily moved generation-time intelligence out of prompts and into deterministic application code operating per-question, per-category. A per-exam API was already the wrong shape for that work - every one of those WPs had to reach *inside* `ExamOrchestrator`'s loop to operate at the granularity it actually needed. Making "the next question for a category" the primary API makes future per-question work (e.g. WP-031's architecture review's recommended deterministic distinguishing-facts layer) a natural extension of the public contract instead of another exam-internal special case.
- Full narrative and rationale: `docs/ARCHITECTURE.md`, new "V1 vs. V2 Generation Architecture: CategoryGenerationService (WP-032)" section (inserted immediately before "Candidate Question Validation").

## 2. New Request Contract

`CategoryGenerationRequest` (`category_generation/models.py`, immutable, `extra="forbid"`):

```python
category: NonBlankStr
generation_mode: GenerationMode
existing_questions: tuple[CandidateQuestion, ...] = ()
generation_options: CategoryGenerationOptions = CategoryGenerationOptions()  # difficulty/style, both unused today
```

- `existing_questions` is passed to the generation layer unchanged - never summarized, concept-extracted, or used for diversity scoring, per section 5. It is used for exactly one thing: WP-014's existing exact-duplicate-text check, now scoped to this request rather than an exam-wide set (see section 8 below).
- `generation_options` carries only default values today (section 2), reserved for future difficulty/style-aware generation - deliberately not wired into any pipeline component, to avoid over-engineering.
- `generation_mode` is a required, caller-supplied field, deliberately **not** inferred from `len(existing_questions)` even though section 2's illustrative example omits it. Mode alternation is a plan-level policy `ExamOrchestrator.build_exam_plan()` already owns (fixed per planned position, independent of any later question-local failure); inferring it here from accepted-count would silently drift from that policy the moment any earlier position in the same category failed. Preserving the caller's existing policy exactly (section 12: "identical retry behavior... unchanged") took priority over section 2's non-binding example shape - documented explicitly in the model's own docstring.

## 3. New Response Contract

`CategoryGenerationResponse` (`category_generation/models.py`, immutable, `extra="forbid"`):

```python
accepted: StrictBool
production: QuestionProductionResult | None = None   # WP-013's own unmodified result
duplicate_replacement_attempts: NonNegativeIntStrict = 0
duplicate_productions: tuple[QuestionProductionResult, ...] = ()
failure_type: NonBlankStr | None = None
failure_message: NonBlankStr | None = None
failure_attempts: tuple[QuestionAttempt, ...] = ()
```

with a `model_validator` enforcing exactly one of the accepted/failed shapes is populated, and two derived `@property` accessors (`question`, `attempts`) matching section 3's illustrative shape without duplicating stored data. `production`/`failure_type`/`failure_message`/`failure_attempts` reuse `QuestionProductionResult`/`QuestionAttempt` wholesale and mirror `FailedPlannedQuestion`'s existing field names exactly - no new duplicate model was introduced for either shape, per section 3's "reuse existing models... avoid duplication" instruction.

## 4. CategoryGenerationService Responsibilities

`CategoryGenerationService.generate_next()` (`category_generation/service.py`) does exactly what section 4 specifies and nothing more:

1. Receives the request; resolves `category` to its canonical form (`CategoryResolver`, reused).
2. Plans exactly one target (`QuestionTargetPlanner.plan_targets(count=1)`) - never zero, never more than one, since one call produces at most one question. No targets available → `accepted=False, failure_type="InsufficientDistinctTargetsError"`, producer never called.
3. Calls `QuestionProducer.produce_question()` with that target, `request.category`, `request.generation_mode` - WP-013's full generate-then-validate-five-ways-then-accept cycle, completely reused.
4. Runs the same bounded duplicate-replacement loop `ExamOrchestrator._produce_unique_question()` used to run (moved here verbatim, including `_normalize_question_text()`), checking each produced candidate against `request.existing_questions` rather than an exam-wide set.
5. Returns exactly one question (`accepted=True`) or an honest, question-local failure (`accepted=False`) - never raises for a question-local outcome.

A system-level failure (`SYSTEM_LEVEL_ERROR_TYPES`, also moved here from `orchestrator.py`) is never caught by the service - it propagates to the caller unchanged, since only the caller has the session-level context (position in an overall plan, questions already completed) needed to contextualize an abort.

## 5. Reused Components (section 6 - "do NOT duplicate logic")

Nothing was reimplemented. `CategoryGenerationService` is a thin reorganization of already-existing, already-tested logic:

| Component | Source | Change |
|---|---|---|
| `QuestionProducer` | WP-013 | None - injected unchanged |
| `QuestionTargetPlanner` | WP-025 | None - injected unchanged, called with `count=1` instead of `count=N` |
| Relationship extraction | WP-030 | None - untouched, runs inside `QuestionGenerator` as before |
| Competitor discovery | WP-031 | None - untouched, runs inside `QuestionGenerator` as before |
| All five validators | WP-010/011/012 | None - untouched, run inside `QuestionProducer` as before |
| `_normalize_question_text()` | WP-014 | Moved verbatim from `orchestrator.py` to `category_generation/service.py` |
| `QUESTION_LOCAL_ERROR_TYPES`/`SYSTEM_LEVEL_ERROR_TYPES` | WP-023 | Moved verbatim from `orchestrator.py` to `category_generation/service.py` |
| Duplicate-replacement retry loop | WP-014 | Moved from `ExamOrchestrator._produce_unique_question()` into `CategoryGenerationService.generate_next()`, now scoped to `request.existing_questions` |

`ExamOrchestrator` (`orchestration/orchestrator.py`) lost `_produce_unique_question()`, `_normalize_question_text()`, and both error-type tuples entirely - it now imports `SYSTEM_LEVEL_ERROR_TYPES` from `category_generation` only to know what to catch-and-wrap as `QuestionProductionFailedError`. `build_exam_plan()` (mode alternation, position numbering) is unchanged - plan construction remains exam-level.

The CLI (`cli.py`) required **zero changes** (section 8) - it already only calls `ExamOrchestrator.from_default_configuration()` and `.generate_exam(request)`; since that call now internally delegates to `CategoryGenerationService` on every iteration, the CLI transitively satisfies "invoke the new service repeatedly" without itself knowing the service exists.

## 6. Tests

- New `tests/unit/test_category_generation.py` (39 tests): `CategoryGenerationOptions`/`CategoryGenerationRequest`/`CategoryGenerationResponse` model contracts (defaults, frozen, `extra=forbid`, the accepted/failed consistency validator, derived-property behavior); `CategoryGenerationService` configuration validation; target-planning-with-`count=1` integration; target stability across duplicate-replacement retries; zero-targets → `InsufficientDistinctTargetsError`; question-local vs. system-level error classification (parametrized over `QUESTION_LOCAL_ERROR_TYPES`, plus explicit grounding/textbook cases); duplicate-replacement mechanics (exact match, normalized whitespace/case, category/mode reuse across retries, exhaustion); no semantic/LLM duplicate detector introduced.
- `tests/unit/test_orchestration.py` rewritten (28 tests, net -17 vs. WP-031's version): now mocks `CategoryGenerationService` at the orchestrator boundary instead of the planner/producer pair directly. All target-planning/duplicate-replacement-mechanics tests moved to `test_category_generation.py`, since that logic moved there. Retained/added: plan construction (unchanged), service delegation (category/mode/`existing_questions` threading - including a new explicit test that `existing_questions` accumulates within a category across calls and never leaks across categories), question-local-failure-response handling, system-level-failure catch-and-wrap-with-context, per-category independence of outcomes.
- `tests/integration/test_end_to_end_pipeline.py`/`test_structured_output_recovery.py`: `ExamOrchestrator` construction sites updated to build a `CategoryGenerationService` first, then pass it in; `_queue_target_plans()` and one manual two-target queue changed from "one combined response with N targets" to "N separate one-target responses" (target planning now happens once per question, not once per category).
- **Full regression suite: 1153 passed, 0 failed** (up from 1131 before this WP), zero network access, no `OPENAI_API_KEY` required. `scripts/generate_schemas.py` re-run: all three schema files byte-identical (`CategoryGenerationRequest`/`Response` are new `category_generation/` models, never schema-exported; `ExamRequest`/`ExamOutput`/`ExamAudit` were not touched).

## 7. Evaluation (Architectural Smoke Test, Section 10)

One category (`אספקת דם`), four sequential `CategoryGenerationService.generate_next()` calls with 0, then 1, then 2, then 3 `existing_questions` (each round's `existing_questions` being exactly what was accepted in every prior round):

| Round | Existing questions | Mode | Accepted | Attempts | Dup. replacements |
|---|---|---|---|---|---|
| 0 | 0 | STYLE_SIMILAR | Yes | 1 | 0 |
| 1 | 1 | INDEPENDENT | Yes | 1 | 0 |
| 2 | 2 | STYLE_SIMILAR | Yes | 1 | 0 |
| 3 | 3 | INDEPENDENT | Yes | 1 | 1 |

**4/4 accepted.** API behaves correctly, generation succeeds at every `existing_questions` size, and every response's output contract (`CandidateQuestion` shape, answers, correct answer, category) is valid - satisfying section 10's stated goal exactly (not a diversity evaluation, per its own scope note). Rounds 2 and 3 both converged on "which artery supplies the superior [surface] of the cerebellum → Superior Cerebellar Artery," reworded but substantively the same fact - round 3's attempt 1 was rejected as an exact-text duplicate and correctly replaced (`duplicate_replacement_attempts=1`), but the *semantic* near-duplicate itself was accepted, since exact-text duplicate detection was never designed to catch semantic overlap (WP-014's own original, explicit scope). This four-call smoke test was the first hint of the diversity effect the full acceptance run below confirmed at scale. Raw results: `evaluation/live_outputs/wp032_smoke_test_results.json`.

## 8. Acceptance Run (Section 11 - New Architecture Only)

Performed exactly once, for every canonical category × 2 questions, **exclusively** through `CategoryGenerationRequest` → `CategoryGenerationService.generate_next()` → append accepted question → repeat - never through `ExamOrchestrator`/the CLI, per section 11's explicit instruction. No reruns, no tuning after seeing results.

**Result: 36/40 accepted, 4 failed** (all `QuestionAttemptsExhaustedError`):

| Category | Round | Failure |
|---|---|---|
| גזע המוח | 0 | QuestionAttemptsExhaustedError |
| גרעיני הבסיס | 0 | QuestionAttemptsExhaustedError |
| מערכת העצבים ההיקפית | 0 | QuestionAttemptsExhaustedError |
| מערכת העצבים ההיקפית | 1 | QuestionAttemptsExhaustedError |

Accepted-on-attempt distribution: **23/5/8** (attempt 1/2/3), avg **1.58** attempts/accepted question. First-attempt acceptance rate: 23/36 (63.9%). Validator rejection counts (all rejected attempts): mcq 12, quality 11, category 4, grounding 22, textbook 1. Grounding rejection breakdown: **20 "another answer also supported," 2 "designated answer unsupported."** Zero generation-contract failures. Zero duplicate-replacement attempts among any *accepted* question this run. Raw per-attempt data: `evaluation/live_outputs/wp032_acceptance_records.json`; target-plan history: `evaluation/live_outputs/wp032_acceptance_targets.json`.

This acceptance run alone satisfies section 11's stated purpose: it demonstrates the new architecture (`CategoryGenerationService`, called directly, never through `ExamOrchestrator`) can completely replace the previous orchestration - every one of the 40 planned calls produced a structurally valid response, and every accepted question passed the same, completely unmodified five-validator acceptance policy.

### Comparison with WP-027/028/030/031

| Metric | WP-027 | WP-028 | WP-030 | WP-031 | **WP-032** |
|---|---|---|---|---|---|
| Accepted | 34/40 | 31/40 | 32/40 | 32/40 | **36/40** |
| Grounding "another also supported" | 12 | 14 | 24 | 16 | **20** |
| Avg attempts/accepted | 1.26 | 1.35 | 1.34 | 1.16 | **1.58** |
| First-attempt rate | - | - | - | 87.5% | **63.9%** |
| False-acceptance CONFIRMED | 0 | 0 | 0 | 0 | **0** |
| False-acceptance POSSIBLE | 1 | 2 | 2 | 1 | **2** |
| Diversity: DISTINCT pairs | 14/14 | - | 13/13 | 12/12 | **7/17** |

## 9. Architectural Evaluation - Why Did Efficiency and Diversity Regress?

WP-032 introduced **no** generation-quality change of any kind (section 13's exclusions were followed exactly - no prompt, validator, retrieval, relationship, or competitor logic was touched). Yet three metrics moved in the wrong direction relative to WP-031: grounding "another also supported" rose (16 → 20), average attempts worsened (1.16 → 1.58), and diversity collapsed (12/12 → 7/17 DISTINCT). At the same time, the raw accepted count *improved* (32 → 36).

**Leading, honestly-labeled hypothesis (not proven from a single run):** target-planning granularity is the one thing that structurally *had* to change to satisfy WP-032's own required design. Under V1, `plan_targets(count=N)` planned an entire category's targets together in one LLM call, letting the model see its own other targets and deliberately choose N mutually distinct topics - this co-awareness is precisely the mechanism WP-025 introduced to solve WP-024's original duplicate-question problem. Under V2, each `generate_next()` call is independent and stateless with respect to target planning; it has no visibility into targets already planned or used for the same category by an earlier call. This is not a design choice this WP was free to avoid while still satisfying section 7 ("no generation logic remains inside exam orchestration") - a service that produces one question per call cannot ask its target planner for `count=N` without either violating that boundary (reaching back into exam-level state) or inventing new cross-call state the WP explicitly excludes (section 5: "do NOT yet compute diversity").

The stark diversity numbers (7 DISTINCT / 3 BORDERLINE / 7 DUPLICATE among 17 reviewed pairs) directly confirm the loss of co-awareness: concrete duplicate pairs (BA4/precentral gyrus tested in both directions, olfactory-nerve-development reworded twice, superior-cerebellar-artery reworded twice, spinothalamic-tract reworded twice, cerebellar-coordination reworded twice, gastrulation reworded twice, microglia-phagocytosis overlapping) are exactly the "same fact reworded, or the same relationship approached from the opposite direction" shape WP-024's original diversity problem had, and WP-025 fixed by co-planning targets. The higher accepted count is plausibly the *same* cause manifesting differently: without co-planned distinct targets, independent per-call planning may gravitate repeatedly toward the most clearly evidence-supported, easiest-to-ground facts (exactly the ones observed duplicating) - easier to validate, but at the cost of testing overlapping content twice, and (for the other metrics) perhaps *harder* to validate on any call where planning happens to land on a genuinely more contested fact without a co-aware sibling to differentiate against.

**This is reported as a hypothesis, not a proven causal claim** - a single acceptance run cannot isolate target-planning granularity from ordinary run-to-run stochasticity, exactly the same caveat WP-030/WP-031 applied to their own single-run findings. Per section 13, fixing this is explicitly out of scope for WP-032 ("do NOT improve diversity... those belong to later work packages"); reporting it with full honesty is not.

## 10. False-Acceptance Human Review

All 36 accepted questions were reviewed for a second, equally-correct answer:

- **CLEAR_SINGLE_ANSWER: 34**
- **POSSIBLE_SECOND_CORRECT_ANSWER: 2** — `מיפוי ודימות מוחי` round 0 ("the main difference between ultrasound and CT" - the designated answer, "ultrasound is mainly used for blood-flow imaging," is plausible, but "CT provides a clearer image of brain structures" is also a defensible answer to "the main difference"); `דיאנצפלון` round 0 ("which structure is central to emotional/memory processes in the diencephalon" - thalamus was designated, but hypothalamus is also strongly associated with emotional processing and is an equally plausible answer).
- **CONFIRMED_SECOND_CORRECT_ANSWER: 0**
- **INSUFFICIENT_EVIDENCE_TO_JUDGE: 0**

Correctness held at the project's established bar (0 CONFIRMED, same as WP-027/028/030/031) even amid the diversity regression - a genuinely separate axis: false-acceptance measures whether one accepted question has a second correct answer *within itself*; diversity measures whether two *different* accepted questions overlap in content. One incidental, non-blocking observation: `חומר לבן` round 1's correct answer text contains a minor apparent typo ("סיבי שלכה" instead of "סיבי השלכה" / projection fibers) - content is still unambiguous and correctly graded, not a false-acceptance concern, noted for completeness only.

## 11. Per-Category Diversity Review

Of the 20 categories, 17 had both planned questions accepted (`גזע המוח`, `גרעיני הבסיס` each had one accepted; `מערכת העצבים ההיקפית` had zero):

| Category | Verdict | Note |
|---|---|---|
| התעלה השדרתית ותכולתה | DISTINCT | Segment identification vs. gray-matter-layer/motor-neuron fact |
| לוקליזציה פונקציונלית | **DUPLICATE** | BA4 ↔ precentral gyrus, same fact tested in both directions |
| חומר לבן | DISTINCT | Association fibers vs. projection fibers |
| עצבים קרניאליים | **DUPLICATE** | Olfactory-nerve/telencephalon-origin, reworded |
| מיפוי ודימות מוחי | BORDERLINE | Both about CT, different specific facts |
| היסטולוגיה | DISTINCT | Layer 5/corticospinal vs. Layer 1/molecular |
| המערכת הלימבית | DISTINCT | Limbic-system composition vs. hippocampus function |
| אספקת דם | **DUPLICATE** | Superior cerebellar artery, reworded |
| קרומים וסינוסים דוראליים | BORDERLINE | Sinus formation vs. sinus definition |
| מסילות עצביות | **DUPLICATE** | Spinothalamic tract, reworded |
| המוח הקטן | **DUPLICATE** | Cerebellar motor coordination, reworded |
| דיאנצפלון | BORDERLINE | Same correct answer (thalamus) via two different facts |
| אמבריולוגיה | **DUPLICATE** | Gastrulation, reworded |
| טופוגרפיה של ההמיספרות | DISTINCT | Postcentral gyrus/somatosensory vs. occipital lobe/vision |
| חדרי המוח | DISTINCT | Lateral ventricle shape vs. fourth ventricle formation |
| תאי מערכת העצבים | **DUPLICATE** | Microglia phagocytosis, overlapping |
| מבוא | DISTINCT | Different historical figures/facts |

**Totals: 7/17 DISTINCT, 3/17 BORDERLINE, 7/17 DUPLICATE.** A sharp reversal from WP-031's 12/12 DISTINCT, WP-030's 13/13, and WP-027's 14/14 - see Section 9 for the leading hypothesis.

## 12. Backward Compatibility

- **CLI**: zero changes required or made (section 8) - `_run_generate()` still calls `ExamOrchestrator.from_default_configuration()` and `.generate_exam(request)` exactly as before; verified by the unmodified `tests/unit/test_cli.py` suite passing unchanged.
- **`ExamOrchestrator.generate_exam()` public contract**: unchanged - same `ExamRequest -> ExamGenerationResult`, same plan construction, same renumbering, same `QuestionProductionFailedError`/`FailedPlannedQuestion` shapes and semantics for callers.
- **Retry/validation/acceptance behavior**: unchanged and directly verified - `QuestionProducer`/all five validators are byte-for-byte the same code, invoked identically; the rewritten `test_orchestration.py` and new `test_category_generation.py` both assert the exact same question-local/system-level classification, duplicate-replacement bounds, and target-stability-across-retries guarantees the pre-WP-032 test suite asserted, just verified at the (moved) boundary where that logic now actually lives.
- **One deliberate, disclosed narrowing**: duplicate-detection scope moved from "every question already accepted anywhere in the exam" to "every question supplied in this request's own `existing_questions`" - `ExamOrchestrator` still threads a category's own accepted-so-far questions into each subsequent request (never across categories, which was never a documented cross-category guarantee under V1 either), so exam-level behavior is unaffected for the only caller that exists today; a different future caller of `CategoryGenerationService` only sees whatever it itself supplies.
- **Schema files** (`schemas/exam_request.schema.json`/`exam_output.schema.json`/`exam_audit.schema.json`): byte-identical - `ExamRequest`/`ExamOutput`/`ExamAudit` were not touched.

## 13. Files Created/Modified

**Created:**
- `src/exam_generator/category_generation/__init__.py`
- `src/exam_generator/category_generation/errors.py`
- `src/exam_generator/category_generation/models.py`
- `src/exam_generator/category_generation/service.py`
- `tests/unit/test_category_generation.py`

**Modified:**
- `src/exam_generator/orchestration/orchestrator.py` (rewritten - thin delegation loop)
- `src/exam_generator/orchestration/errors.py` (`InvalidOrchestrationConfigurationError` removed - replaced by `category_generation.InvalidCategoryGenerationConfigurationError`)
- `src/exam_generator/orchestration/__init__.py` (export list updated)
- `tests/unit/test_orchestration.py` (rewritten)
- `tests/integration/test_end_to_end_pipeline.py` (construction sites + target-plan queueing updated)
- `tests/integration/test_structured_output_recovery.py` (construction sites updated)
- `docs/ARCHITECTURE.md` (new "V1 vs. V2 Generation Architecture" section)
- `docs/PROJECT_STATUS.md` (Tests count, new Live Evaluation Baseline section, Next WP Context updated)
- `evaluation/live_outputs/README.md` (new rows)

## 14. Confirmations

- No prompt file was modified.
- No validator was modified.
- No retrieval/chunking/TF-IDF logic was modified.
- No relationship/competitor logic was modified.
- No diversity-improvement logic was added (the measured regression in Section 9 is reported, not fixed, per section 13).
- `CategoryGenerationRequest`/`CategoryGenerationResponse` reuse `CandidateQuestion`/`GenerationMode`/`QuestionAttempt`/`QuestionProductionResult` wholesale - no duplicate model was introduced for any of them.
- Full regression suite passes: **1153/1153**.
- Acceptance run performed exactly once, exclusively through the new architecture, no reruns, no tuning after seeing results.

---

WP-032 complete.

Tests:
1153 passed, 0 failed

Acceptance run:
36/40 accepted, 4 failed (all QuestionAttemptsExhaustedError) - via CategoryGenerationService only

Completion report:
implementation/WP-032_COMPLETION_REPORT.md

Waiting for architect review.
