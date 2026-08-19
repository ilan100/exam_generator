# WP-063 Completion Report — First Post-WP-060 Deterministic Target-Planning Category Pilot

## 1. Objective

Run the first controlled, single-category, post-WP-060 pilot of deterministic concept-inventory target planning: select exactly one additional canonical category, construct its inventory, add it to production, run a controlled generation experiment against the real OpenAI API, compare with the pre-existing baseline, and report - explicitly not a rollout decision, per WP-063's own repeated instruction.

## 2. Selected Category

`המערכת הלימבית` (the Limbic System).

## 3. Selection Rationale

Chosen from the three categories WP-060 directly spot-checked (`עצבים קרניאליים`, `המערכת הלימבית`, `מערכת העצבים ההיקפית`) via a fresh, direct 9-criterion re-evaluation - full inventory content inspection (not size alone) found `עצבים קרניאליים` carries real numbering-fragment junk entries and `מערכת העצבים ההיקפית` has directly-confirmed category leakage (hippocampal terms + non-anatomical noise), while `המערכת הלימבית`'s 36-concept inventory was the cleanest of the three. The one disclosed trade-off (lower historical question volume: 7 vs. 26/13) was accepted in favor of a clean, low-confound experimental read. Full detail: `implementation/WP-063_CATEGORY_SELECTION.md`.

## 4. Implementation Changes

`src/exam_generator/planning/concept_inventory.py`: `PILOT_CATEGORIES` extended from three to four categories, adding `"המערכת הלימבית"`. Docstring/comment updated to record the addition and its rationale. No other production code was touched - `extract_concept_inventory()`, `refine_concept_inventory()`, `QuestionTargetPlanner`, and every deterministic anchoring/role/enumeration mechanism are reused byte-for-byte, per WP-063 section 5's explicit "do not redesign" instruction.

## 5. Inventory Result

36 concepts, deterministic and reproducible (verified directly - two calls against identical evidence produce an identical result), genuine `chunk_id` provenance preserved throughout. One real, previously-undetected defect was found via the live experiment, not the offline inspection: the first concept in inventory order, `Limbic`, is a mis-extracted chapter-title fragment ("The Limbic Lobe" / "האונה הלימבית"), not a genuine sub-structure - see `implementation/WP-063_EXPERIMENT_REPORT.md` section 5 for the full diagnosis.

## 6. Generation Experiment

4 sequential questions per condition (BASELINE: pre-WP-063 LLM-based planning; PILOT: new deterministic planning), same category, same corpus, same producer/validator configuration, same `GenerationMode.INDEPENDENT`, one uninterrupted live session against the real OpenAI API, no reruns, no manual repair, no prompt modification during the experiment. Full detail and per-round data: `implementation/WP-063_EXPERIMENT_REPORT.md`; raw records: `evaluation/live_outputs/wp063_experiment_records.json`.

## 7. Metrics

| Metric | Baseline | Pilot |
|---|---:|---:|
| Rounds accepted | 2/4 (50%) | 0/4 (0%) |
| Target-planning LLM calls | 4 | 0 |
| Total production attempts | 9 | 12 |
| Duplicate-replacement attempts | 0 | 0 |
| Strong target alignment (accepted rounds) | 1/2 | 0/0 |

## 8. Baseline Comparison

The pilot condition performed **worse** than baseline on every acceptance-related metric: 0% vs. 50% acceptance, and more total production attempts (12 vs. 9) despite zero target-planning LLM calls, because every one of its 4 rounds was assigned the same defective target (`Limbic`) and exhausted its full 3-attempt budget identically each time - coverage-based target exclusion (which correctly excludes concepts from *accepted* questions, per WP-034's existing design) never had a chance to exclude it, since it was never accepted.

## 9. Target-Alignment Findings

Baseline: 1 strong-alignment question (Hippocampus/memory-learning, property-based), 1 weak-alignment-but-valid question (a generic classification-membership target that happened to have non-overlapping distractors). Pilot: all 4 rounds are the "wrong target" case in WP-063's own taxonomy (section 19) - `Limbic` names the category/section itself, not a testable member of it, so no attempt could ever produce a coherent single-best-answer question around it.

## 10. Failure Taxonomy

See `implementation/WP-063_EXPERIMENT_REPORT.md` section 17 for the full table. In summary: baseline's 2 failed rounds were genuine grounding-driven classification-ambiguity rejections (the same known failure family this project has documented since WP-048/052); pilot's 12 failed attempts were driven by the single invalid target, including one attempt caught pre-emptively by the existing WP-046 distractor-containment check (`'Limbic'` vs. `'Limbic System'`) - direct evidence the existing safety checks correctly recognized the target as malformed even though no mechanism exists to recover from it mid-round.

## 11. Language-Policy Observations

The deterministic language-compliance check (WP-058/062) behaved correctly for the pilot's one named-entity target (`Limbic`, English form used consistently, zero language-driven rejections). The baseline condition's two accepted questions provided the first live, concrete confirmation of WP-062's own disclosed limitation for non-named-entity targets: round 1's answers mixed Hebrew renderings of terms with established English forms (`היפוקמפוס`, `אמיגדלה`, `פורניקס`) with one English term (`olfactory bulb`) in the same question; round 2's answers were entirely Hebrew despite every term having an established English form. Neither violates any currently-implemented check (both are within WP-062's explicitly documented, non-named-entity-target scope boundary) - not a new defect, the first real occurrence of an already-known, already-disclosed gap.

## 12. Cost Observations

Pilot saved 4 target-planning LLM calls relative to baseline but consumed 3 more total production attempts (12 vs. 9) while producing zero accepted questions - a net cost increase with a negative acceptance outcome, entirely attributable to the single defective target rather than to the deterministic mechanism's own architecture.

## 13. Regression Results

`.venv/bin/python -m pytest -q` → **1464 passed, 0 failed** (1455 pre-existing + 9 new: 1 in `tests/unit/test_concept_inventory.py` updating the pilot-category-count assertion to four, 12 in `tests/unit/test_planning.py` covering the new category's resolution/deterministic-path/provenance/reproducibility/coverage-exclusion behavior and confirming the three existing pilot categories and one non-selected category remain unaffected).

## 14. Files Changed

Production: `src/exam_generator/planning/concept_inventory.py` (`PILOT_CATEGORIES` extended to four categories). Tests: `tests/unit/test_concept_inventory.py`, `tests/unit/test_planning.py`. New artifacts: `implementation/WP-063_CATEGORY_SELECTION.md`, `implementation/WP-063_EXPERIMENT_REPORT.md`, `implementation/WP-063_COMPLETION_REPORT.md`, `implementation/wp063_experiment.py` (prototype-only, genuinely required to run the live controlled experiment - not created merely because prior WPs used a similar script pattern), `evaluation/live_outputs/wp063_experiment_records.json`. No file outside this scope was modified by this WP - confirmed via `git status --short` (all other pending changes pre-date this WP, from WP-058 through WP-062).

## 15. Architectural Interpretation

This experiment is a valid, evidence-grounded **negative result for `המערכת הלימבית` as currently configured** (WP-063 section 34 explicitly anticipates and permits this outcome) - not a failure of the deterministic mechanism itself, and not evidence against the mechanism's general viability. The mechanism performed exactly as designed (zero LLM calls, deterministic, reproducible, correct provenance); the failure is entirely attributable to one specific, precisely-diagnosed inventory-extraction defect that WP-060's own offline feasibility spot-check did not surface, because it only checked the top-ranked chunk's overall structural shape, not every individual extracted concept's validity. This directly confirms WP-060's own section 11 warning in concrete form: extractability is necessary but not sufficient, and a new category genuinely needs the same kind of per-concept, real-evidence validation the three original pilot categories received - a single clean-looking spot-check is not a substitute for it. The production configuration change (`PILOT_CATEGORIES` now includes `המערכת הלימבית`) was left in place rather than reverted, consistent with this project's own established precedent (WP-036's original three pilot categories had real, undiscovered target-drift defects at their own initial rollout and were fixed incrementally over roughly a dozen subsequent WPs, never reverted out of the pilot set) - but this means the category is **not currently production-ready**: as configured today, requesting a question for `המערכת הלימבית` will very likely fail (the `Limbic` concept sorts first in deterministic order and will be re-selected every round until it is fixed or excluded).

## 16. Recommendation for Next WP

**Immediate, narrowly-scoped priority**: fix or exclude the `Limbic` title-fragment concept before this category is used in production. Two options, both within the existing architecture (no new subsystem required): (a) extend `refine_concept_inventory()`'s WP-037 category-self-restatement exclusion to also recognize title-line fragments more generally (not only exact/near matches of the category's own literal Hebrew text), or (b) a narrower, targeted exclusion specific to this one concept. Either would need its own fresh live verification round before being trusted, per this project's own established discipline. Only after such a fix is verified should a second controlled 4-question pilot for this category be considered to confirm the fix and gather further target-alignment evidence. **Do not select a second new category for a WP-063-style pilot until this one is resolved** - repeating the same pilot pattern on a fresh category would not address the now-demonstrated risk that a clean-looking offline spot-check can still miss a category-blocking defect. This finding is also relevant to WP-060's own broader 16-category feasibility list: any future category pilot should budget for exactly this kind of live-verification step, not assume offline extractability implies production readiness.

---

## Terminal Summary

```text
WP-063 complete.

Objective:
Run the first controlled post-WP-060 deterministic
target-planning category pilot.

Selected category:
המערכת הלימבית (the Limbic System)

Selection rationale:
Cleanest of three WP-060-spot-checked candidates on direct
full-inventory inspection (no numbering-fragment junk, no confirmed
category leakage); lower historical question volume accepted as a
disclosed trade-off for a clean, low-confound experimental read.

Category selection report:
implementation/WP-063_CATEGORY_SELECTION.md

Deterministic inventory:
Built successfully via the existing, unmodified refine_concept_inventory();
deterministic and reproducible; genuine chunk-id provenance preserved.

Inventory size:
36 concepts

Inventory quality:
Mostly clean; one real defect found via the live experiment - a
mis-extracted chapter-title fragment ("Limbic") sorts first in
deterministic order and is not a genuine testable structure.

Baseline:
Pre-existing LLM-based free-text planning, unmodified, 4 rounds.

Pilot:
New deterministic concept-inventory planning (production default,
post-WP-063), 4 rounds.

Sample size:
4 questions per condition (8 total), mirroring WP-036's own precedent.

LLM calls:
Target planning: baseline 4, pilot 0. Generation/validation calls
tracked via total production attempts instead (see below).

Retries:
Baseline 9 total production attempts across 4 rounds; pilot 12 total
production attempts across 4 rounds (every round exhausted 3/3); zero
duplicate-replacement attempts in either condition.

Target alignment:
Baseline: 1 strong, 1 weak-but-valid (of 2 accepted). Pilot: 0/4 -
every round assigned the same invalid target ("wrong target" case).

Target drift:
None observed - pilot's failure is a pre-generation target-validity
defect, not mid-generation drift.

Generation acceptance:
Baseline 2/4 (50%). Pilot 0/4 (0%).

Grounding:
Reliable and correct in both conditions - every grounding-driven
rejection was independently verified accurate against the evidence.

Language-policy observations:
Pilot's one named-entity target handled correctly by the existing
deterministic check. Baseline's two accepted questions provided the
first live confirmation of WP-062's own disclosed non-named-entity-target
limitation (inconsistent Hebrew/English terminology, not caught by any
current validator).

Cost:
Pilot saved 4 LLM calls on target planning but used 3 more total
production attempts than baseline while accepting zero questions - a
net cost increase with a negative outcome, attributable to the one
defective target, not to the mechanism's architecture.

Failure taxonomy:
Baseline: genuine classification-ambiguity grounding rejections
(known failure family since WP-048/052). Pilot: dominated by one
invalid target; one attempt caught pre-emptively by the existing
WP-046 distractor-containment check.

Regression:
1464 passed, 0 failed (1455 pre-existing + 9 new)

IDENTITY_FIRST mappings:
UNCHANGED

Other categories:
UNCHANGED (existing three pilot categories and all non-selected
categories directly verified unaffected)

Retrieval:
UNCHANGED

Source authority:
UNCHANGED

Experiment report:
implementation/WP-063_EXPERIMENT_REPORT.md

Completion report:
implementation/WP-063_COMPLETION_REPORT.md

Architectural conclusion:
Valid negative result for this category as currently configured, not a
failure of the deterministic mechanism itself. Root cause precisely
diagnosed (a single mis-extracted title-fragment concept). Production
configuration left as-is (category added), consistent with this
project's own precedent for the original three pilot categories, but
the category is NOT yet production-ready - a narrow, targeted fix is
recommended as the immediate next step, before any second-category
pilot is considered.

Waiting for architect review.
```
