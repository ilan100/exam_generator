# WP-059 Completion Report — Identity-First Candidate Discovery Across Remaining Targets

## 1. Objective

Systematically determine, from evidence already recorded in this project, which currently-`DEFAULT` (category, target) pairs justify a future WP-060 controlled identity-first experiment - a candidate-discovery WP only, per the WP-052→053→054 / WP-055→056→057 evidence chain's own established discipline. **No production mapping change, no prompt change, no validator change - candidate discovery is evidence only.**

## 2. Architectural Question

> Which currently-`DEFAULT` target/category pairs, if any, show sufficient historical evidence of identity-question success and/or repeated property-generation failure to justify a WP-060 controlled experiment?

Deliberately narrower than "which targets should use `IDENTITY_FIRST`" - this WP answers "which targets deserve an experiment," nothing more.

## 3. Candidate Population

19 distinct (category, target) pairs have any recorded generation-attempt evidence at all, across 175 total recorded attempts (110 with full per-attempt detail, 65 round-level-only). 3 of the 19 are already permanently `IDENTITY_FIRST` (excluded per WP-059 section 6); the remaining **16 are the candidate population**, all within the three pilot categories (`גרעיני הבסיס` 4, `אספקת דם` 4, `מסילות עצביות` 8). See `implementation/WP-059_CANDIDATE_ANALYSIS_REPORT.md` section 3 for the full derivation.

## 4. Data Sources

`evaluation/live_outputs/wp0{36,37,38,39,40,41,43,44,45,46,47,49}_pilot_records.json` - every real historical live-pilot record this project has ever produced. No new LLM/API call was made (zero cost, per WP-059 section 29).

## 5. Excluded Targets

`גרעיני הבסיס + Caudate Nucleus`, `גרעיני הבסיס + Nucleus Accumbens`, `גרעיני הבסיס + Globus Pallidus` - already permanently `IDENTITY_FIRST`, treated as already-handled per WP-059 section 6, never re-scored.

**17 of the project's 20 canonical categories were also excluded, but architecturally, not by analysis choice**: only `גרעיני הבסיס`/`אספקת דם`/`מסילות עצביות` have ever used the deterministic concept-inventory-based target-planning path; every other category's target planning is free-text/LLM-generated with no fixed target population and zero recorded pilot history. This is confirmed directly (a fresh `extract_concept_inventory()` scan and a search of every pilot-record file - see the candidate analysis report section 5/10), not assumed.

## 6. Analysis Implementation

`implementation/wp059_identity_first_candidate_analysis.py` (new, prototype-only, not imported by `src/`) - offline, deterministic, read-only. Loads and normalizes all 12 pilot-record files (schema evolved across WPs - round-level-only through WP-043, per-attempt detail from WP-044 onward, confirmed by direct inspection before writing any parsing code), classifies every attempt's question shape, tags retrospective-bias order, aggregates per (category, target), scores and tiers each candidate, and writes `evaluation/wp059_identity_first_candidate_analysis.json`. Genuinely required for this task (aggregating ~175 records across 9 differently-shaped JSON schemas reproducibly) rather than built merely because prior WPs used a similar file-naming pattern.

## 7. Strategy Classification

Reused directly (imported, not reimplemented) from `implementation/wp056_experiment.py`'s own `classify_question_shape()` - already self-validated against 6 known real examples in WP-056, per WP-059 section 10/30's explicit "reuse the existing classifier" instruction. Its four output categories were relabeled (not changed in logic) to WP-059's requested vocabulary: `VALID_IDENTITY_SHAPE`→`IDENTITY`, `MEMBERSHIP_CLASSIFICATION`→`CLASSIFICATION_MEMBERSHIP`, `PROPERTY`→`PROPERTY`, `OTHER`→`OTHER_UNKNOWN`.

## 8. Scoring Methodology

```text
candidate_score =
    2 * min(identity_accepted, 3)
  + 1 * min(property_rejected, 4)
  + 2  if (identity_acceptance_rate - property_acceptance_rate) >= 0.4 else 0
  + 1  if total_attempts >= 4 else 0
  + 1  if first_attempt_identity_count >= 1 else 0
  - 2  if identity_accepted == 0 else 0

TIER_A_EXPERIMENT_CANDIDATE:  score >= 6  AND  identity_accepted >= 2  AND  total_attempts >= 4
TIER_B_MONITOR:                score >= 3
TIER_C_NOT_SUPPORTED:          score < 3, at least one attempt exists
INSUFFICIENT_DATA:             zero recorded attempts
```

Fixed before inspecting any real candidate's numbers; applied uniformly; never adjusted post-hoc (WP-059 section 48). Explicitly a prioritization heuristic, never a probability/statistical-significance claim (section 18).

## 9. Candidate Ranking

16 candidates scored, **0 reached Tier A**, 4 reached `TIER_B_MONITOR` (`Basillar artery` score 7; `Corpos Striatum`, `Medial Lemniscus Tract`, `Corticospinal Tract` all score 3), 12 reached `TIER_C_NOT_SUPPORTED`. Full ranked table: `implementation/WP-059_CANDIDATE_ANALYSIS_REPORT.md` section 9; full machine-readable data: `evaluation/wp059_identity_first_candidate_analysis.json`.

## 10. Category Coverage

| Category | Targets w/ Evidence | Already IDENTITY_FIRST | Candidates | Tier A | Tier B | Tier C |
|---|---:|---:|---:|---:|---:|---:|
| `גרעיני הבסיס` | 7 | 3 | 4 | 0 | 1 | 3 |
| `אספקת דם` | 4 | 0 | 4 | 0 | 1 | 3 |
| `מסילות עצביות` | 8 | 0 | 8 | 0 | 2 | 6 |
| *(17 other categories)* | 0 | 0 | 0 | 0 | 0 | 0 (all effectively `INSUFFICIENT_DATA`) |

No evidence of candidate-discovery bias toward one category (each pilot category produced both Tier B and Tier C candidates).

## 11. Strongest Candidate

`אספקת דם` + `Basillar artery` - highest score (7) of all 16, but does **not** qualify for Tier A (only 1 accepted identity attempt; the gate requires ≥2, per section 21's explicit anti-single-example instruction). Its property/source-role framing already succeeds 45% of the time (5/11) post-WP-044 - a materially different, less stark evidence shape than the three already-approved targets originally showed (`Caudate Nucleus` 0/8 property acceptance; `Nucleus Accumbens` 1/8). Its one identity success came `AFTER_PRIOR_FAILURE` (WP-047, after 8 consecutive property rejections in the same round) - the weaker, retrospectively-biased evidence shape this project has repeatedly cautioned against overweighting since WP-052. Full analysis: candidate analysis report section 11.

## 12. Retrospective-Bias Analysis

Across all 16 candidates, only **1** accepted identity attempt has confirmed attempt-level order information at all (`Basillar artery`, `AFTER_PRIOR_FAILURE`); the other two candidates with an accepted identity attempt (`Corpos Striatum`, `Medial Lemniscus Tract`) both come from pre-WP-044 round-level-only records with no attempt-level order preserved, honestly tagged `UNKNOWN` rather than guessed. **Zero candidates have a genuine, order-confirmed first-attempt identity success** - a materially weaker evidentiary picture than the three approved targets had at the equivalent WP-052 stage. This is itself a primary, disclosed reason no candidate reaches Tier A.

## 13. Evidence Sufficiency

16/16 candidates have at least 2 recorded attempts (no `INSUFFICIENT_DATA` status was assigned within the three pilot categories); all 17 non-pilot categories are architecturally insufficient-data (section 5), not individually re-analyzed target-by-target since no target population exists for them to enumerate. A known data-quality caveat is disclosed explicitly (candidate analysis report section 15): several candidate rows likely represent the same real entity fragmented across different literal strings due to pre-WP-039 extraction-truncation artifacts (e.g. `Corpos Str` vs. `Corpos Striatum`) - deliberately **not** merged, since this project has repeatedly and explicitly rejected fuzzy/substring target-identity matching (WP-038, WP-054, WP-057).

## 14. Production-Change Verification

```text
$ git status --short -- src/ tests/ prompts/
 M src/exam_generator/generation/generator.py
 M tests/unit/test_generation.py
```

Both are WP-058's own already-completed, unrelated changes (verified by diff content - the new WP-058 language-compliance check and its tests), pre-dating this WP. **WP-059 itself modified no file under `src/`, `tests/`, or `prompts/`.** `src/exam_generator/generation/strategy.py`'s mapping remains byte-identical to its WP-057 state: `{"גרעיני הבסיס": frozenset({"Caudate Nucleus", "Nucleus Accumbens", "Globus Pallidus"})}`.

## 15. Regression Result

```text
.venv/bin/python -m pytest -q
1440 passed, 0 failed
```

Identical to the WP-058 baseline (expected - no production code was touched by this WP).

## 16. Generated Analysis Artifacts

- `implementation/wp059_identity_first_candidate_analysis.py` (analysis script, prototype-only)
- `evaluation/wp059_identity_first_candidate_analysis.json` (structured candidate evidence, 16 records)
- `implementation/WP-059_CANDIDATE_ANALYSIS_REPORT.md` (human-readable analysis)

## 17. Recommended WP-060 or Explicit No-Experiment Conclusion

**Option B: No Tier A candidate found. No new controlled experiment is currently justified.** This is a valid, evidence-grounded outcome per WP-059 section 21/36's own explicit allowance - not a failure of the analysis, and not a reason to manufacture a candidate.

## 18. Architectural Conclusion

The project's three permanently-mapped `IDENTITY_FIRST` targets remain the only ones with evidence strong enough (multiple converging signals: repeated property failure, meaningful identity success, sufficient sample size, and - via WP-053/056's own fresh controlled experiments - confirmed first-attempt causal evidence) to justify their status. The 16 remaining candidates with any historical evidence at all are consistently weaker on the dimension that matters most (order-confirmed, non-retrospectively-biased identity success) - zero of them have one. The project should not expand `IDENTITY_FIRST` further on the current evidence; the `Basillar artery` (`TIER_B_MONITOR`) thread is worth revisiting if future pilots accumulate more evidence, but does not justify a dedicated WP-060 today.

---

# Required Final Candidate Table

| Rank | Category | Target | Status | Score | Property Evidence | Identity Evidence | Main Failure | Evidence Quality |
|---|---|---|---|---:|---|---|---|---|
| 1 | אספקת דם | Basillar artery | TIER_B_MONITOR | 7 | 5/11 accepted | 1/2 accepted (after prior failure) | Historically source-role framing confusion (WP-042/044), largely mitigated | Strong sample size (23), weak identity-order evidence |
| 2 | גרעיני הבסיס | Corpos Striatum | TIER_B_MONITOR | 3 | 2/2 accepted | 1/1 accepted (order unknown) | N/A - small sample | Small sample, round-level-only records |
| 3 | מסילות עצביות | Medial Lemniscus Tract | TIER_B_MONITOR | 3 | 4/4 accepted | 1/1 accepted (order unknown) | N/A - small sample | Small sample, round-level-only records |
| 4 | מסילות עצביות | Corticospinal Tract | TIER_B_MONITOR | 3 | 2/7 accepted | 0/0 (no identity data) | Repeated non-property rejection (mostly classification/other) | Large sample (28), zero identity evidence |
| 5-16 | (various) | (various) | TIER_C_NOT_SUPPORTED | -2 to 2 | mixed, mostly high property acceptance | 0-1 accepted | Not demonstrated | See `evaluation/wp059_identity_first_candidate_analysis.json` |

# Required Final Architecture State

```text
Production strategy mapping:
UNCHANGED

New IDENTITY_FIRST mappings:
NONE

New production prompts:
NONE

New validators:
NONE

Retrieval changes:
NONE

Schema changes:
NONE

Retry changes:
NONE
```

# Required Final Decision

### Option B

```text
No Tier A candidate found.

No new controlled experiment is currently justified.
```

---

# Terminal Summary

```text
WP-059 complete.

Objective:
Systematically identify remaining target/category pairs
that justify a controlled IDENTITY_FIRST experiment.

Production strategy mapping:
UNCHANGED

Current permanent IDENTITY_FIRST targets:
Caudate Nucleus
Nucleus Accumbens
Globus Pallidus

Categories examined:
20 total canonical categories; 3 have any recorded generation-attempt
evidence (גרעיני הבסיס, אספקת דם, מסילות עצביות); 17 have none
(architectural fact - no deterministic target inventory exists for them).

Targets examined:
19 (category, target) pairs with recorded evidence (3 already
IDENTITY_FIRST, 16 candidates scored)

Targets with sufficient historical evidence:
16/16 candidates have >=2 recorded attempts; all 17 non-pilot categories
are INSUFFICIENT_DATA at the category level.

Tier A candidates:
0

Tier B candidates:
4 (Basillar artery score=7; Corpos Striatum, Medial Lemniscus Tract,
Corticospinal Tract all score=3)

Tier C candidates:
12

Insufficient-data targets:
17 categories (no target inventory or recorded evidence exists)

Strongest candidate:
אספקת דם + Basillar artery (TIER_B_MONITOR, not Tier A - only 1 accepted
identity attempt, occurring after prior failure)

Retrospective-bias analysis:
Zero candidates have an order-confirmed first-attempt identity success -
the single largest reason none reaches Tier A.

Candidate analysis artifact:
evaluation/wp059_identity_first_candidate_analysis.json

Human-readable analysis:
implementation/WP-059_CANDIDATE_ANALYSIS_REPORT.md

Production changes:
NONE

Prompt changes:
NONE

Validator changes:
NONE

Retrieval changes:
NONE

Schema changes:
NONE

Retry changes:
NONE

Full regression:
1440 passed, 0 failed (unchanged from WP-058 baseline)

Recommendation:
No controlled experiment currently justified.

Completion report:
implementation/WP-059_COMPLETION_REPORT.md

Waiting for architect review.
```
