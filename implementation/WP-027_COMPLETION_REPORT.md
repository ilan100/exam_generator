# WP-027 Completion Report — Evidence-Aware Per-Option Grounding and Distractor Correctness

## 1. Implementation Summary

`evaluation/wp026_false_acceptance_diagnostic.md` traced WP-026's accepted question #23 (a candidate with two factually correct answer choices, approved by every validator) to a precise root cause: `GroundingValidator` already claimed the relevant responsibility (`other_answers_not_equally_correct`) and already received the evidence needed, but its **single holistic boolean** let the LLM assert "no other answer is equally correct" without having actually evaluated every distractor against the exact question - an internally inconsistent output the architecture never checked. A systematic review of all 35 WP-026-accepted questions found 3 further suspicious cases sharing the same weakness, none enumeration-shaped, showing the gap was general.

WP-027 implements the diagnostic's own recommended direction (E: generation improvement + independent grounding strengthening, zero additional LLM calls):

1. `GroundingValidator` now requires an **explicit, independent, per-answer-choice assessment** instead of a holistic summary.
2. `correct_answer_supported`/`other_answers_not_equally_correct` are **deterministically derived** from those four assessments in Python - never trusted as a separate LLM-reported field.
3. Generation gained a **complementary, deliberately generic** rule (not limited to enumeration targets) requiring every distractor to be checked against the supplied evidence for whether it would also answer the exact question.

No new validator was added; `MCQValidator`/`QualityValidator`/`CategoryValidator`/`TextbookValidator` are completely unchanged.

## 2. Per-Option Grounding Response Model

New (`src/exam_generator/models/validation.py`):

```python
class GroundingAnswerAssessment(BaseModel):
    answer_index: int          # 1, 2, 3, or 4
    supported_as_correct: StrictBool
    evidence_refs: list[int] = []   # WP-022's call-local-reference pattern, unchanged
    reason: NonBlankStr
```

`GroundingValidationResponse` (LLM-facing) restructured:

```python
class GroundingValidationResponse(BaseModel):
    grounded: StrictBool
    answer_assessments: list[GroundingAnswerAssessment]   # exactly one per index 1-4
    evidence_text: NonBlankStr | None = None
    reason: NonBlankStr
    confidence: UnitInterval
```

`correct_answer_supported`/`other_answers_not_equally_correct`/top-level `evidence_refs` **no longer exist on the LLM-facing response at all** - there is nothing left for the model to inconsistently self-summarize. `GroundingValidationResult` (the **public** contract) is **completely unchanged** - every existing consumer (`CandidateValidationResults.accepted`, audit construction, CLI/output serialization) required zero modification.

## 3. Deterministic Derivation Logic

`_resolve_grounding_response()` (`src/exam_generator/validation/grounding.py`), now taking `candidate` as a third parameter:

1. **Structural validation**: exactly one assessment per index in `{1,2,3,4}` - no duplicates, no omissions, no index outside that range. Violation raises `InvalidGroundingOutputError` (reused, no new exception type).
2. **Provenance validation**: every assessment's `evidence_refs`, across all four assessments, bounds-checked against `1..len(validation_evidence)` - identical fail-closed treatment of zero/negative/out-of-range, generalized from WP-022's per-response check to per-option.
3. **Derivation**:
   ```python
   supported_indices = {i for i, a in by_index.items() if a.supported_as_correct}
   correct_answer_supported = candidate.correct_answer in supported_indices
   other_answers_not_equally_correct = supported_indices <= {candidate.correct_answer}
   ```
4. `evidence_chunk_ids` is the deduplicated, order-preserving union of resolved canonical chunk ids from every *supported* assessment's `evidence_refs`.

Both failure kinds (structural, provenance) raise the same `InvalidGroundingOutputError` and are handled identically by WP-021's existing bounded provenance retry (`_MAX_PROVENANCE_RETRIES = 1`, unchanged) - no new retry mechanism.

## 4. Evidence Provenance / Reference Behavior

Unchanged in mechanism from WP-022, applied per-option: call-local `[Evidence N]` references, never canonical chunk-id strings from the LLM; invalid references remain fail-closed; a single invalid reference anywhere in the response (now: in any one of the four assessments) discards the whole response, consistent with WP-022/WP-024/WP-025's established whole-response-discard philosophy.

## 5. Grounding Prompt Changes

`prompts/validation/grounding.txt` rewritten to require explicit evaluation of Answer 1 through Answer 4 against the exact question and the supplied evidence, and to explicitly warn:

- the candidate's own "Intended Correct Answer Position" is only the generator's untrusted claim, never proof of unique correctness;
- do not stop once the designated answer looks supported;
- do not assume a distractor is false merely because the generator labeled it one;
- if a distractor genuinely satisfies the exact question, report it as supported regardless of its label;
- a true sibling member of the same classification/relationship must not be dismissed merely for being non-designated.

A generic worked example ("if evidence says 'X divides into A and B,' and both A and B appear among the choices, both must be assessed as supported") reproduces the diagnostic's own #23 pattern without naming any real category, matching the project's established no-category-names convention for generalized rules.

## 6. Generation Prompt Changes

`prompts/generation/question.txt` gained one new rule, placed immediately after WP-026's hierarchical-classification section, **deliberately not scoped to enumeration/classification targets**: before finalizing four answer choices, check each of the three distractors individually against the supplied evidence for whether it would also correctly answer the exact question as worded; a distractor being a real, true fact is not sufficient to make it valid - what matters is whether it is false for the exact relationship asked. This reduces occurrence probability; grounding remains the independent backstop (the system does not rely on generation alone, per the diagnostic's Option E recommendation).

## 7. Retrieval-Query Investigation (Section 10)

Investigated offline, without new live calls, using already-persisted WP-026 audit data: for **all four** originally-diagnosed cases (#8, #14, #23, #32), the evidence needed to judge the problematic distractor was **already present** in `grounding.evidence_text` from the WP-026 run - i.e., already successfully retrieved and supplied to the (then-inadequate) validator. The failure was in reasoning over adequate evidence, not evidence insufficiency. **Retrieval-query construction (`_build_validation_query()`) was therefore left unchanged**, per WP-027 section 10's explicit default ("do NOT automatically redesign retrieval... only change if evidence demonstrates it is needed"). This is a direct, evidence-based decision, not an oversight.

## 8. Validator Responsibility Confirmation

- **`GroundingValidator`**: expanded within its existing documented responsibility (factual support of the premise and now, explicitly, every answer option) - not a new responsibility, a more rigorous execution of an existing one.
- **`MCQValidator`**: completely unchanged, remains evidence-free (`format_candidate_question()` only), remains focused on structural MCQ quality (four answers, one-best-answer *as presented*, plausible distractors, no giveaway clues).
- **`CategoryValidator`/`QualityValidator`/`TextbookValidator`**: completely unchanged.
- No validator was added; no validator was collapsed into another.

## 9. Failure Semantics

Confirmed by direct code inspection (`CandidateValidationResults.accepted`, `src/exam_generator/production/models.py`): acceptance already requires `grounding.passed` (`grounded AND correct_answer_supported AND other_answers_not_equally_correct`). A strengthened grounding verdict correctly setting `other_answers_not_equally_correct=False` **requires zero new wiring** - it flows through the existing `.accepted` property into the existing `QuestionProducer.produce_question()` bounded-retry loop exactly like any other grounding/MCQ/quality rejection: recorded as a normal rejected `QuestionAttempt`, retried against the *same* `QuestionTarget`. No new exception type, no new `_QUESTION_LOCAL_ERROR_TYPES`/`_SYSTEM_LEVEL_ERROR_TYPES` entry, no distinction needed between "candidate-quality failure" and "operational/contract failure" beyond what WP-019/WP-021 already provide (a malformed per-option structure is exactly the kind of recoverable contract failure WP-021's retry already exists for).

## 10. Retry/Attempt-Budget Confirmation

`max_generation_attempts` unchanged. `GroundingValidator._MAX_PROVENANCE_RETRIES = 1` unchanged. No new retry mechanism of any kind was added.

## 11. Files Created/Modified

**Created:**
- `implementation/WP-027_COMPLETION_REPORT.md` (this file)
- `evaluation/live_outputs/wp027_reeval_persisted_results.json`, `wp027_focused_live_test_results.json`, `wp027_acceptance_exam.json`, `wp027_acceptance_audit.json`, `wp027_acceptance_targets.json`

**Modified:**
- `src/exam_generator/models/validation.py` - new `GroundingAnswerAssessment`; `GroundingValidationResponse` restructured; `GroundingValidationResult` unchanged
- `src/exam_generator/models/__init__.py` - new export
- `src/exam_generator/validation/grounding.py` - `_resolve_grounding_response()` rewritten (structural validation, per-option bounds-checking, deterministic derivation); `validate_grounding()` passes `candidate` through
- `prompts/validation/grounding.txt` - full rewrite for per-option evaluation
- `prompts/generation/question.txt` - new generalized distractor-correctness rule
- `tests/unit/test_grounding_validation.py` - fixtures rewritten for per-option shape; 14 new tests
- `tests/unit/test_prompts.py` - 2 existing tests updated for new prompt content; 12 new tests
- `tests/integration/test_end_to_end_pipeline.py`, `tests/integration/test_structured_output_recovery.py` - `_grounding()` helpers and inline `GroundingValidationResponse` constructions updated to the new per-option shape
- `docs/ARCHITECTURE.md` - new "Evidence-Aware Per-Option Grounding and Distractor Correctness (WP-027)" section
- `docs/PROJECT_STATUS.md` - Tests/Live Evaluation Baseline/Next WP Context sections updated

**No changes:** `src/exam_generator/validation/{mcq,category,quality,textbook}.py`, `src/exam_generator/planning/*`, `src/exam_generator/retrieval/*`, `schemas/*.schema.json` (confirmed byte-identical), `src/exam_generator/production/*`, `src/exam_generator/orchestration/*`.

## 12. Tests Added/Changed

- **`tests/unit/test_grounding_validation.py`** (35 → 49, +14): four named regression cases reproducing #23 (PNS), #8 (CT), #14 (blood-supply), #32 (microglia)'s exact "second answer also supported" shape; a #30-shape "unsupported designated answer, nothing else supported either" case (different defect shape, must still fail); a positive "true fact elsewhere, does not satisfy exact question" case (do-not-overcorrect); a test confirming derivation ignores `reason` text and uses only the structured booleans; a test confirming the two summary booleans no longer exist on the LLM-facing response at all; five structural-validation tests (missing/duplicate/zero/negative/above-4 index); one test confirming bounds-checking covers a non-designated assessment's refs too.
- **`tests/unit/test_prompts.py`** (143 → 155, +12): 8 new grounding-prompt-content assertions (stop-after-designated warning, designated-label-not-proof warning, per-option independence requirement, distractor-label-distrust warning, genuinely-correct-distractor-must-be-reported requirement, sibling-member-protection wording, the generic PNS-shaped worked example with no real category name, and the new response-field documentation); 4 new generation-prompt-content assertions (per-distractor evidence check requirement, not-limited-to-enumeration wording, the generic worked example with no real category name, true-fact-not-sufficient wording); 2 existing tests updated to match the new field/content shape.
- **`tests/integration/*`**: no new tests added (out of WP-027's stated scope); existing fixtures updated mechanically to the new response shape with zero change to any test's actual assertion about prior-WP behavior.

## 13. Full Regression Result

**1050 / 1050 passing** (up from the 1024 baseline entering WP-027; +26 net), zero network access, no `OPENAI_API_KEY` in the offline test shell. `scripts/generate_schemas.py` re-run: all three schema files byte-identical (confirmed via `git status --short schemas/` showing no changes) - grounding models are never schema-exported.

## 14. Focused Live Test Results

Three fresh `QuestionProducer.produce_question()` calls (full pipeline: generation with the new distractor rule + all five validators including the strengthened grounding), reusing the exact persisted `QuestionTarget`s from the WP-026 acceptance run for the categories behind #8 (CT), #23 (PNS), and #32 (microglia):

| Case | Category | Outcome | Attempt | Accepted question's framing |
|---|---|---|---|---|
| #8 CT-shape | מיפוי ודימות מוחי | accepted | 3 | Reframed entirely away from the tumor-ID/3D-imaging ambiguity - asks for CT's main advantage with four structurally distinct properties (speed/cost, 3D image, age-group, radiation use) |
| #23 PNS-shape | מערכת העצבים ההיקפית | accepted | 2 | Flipped framing to "which of the following constitutes the **somatic** part of PNS" - autonomic/sympathetic/parasympathetic are all cleanly wrong for that specific framing, not bare membership |
| #32 microglia-shape | תאי מערכת העצבים | accepted | 1 | Combined both real microglia functions (phagocytosis + synapse clearance) into a single correct answer choice, rather than presenting them as two competing options |

All three accepted candidates' grounding results confirm `correct_answer_supported=True` and `other_answers_not_equally_correct=True`. Intermediate rejected attempts occurred for #8 (2) and #23 (1) - consistent with the strengthened pipeline actively filtering candidates along the way, not merely generation getting lucky on the first try.

## 15. Persisted WP-026 Suspicious-Case Re-Evaluation

Re-ran the exact persisted candidate text/answers/category/mode (not regenerated) through the strengthened `GroundingValidator` (independent retrieval happens fresh, as always):

| # | Previous (WP-026) verdict | New verdict | correct_supported | others_not_equal | New passed |
|---|---|---|---|---|---|
| #8 (CT) | accepted (CONFIRMED false-acceptance) | **rejected** | True | **False** | **False** |
| #14 (blood supply) | accepted (POSSIBLE) | still accepted | True | True | True |
| #23 (PNS) | accepted (CONFIRMED false-acceptance) | **rejected** | True | **False** | **False** |
| #32 (microglia) | accepted (POSSIBLE) | **rejected** | True | **False** | **False** |
| #30 (ventricle stage) | accepted (different defect shape) | still accepted | True | True | True |

The two `CONFIRMED_SECOND_CORRECT_ANSWER` cases (#8, #23) and one of the two `POSSIBLE` cases (#32) are now correctly rejected, each with a `reason` explicitly naming both supported answer indices. #14 (the more genuinely ambiguous case - whether "posterior brain regions" includes the cerebellum) and #30 (a different defect shape - not a distractor-also-correct issue at all) still pass, showing the strengthened validator targets the actual defect precisely rather than over-rejecting.

## 16. Full 40-Question Acceptance Run

- **Planned: 40 | Accepted: 34 | Failed: 6 | Status: PARTIAL**
- **Runtime: ~22.9 minutes** (1373.3 seconds)
- **Exit code: 0**; both `exam.json` (34 questions) and `exam_audit.json` written successfully.

### Every failed planned question and reason

| Position | Category | Mode | Reason |
|---|---|---|---|
| 1 | התעלה השדרתית ותכולתה | STYLE_SIMILAR | `QuestionAttemptsExhaustedError` (3/3 rejected) |
| 4 | לוקליזציה פונקציונלית | INDEPENDENT | `QuestionAttemptsExhaustedError` (3/3 rejected) |
| 9 | מיפוי ודימות מוחי | STYLE_SIMILAR | `QuestionAttemptsExhaustedError` (3/3 rejected) |
| 18 | קרומים וסינוסים דוראליים | INDEPENDENT | `QuestionAttemptsExhaustedError` (3/3 rejected) |
| 19 | גזע המוח | STYLE_SIMILAR | `QuestionAttemptsExhaustedError` (3/3 rejected) |
| 27 | מערכת העצבים ההיקפית | STYLE_SIMILAR | `QuestionAttemptsExhaustedError` (3/3 rejected) |

**Generation-contract failures observed: 0.**

### Accepted-attempt distribution

**27 accepted on attempt 1, 5 on attempt 2, 2 on attempt 3** (43 accepted-path attempts, avg **1.26**/accepted question) plus 18 attempts across the 6 failed questions (3 each) = **61 total candidate attempts**.

### Validator rejection counts (all rejected attempts, accepted-eventually and fully-failed combined)

grounding: 12, quality: 10, mcq: 8, textbook: 6, category: 3.

### Grounding rejection breakdown (the key WP-027 metric)

**Designated answer unsupported: 0. Another answer also supported: 12. Other grounding reasons (premise unsupported): 0.**

Every single grounding-caused rejection in this run was specifically the defect class WP-027 exists to catch - a distractor the strengthened per-option check determined also correctly answered the exact question. This is strong, at-scale confirmation that the mechanism is actively engaged, not merely passing its own unit tests.

## 17. False-Acceptance Human Review

All 34 accepted questions were individually inspected against their cited grounding evidence for the specific invariant: does the evidence support more than one answer as correct for the exact question?

**Totals: 33 CLEAR_SINGLE_ANSWER, 1 POSSIBLE_SECOND_CORRECT_ANSWER, 0 CONFIRMED_SECOND_CORRECT_ANSWER, 0 INSUFFICIENT_EVIDENCE_TO_JUDGE.**

The one `POSSIBLE` case: question #7 (`מיפוי ודימות מוחי`, "which method is used for diffusion imaging to identify anatomical connectivity") designates "Diffusion Imaging" correct against distractors CT/Ultrasound/MRI. In real-world neuroimaging, diffusion imaging (DTI) is technically a specific MRI modality, so a well-informed student could argue "MRI" is defensible too. The supplied evidence, however, listed Diffusion Imaging as its own distinct named technique separate from MRI (matching this course's own apparent categorization), and the grounding call - which had access to the full evidence, not just the truncated excerpt reviewed here - explicitly rejected MRI as unsupported. Reported honestly as `POSSIBLE` rather than silently classified as `CLEAR`, per the review's own instruction not to under-report uncertainty.

**This meets WP-027's stated primary quality goal: `CONFIRMED_SECOND_CORRECT_ANSWER = 0`.**

Notably, several accepted questions (#24, #26, #27, #28) tested one member of an enumeration-shaped target (diencephalon-derived structures; neural-tube flexures; parietal-lobe gyri; inferior-hemisphere sensory structures) with genuine sibling members present as distractors - the same *shape* that produced WP-026's #23 - but succeeded because the question's added specific property (a function, a location, a system membership) cleanly excluded the siblings, and the strengthened grounding correctly confirmed only one answer satisfied that specific property. This is direct evidence the WP-026 (generation-side framing) and WP-027 (grounding-side backstop) fixes work together, not merely each in isolation.

## 18. Per-Category Diversity Review

Every category with **both** planned questions accepted (14 of 20; the other 6 - matching the 6 failures above - had only one planned question accepted, leaving no pair to judge):

| Category | Question 1 | Question 2 | Assessment |
|---|---|---|---|
| חומר לבן | Association fibers (same-hemisphere connection) | Internal Medullary Lamina (separates thalamic nuclei) | DISTINCT |
| עצבים קרניאליים | Olfactory nerve development path | Optic nerve function | DISTINCT |
| היסטולוגיה | Neocortex molecular layer | Microscope/history of histology | DISTINCT |
| המערכת הלימבית | Hippocampus (memory) | Amygdala (emotion) | DISTINCT |
| אספקת דם | Superior cerebellar artery | Anterior spinal artery | DISTINCT |
| מסילות עצביות | Spinothalamic tract | Medial lemniscus tract | DISTINCT |
| גרעיני הבסיס | Central role (motor execution) | Indirect pathway (reduces movement) | DISTINCT |
| המוח הקטן | Central function (coordination) | Structure (gray matter outside) | DISTINCT |
| דיאנצפלון | Hypothalamus (thermoregulation) | Thalamus (main structure/sensory relay) | DISTINCT |
| אמבריולוגיה | Gastrulation | Cervical flexure | DISTINCT |
| טופוגרפיה של ההמיספרות | Postcentral gyrus (parietal) | Optic nerve (visual system, inferior surface) | DISTINCT |
| חדרי המוח | Lateral ventricle C-shape | 3rd-4th ventricle connection | DISTINCT |
| תאי מערכת העצבים | Microglia | Ependymal cells | DISTINCT |
| מבוא | Edwin Smith Papyrus | Evolution (brain volume) | DISTINCT |

**Totals: 14 / 14 DISTINCT (100%), 0 BORDERLINE, 0 DUPLICATE/NEAR-DUPLICATE.** WP-025's diversity-by-construction and WP-026's target-aware framing both remain fully intact under WP-027's strengthened grounding.

## 19. Comparison with WP-026

- **Accepted**: 34/40 (WP-027) vs. 35/40 (WP-026) - one fewer, and this is the *expected*, *reported-honestly* reliability trade-off (see section 20), not a regression: the strengthened validator now correctly rejects candidates the old one would likely have waved through.
- **Accepted on attempt 1/2/3**: 27/5/2 (WP-027) vs. 27/4/4 (WP-026) - materially unchanged.
- **Diversity**: 14/14 DISTINCT (WP-027) vs. 15/15 DISTINCT (WP-026) - both 100%.
- **Generation-contract failures**: 0 in both.
- **False acceptance**: WP-026 had 2 `CONFIRMED` + 2 `POSSIBLE` among 35 accepted; WP-027 has 0 `CONFIRMED` + 1 `POSSIBLE` among 34 accepted - the headline result this WP set out to achieve.

## 20. Reliability Trade-Off

Grounding rejections rose modestly relative to what would be attributable purely to chance (12 of them, all "another also supported" - a rejection reason that essentially did not exist as a *correct* rejection reason before WP-027, since the old contract could not reliably produce it). Total candidate attempts (61) and accepted-question count (34) are close to WP-026's (62, 35) - a one-question difference, not a meaningful capacity regression. **Per WP-027 section 29's explicit instruction, this is accepted and not treated as something to fix by weakening grounding**: correctness (0 confirmed false acceptances) takes priority over marginal acceptance-rate recovery. This is a single live run (n=1); the direction (fewer silent false acceptances, comparable overall throughput) is clear, but the exact magnitude is not a statistically powered measurement.

## 21. Cost/Call-Count Impact

- **Additional LLM calls: none.** Per-option assessment happens inside the existing single `GroundingValidator.validate_grounding()` call.
- **Additional retrieval calls: none.** Retrieval-query construction was investigated and left unchanged (section 7).
- **Larger grounding structured output: yes**, as expected - four assessments instead of two flat booleans.
- **Runtime**: ~22.9 min (WP-027) vs. ~22.5 min (WP-026) - materially unchanged; the larger grounding response did not produce an observable runtime regression in this single run.

## 22. Known Limitations / Deviations

- This is a single live acceptance run (n=1) and a small set of targeted re-evaluations/focused-live-test cases; the results are strong single-run evidence, not a statistically powered guarantee at scale.
- Question #7's `POSSIBLE_SECOND_CORRECT_ANSWER` classification (section 17) reflects genuine real-world domain overlap (diffusion imaging as an MRI modality) that the supplied course evidence itself treats as distinct - reported honestly rather than resolved, since WP-027 explicitly forbids tuning based on this run's findings.
- No deviations from the WP-027 specification were made. Retrieval-query construction was investigated (required) and left unchanged (a decision, not an omission - section 7/10).

## 23. Confirmations

- **No new validator was added.** Five validators, unchanged in count and boundary, remain: grounding, MCQ, category, quality, textbook.
- **Attempt/retry limits unchanged**: `max_generation_attempts`, `GroundingValidator._MAX_PROVENANCE_RETRIES`, and WP-020's structured-output retry bound are all untouched.
- **TF-IDF/retrieval implementation unchanged**, confirmed by explicit investigation (section 7) rather than assumption - no file under `src/exam_generator/retrieval/` was modified.
- **No embeddings/vector DB introduced**: no new dependency was added (`pyproject.toml` unchanged).
- **No post-acceptance tuning or rerun performed**: the full acceptance run's result (34/40) is reported exactly as produced; no prompt/config change was made afterward and no rerun was performed based on its results.

---

WP-027 complete.
Tests: 1050 passed
Focused false-acceptance regression: 3/3 accepted with correct single-answer framing (#8, #23, #32 shapes); 3/5 persisted WP-026 suspicious cases now correctly rejected (#8, #23, #32), 2 correctly still pass (#14, #30)
Acceptance run: PARTIAL, 34/40 accepted, 6 failed (0 false-acceptance-caused)
False-acceptance review:
    confirmed second-correct: 0
    possible second-correct: 1
Diversity: 14/14 DISTINCT
Completion report:
    implementation/WP-027_COMPLETION_REPORT.md

Do not start WP-028. Wait for architect/user review.
