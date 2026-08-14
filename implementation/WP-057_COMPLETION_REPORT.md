# WP-057 Completion Report — Permanent Globus Pallidus Identity-First Mapping

## 1. Objective

Implement the architect-approved decision from the WP-056 architecture review: permanently add `גרעיני הבסיס` + `Globus Pallidus` to the narrow `IDENTITY_FIRST` mapping, using the existing WP-054 strategy infrastructure. **Narrow production implementation** - no redesign of the strategy mechanism itself.

## 2. Architectural Decision Being Implemented

```text
Before WP-057:
גרעיני הבסיס + Caudate Nucleus     -> IDENTITY_FIRST
גרעיני הבסיס + Nucleus Accumbens   -> IDENTITY_FIRST
גרעיני הבסיס + Globus Pallidus     -> DEFAULT

After WP-057:
גרעיני הבסיס + Caudate Nucleus     -> IDENTITY_FIRST
גרעיני הבסיס + Nucleus Accumbens   -> IDENTITY_FIRST
גרעיני הבסיס + Globus Pallidus     -> IDENTITY_FIRST
everything else                     -> DEFAULT
```

Authorized by: WP-055 (diagnostic investigation) → WP-056 (controlled experiment: CONTROL 0/7 vs. EXPERIMENT 3/4 primary-success attempts) → WP-056 architecture review's explicit approval ("Add Globus Pallidus to the permanent narrow IDENTITY_FIRST mapping, subject to implementation in a separate WP").

## 3. Existing Strategy Mechanism Located

`src/exam_generator/generation/strategy.py`'s `_IDENTITY_FIRST_TARGETS_BY_CATEGORY: dict[str, frozenset[str]]` - exactly the mechanism the WP-056 architecture review identified. `resolve_strategy_preference(*, category, topic)` (same file) performs an exact-match lookup against this table and is called once per generation attempt by `QuestionGenerator.generate_candidate_question()` (`generation/generator.py`, unmodified since WP-054). No second mapping or parallel mechanism exists or was created.

## 4. Exact Production Change

One line changed in `src/exam_generator/generation/strategy.py`:

```diff
- "גרעיני הבסיס": frozenset({"Caudate Nucleus", "Nucleus Accumbens"}),
+ "גרעיני הבסיס": frozenset({"Caudate Nucleus", "Nucleus Accumbens", "Globus Pallidus"}),
```

The module docstring and `resolve_strategy_preference()`'s own docstring were updated to reflect the new mapping and cite the WP-055/WP-056 evidence chain (no behavioral change, documentation only). **This is the entire production behavior change.** No other production file was modified.

## 5. Files Changed

**Modified (production):**
- `src/exam_generator/generation/strategy.py` - the one-line mapping change (+ docstring updates).

**Modified (tests):**
- `tests/unit/test_strategy.py` - `test_case_3_globus_pallidus_in_basal_nuclei_is_default` renamed/flipped to `test_case_3_globus_pallidus_in_basal_nuclei_is_identity_first`; added `test_case_7_globus_pallidus_in_another_category_is_default` (category isolation), `test_globus_pallidus_externus_is_not_identity_first` and `test_gpe_abbreviation_is_not_identity_first` (exact-matching regression).
- `tests/unit/test_generation.py` - `test_globus_pallidus_generation_never_receives_the_identity_first_instruction` renamed/flipped to `test_globus_pallidus_generation_now_receives_the_identity_first_instruction`; added `test_globus_pallidus_outside_basal_nuclei_never_receives_the_identity_first_instruction`, `test_globus_pallidus_externus_never_receives_the_identity_first_instruction`, `test_caudate_and_nucleus_accumbens_still_receive_identity_first_alongside_globus_pallidus`.

**New (evaluation artifact, not production code):**
- `implementation/wp057_verification.py` - minimal, single-round production-path smoke verification (section 11).
- `evaluation/live_outputs/wp057_verification_record.json` - its result.

**Untouched (explicitly verified via `git status`/inspection):** `production/producer.py`, all five validators, `retrieval/*.py`, `models/target.py` (`QuestionTarget`), `planning/*.py`, every schema under `schemas/`, `config/*.yaml`, `prompts/generation/question.txt`, `prompts/context.py`, `prompts/formatting.py`.

## 6. Tests Added/Updated

6 net-new tests (3 in `test_strategy.py`, 3 in `test_generation.py`), plus 2 existing tests renamed to reflect the flipped expected behavior (not new tests - the same scenario, corrected expectation). See section 5 for the full list.

## 7. Strategy Resolution Results (OBSERVED, direct execution)

| Category | Target | Expected Strategy | Actual Strategy |
|---|---|---|---|
| גרעיני הבסיס | Caudate Nucleus | IDENTITY_FIRST | **IDENTITY_FIRST** |
| גרעיני הבסיס | Nucleus Accumbens | IDENTITY_FIRST | **IDENTITY_FIRST** |
| גרעיני הבסיס | Globus Pallidus | IDENTITY_FIRST | **IDENTITY_FIRST** |
| גרעיני הבסיס | Putamen (unrelated target) | DEFAULT | **DEFAULT** |
| אספקת דם (unrelated category) | Globus Pallidus | DEFAULT unless explicitly mapped | **DEFAULT** |
| גרעיני הבסיס | Globus Pallidus Externus (substring, not exact) | DEFAULT | **DEFAULT** |
| גרעיני הבסיס | (GPe) | DEFAULT | **DEFAULT** |

## 8. DEFAULT Fallback Verification

Confirmed by `test_case_4_another_target_in_basal_nuclei_is_default` (Putamen), `test_unknown_category_is_default`, and the two new exact-matching tests (`Globus Pallidus Externus`, `(GPe)`) - all PASS. The `_IDENTITY_FIRST_TARGETS_BY_CATEGORY.get(category, frozenset())` lookup pattern is structurally incapable of matching an unlisted target/category; no change to this fallback logic was made.

## 9. Category Isolation Verification

Confirmed by `test_case_7_globus_pallidus_in_another_category_is_default` (resolver-level) and `test_globus_pallidus_outside_basal_nuclei_never_receives_the_identity_first_instruction` (generator/prompt-level, mock LLM) - both PASS. `Globus Pallidus` under `אספקת דם` (or any category other than `גרעיני הבסיס`) resolves to `DEFAULT`, exactly as the pre-existing `Caudate Nucleus`/`Nucleus Accumbens` category-isolation tests already established.

## 10. Existing Identity-First Mapping Regression Verification

Confirmed by `test_case_1_caudate_nucleus_in_basal_nuclei_is_identity_first`, `test_case_2_nucleus_accumbens_in_basal_nuclei_is_identity_first`, and the new `test_caudate_and_nucleus_accumbens_still_receive_identity_first_alongside_globus_pallidus` (generator-level, both targets in the same test) - all PASS. Adding `Globus Pallidus` to the `frozenset` did not disturb either pre-existing member.

## 11. Production-Path Verification (OBSERVED, one real live round, no reruns)

Per WP-057 section 27's explicit cost-discipline instruction ("WP-057 should not run another 3×3 controlled experiment... at most, perform a minimal smoke verification"), one fresh, single round was run through the real, unmodified production path (`implementation/wp057_verification.py` - not production code, mirrors the WP-054/WP-056 verification-script pattern, records to `evaluation/live_outputs/wp057_verification_record.json`):

```text
permanent resolver: resolve_strategy_preference(category='גרעיני הבסיס', topic='Globus Pallidus') -> IDENTITY_FIRST
--- round start: target='Globus Pallidus' ---
--- round end: accepted=True attempts=1 ---
```

Question: `"איזה מהמבנים הבאים הוא Globus Pallidus?"` (a clean, reverse-framed identity question, matching the exact semantic WP-056 validated); correct answer: `"Globus Pallidus"`; all five validators passed (grounding, MCQ, category, quality all `true`/`valid`; textbook `CONSISTENT`); accepted on attempt 1. This confirms the permanent resolver → `IDENTITY_FIRST` → existing generation pipeline is genuinely wired together in production, not merely proven by mocked unit tests.

## 12. Full Regression Result

```text
.venv/bin/python -m pytest -q
1432 passed, 0 failed
```

Baseline (end of WP-056): 1426 passed. Delta: +6 (the net-new tests listed in section 5/6; two tests were renamed/flipped rather than added, so they are not part of this delta).

## 13. API Calls

One real OpenAI API call sequence: one generation call + up to five validator calls for the single production-path verification round (section 11) - accepted on attempt 1, so exactly one generation call and five validation calls were made, not the full 3-attempt budget. No other API call was made in this WP; the full regression suite (section 12) uses only mocked `LLMProvider` instances, as established throughout this project's test suite.

## 14. Production Behavior Changes

Exactly one: `resolve_strategy_preference(category="גרעיני הבסיס", topic="Globus Pallidus")` now returns `IDENTITY_FIRST` instead of `DEFAULT`. No other production behavior changed - confirmed by `git status`/inspection showing no other file under `src/exam_generator/` modified.

## 15. WP-056 Experiment Provenance

`implementation/wp056_experiment.py` and `evaluation/live_outputs/wp056_experiment_records.json` were **preserved, not deleted or modified** - per the WP-056 architecture review's explicit instruction ("Do not delete the evidence merely because the strategy is promoted... it is useful architectural provenance") and WP-057 section 28's identical instruction. No repository convention in this project requires deleting prototype/evaluation artifacts after a strategy is promoted (every prior WP's own prototype scripts - `wp050_architecture_probe.py` through `wp056_experiment.py` - remain in `implementation/` unmodified); this WP's own new verification script (`wp057_verification.py`) follows the same, now well-established convention.

## 16. Confirmation That WP-056 Experimental Code Is Not a Runtime Dependency

**Confirmed.** `grep -r "wp056_experiment"` across `src/` returns no matches - nothing in `src/exam_generator/` imports, references, or depends on `implementation/wp056_experiment.py` in any way. The permanent implementation (section 4) is a single dictionary-literal change in already-existing, already-reviewed production code, with no dependency on any experiment script.

## 17. Language-Rule Compliance

Unchanged and preserved. `Globus Pallidus` remains the required English representation for this target (via the pre-existing, unmodified `format_target_language_requirement()`, WP-041); no Hebrew representation was introduced for the target. The production-path verification (section 11) confirms this live: the correct answer text is `"Globus Pallidus"` verbatim, English, exactly as required. No prompt text, language-selection logic, or `QuestionTarget` field was touched by this WP.

## 18. Source-Authority Compliance

Unchanged and preserved. `resolve_strategy_preference()` performs no source access of any kind (confirmed unchanged by the pre-existing `test_resolve_strategy_preference_never_reads_the_historical_workbook` regression test, still passing). Student summaries remain the sole factual grounding authority (confirmed live: `grounding.passed = true` in section 11's verification, reasoning explicitly cites the supplied student-summary evidence); `course_book.pdf` remains a secondary consistency check (`textbook.status = CONSISTENT`); the historical Excel workbook remains style/structure/terminology reference only, never runtime strategy authority.

## 19. Architectural Conclusion

WP-057 implemented the architect-approved permanent mapping:

```text
גרעיני הבסיס + Globus Pallidus -> IDENTITY_FIRST
```

No other target/category mapping was changed. The change is the smallest possible extension of the already-accepted WP-054 mechanism - one `frozenset` member added, zero new abstractions, zero validator/retrieval/schema/retry changes - and is confirmed correctly wired end-to-end by both a deterministic mock-based test suite (1432 passed) and one real production-path live verification (accepted on attempt 1, clean reverse-framed identity question, all validators passed).

## 20. Explicit Final Mapping

```text
גרעיני הבסיס + Caudate Nucleus     -> IDENTITY_FIRST
גרעיני הבסיס + Nucleus Accumbens   -> IDENTITY_FIRST
גרעיני הבסיס + Globus Pallidus     -> IDENTITY_FIRST
everything else                     -> DEFAULT
```

---

# Required Mapping Table

| Category | Target | Expected Strategy | Actual Strategy |
|---|---|---|---|
| גרעיני הבסיס | Caudate Nucleus | IDENTITY_FIRST | IDENTITY_FIRST |
| גרעיני הבסיס | Nucleus Accumbens | IDENTITY_FIRST | IDENTITY_FIRST |
| גרעיני הבסיס | Globus Pallidus | IDENTITY_FIRST | IDENTITY_FIRST |
| גרעיני הבסיס | unrelated target (Putamen) | DEFAULT | DEFAULT |
| unrelated category (אספקת דם) | Globus Pallidus | DEFAULT unless explicitly mapped | DEFAULT |

# Required Change Table

| Area | Changed? | Details |
|---|---|---|
| Strategy mapping | YES | Added `"Globus Pallidus"` to the existing `גרעיני הבסיס` category's `frozenset` |
| Strategy resolver | NO | Reused existing `resolve_strategy_preference()` unchanged (only its docstring updated) |
| QuestionGenerator | NO | Unchanged |
| QuestionProducer | NO | Unchanged |
| Retrieval | NO | Unchanged |
| Validators | NO | Unchanged |
| Schemas | NO | Unchanged |
| Retry budget | NO | Unchanged |
| Target representation | NO | Unchanged |
| Prompt architecture | NO | Reused existing identity-first mechanism (`prompts/generation/question.txt` untouched) |
| Production language rule | NO | Preserved |

# Required Regression Table

| Test group | Result |
|---|---|
| Existing tests | PASS (all pre-existing tests, including the two flipped to their corrected expectation) |
| New WP-057 strategy tests | PASS (6/6) |
| Caudate mapping | PASS |
| Nucleus Accumbens mapping | PASS |
| Globus Pallidus mapping | PASS |
| DEFAULT fallback | PASS |
| Category isolation | PASS |
| Full suite | 1432 passed, 0 failed |

---

# Required Production Verification

```text
Globus Pallidus resolves to IDENTITY_FIRST:
YES

Caudate Nucleus remains IDENTITY_FIRST:
YES

Nucleus Accumbens remains IDENTITY_FIRST:
YES

Unmapped targets remain DEFAULT:
YES

Unmapped categories remain DEFAULT:
YES
```

---

# Terminal Summary

```text
WP-057 complete.

Objective:
Permanently add Globus Pallidus to the existing
גרעיני הבסיס IDENTITY_FIRST mapping.

Production change:
גרעיני הבסיס + Globus Pallidus
    DEFAULT -> IDENTITY_FIRST

Existing mappings:
Caudate Nucleus -> IDENTITY_FIRST
Nucleus Accumbens -> IDENTITY_FIRST

Fallback:
Unmapped targets/categories -> DEFAULT

Strategy mechanism:
Existing WP-054 mechanism reused

Production prompt redesign:
NONE

Validator changes:
NONE

Retrieval changes:
NONE

Schema changes:
NONE

Retry changes:
NONE

Target representation changes:
NONE

Tests added/updated:
6 new (3 test_strategy.py, 3 test_generation.py) + 2 flipped to corrected
expectation

Full regression:
1432 passed, 0 failed (baseline 1426 + 6 new)

Production-path verification:
PASS - one real live round, accepted on attempt 1, clean reverse-framed
identity question ("איזה מהמבנים הבאים הוא Globus Pallidus?"), all five
validators passed

WP-056 experimental artifacts:
Preserved (implementation/wp056_experiment.py,
evaluation/live_outputs/wp056_experiment_records.json) - not imported by
production, confirmed by source search

WP-054 mappings:
PRESERVED

Architectural conclusion:
WP-057 implemented the approved permanent
Globus Pallidus IDENTITY_FIRST mapping.

Completion report:
implementation/WP-057_COMPLETION_REPORT.md

Waiting for architect review.
```
