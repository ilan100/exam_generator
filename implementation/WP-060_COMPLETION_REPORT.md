# WP-060 Completion Report — Cross-Category Target Inventory Feasibility and Evidence-Gap Analysis

## 1. Objective

Investigate whether the 17 canonical categories that currently lack a deterministic target inventory (WP-059's own exposed evidence-coverage bottleneck) can obtain one, and determine the smallest safe next step for collecting target-level strategy evidence from them. **Feasibility/architecture analysis only - no production target-planning change authorized or made, zero LLM/API calls.**

## 2. Files Inspected

`src/exam_generator/planning/planner.py` (`QuestionTargetPlanner`), `src/exam_generator/planning/concept_inventory.py` (`extract_concept_inventory`, `PILOT_CATEGORIES`), `src/exam_generator/planning/concept_anchor.py` (`refine_concept_inventory`), `src/exam_generator/historical/repository.py` (`HistoricalQuestionRepository.canonical_categories`), `src/exam_generator/retrieval/` (category resolution + retrieval), `docs/ARCHITECTURE.md`'s WP-034/036/037/039 sections, `evaluation/live_outputs/wp023-034_acceptance_exam.json` (pre-WP-036 full-exam records).

## 3. Canonical Category Inventory

20 total, confirmed directly via `HistoricalQuestionRepository.canonical_categories` (the authoritative source `docs/ARCHITECTURE.md` itself names) - identical to WP-059's own count, **no discrepancy found**. Full list: see `implementation/WP-060_CATEGORY_TARGET_INVENTORY_FEASIBILITY_REPORT.md` section 4.

## 4. Existing Target-Planning Mechanisms

Two mechanisms, both documented in full (inputs/outputs/determinism/source-authority/validation/failure-behavior) in the feasibility report section 5: (1) deterministic concept-inventory planning (`_plan_targets_from_concept_inventory()`, three pilot categories only), (2) LLM free-text planning (every other category). **Critical finding**: `extract_concept_inventory()`/`refine_concept_inventory()` are themselves category-agnostic - they accept only `source_evidence`, never a category identifier. `PILOT_CATEGORIES` (`planning/concept_inventory.py`, a plain `frozenset`) is the *only* place the three-category scope is enforced - confirmed by direct code reading, not assumed.

## 5. Pilot-Category Comparison

See feasibility report section 6. The architectural property that made deterministic planning possible for the three pilot categories is a **document-format artifact** (English-language named entities land on standalone text lines during this corpus's PDF extraction), not a category-content property - directly relevant to why generalization is plausible.

## 6. 17-Category Feasibility Results

`refine_concept_inventory()` (real, unmodified, zero code change) was run directly against real retrieved evidence for all 17 non-pilot categories. **16 of 17 produced substantial (9-54, median ~28), plausible, real-entity-containing inventories**; a qualitative spot-check of 5 representative categories' own top-ranked retrieved chunks directly confirmed the same list-structured evidence shape the pilot categories have. **One category, `מבוא` (Introduction/history), is a genuine outlier** - its real top-ranked chunk is narrative historical prose, confirmed by direct reading, not inferred from inventory size alone.

Status distribution: **16 `SAFE_GENERALIZATION_POSSIBLE`, 1 `SOURCE_STRUCTURE_INSUFFICIENT` (`מבוא`), 3 `ALREADY_PILOT_CATEGORY`** (excluded from re-analysis, matching WP-059's own precedent of not re-scoring already-handled targets).

## 7. Category Table

See `implementation/WP-060_CATEGORY_TARGET_INVENTORY_FEASIBILITY_REPORT.md` section 8 for the full 20-row table (current planning mode, deterministic-inventory availability, historical-evidence availability, feasibility status, main constraint, recommended next step per category).

## 8. Analysis Artifact

`evaluation/wp060_category_target_inventory_feasibility.json` (20 category records, each with inventory size/sample, top-chunk excerpt, and feasibility status), produced by `implementation/wp060_category_target_inventory_feasibility.py` (new, prototype-only, not imported by `src/`, offline/deterministic/zero-LLM). Genuinely required for this task (systematic, reproducible extraction-feasibility testing across 20 categories) rather than built merely because prior WPs used a similar script pattern.

## 9. Recommended Architecture

**Option B: PARTIAL.** Deterministic extraction is technically feasible for 16/17 remaining categories using the existing, unmodified mechanism - but feasibility is not sufficient for a production rollout decision. WP-036's own real history (inventory availability alone did not prevent the target-drift problem that took roughly a dozen further WPs to address) means a hybrid architecture, expanded one category at a time with real validation, is the correct approach - never a blanket simultaneous rollout. Full reasoning: feasibility report sections 11-13.

## 10. Production-Change Verification

```text
$ git status --short -- src/ tests/ prompts/
 M src/exam_generator/generation/generator.py
 M tests/unit/test_generation.py
```

Both pre-date this WP (WP-058's own unrelated language-compliance change, verified by diff content). **WP-060 modified no file under `src/`, `tests/`, or `prompts/`.** `PILOT_CATEGORIES` remains byte-identical: `{"אספקת דם", "מסילות עצביות", "גרעיני הבסיס"}`.

## 11. Regression Result

```text
.venv/bin/python -m pytest -q
1440 passed, 0 failed
```

Identical to the WP-059 baseline (expected - no production code was touched by this WP).

## 12. Recommended Next WP or Explicit Stopping Point

**Recommended, if pursued**: a single-category narrow pilot mirroring WP-036's own original scope-limiting discipline exactly - add exactly one new category to `PILOT_CATEGORIES`, run a small live pilot, and manually verify target alignment before considering a second. No specific category is recommended by this WP (feasibility report section 14 offers evidentiary context for that future choice, not a decision). **This WP does not authorize that pilot itself** - per its own explicit "not permission to change production target planning yet" scope.

## 13. Final Architectural Conclusion

The 17-category evidence gap WP-059 exposed is an **architectural capability gap for target-level strategy evidence collection**, not a fundamental source-structure limitation - the overwhelming majority of remaining categories (16/17) show real, directly-confirmed extractable structure using the exact mechanism already in production, with zero new code required. Production readiness is a separate, larger question this WP does not resolve and does not recommend resolving all at once - the safest next step, if any, is exactly one more category, validated the same careful way the first three were.

---

# Required Final Architecture State

```text
New IDENTITY_FIRST mappings:
NONE

Production strategy changes:
NONE

Generation prompt changes:
NONE

Validator changes:
NONE

Retrieval changes:
NONE

Schema changes:
NONE

Retry changes:
NONE
```

---

# Terminal Summary

```text
WP-060 complete.

Objective:
Analyze target-inventory/evidence coverage across all 20 canonical categories.

Canonical categories:
20

Categories with deterministic target inventory:
3 (production) + 16 (technically feasible, not implemented)

Categories with historical generation evidence:
3 (target-level, per-attempt) + 20 (exam-output-level only, pre-WP-036 records)

Categories without deterministic inventory:
17 (production); 1 of those (מבוא) also technically infeasible

DIRECT_REUSE:
0

SAFE_GENERALIZATION_POSSIBLE:
16

CATEGORY_SPECIFIC_EXTRACTION_REQUIRED:
0

EXPLICIT_TARGET_CONFIGURATION_REQUIRED:
0

SOURCE_STRUCTURE_INSUFFICIENT:
1 (מבוא)

LLM_TARGET_PLANNING_ONLY_CURRENTLY:
0 (מבוא remains on LLM planning, but its status is SOURCE_STRUCTURE_INSUFFICIENT
for deterministic extraction, not a deliberate LLM-preference finding)

INSUFFICIENT_INFORMATION:
0

Production strategy mapping:
UNCHANGED

New IDENTITY_FIRST mappings:
NONE

Production prompt changes:
NONE

Validator changes:
NONE

Retrieval changes:
NONE

Schema changes:
NONE

Retry changes:
NONE

Analysis artifact:
evaluation/wp060_category_target_inventory_feasibility.json

Human-readable report:
implementation/WP-060_CATEGORY_TARGET_INVENTORY_FEASIBILITY_REPORT.md

Full regression:
1440 passed, 0 failed (unchanged from WP-059 baseline)

Architectural recommendation:
Option B (PARTIAL) - deterministic extraction is feasible for 16/17
remaining categories using the existing, unmodified mechanism, but
production rollout should proceed one category at a time with real
validation, mirroring WP-036's own original discipline - never a
blanket rollout. No implementation authorized by this WP.

Completion report:
implementation/WP-060_COMPLETION_REPORT.md

Waiting for architect review.
```
