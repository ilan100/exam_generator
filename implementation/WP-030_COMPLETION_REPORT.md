# WP-030 Completion Report — Relationship-Constrained Generation

## 1. Implementation Summary

WP-029 (design-only) analyzed why WP-028's blueprint failed to improve generation quality and recommended moving toward application-controlled, relationship-driven construction. WP-030 is Phase 1 of that migration: introduce the tested relationship as a first-class, deterministically-derived application concept, entirely separate from `QuestionTarget` (WHAT to test) and from generation policy (HOW to construct the question, i.e. distractor strategy - explicitly deferred to later phases per section 7).

The implementation is exactly as scoped: a pure, deterministic, zero-LLM-call relationship classifier runs in Python before the existing single generation call; its output is threaded into the generation prompt as one new variable. No validator, retrieval, orchestration, diversity planner, or `QuestionTarget` field was touched.

**The live acceptance run did not meet the WP's own stated primary success criterion** - grounding rejections caused by "another answer also supported" rose rather than fell. Secondary metrics (MCQ, quality) improved substantially. This report documents both results exactly as measured, per the project's standing evidence-based-decision discipline.

## 2. Relationship Model

`QuestionRelationship` (new, `src/exam_generator/models/relationship.py`):

```python
class QuestionRelationship(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    relationship_type: NonBlankStr   # e.g. "SUPPLIES" - deliberately NOT a closed enum
    statement: NonBlankStr           # verbatim QuestionTarget.factual_focus, never rewritten
```

`relationship_type` is a plain string, not a Python enum, per WP-030 section 2's explicit "do not hard-code these values... the representation should be extensible" instruction - the vocabulary can grow by adding one entry to a keyword table (section 3 below), never by a schema/model change.

## 3. Deterministic Relationship Extraction

`extract_relationship()` (new, `src/exam_generator/generation/relationship.py`) is a pure function: `QuestionTarget -> QuestionRelationship`. It scans `target.factual_focus` (case-insensitive substring match) against an ordered, explicitly-extensible keyword table covering ten relationship types named in the WP (`SUPPLIES`, `INNERVATES`, `CONNECTS`, `CONTAINS`, `PROJECTS_TO`, `LOCATED_IN`, `DEVELOPS_INTO`, `RECEIVES_INPUT_FROM`, `DRAINS_INTO`, `SURROUNDS`), each with Hebrew and English keyword variants. No match falls back to `UNSPECIFIED` - never a guess.

**Zero LLM calls** - per section 4's explicit "application logic owns this responsibility" requirement, this runs entirely before the generation call. Verified directly by test (`test_relationship_extraction_adds_no_llm_call`, `test_extract_relationship_makes_no_llm_or_network_call`).

**Honest coverage limitation, measured directly from live data**: only 17 of 40 planned targets in the full acceptance run (42.5%) actually matched a known keyword; the remaining 23 classified as `UNSPECIFIED`. This is reported as a real, current limitation of the heuristic - not a defect requiring a fix within this WP's scope (no prompt-tuning-after-results occurred).

## 4. QuestionTarget Changes

**None.** `QuestionTarget` (`src/exam_generator/models/target.py`) is byte-for-byte unchanged - still exactly `target_id`, `category`, `topic`, `factual_focus`, `supporting_evidence_chunk_ids`. WP-030 section 3 required extending it "only where necessary"; it turned out not to be necessary at all, since the relationship is a pure function of the existing `factual_focus` and can be computed transiently. Verified directly by test (`test_question_target_gained_no_new_field`).

The relationship is instead threaded through `GenerationPromptContext` (`src/exam_generator/prompts/context.py`), which gained a new required `relationship: QuestionRelationship` field, with a constructor-time invariant check that `relationship.statement == target.factual_focus` (the relationship must be extracted from this exact target, never substituted or reused across targets - mirroring the existing `target.category == category` check already present since WP-025).

## 5. Prompt Changes

`prompts/generation/question.txt` gained one new small section, "Tested relationship," placed right after "Assigned question target" and one new template variable, `{relationship_type}`, rendered as `Tested relationship type: {relationship_type}` immediately before the existing target block. The new prose:

- Explains the label is a coarse, deterministically-derived classification (or `UNSPECIFIED`), not a substitute for reading `factual_focus` itself, and that `UNSPECIFIED` relaxes nothing.
- Reinforces the existing (WP-027) "every distractor must be false for the exact question asked" rule with an explicit "does this specific answer satisfy the stated relationship" framing, rather than "does this answer merely look plausible."

Per section 5's explicit "keep prompt changes minimal" instruction, no other prompt content was rewritten - WP-026/027's existing enumeration/hierarchy/distractor-correctness guidance and WP-028's (now-frozen) blueprint section remain completely untouched.

## 6. Files Created/Modified

**Created:**
- `src/exam_generator/models/relationship.py`, `src/exam_generator/generation/relationship.py`
- `tests/unit/test_relationship.py`
- `implementation/WP-030_COMPLETION_REPORT.md` (this file)
- `evaluation/live_outputs/wp030_focused_eval_results.json`, `wp030_acceptance_exam.json`, `wp030_acceptance_audit.json`, `wp030_acceptance_targets.json`

**Modified:**
- `src/exam_generator/models/__init__.py`, `src/exam_generator/generation/__init__.py` - new exports
- `src/exam_generator/generation/generator.py` - calls `extract_relationship()`, threads the result into `GenerationPromptContext`
- `src/exam_generator/prompts/context.py` - `GenerationPromptContext` gained required `relationship` field plus an invariant check
- `prompts/generation/question.txt` - new "Tested relationship" section, new `{relationship_type}` variable
- `tests/unit/test_generation.py` - 3 new tests; `_generated_response()` fixtures untouched (relationship is generator-internal, not part of the LLM-facing response contract)
- `tests/unit/test_prompts.py` - 7 direct `GenerationPromptContext(...)` constructions updated to supply `relationship`; 6 new prompt-content tests
- `docs/ARCHITECTURE.md`, `docs/PROJECT_STATUS.md` - new WP-030 sections

**No changes:** any of the five validators, `src/exam_generator/planning/*`, `src/exam_generator/orchestration/*`, `src/exam_generator/retrieval/*`, `src/exam_generator/production/*`, `schemas/*.schema.json` (confirmed byte-identical).

## 7. Tests

- **`tests/unit/test_relationship.py`** (new, 32 tests): keyword classification for all 10 relationship types (Hebrew + English variants), case-insensitivity, `UNSPECIFIED` fallback, determinism (same input → same output twice), purity (target never mutated), `statement` matches `factual_focus` exactly, no-LLM-call signature check, `QuestionRelationship` immutability/unknown-field-rejection/blank-field-rejection, `QuestionTarget` gained no new field, existing `QuestionTarget` construction still works unchanged.
- **`tests/unit/test_generation.py`** (+3): relationship type threaded into the actual sent prompt content (`SUPPLIES` case and `UNSPECIFIED` case), generation still makes exactly one LLM call.
- **`tests/unit/test_prompts.py`** (+6): the `relationship_type` template variable is required; a classified type renders correctly; `UNSPECIFIED` renders honestly (not hidden or substituted); the "not a substitute for factual focus" / "does not relax any requirement" wording is present; the "satisfy the relationship vs. look plausible" framing is present; the new section explicitly ties back to the existing WP-027 distractor rule by name.

## 8. Full Regression Result

**1111 / 1111 passing** (up from the 1070 baseline entering WP-030; +41 net), zero network access, no `OPENAI_API_KEY` in the offline test shell. `scripts/generate_schemas.py` re-run: all three schema files byte-identical - relationship models are never schema-exported.

## 9. Focused Live Evaluation

6 candidates (2 per category) across `מערכת העצבים ההיקפית`, `אספקת דם`, `תאי מערכת העצבים` - the same categories and methodology as WP-028's own focused evaluation, for direct comparability.

**Result: 6/6 accepted, avg 1.00 attempts** - a clean sweep on the first attempt for every target, including a fresh PNS-divisions target (the category that has proven hardest across WP-025A, WP-026, WP-027, and WP-028's own focused eval). This is a genuine improvement over WP-028's 5/6 (avg 1.67) on the identical methodology. All 6 accepted questions were manually inspected and show no obvious second-correct-answer risk.

## 10. Full Acceptance Run

- **Planned: 40 | Accepted: 32 | Failed: 8 | Status: PARTIAL**
- **Runtime: ~29.7 minutes** (1781.1 seconds)
- **Exit code: 0**; both `exam.json` (32 questions) and `exam_audit.json` written successfully on the first attempt (no crash this time).

### Every failed planned question and reason

| Position | Category | Mode |
|---|---|---|
| 1 | התעלה השדרתית ותכולתה | STYLE_SIMILAR |
| 10 | מיפוי ודימות מוחי | INDEPENDENT |
| 13 | המערכת הלימבית | STYLE_SIMILAR |
| 19 | גזע המוח | STYLE_SIMILAR |
| 20 | גזע המוח | INDEPENDENT |
| 27 | מערכת העצבים ההיקפית | STYLE_SIMILAR |
| 33 | טופוגרפיה של ההמיספרות | STYLE_SIMILAR |
| 40 | מבוא | INDEPENDENT |

All 8 are `QuestionAttemptsExhaustedError`. **`גזע המוח` failed both of its planned positions** - zero accepted for that category this run. **Generation-contract failures observed: 0.**

### Accepted-attempt distribution

**25 accepted on attempt 1, 3 on attempt 2, 4 on attempt 3** (43 accepted-path attempts, avg **1.34**/accepted question) plus 24 attempts across the 8 failed questions (3 each) = **67 total candidate attempts**.

### Validator rejection counts (all rejected attempts)

mcq: 9, quality: 3, grounding: 24, category: 8, textbook: 0.

### Grounding rejection breakdown (the WP's own primary metric)

**Designated answer unsupported: 0. Another answer also supported: 24. Other grounding reasons: 0.**

## 11. Comparison with WP-027 (and WP-028)

| Metric | WP-027 | WP-028 | WP-030 | Direction (vs. WP-027) |
|---|---|---|---|---|
| Accepted / planned | 34/40 | 31/40 | 32/40 | worse |
| Accepted on attempt 1/2/3 | 27/5/2 | 23/5/3 | 25/3/4 | worse |
| Avg attempts per accepted | 1.26 | 1.35 | 1.34 | worse |
| Total candidate attempts | 61 | 69 | 67 | worse |
| Grounding rejections (total) | 12 | 16 | 24 | **much worse** |
| Grounding: "another also supported" | 12 | 14 | **24** | **worse - the WP's own primary success metric, and the worst of the three runs** |
| MCQ rejections | 8 | 18 | **9** | roughly flat - a real recovery from WP-028's regression |
| Quality rejections | 10 | 15 | **3** | **better than both prior runs** |
| Category rejections | 3 | 6 | 8 | worse |
| Textbook rejections | 6 | 2 | 0 | better (small-sample; likely variance) |
| False acceptance: CONFIRMED | 0 | 0 | 0 | held |
| False acceptance: POSSIBLE | 1 | 2 | 2 | comparable (single-run) |
| Diversity | 14/14 DISTINCT | 12/12 DISTINCT | 13/13 DISTINCT | held (all 100%) |

**WP-030's own explicitly-stated primary success metric did not improve - it moved sharply in the wrong direction (24 vs. 12), the worst result on this specific metric across all three most recent full runs.** At the same time, MCQ and quality rejections - which had regressed badly under WP-028 - both recovered, with quality reaching its best level yet. This is a genuinely mixed result, reported without minimizing either half.

## 12. Investigation: Why Did Grounding Rejections Rise?

Performed as part of honest reporting, not as a route to tuning the run's own result.

- **Relationship-classifier coverage this run: 17/40 targets (42.5%) matched a known keyword** (`CONTAINS`: 10, `DEVELOPS_INTO`: 4, `SUPPLIES`/`DRAINS_INTO`/`LOCATED_IN`: 1 each); 23/40 classified `UNSPECIFIED`.
- Of the 13 distinct planned positions that had at least one "another also supported" grounding rejection, only 4 had a classified (`CONTAINS`) target; the other 9 were `UNSPECIFIED`. The failure rate among classified targets (4/17 ≈ 24% of classified positions had a failure) was not meaningfully higher than among unclassified targets (9/23 ≈ 39% - actually somewhat higher for `UNSPECIFIED`). **This does not support the hypothesis that the relationship-type framing itself is causing the regression** - if it were, classified targets should fail distinctly more often, and they do not.
- The more likely explanation, consistent with this project's own repeated observations across WP-025 through WP-028's live runs, is **ordinary run-to-run variance in which specific targets the planner happened to select** - several classically enumeration/hierarchy-shaped categories (`מערכת העצבים ההיקפית`, `המערכת הלימבית`, `אמבריולוגיה`'s neural-tube flexures) were planned again this run, and this shape remains the project's known hardest failure class regardless of which WP is active.
- A plausible secondary hypothesis, offered honestly as a hypothesis and not asserted as proven from a single run: improving structural/wording clarity (reflected in the large MCQ/quality improvement) may make the model's distractors *individually* more confident and complete, which could paradoxically make grounding's independent per-option check *more* likely to find genuine secondary support for one of them - i.e. a possible clarity/uniqueness trade-off. This is not established here and would require a controlled, larger-sample comparison to confirm or reject.

## 13. False-Acceptance Human Review

All 32 accepted questions were individually inspected against their cited grounding evidence.

**Totals: 30 CLEAR_SINGLE_ANSWER, 2 POSSIBLE_SECOND_CORRECT_ANSWER, 0 CONFIRMED_SECOND_CORRECT_ANSWER, 0 INSUFFICIENT_EVIDENCE_TO_JUDGE.**

- Question #11 (`המערכת הלימבית`, "which structure is the evolutionary basis for the limbic system") designates "Rhinencephalon" correct against a distractor "the olfactory system" (`המערכת האולפקטורית`) - in real neuroanatomy, Rhinencephalon is literally defined as encompassing olfactory-system structures, a genuine terminology-overlap subtlety in the same spirit as WP-027's own Diffusion-Imaging/MRI case.
- **Question #26 (`אמבריולוגיה`, "which fold occurs during the fifth week of neural tube development") is the more concerning finding.** The assigned target's own `factual_focus` reads: *"Neural tube folds are processes occurring during the fifth week of embryonic development, and include the formation of folds such as the cervical fold, pontine fold, and cephalic fold"* - explicitly grouping **all three** folds under the shared "fifth week" timeframe. The accepted question asks "which fold occurs during the fifth week" and designates only the cervical fold correct, with pontine and cephalic marked as distractors. This is a direct structural recurrence of the original WP-025A/WP-026 enumeration-ambiguity shape: a target names multiple members sharing one relationship, and the accepted question tests bare membership in that relationship rather than a further-narrowing property. The grounding call's own cited reasoning ("the cervical flexure is specifically mentioned as occurring during the fifth week... the other options do not meet the criteria") may reflect more specific timing information in the full underlying evidence than the target's own coarser summary preserved - this cannot be fully resolved from the audit data alone, so it is reported as `POSSIBLE` rather than `CONFIRMED`, but it is flagged prominently here as the single most concerning finding in this review, worth a follow-up diagnostic rather than being dismissed as ordinary noise.

## 14. Per-Category Diversity Review

13 of 20 categories had both planned questions accepted (`גזע המוח` had zero; `התעלה השדרתית ותכולתה`, `מיפוי ודימות מוחי`, `המערכת הלימבית`, `מערכת העצבים ההיקפית`, `טופוגרפיה של ההמיספרות`, `מבוא` each had one):

| Category | Question 1 | Question 2 | Assessment |
|---|---|---|---|
| לוקליזציה פונקציונלית | M1 location | V1 simple-cell response | DISTINCT |
| חומר לבן | Projection fibers | Internal Medullary Lamina | DISTINCT |
| עצבים קרניאליים | Olfactory nerve | Optic nerve | DISTINCT |
| היסטולוגיה | Molecular layer synapses | Nervous-tissue excitability | DISTINCT |
| אספקת דם | SCA | Anterior spinal artery | DISTINCT |
| קרומים וסינוסים דוראליים | Superior sagittal sinus drainage | Dura periosteum layer | DISTINCT |
| מסילות עצביות | Spinothalamic tract | Medial lemniscus tract | DISTINCT |
| גרעיני הבסיס | Central role (executes movement) | Direct pathway (specific mechanism) | DISTINCT |
| המוח הקטן | Function (coordination/balance) | Structure (hemispheres/lobes/matter) | DISTINCT |
| דיאנצפלון | Thalamus (central structure) | Hypothalamus (regulation) | DISTINCT |
| אמבריולוגיה | Gastrulation | Neural tube flexures (week 5) | DISTINCT |
| חדרי המוח | 3rd-4th ventricle connection | Septum pellucidum | DISTINCT |
| תאי מערכת העצבים | Microglia | Ependymal cells | DISTINCT |

**Totals: 13 / 13 DISTINCT (100%), 0 BORDERLINE, 0 DUPLICATE/NEAR-DUPLICATE.**

## 15. Remaining Limitations

- **The relationship classifier's coverage is low (42.5% this run)** - most targets fall back to `UNSPECIFIED`, meaning the new mechanism had no effect on the majority of this run's candidates at all. Extending the keyword table (e.g. adding "מחולק ל"/"divides into" as a `CONTAINS` trigger, which the recurring PNS-divisions target actually uses and which the current table misses) is a plausible, low-risk future improvement, but was **not made** here, per the "no tuning after results" discipline.
- **The primary hypothesis behind Phase 1 - that naming the relationship explicitly would reduce the dominant grounding failure class - is not supported by this run's data.** The secondary finding (MCQ/quality improvement) is real and worth preserving, but the central problem WP-029's proposal set out to solve remains unsolved after Phase 1 alone.
- Question #26 (section 13) deserves a focused, dedicated look before Phase 2 proceeds - it is a clean, reproducible instance of the exact failure shape this whole multi-WP effort has been chasing since WP-025A, occurring despite five WPs of guidance specifically aimed at it.
- This is a single live acceptance run (n=1) and a small focused-evaluation sample (n=6); the directional signals reported here (grounding worse, MCQ/quality better) are real single-run measurements, not statistically powered claims.

## 16. Open Question for the Architect

Per WP-029's own migration plan, Phase 2 (evidence-anchored distractor construction) was designed to follow Phase 1 directly. Given Phase 1's mixed result - a clear MCQ/quality improvement alongside a clear regression on the metric that actually matters most for correctness - **should Phase 2 proceed as originally scoped, or does this result warrant a focused diagnostic (in the spirit of WP-025A/WP-026's own false-acceptance diagnostics) specifically on why grounding rejections rose, before committing to the next phase of the migration?** This report does not decide that question; it provides the data needed to decide it.

## 17. Confirmations

- **No validator was added or modified**: `GroundingValidator`/`MCQValidator`/`CategoryValidator`/`QualityValidator`/`TextbookValidator` are byte-for-byte unchanged from WP-027.
- **No diversity/planning change**: `QuestionTargetPlanner` and `QuestionTarget` are untouched.
- **No pipeline/orchestration change**, **no retry/attempt-budget change**, **no additional LLM calls** (confirmed both by design and by the `test_relationship_extraction_adds_no_llm_call` test).
- **No embeddings/vector DB introduced.**
- **No post-run tuning performed**: the prompt/code as they existed when the acceptance run was launched are exactly as they exist now.

---

WP-030 complete.
Tests: 1111 passed
Acceptance run: PARTIAL, 32/40 accepted, 8 failed (grounding "another-also-supported" rejections: 24, up from WP-027's 12 - primary metric regressed; MCQ/quality rejections improved substantially; false acceptance held at 0 confirmed / 2 possible, one notable enumeration-ambiguity recurrence flagged)
Completion report:
implementation/WP-030_COMPLETION_REPORT.md

Wait for architect review.
