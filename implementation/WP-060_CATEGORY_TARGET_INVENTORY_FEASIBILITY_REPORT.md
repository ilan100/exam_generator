# WP-060 Category Target-Inventory Feasibility Report

## 1. Objective

Investigate the evidence bottleneck WP-059 exposed: can the 17 canonical categories that currently have no deterministic target inventory obtain one, without changing factual source authority or introducing unnecessary production complexity - and what is the safest next step for collecting target-level strategy evidence from them? **Feasibility analysis only - no production target-planning change is authorized or made.**

## 2. Architectural Question

> Can the remaining 17 categories obtain a reliable, deterministic target/concept inventory without changing factual source authority or introducing unnecessary production complexity, and what is the smallest safe next step for collecting strategy evidence from those categories?

## 3. Current Architecture

`QuestionTargetPlanner.plan_targets()` (`src/exam_generator/planning/planner.py`) branches on `canonical_category in self._pilot_categories` (`PILOT_CATEGORIES`, `planning/concept_inventory.py`, a `frozenset` of exactly three category names): pilot categories take a **zero-LLM-call, fully deterministic** path (`_plan_targets_from_concept_inventory()`); every other category takes the **LLM-based, free-text** path (one `LLMProfile.GENERATION` call to `QUESTION_TARGET_PLANNING`, returning self-authored `topic`/`factual_focus` text). **Both `extract_concept_inventory()` and `refine_concept_inventory()` (the deterministic extraction functions) are themselves category-agnostic** - they take only already-retrieved `source_evidence`, never a category name - so `PILOT_CATEGORIES` is the *only* place the pilot scope is actually enforced. This is directly confirmed by reading the code, not assumed.

## 4. Canonical Category Inventory

Source of truth: `HistoricalQuestionRepository.canonical_categories` (`src/exam_generator/historical/repository.py`) - derived from the historical workbook's own `category` column, first-seen order, the same authoritative source `docs/ARCHITECTURE.md`'s "Canonical Categories" section names. **20 total canonical categories**, confirmed by direct execution:

`התעלה השדרתית ותכולתה`, `לוקליזציה פונקציונלית`, `חומר לבן`, `עצבים קרניאליים`, `מיפוי ודימות מוחי`, `היסטולוגיה`, `המערכת הלימבית`, `אספקת דם`, `קרומים וסינוסים דוראליים`, `גזע המוח`, `מסילות עצביות`, `גרעיני הבסיס`, `המוח הקטן`, `מערכת העצבים ההיקפית`, `דיאנצפלון`, `אמבריולוגיה`, `טופוגרפיה של ההמיספרות`, `חדרי המוח`, `תאי מערכת העצבים`, `מבוא`.

**This matches WP-059's own count exactly (20 categories, 3 pilot) - no discrepancy found**, confirmed independently rather than copied.

**One genuinely new finding beyond WP-059's own scope**: `evaluation/live_outputs/wp023_acceptance_exam.json` through `wp031_acceptance_exam.json` (pre-WP-036 full-exam evaluation runs, via the always-LLM-based planning path that predates the pilot/non-pilot split) contain **final accepted exam questions for all 20 categories**, not just the three current pilot categories. This is real historical evidence that all 20 categories can and do produce accepted questions via the existing LLM-based path - but it is **exam-output-level evidence only** (question/answer/category text), never the target-level, per-attempt, question-shape-classifiable evidence WP-059's own analysis specifically required (no `target`/`attempts`/`validations` detail is preserved in this earlier record format). WP-059's own conclusion ("17 categories have no target-level generation-attempt evidence") remains correct and is not contradicted by this finding - it is a complementary, coarser-grained fact worth recording for future reference.

## 5. Current Target-Planning Mechanisms

| Mechanism | Input | Output | Determinism | Source Authority | Validation | Failure Behavior | Where Used |
|---|---|---|---|---|---|---|---|
| `extract_concept_inventory()` (`planning/concept_inventory.py`) | `Sequence[SourceEvidenceChunk]` | `tuple[InventoryConcept, ...]` | Fully deterministic, zero LLM/embedding calls | Student summaries only (operates directly on retrieved chunks) | Structural line-pattern match only (ASCII, capitalized, ≤6 words, ≥2 alpha chars) | Empty inventory on no match - never an error, never fabricated | Called by `refine_concept_inventory()` |
| `refine_concept_inventory()` (`planning/concept_anchor.py`) | Same | Same, filtered/repaired | Fully deterministic | Same | Adds category-self-restatement exclusion + WP-037/039 leading/trailing-truncation repair | Same fail-honest behavior | `_plan_targets_from_concept_inventory()` (pilot categories only) |
| LLM free-text target planning (`QuestionTargetPlanner.plan_targets()`, non-pilot branch) | Retrieved evidence + `QUESTION_TARGET_PLANNING` prompt + `CategoryCoverage` | `QuestionTargetPlanningResponse` (self-authored `topic`/`factual_focus` + local `evidence_refs`) | Non-deterministic (one LLM call per planning request) | Student summaries (evidence supplied in prompt); claimed `evidence_refs` independently verified against actually-supplied evidence (never trusted) | Provenance check only (`_resolve_planned_targets()`) - no semantic/factual check at planning time | Invalid provenance claim discards the whole response (`targets = []`), never partially repaired | Every non-pilot category (17 of 20) |

Neither mechanism was modified by this WP.

## 6. Three Pilot-Category Reference Analysis

| Pilot Category | Source Structure | Inventory Mechanism | Inventory Size (refined) | Deterministic | Generation-Ready | Reusable Pattern |
|---|---|---:|---:|---|---|---|
| `גרעיני הבסיס` | Bulleted list of named sub-structures within Hebrew prose (confirmed, WP-036) | `refine_concept_inventory()` | 53 | Yes | Yes (in production) | Standalone-ASCII-line structural marker |
| `אספקת דם` | Same list-of-named-arteries structure (WP-035's original finding) | `refine_concept_inventory()` | 44 | Yes | Yes (in production) | Same |
| `מסילות עצביות` | Same list-of-named-tracts structure (WP-035's original finding) | `refine_concept_inventory()` | 25 | Yes | Yes (in production) | Same |

**The architectural property that actually made deterministic planning possible for these three is not category content - it is a structural artifact of how this specific PDF corpus renders English-language named entities embedded in Hebrew prose** (WP-035/036's own finding, reconfirmed here): English terms tend to land on their own standalone text line during PDF extraction (WP-004's PyMuPDF-based extraction), distinct from the surrounding Hebrew sentence structure. `extract_concept_inventory()`'s pure-ASCII-line filter directly targets this artifact. **This property is a function of the source document format, not of anatomical subject matter** - directly relevant to section 7 below.

## 7. Remaining 17-Category Analysis (OBSERVED, direct execution)

`refine_concept_inventory()` (the real, unmodified, already-production function - zero code change) was run directly against each of the 17 non-pilot categories' real, retrieved student-summary evidence (the same retrieval call `QuestionTargetPlanner` itself would make). **16 of 17 produced a substantial, plausible-looking inventory** (9-54 concepts; median ~28) containing real anatomical/technical named entities (`Midbrain`, `Pons`, `Medulla Oblongata`, `Olfactory Nerve`, `Optic Nerve`, `Cerebrum`, `Cerebellum`, `Bilaminar Disk`, `Epiblast`, `Microglia`, `Sympathetic Chain`, etc.) - not merely noise. The same truncation-artifact class WP-037/039 already diagnosed and repaired for the pilot categories (`_repair_trailing_truncations()`, leading-truncation repair) was observed and correctly repaired here too, since both repair functions are equally category-agnostic.

**A direct, qualitative spot-check of each category's real, top-ranked retrieved chunk** (not merely the extracted concept count) confirms most non-pilot categories share the pilot categories' own list-structured shape - e.g. `עצבים קרניאליים`'s top chunk contains bare standalone lines `Sympathetic Chain` / `Ganglion`-style content; `המערכת הלימבית`'s top chunk explicitly enumerates `cingulate gyrus`, `(DG) Dentate Gyrus`, `fimbria`, `mammillary body`, `septal area` in the same bulleted-list style as the pilot categories' own evidence.

**One category, `מבוא` (Introduction/history of the field), is a genuine, qualitatively distinct outlier**: its top-ranked real chunk is narrative historical prose (Egyptian medical history, Aristotle, Galen, Vesalius) with only incidental capitalized terms (`The Edwin Smith Papyrus`, proper names) rather than a structured list of named anatomical sub-entities - confirmed by direct reading, not inferred from its smaller inventory size (9) alone. This is architecturally expected: `מבוא` is an overview/historical category, not a specific anatomical system with enumerable sub-structures, so its source material genuinely differs in kind, not merely in cleanliness.

## 8. Category Feasibility Table

| Category | Current Target Planning | Deterministic Inventory | Historical Evidence | Feasibility Status | Main Constraint | Recommended Next Step |
|---|---|---|---|---|---|---|
| גרעיני הבסיס | Deterministic | Yes (production) | Target-level (WP-036-057) | `ALREADY_PILOT_CATEGORY` | - | None - already implemented |
| אספקת דם | Deterministic | Yes (production) | Target-level (WP-036-049) | `ALREADY_PILOT_CATEGORY` | - | None - already implemented |
| מסילות עצביות | Deterministic | Yes (production) | Target-level (WP-036-049) | `ALREADY_PILOT_CATEGORY` | - | None - already implemented |
| חומר לבן | LLM free-text | Extractable (54 concepts) | Exam-level only | `SAFE_GENERALIZATION_POSSIBLE` | No target-level validation history | Narrow pilot if selected |
| עצבים קרניאליים | LLM free-text | Extractable (34), spot-check confirmed list-structured | Exam-level only | `SAFE_GENERALIZATION_POSSIBLE` | Same | Narrow pilot if selected |
| גזע המוח | LLM free-text | Extractable (39) | Exam-level only | `SAFE_GENERALIZATION_POSSIBLE` | Same | Narrow pilot if selected |
| המוח הקטן | LLM free-text | Extractable (43) | Exam-level only | `SAFE_GENERALIZATION_POSSIBLE` | Same | Narrow pilot if selected |
| טופוגרפיה של ההמיספרות | LLM free-text | Extractable (47) | Exam-level only | `SAFE_GENERALIZATION_POSSIBLE` | Same | Narrow pilot if selected |
| המערכת הלימבית | LLM free-text | Extractable (36), spot-check confirmed list-structured | Exam-level only | `SAFE_GENERALIZATION_POSSIBLE` | Same | Narrow pilot if selected |
| דיאנצפלון | LLM free-text | Extractable (41) | Exam-level only | `SAFE_GENERALIZATION_POSSIBLE` | Same | Narrow pilot if selected |
| קרומים וסינוסים דוראליים | LLM free-text | Extractable (30) | Exam-level only | `SAFE_GENERALIZATION_POSSIBLE` | Same | Narrow pilot if selected |
| אמבריולוגיה | LLM free-text | Extractable (25) | Exam-level only | `SAFE_GENERALIZATION_POSSIBLE` | Same | Narrow pilot if selected |
| תאי מערכת העצבים | LLM free-text | Extractable (25) | Exam-level only | `SAFE_GENERALIZATION_POSSIBLE` | Same | Narrow pilot if selected |
| התעלה השדרתית ותכולתה | LLM free-text | Extractable (21) | Exam-level only | `SAFE_GENERALIZATION_POSSIBLE` | Same | Narrow pilot if selected |
| לוקליזציה פונקציונלית | LLM free-text | Extractable (20) | Exam-level only | `SAFE_GENERALIZATION_POSSIBLE` | Same | Narrow pilot if selected |
| היסטולוגיה | LLM free-text | Extractable (18) | Exam-level only | `SAFE_GENERALIZATION_POSSIBLE` | Same | Narrow pilot if selected |
| מיפוי ודימות מוחי | LLM free-text | Extractable (18), prose-and-terms mix | Exam-level only | `SAFE_GENERALIZATION_POSSIBLE` | Somewhat more narrative source than other candidates | Narrow pilot if selected, lower priority |
| חדרי המוח | LLM free-text | Extractable (16) | Exam-level only | `SAFE_GENERALIZATION_POSSIBLE` | Same | Narrow pilot if selected |
| מערכת העצבים ההיקפית | LLM free-text | Extractable (15), spot-check confirmed list-structured | Exam-level only | `SAFE_GENERALIZATION_POSSIBLE` | Same | Narrow pilot if selected |
| מבוא | LLM free-text | Poor (9, narrative/historical prose, spot-check confirmed) | Exam-level only | `SOURCE_STRUCTURE_INSUFFICIENT` | Source is inherently narrative/historical, not enumerable sub-structures | Keep LLM planning - no deterministic extraction path is justified |

Full machine-readable data (including every category's inventory sample and top-chunk excerpt): `evaluation/wp060_category_target_inventory_feasibility.json`.

## 9. Inventory Quality Assessment

| Criterion | Assessment across the 16 `SAFE_GENERALIZATION_POSSIBLE` categories |
|---|---|
| Deterministic | Yes - same unmodified function, zero LLM/embedding calls |
| Reproducible | Yes - pure function of retrieved evidence |
| Source-grounded | Yes - every concept carries its genuine source `chunk_id` |
| Category-specific | Yes - retrieval is category-scoped, as already established since WP-006 |
| Stable across runs | Yes - deterministic TF-IDF retrieval + deterministic extraction |
| Not dependent on LLM interpretation | Yes | 
| Not dominated by OCR/header noise | Mostly - the same truncation-artifact class already known and partially repaired (WP-037/039); a residual, already-disclosed OCR-scramble class remains unfixable (matches the pre-existing, already-documented `"Deep Brain Stimulatino D(SB.)"`-style limitation) |
| Usable by generation | Not directly assessed by this WP - inventory extraction success is necessary but, per WP-036's own live-pilot finding (section 11 below), **not sufficient** for reliable generation |

## 10. Source-Authority Assessment

No change to source authority anywhere in this analysis. `extract_concept_inventory()`/`refine_concept_inventory()` operate exclusively on already-retrieved `SourceEvidenceChunk`s (student-summary evidence, the sole factual grounding authority) - the historical Excel workbook was not consulted as a target/inventory source anywhere in this WP, consistent with its existing style/structure/terminology-only role.

## 11. Risks of Generalizing Deterministic Extraction

**The central risk is not extraction failure - it is the target-drift problem WP-036's own live pilot already discovered and the project spent roughly a dozen subsequent WPs (WP-037 through WP-047, plus WP-055-057's own separate Globus Pallidus thread) incrementally fixing, specific to the three pilot categories' own real evidence content.** Concretely, WP-036's live pilot found that even a correctly-assigned, well-formed target does not guarantee generation actually tests that target - two distinct, real failure modes were found (context-window ambiguity causing drift to a more salient neighboring entity; category-self-restatement concepts producing untestable generic questions), each requiring its own dedicated, evidence-driven deterministic fix (`anchor_concept_evidence()`'s narrowing, `is_enumeration_evidence_insufficient()`, `detect_source_evidence_role()`, and eventually the identity-first strategy work of WP-052-057). **None of this iterative, category-specific validation has been done for any of the 16 candidate categories.** Rolling out deterministic target planning to all 16 simultaneously would very plausibly rediscover the same class of problems in new categories' own evidence shapes, with no prior tuning - a materially different, larger risk than the narrow, single-round inventory-extraction test this WP performed.

## 12. Risks of Retaining LLM Target Planning

**Already documented, real, and specific to this project's own data - not speculative.** WP-034's own live-verified finding (`docs/ARCHITECTURE.md`'s WP-034 section): informing the LLM-based planner about already-tested coverage via prompt guidance **did not meaningfully improve diversity** - a four-question sequential run in `אספקת דם` (before that category was moved to deterministic planning) converged on the identical fact in all four questions despite coverage correctly listing it as already tested from the second call onward; the full 40-question acceptance run showed only marginal, noise-level improvement (47% distinct vs. WP-032's 41% baseline). **This is the exact problem deterministic concept-inventory planning was built to solve** for the three pilot categories (target selection "by construction" rather than by soft LLM guidance) - and it remains an active, undisclosed-elsewhere risk for all 17 non-pilot categories today, independent of and prior to any identity-first/strategy-selection question.

## 13. Recommended Architecture

**Option B: PARTIAL** - deterministic target inventories are technically feasible, via the existing, unmodified extraction mechanism, for 16 of the 17 remaining categories (all except `מבוא`, whose source material is narrative/historical rather than list-structured). This is not, however, a recommendation to generalize immediately or broadly. Per WP-060's own explicit "do not force one mechanism across all categories" principle and section 29's hybrid-architecture guidance, the correct architecture remains:

```text
deterministic target inventory
    where source structure supports it (confirmed per-category, not assumed)

LLM target planning
    where source structure does not support safe extraction (מבוא)
```

**Feasibility is necessary but not sufficient for a production rollout decision** - WP-036's own hard-won lesson (section 11 above) is that inventory availability alone does not guarantee reliable generation; each category's own evidence shape needs the same kind of iterative, real-evidence-driven validation the three pilot categories received over roughly a dozen WPs. A simultaneous rollout to all 16 categories would bypass that discipline and is not recommended.

## 14. Recommended Next Implementation WP, If Justified

**Recommended, if the architect wants to proceed: a single-category narrow pilot, mirroring WP-036's own original scope-limiting discipline exactly** - add exactly one new category (not several, not all sixteen) to `PILOT_CATEGORIES`, run a small live pilot (matching WP-036's own four-question-per-category evaluation shape), and manually verify target alignment before considering a second category. This is deliberately the same size/risk step WP-036 itself took, applied once more, rather than a blanket generalization. **No specific category is recommended by this WP** - selection should weigh evidence quality (e.g. `עצבים קרניאליים`, `המערכת הלימבית`, and `מערכת העצבים ההיקפית` had their list-structured quality directly spot-checked and confirmed in this analysis, a slightly stronger evidentiary basis than categories whose feasibility rests on inventory size alone) against the project's own current priorities. **This WP does not authorize that pilot** - it is offered as the smallest safe next step if the architect chooses to pursue this thread at all.

## 15. Production-Change Verification

```text
$ git status --short -- src/ tests/ prompts/
 M src/exam_generator/generation/generator.py
 M tests/unit/test_generation.py
```

Both are WP-058's own already-completed, unrelated changes (pre-dating this WP, verified by diff content). **WP-060 itself modified no file under `src/`, `tests/`, or `prompts/`.** `PILOT_CATEGORIES` remains exactly `{"אספקת דם", "מסילות עצביות", "גרעיני הבסיס"}`, byte-identical to its pre-WP-060 state.

## 16. Regression Result

```text
.venv/bin/python -m pytest -q
1440 passed, 0 failed
```

Identical to the WP-059 baseline (expected - no production code was touched).

## 17. Final Architectural Conclusion

The evidence-coverage asymmetry WP-059 exposed is a genuine **architectural capability gap for target-level strategy evidence**, not a fundamental **source-structure limitation** - 16 of 17 non-pilot categories show real, direct, quantitatively and qualitatively confirmed extractable structure using the exact same mechanism already in production for three categories, requiring zero new code. However, extractability alone does not establish production readiness - WP-036's own real, hard-won history shows that inventory availability is only the first of several conditions (context-window anchoring, enumeration-shape handling, source-role framing, and more) that took roughly a dozen further WPs to work out for even the three already-piloted categories. The safest next step, if this thread is pursued at all, is a single-category narrow pilot mirroring WP-036's own original discipline - never a blanket rollout to all sixteen feasible categories at once.
