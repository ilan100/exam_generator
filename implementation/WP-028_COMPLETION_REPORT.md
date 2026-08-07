# WP-028 Completion Report — Blueprint-Driven Question Generation

## 1. Implementation Summary

WP-027's own live acceptance run showed the validation architecture working correctly but at a cost: 12 grounding rejections, all "another answer also supported" - generation was routinely submitting candidates that failed on the first attempt for a defect class the architecture could now name precisely. WP-028's objective, as specified, was narrow: improve generation quality so the first generated candidate is more likely to satisfy the *existing*, *unchanged* validators - never to weaken them.

The implementation is exactly as scoped: generation now constructs an explicit **internal question blueprint** as a required part of its existing single structured-output call - no second LLM call, no new pipeline stage, no orchestration change, no validator change. The blueprint forces the model to state, before finalizing the question, the precise tested relationship (not a bare label), an intentional design and evidence check for each of the three distractors, and a final self-review checklist.

**The live full acceptance run, however, did not show the hoped-for improvement** - see sections 15-20. This report documents the implementation faithfully and reports that result exactly as measured, per the project's standing "no tuning after results" discipline.

## 2. Blueprint Design

`QuestionBlueprint` (new, `src/exam_generator/models/question.py`):

```python
class QuestionBlueprint(BaseModel):
    knowledge_target: NonBlankStr
    tested_relationship: NonBlankStr   # stated as a relationship/property, not a bare label
    question_style: NonBlankStr
    intended_difficulty: QuestionDifficulty   # EASY / MEDIUM / HARD
    correct_answer_role: NonBlankStr
    distractors: list[DistractorDesign]   # exactly 3
```

```python
class DistractorDesign(BaseModel):
    archetype: DistractorArchetype
    plausibility_reason: NonBlankStr
    incorrectness_reason: NonBlankStr   # a single, exact reason - not several unrelated ones
    evidence_checked: StrictBool        # self-reported confirmation the distractor was checked against evidence
```

`DistractorArchetype` (8 named strategies, per the WP's own list): `SIBLING_STRUCTURE`, `PARENT_CATEGORY`, `CHILD_CATEGORY`, `NEIGHBORING_ANATOMY`, `FUNCTIONAL_CONFUSION`, `LOCATION_CONFUSION`, `DEVELOPMENTAL_STAGE_CONFUSION`, `TERMINOLOGY_CONFUSION`. Generation must intentionally choose one per distractor rather than inventing plausible wrong answers ad hoc.

The blueprint deliberately does not restate the final answer text (would duplicate the MCQ, per the WP's own instruction) - it captures design *reasoning* only.

## 3. Generation Changes

`GeneratedQuestionResponse` gained a required `blueprint: QuestionBlueprint` field. `QuestionGenerator.generate_candidate_question()` (`src/exam_generator/generation/generator.py`) required **zero code changes** - it already discards everything on the response it doesn't explicitly copy onto `CandidateQuestion`, so the blueprint is automatically dropped without any new logic. `CandidateQuestion` itself is untouched.

## 4. Prompt Changes

`prompts/generation/question.txt` gained one new required section ("Question blueprint (required - read carefully)"), placed after the existing distractor-correctness guidance, requiring:

- Constructing the blueprint before finalizing the question, as part of the same response.
- Stating the tested relationship precisely (not a bare label) - explicitly tied to the narrowing guidance already present from WP-026.
- Reporting the knowledge target, tested relationship, question style, intended difficulty, and correct-answer justification.
- Intentionally designing each distractor with a named archetype, a plausibility reason, and a single exact incorrectness reason.
- Explicitly checking each distractor against the supplied evidence before including it, and only reporting `evidence_checked: true` once that check was actually performed - reinforcing WP-027's own generation-side distractor rule as a required structured field rather than unenforced prose.
- A final self-review checklist (exactly one answer satisfies the relationship; each distractor fails for one clear reason; wording is specific; hierarchy is unambiguous; evidence supports the intended answer; evidence does not support any distractor) before finalizing.

The `Required output` list at the top of the prompt was updated to reference the blueprint requirement. No other prompt file was touched.

## 5. New LLM-Facing Models

`QuestionBlueprint`, `DistractorDesign`, `DistractorArchetype`, `QuestionDifficulty` - all new, all in `src/exam_generator/models/question.py`, all exported from `src/exam_generator/models/__init__.py`.

## 6. Deterministic Conversion

Unchanged code path: `QuestionGenerator.generate_candidate_question()` constructs `CandidateQuestion` from only `response.question`/`response.answers`/`response.correct_answer` plus caller-supplied `category`/`generation_mode` - the same five fields it has always used. `response.blueprint` is simply never read, so it cannot leak downstream by construction, not by an added check. Verified directly by test (`test_deterministic_conversion_discards_blueprint`, `test_candidate_question_never_carries_a_blueprint_field`).

## 7. Files Created/Modified

**Created:**
- `implementation/WP-028_COMPLETION_REPORT.md` (this file)
- `evaluation/live_outputs/wp028_focused_eval_results.json`, `wp028_acceptance_exam.json`, `wp028_acceptance_audit.json`, `wp028_acceptance_targets.json`

**Modified:**
- `src/exam_generator/models/question.py` - new `DistractorArchetype`, `QuestionDifficulty`, `DistractorDesign`, `QuestionBlueprint`; `GeneratedQuestionResponse` gained required `blueprint`
- `src/exam_generator/models/__init__.py` - new exports
- `prompts/generation/question.txt` - new "Question blueprint" section
- `tests/unit/test_generation.py` - fixtures updated; 11 new tests
- `tests/unit/test_prompts.py` - 9 new tests
- `tests/integration/test_end_to_end_pipeline.py`, `tests/integration/test_structured_output_recovery.py` - `_generated_response()` fixtures and every inline `GeneratedQuestionResponse(...)` construction updated to include a blueprint
- `docs/ARCHITECTURE.md` - new "Blueprint-Driven Question Generation (WP-028)" section
- `docs/PROJECT_STATUS.md` - Tests/Live Evaluation Baseline/Next WP Context sections updated

**No changes:** `src/exam_generator/validation/*` (all five validators untouched, confirmed), `src/exam_generator/production/*`, `src/exam_generator/orchestration/*`, `src/exam_generator/planning/*`, `src/exam_generator/retrieval/*`, `schemas/*.schema.json` (confirmed byte-identical).

## 8. Tests

- **`tests/unit/test_generation.py`** (43 → 54, +11): blueprint required on `GeneratedQuestionResponse`; exactly-3-distractors structural validation; archetype/difficulty must be named enum values; `incorrectness_reason` cannot be blank; `evidence_checked` must be strict bool; unknown blueprint fields forbidden; `CandidateQuestion` never carries a blueprint field; deterministic conversion discards the blueprint; generation still makes exactly one LLM call; all 8 archetypes are constructible.
- **`tests/unit/test_prompts.py`** (155 → 164, +9): blueprint-required-before-final-answer wording; relationship-vs-bare-label framing; all five required blueprint fields present; intentional-distractor-design requirement; all 8 archetype phrases present; single-clear-incorrectness-reason wording; evidence-check-before-confirming wording; same-call-only wording; self-review checklist wording.

## 9. Full Regression Result

**1070 / 1070 passing** (up from the 1050 baseline entering WP-028; +20 net), zero network access, no `OPENAI_API_KEY` in the offline test shell. `scripts/generate_schemas.py` re-run: all three schema files byte-identical - blueprint models are never schema-exported.

## 10. Focused Live Evaluation

6 candidates (2 per category) across `מערכת העצבים ההיקפית`, `אספקת דם`, `תאי מערכת העצבים` (the categories the WP specifically named as historically weak-distractor-prone), via `QuestionTargetPlanner` + `QuestionProducer` (the same production wiring the CLI uses):

**Result: 5/6 accepted, avg 1.67 attempts.**

| Category | Topic | Outcome | Attempt |
|---|---|---|---|
| מערכת העצבים ההיקפית | PNS divisions | **exhausted** | 3/3 |
| מערכת העצבים ההיקפית | Schwann cells | accepted | 1 |
| אספקת דם | Cerebellar blood supply | accepted | 1 |
| אספקת דם | Spinal cord blood supply | accepted | 3 |
| תאי מערכת העצבים | Microglia | accepted | 1 |
| תאי מערכת העצבים | Ependymal cells | accepted | 1 |

The one exhaustion (PNS divisions - the same target that has proven hard across WP-025A, WP-026, and WP-027's own focused control runs) failed for a **different reason than the multi-correct-answer pattern**: the first two attempts contained outright factual errors in distractor content (e.g. one distractor claimed the autonomic nervous system controls voluntary skeletal-muscle movement, which is simply false - correctly caught by MCQ/category/quality), and the third was rejected on category-scope grounds (a question about "voluntary control of skeletal muscles" judged as more specifically about the somatic subsystem than the PNS category as a whole). No false-acceptance-shaped failure occurred in this focused sample.

## 11. Full Acceptance Run

### First attempt: crashed, not a valid measurement

The first full-run attempt reached question 34/40 (27 completed) before crashing with an uncaught `QuestionProductionFailedError`, root-caused to a `GroundingValidationResponse` that was truncated mid-JSON (`Invalid JSON: EOF while parsing a string`), exhausting WP-020's existing bounded physical structured-output retry (2 attempts). `LLMStructuredOutputError` is deliberately classified **system-level** in `orchestrator.py` (matching pre-existing, deliberately-written test expectations - `_SYSTEM_LEVEL_ERROR_TYPES` - not a new or surprising classification), so the whole run correctly aborted by design rather than silently continuing.

This is judged **not** a WP-028-caused regression and **not** something tuned away: the truncation occurred in the *grounding* validator's response (a call WP-028 never touches - WP-028 only modifies `GeneratedQuestionResponse`, the *generation* call's contract), and is a known, pre-existing stochastic risk in WP-020's retry mechanism that this specific run happened to hit. Since the crash produced no completed measurement at all (not a worse-than-hoped PARTIAL result, but no result), a second full run was performed. No code, prompt, or configuration was changed between the two attempts.

### Second attempt: the official result

- **Planned: 40 | Accepted: 31 | Failed: 9 | Status: PARTIAL**
- **Runtime: ~27.8 minutes** (1670.0 seconds)
- **Exit code: 0**; both `exam.json` (31 questions) and `exam_audit.json` written successfully.

### Every failed planned question and reason

| Position | Category | Mode |
|---|---|---|
| 1 | התעלה השדרתית ותכולתה | STYLE_SIMILAR |
| 4 | לוקליזציה פונקציונלית | INDEPENDENT |
| 7 | עצבים קרניאליים | STYLE_SIMILAR |
| 9 | מיפוי ודימות מוחי | STYLE_SIMILAR |
| 10 | מיפוי ודימות מוחי | INDEPENDENT |
| 18 | קרומים וסינוסים דוראליים | INDEPENDENT |
| 19 | גזע המוח | STYLE_SIMILAR |
| 32 | אמבריולוגיה | INDEPENDENT |
| 40 | מבוא | INDEPENDENT |

All 9 are `QuestionAttemptsExhaustedError` (normal candidate-quality exhaustion). **`מיפוי ודימות מוחי` failed both of its planned positions** - zero accepted questions for that category this run. **Generation-contract failures observed: 0.**

### Accepted-attempt distribution

**23 accepted on attempt 1, 5 on attempt 2, 3 on attempt 3** (42 accepted-path attempts, avg **1.35**/accepted question) plus 27 attempts across the 9 failed questions (3 each) = **69 total candidate attempts**.

### Validator rejection counts (all rejected attempts)

mcq: 18, quality: 15, grounding: 16, category: 6, textbook: 2.

### Grounding rejection breakdown (the WP's own primary metric)

**Designated answer unsupported: 2. Another answer also supported: 14. Other grounding reasons: 0.**

## 12. Comparison with WP-027

| Metric | WP-027 | WP-028 | Direction |
|---|---|---|---|
| Accepted / planned | 34/40 | 31/40 | worse |
| Accepted on attempt 1/2/3 | 27/5/2 | 23/5/3 | worse |
| Avg attempts per accepted | 1.26 | 1.35 | worse |
| Total candidate attempts | 61 | 69 | worse |
| Grounding rejections (total) | 12 | 16 | worse |
| Grounding: "another also supported" | 12 | 14 | **worse - the WP's own primary success metric** |
| Grounding: "designated unsupported" | 0 | 2 | worse |
| MCQ rejections | 8 | 18 | much worse |
| Quality rejections | 10 | 15 | worse |
| Category rejections | 3 | 6 | worse |
| Textbook rejections | 6 | 2 | better |
| False acceptance: CONFIRMED | 0 | 0 | **held** |
| False acceptance: POSSIBLE | 1 | 2 | marginally worse (single-run) |
| Diversity | 14/14 DISTINCT | 12/12 DISTINCT | held (both 100%; fewer pairs since more categories had <2 accepted) |

**WP-028's own explicitly-stated primary success metric ("grounding rejections caused by another supported answer should decrease") moved in the wrong direction.** Nearly every efficiency metric is modestly worse. The one metric that matters most - final correctness of the accepted set - held at WP-027's own bar (0 confirmed false acceptances), which is the one result reported without qualification as a genuine success.

## 13. False-Acceptance Human Review

All 31 accepted questions were individually inspected against their cited grounding evidence.

**Totals: 29 CLEAR_SINGLE_ANSWER, 2 POSSIBLE_SECOND_CORRECT_ANSWER, 0 CONFIRMED_SECOND_CORRECT_ANSWER, 0 INSUFFICIENT_EVIDENCE_TO_JUDGE.**

The two `POSSIBLE` cases, both genuine real-world anatomical-overlap subtleties rather than clear defects:

- Question #11 (`אספקת דם`, "which artery supplies posterior areas of the CNS") designates PCA correct; the Superior Cerebellar Artery (a distractor) also genuinely branches from the Basilar artery and supplies the cerebellum, arguably also "a posterior region" - the same shape as WP-027's own #14 `POSSIBLE` case, again not clearly resolved by the supplied evidence excerpt.
- Question #12 (`קרומים וסינוסים דוראליים`, "what is the role of venous sinuses") designates "drains blood from the brain to the jugular vein" correct against a distractor "drains skull blood to emissary veins" - in real anatomy, dural venous sinuses genuinely drain via *both* the internal jugular vein (primary) and connect to extracranial veins via emissary veins (a real, secondary pathway), so the distractor is not obviously false in general anatomical fact, even though the cited evidence excerpt only explicitly credits the jugular-vein route.

Several accepted questions again showed the WP-026/027-established "specific qualifier cleanly narrows despite an enumeration-shaped target" pattern working correctly (e.g. #13 - "which brainstem function handles breathing" correctly excludes real sibling functions heart-rate/sleep-wake; #16 - "central role in executing movement" correctly excludes real secondary basal-ganglia functions like learning/reward; #23 - "the central diencephalon structure" correctly excludes real sibling structures).

## 14. Per-Category Diversity Review

12 of 20 categories had both planned questions accepted (fewer than WP-027's 14, since more categories had 0 or 1 accepted this run - `מיפוי ודימות מוחי` had 0; `התעלה השדרתית ותכולתה`, `לוקליזציה פונקציונלית`, `עצבים קרניאליים`, `קרומים וסינוסים דוראליים`, `גזע המוח`, `אמבריולוגיה`, `מבוא` each had 1):

| Category | Question 1 | Question 2 | Assessment |
|---|---|---|---|
| חומר לבן | Association fibers (same-hemisphere) | Projection fibers (cortical-to-subcortical) | DISTINCT |
| היסטולוגיה | Nervous-tissue excitability | Neocortex layer 5 (spinal-cord transmission) | DISTINCT |
| המערכת הלימבית | Cingulate gyrus (emotion) | Hippocampus (memory) | DISTINCT |
| אספקת דם | SCA (upper cerebellum) | PCA (posterior CNS) | DISTINCT |
| מסילות עצביות | Spinothalamic tract | Medial lemniscus tract | DISTINCT |
| גרעיני הבסיס | Central role (executes movement) | Direct pathway (specific mechanism) | DISTINCT |
| המוח הקטן | Function (coordination) | Structure (gray matter location) | DISTINCT |
| מערכת העצבים ההיקפית | Sympathetic (fight/flight) | Schwann cells (myelin) | DISTINCT |
| דיאנצפלון | Hypothalamus (emotion/memory) | Thalamus (central structure) | DISTINCT |
| טופוגרפיה של ההמיספרות | Frontal lobe (location) | Postcentral gyrus (S1 identity) | DISTINCT |
| חדרי המוח | Lateral ventricles (C-shape) | 3rd ventricle (interventricular foramen) | DISTINCT |
| תאי מערכת העצבים | Microglia | Ependymal cells | DISTINCT |

**Totals: 12 / 12 DISTINCT (100%), 0 BORDERLINE, 0 DUPLICATE/NEAR-DUPLICATE.**

## 15. Observed Improvements

- **None on the WP's own stated efficiency metric.** This is reported plainly rather than reframed around a metric that did improve.
- Correctness (0 `CONFIRMED_SECOND_CORRECT_ANSWER`) held exactly at WP-027's bar.
- The focused live evaluation's PNS-divisions failure showed a genuinely different failure signature (factual distractor errors, category drift) than the multi-correct-answer pattern that has dogged this specific target since WP-025A - inconclusive as improvement evidence on its own (n=1), but at least not a recurrence of the previously-diagnosed shape in that one sample.
- Several accepted questions in the full run continued to demonstrate the WP-026/027 "specific qualifier narrows despite enumeration" pattern working correctly (section 13) - this is not new to WP-028, but confirms the mechanism remains intact.

## 16. Remaining Weaknesses

- **The blueprint's `evidence_checked` field, and every other blueprint field, is entirely self-reported by the same call that produces the final question - never independently verified.** This is architecturally different from WP-027's fix, where the equivalent claim (a distractor doesn't also satisfy the question) is checked by a genuinely separate validator call with its own retrieval and its own reasoning. A model can set `evidence_checked: true` regardless of whether it actually performed a rigorous check, and nothing in this WP's design can detect that. This is the leading hypothesis for why the live result did not improve, and is consistent with the project's own repeatedly-applied principle (first stated at WP-009, reapplied at WP-022/024/027) that a generator's self-reported claims are never proof.
- MCQ rejections roughly doubled (8 → 18). One plausible contributing factor: the added blueprint reasoning increases the structured-output response's overall complexity, which could plausibly make consistent execution of the *final* question/answer fields harder, not easier - a real design-complexity cost the WP did not anticipate.
- The PNS-divisions target remains the single most reliably difficult case across five consecutive WPs' worth of live evidence (WP-025A, WP-026, WP-027 x2, WP-028's focused eval and full run) - it is now well-established as a genuinely hard case for this architecture, not a fluke of any one WP's specific approach.

## 17. Known Limitations / Deviations

- This is a single completed live acceptance run (n=1) plus a small focused-evaluation sample (n=6); the comparison with WP-027 (also n=1) is a real, honestly-reported directional signal, not a statistically powered claim that the blueprint mechanism is a net regression - a second independent run could show different numbers by chance alone, though the consistency of the direction across nearly every metric (not just one) makes pure noise a less likely full explanation.
- The first full-run attempt's crash (section 11) is documented in full; a second run was performed since the first produced no valid completed measurement, not because its partial results (27/34 completed before crashing) were undesirable - no data from the first attempt was used in any reported metric.
- No deviations from the WP-028 specification were made: no validator was touched, no pipeline stage was added, no attempt/retry limit was changed, and no prompt tuning occurred after either the focused evaluation or the full acceptance run.

## 18. Confirmations

- **No validator was added or modified**: `GroundingValidator`/`MCQValidator`/`CategoryValidator`/`QualityValidator`/`TextbookValidator` are byte-for-byte unchanged from WP-027.
- **No pipeline/orchestration change**: no new stage, no new LLM call, no blueprint persistence/audit output/JSON file of any kind.
- **Attempt/retry limits unchanged**: `max_generation_attempts` and every existing retry bound (WP-020/WP-021) are untouched.
- **TF-IDF/retrieval unchanged**: no file under `src/exam_generator/retrieval/` was modified.
- **No embeddings/vector DB introduced.**
- **No post-run tuning performed**: the prompt, models, and code as they existed when the acceptance run was launched are exactly as they exist now; no change was made after seeing either the focused-evaluation or full-run results.

---

WP-028 complete.
Tests: 1070 passed
Acceptance run: PARTIAL, 31/40 accepted, 9 failed (grounding "another-also-supported" rejections: 14, up from WP-027's 12 - primary metric did not improve; false acceptance held at 0 confirmed / 2 possible)
Completion report:
implementation/WP-028_COMPLETION_REPORT.md

Wait for architect review.
