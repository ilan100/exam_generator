# WP-025 Completion Report — Evidence-Grounded Question Target Planning and Within-Category Diversity

## 1. Implementation Summary

WP-024 achieved the first fully `COMPLETE` real acceptance run (40/40 accepted). Human review of that exam found a genuine exam-construction quality problem no validator could catch: multiple questions requested from the same category were often near-duplicates - the same fact reworded, or question/answer inverted - even though each individually passed grounding, MCQ, category, quality, and textbook validation cleanly.

WP-025 introduces a planning stage, inserted once per category, before any question generation for that category begins:

```
category
    ↓
retrieve factual evidence
    ↓
plan up to N distinct evidence-supported question targets
    ↓
    ├── target 1 → generate → existing validators
    ├── target 2 → generate → existing validators
    └── ...
```

Diversity is achieved primarily **by construction** - the implementation deliberately does not generate arbitrary questions and rely on WP-013's three-attempt budget to reject duplicates after the fact.

## 2. Target Model

`QuestionTarget` (`src/exam_generator/models/target.py`) - a generation plan, never a generated question, a validator verdict, or an accepted exam question:

```python
class QuestionTarget(BaseModel):
    target_id: PositiveIntStrict
    category: NonBlankStr
    topic: NonBlankStr
    factual_focus: NonBlankStr
    supporting_evidence_chunk_ids: tuple[NonBlankStr, ...] = ()
```

`supporting_evidence_chunk_ids` are already-resolved genuine canonical `SourceEvidenceChunk.chunk_id` values - never a raw LLM claim.

## 3. Planner Interface

New `src/exam_generator/planning/` package (a sibling of `generation/`/`validation/`/`production/`/`orchestration/`/`output/`, not a submodule of any):

```python
class QuestionTargetPlanner:
    def __init__(self, *, category_resolver, student_summary_index, prompt_repository, llm_provider): ...

    @classmethod
    def from_default_configuration(cls) -> "QuestionTargetPlanner": ...

    @property
    def plan_history(self) -> tuple[tuple[str, tuple[QuestionTarget, ...]], ...]: ...

    def plan_targets(self, *, category: str, count: int) -> list[QuestionTarget]: ...
```

Every dependency is injected explicitly, identical to `QuestionGenerator`'s own wiring pattern - retrieval reuses the existing `retrieve_for_category()` call and the existing student-summary index unchanged. The planner is responsible for planning only: it never generates a final MCQ, validates a candidate, decides acceptance, or performs orchestration/output.

## 4. Planner LLM Response Contract

LLM-facing models (`models/target.py`), never exposed beyond `QuestionTargetPlanner`:

```python
class PlannedQuestionTargetResponse(BaseModel):
    topic: NonBlankStr
    factual_focus: NonBlankStr
    evidence_refs: list[int] = []

class QuestionTargetPlanningResponse(BaseModel):
    targets: list[PlannedQuestionTargetResponse] = []
```

`plan_targets()` makes exactly one LLM call (`LLMProfile.GENERATION`) - no retry loop of any kind lives in this layer, per the WP's explicit "no hidden retry loop" requirement.

## 5. Evidence-Provenance Mechanism

Reuses WP-022/WP-024's proven local-reference principle exactly, one layer earlier: the planner LLM cites the "[Evidence N]" label already shown in the prompt; the application never trusts a canonical chunk-id string from the model.

`_resolve_planned_targets()` (`planning/planner.py`):

- Bounds-checks every `evidence_refs` value against `1..len(source_evidence)` - zero, negative, and out-of-range all rejected identically.
- Resolves valid references to genuine canonical `SourceEvidenceChunk.chunk_id` values.
- **A single invalid reference anywhere in the response discards every target from that attempt** - never partially repaired, matching WP-022/WP-024's whole-response-discard philosophy applied uniformly rather than per-target.
- Reuses the existing `InvalidGeneratedOutputError` (no new exception subtype was judged necessary).
- Internally, `plan_targets()` catches this and treats it as "zero usable targets from this attempt" rather than raising or retrying - a stochastic per-call reliability issue must never be able to abort an otherwise-healthy exam, and no retry mechanism was added for planning (per the WP's explicit scope).

## 6. Diversity Rules (Prompt-Level)

`prompts/generation/question_target_planning.txt` (new; `PromptId.QUESTION_TARGET_PLANNING`) explicitly rules out four specific superficial-diversity patterns the WP-024 human review actually observed:

1. Rewording ("What does X transmit?" vs. "Which modalities are carried by X?")
2. Question/answer inversion ("Which tract carries Y?" vs. "What does X carry?")
3. Same structure + same property tested differently (e.g. two targets both about "hippocampus → memory")
4. Same narrow relationship approached from opposite directions ("Where is X?" vs. "What is located at Y?")

The prompt explicitly instructs the model to prefer targets differing in concept, structure, function, pathway, relationship, mechanism, or anatomically/clinically relevant distinction, and to return fewer targets rather than fabricate artificial diversity.

## 7. Limited-Content Behavior

The planner may legitimately return **fewer targets than requested - never more, never fabricated**. `plan_targets()` truncates if the model over-returns; if the model under-returns (or a response is discarded due to an invalid reference), the shortfall is represented honestly.

At the orchestration layer, `ExamOrchestrator.generate_exam()` (`orchestration/orchestrator.py`) now groups the deterministic plan by category (preserving the plan's own overall position order exactly), calls `plan_targets(category, count)` once per category, and for any planned position beyond the number of targets actually planned, records a `FailedPlannedQuestion` with `failure_type="InsufficientDistinctTargetsError"` **without ever calling the producer** for it.

No category (including `מבוא`) is special-cased anywhere - the mechanism is fully general and was verified general by direct test (`test_shortfall_in_one_category_does_not_affect_another_category`, `test_planner_zero_targets_fails_every_planned_position_for_that_category`).

A genuine system-level planning failure (provider/auth/rate-limit error, or `MissingEvidenceError` - reused unchanged from `generation.errors`, for literally zero retrievable evidence) still aborts the whole run immediately via the existing `QuestionProductionFailedError`, contextualized against that category's first planned position.

## 8. Generation-Target Integration

`QuestionGenerator.generate_candidate_question()` and `QuestionProducer.produce_question()` both gained a **required** `target: QuestionTarget` parameter (no default). `GenerationPromptContext` gained a required `target` field, enforced (via `PromptContextError`) to belong to the same category as the call itself. `prompts/generation/question.txt` gained a new "Assigned question target" section instructing the model to test specifically its assigned target, never silently switch to an easier fact, and never let a `STYLE_SIMILAR` historical reference (style only, never factual authority) override the planned factual focus.

## 9. Retry/Attempt-Budget Behavior

**Target assignment is fixed across every retry.** `_produce_unique_question()` passes the same `target` object into every one of its bounded duplicate-replacement retries; `QuestionProducer`'s own WP-013/WP-019 attempt loop never asks the planner for anything - the target is decided once, before any attempt begins. Verified directly: `test_target_remains_stable_across_duplicate_replacement_retries` asserts the identical target object is passed on every retry call.

Diversity does not routinely consume `generation.max_generation_attempts` - confirmed live: the full acceptance run's 4 failures were all normal MCQ/quality-validator rejections (the pre-existing WP-013 mechanism), with **zero generation-contract failures**, meaning target-following itself never caused a discarded attempt.

`max_generation_attempts` was not increased; no category-specific attempt budget was introduced.

## 10. Confirmation: Existing Validators Unchanged in Responsibility

`GroundingValidator`, `MCQValidator`, `CategoryValidator`, `QualityValidator`, `TextbookValidator` were not modified in any way. No "different from previous question" check was added to `QualityValidator` or anywhere else - diversity is entirely a planning/orchestration concern, never a candidate-validation concern, per the WP's explicit instruction.

No post-generation diversity validator was added at all. WP-025 section 11 required first determining whether target-identity-by-construction plus existing generation constraints are sufficient, preferring the simpler design; the live acceptance run's diversity review (16/16 DISTINCT, 0 borderline, 0 duplicate - see section 16 below) supported not adding one. This is a deliberate, documented decision, not an oversight, and is revisitable if future evidence at larger scale shows target-based planning alone is insufficient.

## 11. Files Created/Modified

**Created:**
- `src/exam_generator/planning/__init__.py`, `src/exam_generator/planning/planner.py`
- `src/exam_generator/models/target.py`
- `prompts/generation/question_target_planning.txt`
- `tests/unit/test_planning.py` (29 tests)
- `implementation/WP-025_COMPLETION_REPORT.md` (this file)

**Modified:**
- `src/exam_generator/models/__init__.py` - new exports
- `src/exam_generator/prompts/models.py` - new `PromptId.QUESTION_TARGET_PLANNING`
- `src/exam_generator/prompts/repository.py` - new prompt-file mapping
- `src/exam_generator/prompts/formatting.py` - new `format_question_target()`
- `src/exam_generator/prompts/context.py` - `GenerationPromptContext` gained required `target`; new `QuestionTargetPlanningPromptContext`
- `src/exam_generator/prompts/__init__.py` - new exports
- `src/exam_generator/generation/generator.py` - `generate_candidate_question()` gained required `target`
- `prompts/generation/question.txt` - "Assigned question target" section, STYLE_SIMILAR wording updated
- `src/exam_generator/production/producer.py` - `produce_question()` gained required `target`
- `src/exam_generator/orchestration/orchestrator.py` - per-category planning loop, `InsufficientDistinctTargetsError` shortfall handling, `target_planner` constructor dependency
- `docs/ARCHITECTURE.md`, `docs/PROJECT_STATUS.md` - new WP-025 sections
- `tests/unit/test_generation.py`, `tests/unit/test_production.py`, `tests/unit/test_orchestration.py`, `tests/unit/test_prompts.py` - required-parameter fixture updates plus new WP-025-specific tests
- `tests/integration/test_end_to_end_pipeline.py`, `tests/integration/test_structured_output_recovery.py` - `target_planner` wiring, `_queue_target_plans()` helper, new end-to-end distinct-targets test; `FakeLLMProvider` gained additive `messages_log` observability

**No changes:** `src/exam_generator/validation/*` (all five validators untouched), `src/exam_generator/retrieval/*` (unchanged), `schemas/*.schema.json` (confirmed byte-identical).

## 12. Tests Added/Changed

- **`tests/unit/test_planning.py`** (new, 29 tests): basic planning (count=1/2/4, category preservation, alias resolution, exact-count truncation, honest shortfall, empty response, missing-evidence), LLM call shape, local-reference resolution (valid/zero/negative/out-of-range/one-bad-ref-discards-all), direct `_resolve_planned_targets()` coverage, observability (`plan_history`), scope boundaries.
- **`tests/unit/test_generation.py`**: added `_target()` fixture; all `generate_candidate_question()` calls updated; new tests for target-in-prompt content, different-targets-produce-different-prompts, target-category-mismatch rejection, STYLE_SIMILAR-cannot-override-target.
- **`tests/unit/test_production.py`**: added `_target()` fixture; all `produce_question()` calls updated; signature test updated.
- **`tests/unit/test_orchestration.py`**: added `_target()`/`_planner()` fixtures; new tests for once-per-category planning, per-distinct-category planning, producer-receives-assigned-target, target-stability-across-duplicate-replacement, planner-shortfall handling (partial and all-zero), shortfall-in-one-category-does-not-affect-another, system-level planning-failure abort (provider error and missing-evidence), failure-context preservation after an earlier category completed.
- **`tests/unit/test_prompts.py`**: new "Target planning prompt policy" section - required-variable tests, diversity-wording assertions (all four superficial-diversity patterns), local-reference wording, honest-shortfall wording, context validation tests.
- **`tests/integration/test_end_to_end_pipeline.py`**: `_build_pipeline()` now constructs a real `QuestionTargetPlanner`; new `_queue_target_plans()` helper inserted before all 22 `generate_exam()` call sites; new `test_two_distinct_planned_targets_reach_two_distinct_generation_prompts` (real orchestrator, real generator, verifies actual prompt content differs between two sequential calls).
- **`tests/integration/test_structured_output_recovery.py`**: `_build_real_pipeline()` now constructs a real `QuestionTargetPlanner`; new `_queue_target_plan()` helper inserted before all 6 `generate_exam()` call sites.
- Existing WP-019/020/021/022/023/024 tests were **updated, not weakened** - every change was a mechanical fixture addition (a required `target` parameter) or an additive queue call, with zero change to any test's actual assertion about WP-019 through WP-024 behavior.

## 13. Full Regression Result

**1010 / 1010 passing** (up from the 951 baseline entering WP-025; +59 net from WP-025's own additions), zero network access, no `OPENAI_API_KEY` in the offline test shell.

`scripts/generate_schemas.py` re-run: all three schema files byte-identical to before (confirmed via `git diff --stat schemas/` showing no changes) - `QuestionTarget`/planning models are never exported into any of them.

## 14. Live Smoke-Test Result

3 categories × 2 questions, selected as the categories with the worst diversity in WP-024's exam (`מסילות עצביות`, `גזע המוח`, `המערכת הלימבית`), run via the exact same production `ExamOrchestrator.from_default_configuration()` wiring the CLI itself uses (plus one added instrumentation read of `QuestionTargetPlanner.plan_history`, never a shortcut around real components):

- **Status: COMPLETE, 6/6 accepted.**
- All 3 planned target pairs were genuinely distinct and correctly followed by generation:
  - `מסילות עצביות`: spinothalamic tract (pain/temperature) vs. medial lemniscus tract (fine touch/proprioception) - the WP's own worked example, reproduced live.
  - `גזע המוח`: structure (three parts) vs. function (breathing/sleep/cardiac).
  - `המערכת הלימבית`: constituent structures (hippocampus/amygdala/fornix) vs. evolutionary origin (Rhinencephalon).

## 15. Full 2-Per-Category Acceptance-Run Result

- **Planned count: 40**
- **Accepted count: 36**
- **Failed count: 4**
- **Status: PARTIAL**
- **Runtime: ~20.4 minutes** (1222.1 seconds) - longer than WP-024's ~13.6 minutes, consistent with the added planning LLM call per category (20 extra calls).
- **Exit code: 0**
- **Output files**: both `exam.json` (36 questions) and `exam_audit.json` written successfully.

### Every failed planned question and reason

| Position | Category | Mode | Reason |
|---|---|---|---|
| 5 | חומר לבן | STYLE_SIMILAR | `QuestionAttemptsExhaustedError` - all 3 attempts rejected (MCQ ambiguity, quality clarity) |
| 11 | היסטולוגיה | STYLE_SIMILAR | `QuestionAttemptsExhaustedError` - all 3 attempts rejected (MCQ ambiguity, quality clarity) |
| 26 | המוח הקטן | INDEPENDENT | `QuestionAttemptsExhaustedError` - all 3 attempts rejected (MCQ ambiguity, quality clarity) |
| 27 | מערכת העצבים ההיקפית | STYLE_SIMILAR | `QuestionAttemptsExhaustedError` - all 3 attempts rejected (MCQ ambiguity, quality clarity) |

**Generation-contract failures observed: 0.** **Invalid local-reference (planning or generation) failures observed: 0.** All 4 failures were the pre-existing, normal WP-013 candidate-quality mechanism - target assignment introduced no new failure mode.

### Accepted-attempt distribution

23 questions accepted on attempt 1, 7 on attempt 2, 6 on attempt 3 (55 total attempts across 36 accepted questions).

### Validator rejection distribution (among accepted questions' non-final attempts)

quality: 15, MCQ: 12, category: 1, textbook-conflict: 2 (a single attempt can trigger more than one).

### WP-020/WP-021 retry observations

Not independently captured for this specific live run (the production orchestrator path does not surface `StructuredOutputRetryEvent`/`ProvenanceRetryEvent` counts without additional instrumentation beyond what was added for target-plan capture); not fabricated, reported as unavailable.

## 16. Per-Category Target/Question Diversity Review

Every category with **both** planned questions accepted (16 of 20 categories; the other 4 - `חומר לבן`, `היסטולוגיה`, `המוח הקטן`, `מערכת העצבים ההיקפית` - had one planned question fail, leaving no pair to judge):

| Category | Target 1 | Target 2 | Assessment |
|---|---|---|---|
| התעלה השדרתית ותכולתה | Vertebra/spinal canal structure | Gray matter Rexed laminae function | DISTINCT |
| לוקליזציה פונקציונלית | M1 motor cortex location | V1 visual cortex response properties | DISTINCT |
| עצבים קרניאליים | CN I olfactory nerve | CN III oculomotor nerve | DISTINCT |
| מיפוי ודימות מוחי | CT imaging advantages | DTI imaging advantages | DISTINCT (same topic label, but different imaging modality/fact - a minor planner topic-naming imprecision worth noting, not a content duplicate) |
| המערכת הלימבית | Constituent structures | Evolutionary origin (Rhinencephalon) | DISTINCT |
| אספקת דם | Cerebellum blood supply | Spinal cord blood supply | DISTINCT |
| קרומים וסינוסים דוראליים | Venous sinus drainage function | Dura layer structure (periosteal vs. meningeal) | DISTINCT |
| גזע המוח | Structure (3 parts) | Function (breathing/sleep/cardiac) | DISTINCT |
| מסילות עצביות | Spinothalamic tract (pain/temp) | Medial lemniscus tract (touch/proprioception) | DISTINCT |
| גרעיני הבסיס | General motor role | Direct/indirect pathway mechanism | DISTINCT (closest call in this review - both broadly about movement, but one is general function and the other a specific mechanistic pathway distinction, not a reworded repeat) |
| דיאנצפלון | Functional role (emotion/learning/memory) | Developmental structures (thalamus/hypothalamus/pituitary) | DISTINCT |
| אמבריולוגיה | Gastrulation/germ layers | Neural tube flexures | DISTINCT |
| טופוגרפיה של ההמיספרות | Four lobes | Inferior-surface visual structures | DISTINCT |
| חדרי המוח | Lateral ventricle shape | Third-to-fourth ventricle connection | DISTINCT |
| תאי מערכת העצבים | Microglia (immune function) | Ependymal cells (CSF production) | DISTINCT |
| מבוא | History of anatomy study (ancient Egypt) | Evolution of the nervous system | DISTINCT |

**Totals: 16 / 16 DISTINCT (100%), 0 BORDERLINE, 0 DUPLICATE/NEAR-DUPLICATE.**

## 17. Comparison with the WP-024 Diversity Problem

WP-024's exam (`evaluation/live_outputs/wp024_acceptance_exam.json`) had 6 near-duplicate/duplicate pairs among its 20 same-category pairs (30%): positions 1-2, 3-4, 13-14, 17-18, 19-20, 21-22. Three of those exact categories (`מסילות עצביות`, `גזע המוח`, `המערכת הלימבית`) reappear in this WP-025 review above and are now DISTINCT - directly showing the mechanism working on the exact cases that motivated the WP. `קרומים וסינוסים דוראליים` (WP-024 positions 17-18) is also DISTINCT here. This is a single-run comparison (n=1 each), not a statistically powered study, but the improvement is large and lands precisely on the cases the WP set out to fix.

## 18. Cost/Reliability Observations

- **Planner LLM calls**: 20 (one per category, confirmed by `plan_history` length).
- **Candidate-generation attempts**: 55 total across 36 accepted questions (avg 1.53/accepted question) plus 12 attempts across the 4 failed questions (3 each) = 67 total generation attempts, vs. WP-024's 50 total attempts across 40 accepted questions (avg 1.25/accepted question).
- **Accepted on attempt 1/2/3**: 23/7/6 (WP-025) vs. 31/8/1 (WP-024).
- **Generation-contract failures**: 0 (WP-025) vs. 0 (WP-024) - unchanged, zero in both.
- **Result**: PARTIAL, 36/40 (WP-025) vs. COMPLETE, 40/40 (WP-024).
- **Runtime**: ~20.4 min (WP-025) vs. ~13.6 min (WP-024) - the difference is consistent with 20 additional planning calls.

The modestly higher attempt count and one PARTIAL vs. COMPLETE result are plausibly explained by target-focused questions being somewhat harder to phrase with one unambiguous best MCQ answer than an unconstrained question - this is a single-run observation, not a statistically significant finding, and is reported honestly rather than claimed as a regression or dismissed.

## 19. Human-Review Findings

- Clean exam contains accepted questions only (36/36), zero structural defects (every question has exactly 4 distinct answers and a correct-answer id in 1-4).
- Numbering is contiguous 1..36.
- All 4 failed planned questions are represented in the audit with full attempt history.
- Canonical evidence ids confirmed real supplied chunk ids throughout the audit (regex check against every `evidence_chunk_ids` entry - zero non-canonical values found).
- Zero `evidence_refs`/`[Evidence` leakage into either `exam.json` or `exam_audit.json`.
- Hebrew renders correctly throughout; zero `\u`-escaped characters in `exam.json`.
- The two `מבוא` questions (positions 35-36) are well-formed, unambiguous, and clearly distinct (ancient-Egypt brain-injury documentation vs. an evolutionary nervous-system change).
- No obvious regression in question quality was observed in the reviewed sample.

## 20. Known Limitations / Deviations

- This is a single live acceptance run (n=1); the diversity improvement (16/16 DISTINCT) is strong evidence at this sample size but not a statistically powered guarantee at scale.
- The `מיפוי ודימות מוחי` category's two targets shared an identical `topic` label ("שיטות דימות מוחי") despite testing genuinely distinct facts (CT vs. DTI) - a minor planner topic-naming imprecision, not a content-diversity defect; no code change was made for this single observation, consistent with the instruction not to tune based on one stochastic example unless it exposes an actual contract defect.
- WP-020/WP-021 retry counts were not independently captured for this specific live run (a reporting limitation, not a WP-025 defect).
- No deviations from the WP-025 specification were made.

## 21. Confirmations

- **Retrieval/TF-IDF unchanged**: no file under `src/exam_generator/retrieval/` was modified; `FactualRetrievalIndex`, category resolution, and chunking are untouched by this WP.
- **No embeddings/vector DB introduced**: no new dependency was added (`pyproject.toml` unchanged); retrieval remains the existing TF-IDF mechanism exclusively.

---

WP-025 complete. Not starting WP-026 - waiting for architect/user review.
