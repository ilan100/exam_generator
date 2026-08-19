# WP-059 Candidate Analysis Report — Identity-First Candidate Discovery

## 1. Objective

Systematically identify, from already-recorded historical generation-attempt evidence, which currently-`DEFAULT` (category, target) pairs - if any - show enough evidence to justify a future WP-060-style controlled identity-first experiment, mirroring the WP-052 → WP-053 → WP-054 and WP-055 → WP-056 → WP-057 evidence chain. **Candidate discovery only - no production mapping change, no experiment design, no implementation.**

## 2. Architectural Context

Three (category, target) pairs currently have a permanent `IDENTITY_FIRST` mapping, all reached via the same evidence → controlled experiment → architecture review → implementation sequence: `Caudate Nucleus`, `Nucleus Accumbens` (WP-052→054), and `Globus Pallidus` (WP-055→057), all within `גרעיני הבסיס`. WP-059 asks the narrower question this project has consistently insisted on: not "which targets should be `IDENTITY_FIRST`," but "which targets *deserve an experiment*."

## 3. Candidate Population

**141 total concepts** exist across the three pilot categories' concept inventories (`extract_concept_inventory()`, deterministic, zero LLM calls): `גרעיני הבסיס` 63, `אספקת דם` 47, `מסילות עצביות` 31. The large majority are extraction noise (OCR fragments, header/metadata lines, non-target sub-concepts like individual thalamic nuclei abbreviations) that were never assigned as a real generation target in any recorded pilot.

**The evidence-based candidate population is narrower and more honest**: only (category, target) pairs that actually appear as a real, recorded generation target in at least one historical pilot round. This analysis found **19 distinct (category, target) pairs with recorded evidence** (3 already `IDENTITY_FIRST`, 16 remaining candidates) across **175 total recorded generation attempts** (110 with full per-attempt detail - question, answers, validator results; 65 round-level-only - final accepted question/answer, or a bare failure marker, from earlier WPs whose recorded schema did not preserve per-attempt detail).

## 4. Data Sources

`evaluation/live_outputs/wp0{36,37,38,39,40,41,43,44,45,46,47,49}_pilot_records.json` - every real live-pilot record file this project has ever produced for the three pilot categories. **No new LLM/API call was made** for this analysis (WP-059 section 29's explicit instruction). Question-shape classification reuses `implementation/wp056_experiment.py`'s own `classify_question_shape()` **verbatim, imported directly, not reimplemented** (WP-059 section 10/30's explicit "reuse the existing classifier, do not build a second incompatible taxonomy" instruction), relabeled to this WP's requested vocabulary: `VALID_IDENTITY_SHAPE` → `IDENTITY`, `MEMBERSHIP_CLASSIFICATION` → `CLASSIFICATION_MEMBERSHIP`, `PROPERTY` → `PROPERTY`, `OTHER` → `OTHER_UNKNOWN`.

**Source-authority preserved**: historical pilot records are this project's own recorded application behavior (not the historical Excel workbook), used here as behavioral evidence about generation reliability - never as factual grounding evidence, exactly the same distinction this project has maintained since WP-001. The historical Excel workbook itself was not consulted for this analysis (it is style/structure reference only and carries no generation-attempt/strategy information).

## 5. Exclusions

`גרעיני הבסיס + Caudate Nucleus`, `גרעיני הבסיס + Nucleus Accumbens`, `גרעיני הבסיס + Globus Pallidus` - already permanently `IDENTITY_FIRST`, excluded from re-scoring per WP-059 section 6's explicit instruction ("treat these three targets as already handled").

**Architecturally important exclusion, not an oversight**: **17 of the project's 20 canonical categories have zero recorded generation-attempt evidence of any kind**, and no deterministic target/concept inventory either - only `גרעיני הבסיס`, `אספקת דם`, and `מסילות עצביות` have ever used the deterministic, concept-inventory-based target-planning path (`_plan_targets_from_concept_inventory()`, WP-036). Every other category uses free-text, LLM-generated target planning with no fixed target population and no pilot history. This is confirmed directly (see section 10 below), not assumed.

## 6. Strategy Classification Method

`classify_question_shape(question, target_topic)` (`implementation/wp056_experiment.py`, self-validated against 6 known real examples before its own original use in WP-056) - a small, deterministic, keyword/copula-proximity rule over the generated question's own text, distinguishing:

- **IDENTITY**: the target's own name appears *within the question text itself*, adjacent to a copula/naming cue, with no membership marker present (e.g. "Which of the following IS X").
- **CLASSIFICATION_MEMBERSHIP**: a membership marker ("part of", "belongs to", etc.) is present, with the target's own name absent from the question text (e.g. "Which structure is part of X").
- **PROPERTY**: a property marker (function/source/role/location word) is present, with no identity or membership signal.
- **OTHER_UNKNOWN**: none of the above apply, or (for round-level-only records, see section 4) no question text is available to classify at all.

No new classifier was built; no LLM was used for classification anywhere in this analysis.

## 7. Candidate Scoring Method

```text
candidate_score =
    2 * min(identity_accepted, 3)
  + 1 * min(property_rejected, 4)
  + 2  if (identity_acceptance_rate - property_acceptance_rate) >= 0.4 else 0
  + 1  if total_attempts >= 4 else 0
  + 1  if first_attempt_identity_count >= 1 else 0
  - 2  if identity_accepted == 0 else 0
```

Fixed **before** inspecting any real candidate's numbers, applied uniformly to all 16 candidates, never adjusted after seeing results (WP-059 section 48's explicit "no hidden human judgment in scoring" requirement). This is a prioritization heuristic only - **never a probability estimate or a statistical-significance claim** (section 18).

## 8. Tier Definitions

```text
TIER_A_EXPERIMENT_CANDIDATE:  score >= 6  AND  identity_accepted >= 2  AND  total_attempts >= 4
TIER_B_MONITOR:                score >= 3  (does not meet Tier A)
TIER_C_NOT_SUPPORTED:          score < 3, but at least one recorded attempt exists
INSUFFICIENT_DATA:             zero recorded generation attempts found
```

The Tier A gate deliberately requires **both** a minimum score **and** at least 2 independent accepted identity attempts (never a single lucky example, per section 21's explicit "do not define Tier A merely by a single successful identity example" instruction) **and** a minimum sample size.

## 9. Ranked Candidates

| Rank | Category | Target | Status | Score | Attempts | Property (accept/total) | Identity (accept/total) | First-attempt identity | After-failure identity |
|---:|---|---|---|---:|---:|---|---|---:|---:|
| 1 | אספקת דם | Basillar artery | TIER_B_MONITOR | 7 | 23 | 5/11 | 1/2 | 0 | 1 |
| 2 | גרעיני הבסיס | Corpos Striatum | TIER_B_MONITOR | 3 | 8 | 2/2 | 1/1 | 0 | 0 (order UNKNOWN - round-level-only source) |
| 3 | מסילות עצביות | Medial Lemniscus Tract | TIER_B_MONITOR | 3 | 6 | 4/4 | 1/1 | 0 | 0 (order UNKNOWN) |
| 4 | מסילות עצביות | Corticospinal Tract | TIER_B_MONITOR | 3 | 28 | 2/7 | 0/0 (N/A) | 0 | 0 |
| 5 | גרעיני הבסיס | (GPe) | TIER_C_NOT_SUPPORTED | 2 | 2 | N/A | 1/1 | 0 | 1 |
| 6 | אספקת דם | Anterior Inferior Cerebellar Artery (AICA) | TIER_C_NOT_SUPPORTED | 0 | 7 | 0/1 | 0/0 (N/A) | 0 | 0 |
| 7-16 | (various) | (various - see `evaluation/wp059_identity_first_candidate_analysis.json` for the complete list) | TIER_C_NOT_SUPPORTED | -1 to -2 | 2-18 | mostly high property acceptance, zero identity evidence | - | 0 | 0 |

Full machine-readable ranking (all 16 candidates, every field): `evaluation/wp059_identity_first_candidate_analysis.json`.

## 10. Category Coverage

| Category | Targets w/ Evidence | Already IDENTITY_FIRST | Candidates | Tier A | Tier B | Tier C |
|---|---:|---:|---:|---:|---:|---:|
| `גרעיני הבסיס` | 7 | 3 | 4 | 0 | 1 | 3 |
| `אספקת דם` | 4 | 0 | 4 | 0 | 1 | 3 |
| `מסילות עצביות` | 8 | 0 | 8 | 0 | 2 | 6 |
| *(all 17 other canonical categories)* | 0 | 0 | 0 | 0 | 0 | 0 (all `INSUFFICIENT_DATA` - no target inventory or recorded evidence exists) |

No candidate-discovery bias toward one category is evident within the three pilot categories (each contributed both Tier B and Tier C candidates); the complete absence of evidence for the other 17 categories is an architectural fact (section 5), not a scope choice made by this analysis.

## 11. Strongest Candidate: `אספקת דם` + `Basillar artery` (still only TIER_B, not TIER_A)

Highest score (7) of all 16 candidates, but **does not qualify for Tier A** because it has only **1** accepted identity attempt (the gate requires ≥2) - exactly the "do not rank on a single accepted example" caution section 13/21 explicitly warns against.

**Why it scores relatively high**: 11 recorded property-shaped attempts (5 accepted, 45%) and 23 total attempts across 8 separate WPs - by far the largest evidence base of any candidate. **Why it is genuinely different from the three already-approved targets**: unlike `Caudate Nucleus` (historical property acceptance 0/8) or `Nucleus Accumbens` (1/8), `Basillar artery`'s property-shaped attempts already succeed **45% of the time** post-WP-044 - closer to an already-workable `DEFAULT` strategy than to the stark 0%-vs-100% contrast that originally justified the three approved experiments. The one identity success occurred **after 8 consecutive property-attempt rejections within the same round** (`AFTER_PRIOR_FAILURE`, WP-047) - the weaker, retrospectively-biased evidence shape section 22/23 explicitly asks to be distinguished from a first-attempt success, and it is the *only* identity data point available for this target at all.

**Additional context (not part of the score, but directly relevant, per WP-048's own prior diagnostic finding)**: this target's dominant historical problem is not classification/membership ambiguity but a **source-role framing issue** (Basillar artery is evidence-positioned as the *source* of the more salient `Superior Cerebellar Artery`) - already partially addressed by WP-044 Part B's `is_source_role`/target-role-consistency mechanism, which is a large part of why its property-shaped acceptance rate (45%) is already reasonably workable. This target's own next diagnostic step, if pursued, would more naturally continue that already-open thread (WP-048's own still-unresolved "grounding-validator interpretation variance" sub-finding for this exact target) than restart a fresh identity-first investigation from zero.

## 12. Evidence Against Over-Generalization

All three permanently-mapped targets are in `גרעיני הבסיס`. This analysis explicitly did **not** treat that as evidence that other `גרעיני הבסיס` targets (e.g. `Putamen`, which has zero recorded pilot evidence at all) or other categories should inherit `IDENTITY_FIRST` - each of the 16 candidates was scored independently, on its own recorded evidence only, per WP-059 section 24's explicit "the unit of decision remains category + target" instruction. No category-level or cross-target generalization was applied anywhere in the scoring.

## 13. Retrospective-Bias Analysis

Across all 16 candidates, only **1 total accepted identity attempt** was found with any attempt-level order information (`Basillar artery`, `AFTER_PRIOR_FAILURE`) - `Corpos Striatum`'s and `Medial Lemniscus Tract`'s single accepted identity attempts both come from round-level-only-schema WPs (pre-WP-044) where no attempt-level order is recorded, honestly tagged `UNKNOWN` rather than guessed. **Zero candidates have a genuine, order-confirmed FIRST_ATTEMPT identity success** - a materially weaker evidentiary picture than the three already-approved targets had at the equivalent WP-052 stage (which found `Caudate Nucleus` 4/4 and `Nucleus Accumbens` 3/3 identity acceptance, several of which were independently confirmed via WP-053's own *fresh, first-attempt* controlled rounds). This is itself an important, disclosed reason none of the current 16 candidates reaches Tier A.

## 14. Category-vs-Target Analysis

Confirmed no category was scored as a unit; every candidate row is one specific (category, target) pair. `גרעיני הבסיס`'s own 4 non-approved candidates (`Corpos Striatum`, `Corpos Str`, `The Basal Gang`, `(GPe)`) score very differently from each other (3, -1, -2, 2 respectively) despite sharing a category with three approved `IDENTITY_FIRST` targets - direct, concrete evidence that category membership alone does not predict a target's strategy evidence.

## 15. Evidence Availability

**Known data-quality caveat, disclosed explicitly rather than silently corrected**: several candidate rows are almost certainly the *same real anatomical entity* recorded under different literal strings across WPs, due to pre-WP-039 extraction-truncation artifacts and natural target-name variation - e.g. `Corpos Str` (2 attempts) is very likely the same entity as `Corpos Striatum` (8 attempts, an earlier, unrepaired truncation); `Anterior Corticospinal T` (2 attempts) vs. `Anterior Corticospinal Tract` (3 attempts) likewise; `edial Lemniscus Tract` (3 attempts, a leading-truncation artifact - the same phenomenon WP-037 first diagnosed) is almost certainly `Medial Lemniscus Tract` missing its leading "M". **These were deliberately NOT merged** - this project has repeatedly and explicitly rejected fuzzy/substring target-identity matching (WP-038, WP-054 section 34, WP-057's own exact-match regression tests), and inventing a merge heuristic here would violate that same precedent. Each row is therefore the literal, exact evidence recorded under that literal string; a real entity's *total* evidence may be understated by this fragmentation, but never fabricated by an incorrect merge.

## 16. Recommended Next Experiment

**None.** No Tier A candidate exists (see section 17/Final Decision below).

## 17. Candidates Not Recommended

All 16 candidates - see the ranked table (section 9) and the full JSON artifact for every candidate's individual score and rationale. The four Tier B candidates (`Basillar artery`, `Corpos Striatum`, `Medial Lemniscus Tract`, `Corticospinal Tract`) are flagged as `TIER_B_MONITOR` - worth revisiting if future pilots of these same categories accumulate more evidence (particularly more first-attempt-order-confirmed identity data), but not currently justified for a dedicated controlled experiment.

## 18. Production Changes

**NONE.** `git status`/`git diff` confirm no file under `src/exam_generator/`, `tests/`, or `prompts/` was modified by this WP (the only pre-existing diffs present, `generation/generator.py` and `test_generation.py`, are WP-058's own already-completed, unrelated changes). `src/exam_generator/generation/strategy.py`'s mapping remains exactly `{"גרעיני הבסיס": frozenset({"Caudate Nucleus", "Nucleus Accumbens", "Globus Pallidus"})}` - byte-identical to its WP-057 state.

## 19. Regression Result

```text
.venv/bin/python -m pytest -q
1440 passed, 0 failed
```

Identical to the WP-058 baseline - expected, since no production code was touched.

## 20. Final Architectural Conclusion

**Option B: No Tier A candidate found. No new controlled experiment is currently justified.**

The evidence base for the 16 remaining candidates is real but consistently weaker than the evidence that justified the three already-approved experiments: no candidate has more than one accepted identity attempt, no candidate has an order-confirmed first-attempt identity success, and the strongest-scoring candidate (`Basillar artery`) already has a substantially workable `DEFAULT`/property acceptance rate (45%) that does not show the stark contrast the three approved targets originally showed. This is a valid, evidence-grounded negative result, not a failure of the analysis - per WP-059 section 21's own explicit instruction, "No Tier A candidates found" is a valid, expected possible outcome, not something to be manufactured around.
