# WP-034 Completion Report — Coverage-Aware Target Planning

## 1. Objective and Scope

WP-032/WP-033 built the architecture and the permanent contract (`CategoryQuestionSetRequest`/`Response`) but neither used `existing_questions` for anything beyond exact-text duplicate detection. WP-034 is the first WP to actually use it: transform target planning from "choose a valid target" into "choose the next uncovered target," entirely within WP-033's already-stable contract (no new request/response field). Generation, validation, retrieval, and prompts (beyond one new planning-prompt section) remain unchanged, per the WP's own explicit scope.

## 2. Coverage Model

`CategoryCoverage` (new, `models/coverage.py`) - a deliberately internal-only model, never part of any public request/response contract (WP-034 section 3/7):

```python
tested_concepts: tuple[str, ...] = ()            # verbatim correct-answer text of each existing question
tested_relationship_types: tuple[str, ...] = ()  # WP-030 relationship vocabulary, inferred from question+answer text
```

Both fields are deduplicated, first-occurrence order preserved. It lives in `models/` rather than `planning/` (where it is produced/consumed) purely to avoid a circular import (`exam_generator.prompts` needs the type to render it; `exam_generator.planning` already imports `exam_generator.prompts`) - the same precedent `QuestionRelationship`/`CompetitorCandidate` already established for the same reason.

## 3. Extraction Algorithm

`extract_category_coverage()` (new, `planning/coverage.py`) - `Sequence[(question_text, correct_answer_text)] -> CategoryCoverage`. Pure, deterministic, **zero LLM calls, zero embeddings, zero semantic similarity** (section 4's explicit requirement):

1. For each `(question_text, correct_answer_text)` pair: record the stripped `correct_answer_text` verbatim as a tested concept (skipped if blank).
2. Classify a relationship type from the combined lowercased `question_text + correct_answer_text` via `classify_relationship_type()` (see section 6 below) - recorded only if not `UNSPECIFIED`.
3. Both lists deduplicated, preserving first-occurrence order.

**Honest limitation, documented in the module's own docstring (section 4: "if existing fields are insufficient, document exactly why")**: the production question schema carries only plain question/answer text - it does not preserve the original `QuestionTarget`/`QuestionRelationship` that produced a given question, since WP-033 deliberately did not add them to keep the contract stable. Coverage extraction can therefore only *approximately* recover what was tested, by re-applying existing heuristics to plain text after the fact - never the ground truth the original planning/generation call actually used.

Each service resolves its own `existing_questions` shape into plain pairs before calling this shared function: `CategoryGenerationService` uses `CandidateQuestion.answers[correct_answer - 1]`; `CategoryQuestionSetService` uses `ExamQuestion`'s four discrete `answer1..answer4` fields indexed the same way. The extraction function itself depends on neither model directly.

## 4. Planner Changes

- **`QuestionTargetPlanner.plan_targets()` gained one new optional parameter**: `coverage: CategoryCoverage | None = None` (defaults to empty - every pre-WP-034 caller/test continues to behave identically, confirmed by the full regression suite passing unchanged for every pre-existing test).
- **`QuestionTargetPlanningPromptContext` gained a `coverage: CategoryCoverage = CategoryCoverage()` field**, rendered into a new `already_tested_summary` template variable via `format_category_coverage()` (new, `prompts/formatting.py`) - the same `BEGIN/END (INFORMATION ONLY)` sentinel style already used for competitor concepts (WP-031), and the same honest "nothing tested yet" fallback pattern already used for historical references/course-book evidence.
- **`prompts/generation/question_target_planning.txt` gained one new section** ("Already-tested knowledge"), explicitly extending the prompt's pre-existing "genuine diversity" guidance (originally written for comparing targets *within* one batched call, now dormant since every call plans `count=1`) to also apply against coverage from *prior* calls for the same category.
- **No retry loop, no rejection mechanism was added** (section 6: "coverage does NOT become another validator") - planning still makes exactly one LLM call; a target overlapping with already-tested knowledge is never itself rejected or retried by application code, only (potentially) avoided by the LLM's own choice given the information.

## 5. Reused Components (Section 8)

| Component | Change |
|---|---|
| `QuestionProducer` | None |
| `QuestionGenerator` | None |
| Relationship model (`QuestionRelationship`, `extract_relationship()`) | None in behavior - `extract_relationship()` now calls a factored-out `classify_relationship_type()` helper internally, verified behavior-identical by the full pre-existing `test_relationship.py` suite passing unchanged |
| Competitor discovery | None |
| All five validators | None |
| Retry mechanisms (WP-013 attempt budget, WP-014 duplicate replacement) | None |
| Acceptance policy | None |

`generation/relationship.py`'s only change: the keyword-matching loop inside `extract_relationship()` was factored out into `classify_relationship_type(haystack: str) -> str` (now exported from `exam_generator.generation`), reused by both `extract_relationship()` (unchanged behavior) and `extract_category_coverage()` - one classification implementation, never two copies of the keyword table.

## 6. Tests

- New `tests/unit/test_coverage.py` (14 tests): `CategoryCoverage` model (defaults, frozen, forbids unknown fields); `extract_category_coverage()` over 0/1/2/3 existing questions (section 9's explicit count requirement); determinism; concept/relationship-type deduplication with first-occurrence order; blank-answer handling; agreement between `extract_relationship()` and `classify_relationship_type()` for identical text; no LLM/embedding call.
- 4 new tests in `tests/unit/test_planning.py`: planning works unchanged when coverage is omitted; coverage content is actually rendered into the sent prompt; empty coverage renders the honest sentinel; coverage never triggers a second LLM call.
- 6 new tests in `tests/unit/test_prompts.py`: the template requires the new `already_tested_summary` variable; default/supplied coverage rendering; "INFORMATION ONLY" framing preserved; context defaults to empty coverage.
- 4 new end-to-end wiring tests split across `tests/unit/test_category_generation.py`/`test_category_question_set.py`: coverage is correctly extracted from each service's own `existing_questions` shape (`CandidateQuestion` vs. `ExamQuestion`) and reaches `plan_targets()`'s `coverage` kwarg with the expected content; empty `existing_questions` yields empty coverage at the planner.
- Existing mocked-planner test doubles across both those files updated to accept the new `coverage` kwarg (backward-compatible signature change, not a behavior change).
- **Full regression suite: 1206 passed, 0 failed** (up from 1179 before this WP), zero network access, no `OPENAI_API_KEY` required.
- `scripts/generate_schemas.py` re-run: all three schema files **byte-identical** (`CategoryCoverage` is a deliberately internal-only model, never schema-exported - no public contract was touched).

## 7. Evaluation (Section 10)

Same category as WP-033's own evaluation (`אספקת דם`), four sequential `CategoryQuestionSetService.generate_next()` calls, coverage-aware planning active throughout:

| Round | Existing | Planned target focus (abbreviated) | Relationship | Accepted | Attempts | Dup. replacements |
|---|---|---|---|---|---|---|
| 1 | 0 | "arteries supplying cerebellum incl. SCA/AICA/PICA" | SUPPLIES | Yes | 1 | 0 |
| 2 | 1 | same, reworded | SUPPLIES | Yes | 1 | 0 |
| 3 | 2 | same, reworded | SUPPLIES | Yes | 1 | 2 |
| 4 | 3 | "arteries supplying various parts of cerebellum" | SUPPLIES | Yes | 1 | 0 |

**4/4 accepted, but zero diversity improvement.** All four accepted questions' correct answer was "Superior Cerebellar Artery" - the identical fact, every time. The coverage section was **verified** (by inspecting `QuestionTargetPlanner.plan_history`) to correctly and explicitly list "Superior Cerebellar Artery" as an already-tested concept and `SUPPLIES` as an already-tested relationship type from round 2 onward - the wiring is confirmed correct - yet the planner re-selected an overlapping target every single time. Round 3 needed 2 duplicate-replacement attempts (exact-text matches against round 1/2's questions) before landing on a differently-worded but conceptually identical question. This is the same category, same convergence pattern, same outcome as WP-033's own four-scenario evaluation. Raw results: `evaluation/live_outputs/wp034_evaluation_results.json`.

## 8. Acceptance Run (Section 11)

Performed exactly once, 20 categories × 2 questions, via `CategoryQuestionSetService` only. No reruns, no prompt modifications, no planner tuning after observing results.

**Result: 33/40 accepted, 7 failed** (all `QuestionAttemptsExhaustedError`):

| Category | Round | Failure |
|---|---|---|
| התעלה השדרתית ותכולתה | 0 | QuestionAttemptsExhaustedError |
| גזע המוח | 0 | QuestionAttemptsExhaustedError |
| גזע המוח | 1 | QuestionAttemptsExhaustedError |
| גרעיני הבסיס | 1 | QuestionAttemptsExhaustedError |
| מערכת העצבים ההיקפית | 0 | QuestionAttemptsExhaustedError |
| מערכת העצבים ההיקפית | 1 | QuestionAttemptsExhaustedError |
| טופוגרפיה של ההמיספרות | 0 | QuestionAttemptsExhaustedError |

Accepted-on-attempt distribution: **23/5/5** (attempt 1/2/3), avg **1.45** attempts/accepted question. First-attempt rate: 23/33 (69.7%). Validator rejection counts: mcq 7, quality 7, category 5, grounding 24, textbook 0. Grounding rejection breakdown: **23 "another answer also supported," 1 "designated answer unsupported."** Zero generation-contract failures. Raw data: `evaluation/live_outputs/wp034_acceptance_records.json`.

### Comparison with WP-032 (the only prior full-scale run of the current architecture; WP-033 had none)

| Metric | WP-032 | **WP-034** |
|---|---|---|
| Accepted | 36/40 | **33/40** |
| Grounding "another also supported" | 20 | **23** |
| Avg attempts/accepted | 1.58 | **1.45** |
| First-attempt rate | 63.9% | **69.7%** |
| Diversity: DISTINCT pairs | 7/17 (41%) | **7/15 (47%)** |
| Diversity: DUPLICATE pairs | 7/17 (41%) | **6/15 (40%)** |

## 9. Per-Category Diversity Review

Of the 20 categories, 15 had both planned questions accepted (`גזע המוח` and `מערכת העצבים ההיקפית` had zero; `התעלה השדרתית ותכולתה`, `גרעיני הבסיס`, `טופוגרפיה של ההמיספרות` had one each):

| Category | Verdict | Note |
|---|---|---|
| לוקליזציה פונקציונלית | **DUPLICATE** | Primary motor cortex / precentral gyrus, reworded |
| חומר לבן | **DUPLICATE** | Projection fibers, reworded |
| עצבים קרניאליים | DISTINCT | Olfactory-nerve connection vs. its developmental origin |
| מיפוי ודימות מוחי | BORDERLINE | Both fundamentally about CT detecting tumors/bleeds |
| היסטולוגיה | DISTINCT | Layer 5/corticospinal vs. molecular layer |
| המערכת הלימבית | DISTINCT | Hippocampus/memory vs. amygdala/smell |
| אספקת דם | **DUPLICATE** | Superior cerebellar artery, both rounds |
| קרומים וסינוסים דוראליים | BORDERLINE | Same sinus, formation vs. drainage function |
| מסילות עצביות | DISTINCT | Spinothalamic vs. medial lemniscus tract |
| גרעיני הבסיס | (only 1 accepted) | - |
| המוח הקטן | DISTINCT | Motor coordination vs. balance |
| דיאנצפלון | DISTINCT | Hypothalamus/emotion vs. thalamus/central structure |
| אמבריולוגיה | **DUPLICATE** | Gastrulation, near-identical phrasing |
| טופוגרפיה של ההמיספרות | (only 1 accepted) | - |
| חדרי המוח | DISTINCT | Fourth ventricle/aqueduct vs. lateral ventricle shape |
| תאי מערכת העצבים | **DUPLICATE** | Microglia phagocytosis, both rounds |
| מבוא | **DUPLICATE** | Edwin Smith papyrus, both rounds |

**Totals: 7/15 DISTINCT (47%), 2/15 BORDERLINE (13%), 6/15 DUPLICATE (40%).**

One notable case: `מסילות עצביות` duplicated in both WP-032 and WP-033's runs (spinothalamic tract tested twice) but was DISTINCT here (spinothalamic vs. medial lemniscus) - plausibly coverage helping, but equally plausibly ordinary run-to-run stochasticity (this exact tract pair was also WP-025's own original successful worked example under the old batched-planning architecture). Categories with one especially dominant, clearly-stated fact (`אספקת דם`, `חומר לבן`, `אמבריולוגיה`, `תאי מערכת העצבים`, `מבוא`, `לוקליזציה פונקציונלית`) duplicated regardless of coverage information being present and correctly rendered.

## 10. False-Acceptance Note

A quick pass over all 33 accepted questions found no obvious second-correct-answer concerns. A full formal `CLEAR_SINGLE_ANSWER`/`POSSIBLE`/`CONFIRMED`/`INSUFFICIENT_EVIDENCE` categorization (as performed for WP-027 through WP-032's own primary-metric runs) was not repeated here, since correctness was not the axis WP-034 changed or measured against (its own section 12 success criteria list "no decrease in acceptance rate" as secondary, not a false-acceptance requirement) and nothing in this WP's changes touches grounding/validation logic at all.

## 11. Architectural Evaluation (Section 14 - Required)

**Did using `existing_questions` improve planning? No, not meaningfully.**

**Did the planner genuinely become coverage-aware? No** - not in its actual target-selection behavior, despite the wiring being demonstrably correct.

Evidence for both conclusions:
- Coverage is correctly and deterministically computed (14 dedicated unit tests) and correctly delivered into the planning prompt as a clearly-labeled section (6 dedicated prompt tests, plus direct observation via `plan_history` in the live evaluation) - **the mechanism works exactly as designed.**
- The acceptance-run diversity metric moved from 41% to 47% DISTINCT - a 6-percentage-point difference on a 15-17-pair sample, well within ordinary run-to-run noise already observed across WP-025 through WP-033's own acceptance runs (which have ranged from 41% to 100% DISTINCT on similarly-sized samples without any target-planning change at all).
- The controlled, same-category evaluation (identical methodology to WP-033's own) showed **zero** improvement - a clean, unconfounded negative result in the one scenario designed to isolate coverage's effect.
- The DUPLICATE rate (the more decision-relevant number, since a BORDERLINE pair isn't a clear failure) barely moved: 41% (WP-032) → 40% (WP-034).

**What appears to be missing, based on this evidence**: soft, information-only prompt guidance ("avoid this if a genuine alternative exists") does not reliably override the model's tendency to select the single most salient, most clearly evidence-supported fact in a category - particularly in categories where the evidence has one dominant fact and the alternatives are comparatively weaker or less directly stated (exactly the categories that duplicated here). The target-planning prompt already asks the model to avoid rewording/reversal/same-structure duplicates *within* one batched call (WP-025's original guidance) and that guidance works when the model is comparing options it is about to generate together; extending the same soft framing to compare against *already-generated* text across separate, independent calls did not transfer with the same effectiveness.

A stronger mechanism - e.g. deterministically excluding or de-weighting already-tested evidence *before* it reaches the planning prompt, rather than only informing an otherwise-unconstrained retrieval/prompt - might work better, since it would remove the dominant fact from the model's view entirely rather than asking it to voluntarily avoid something still prominently presented. This is explicitly out of WP-034's own scope: section 13 forbids redesigning retrieval, and section 6 forbids turning coverage into a validator/rejection mechanism. This is reported as a genuine, disclosed limitation of what this WP's own scope allowed it to attempt, not a design flaw in what was built.

## 12. Limitations

- Coverage extraction's "tested concept" signal is only as good as an existing question's correct-answer *text* - two questions testing the same underlying fact with differently-worded correct answers (e.g. "SCA" vs. "Superior Cerebellar Artery" vs. "the superior cerebellar artery") would not be recognized as the same concept by this heuristic. This did not occur in the observed data (correct-answer wording was consistent within each category) but is a known, undocumented-until-now edge case.
- Relationship-type coverage inherits WP-030's own keyword-coverage limitation (~40-50% of real text matches a known keyword) - a question whose text uses an unlisted verb form contributes no relationship-type signal to coverage at all.
- This WP did not attempt to distinguish whether the marginal diversity difference (41%→47%) is attributable to coverage-awareness or to ordinary stochasticity - the sample size (15-17 pairs) is too small to separate the two, and this is stated explicitly rather than claimed as a proven improvement.

## 13. Confirmations

- No prompt file other than `question_target_planning.txt` was modified.
- No validator was modified.
- No retrieval/chunking/TF-IDF logic was modified.
- No relationship/competitor logic was modified (only a non-behavioral refactor extracting a reusable helper from `extract_relationship()`).
- `CategoryQuestionSetRequest`/`Response` (WP-033) were not modified - no new field was added.
- Coverage never became a validator or retry trigger - planning still makes exactly one LLM call.
- Full regression suite passes: **1206/1206**.
- Acceptance run performed exactly once, no reruns, no tuning after seeing results.

## 14. Files Created/Modified

**Created:**
- `src/exam_generator/models/coverage.py`
- `src/exam_generator/planning/coverage.py`
- `tests/unit/test_coverage.py`

**Modified:**
- `src/exam_generator/models/__init__.py` (export `CategoryCoverage`)
- `src/exam_generator/generation/relationship.py` (factored out `classify_relationship_type()`)
- `src/exam_generator/generation/__init__.py` (export `classify_relationship_type`)
- `src/exam_generator/planning/__init__.py` (export `extract_category_coverage`)
- `src/exam_generator/planning/planner.py` (`plan_targets()` gained `coverage` parameter)
- `src/exam_generator/prompts/context.py` (`QuestionTargetPlanningPromptContext` gained `coverage` field)
- `src/exam_generator/prompts/formatting.py` (new `format_category_coverage()`)
- `src/exam_generator/prompts/__init__.py` (export `format_category_coverage`)
- `src/exam_generator/category_generation/service.py` (both services extract and thread coverage)
- `prompts/generation/question_target_planning.txt` (new "Already-tested knowledge" section)
- `tests/unit/test_planning.py`, `tests/unit/test_prompts.py`, `tests/unit/test_category_generation.py`, `tests/unit/test_category_question_set.py` (new/updated tests)
- `docs/ARCHITECTURE.md` (new "Coverage-Aware Target Planning" section)
- `docs/PROJECT_STATUS.md` (Tests count, new Live Evaluation Baseline section, Next WP Context updated)
- `evaluation/live_outputs/README.md` (new rows)

---

WP-034 complete.

Tests:
1206 passed, 0 failed

Acceptance run:
33/40 accepted, 7 failed (all QuestionAttemptsExhaustedError) via CategoryQuestionSetService with coverage-aware planning; diversity 7/15 (47%) DISTINCT vs. WP-032's 7/17 (41%) baseline - marginal, not statistically meaningful improvement (see section 11)

Completion report:
implementation/WP-034_COMPLETION_REPORT.md

Waiting for architect review.
