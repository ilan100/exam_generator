# WP-022 Targeted Diagnostic — `תאי מערכת העצבים` / INDEPENDENT (5 independent runs)

Read-only diagnostic, real `QuestionProducer.from_default_configuration()`, real OpenAI API. Nothing modified (source code, prompts, configuration, schemas, retrieval, validators, retry behavior, attempt limits, category mappings, tests), no reruns, no sample replacement, no fix implemented.

Purpose: determine whether the WP-022 40-question acceptance run's exhaustion at this exact category/mode (position 38/40, all 3 attempts exhausted) reflects a recurring category-specific problem or is consistent with stochastic variance.

## 1. Per-run table

| Run | Outcome | Attempts | Accepted attempt | Key failure/rejection reason |
|---|---|---|---|---|
| 1 | accepted | 3 | 3 | Attempts 1-2: generation-contract failure (invented `...student_summary_1.pdf:0002:0002`) |
| 2 | accepted | 3 | 3 | Attempts 1-2: generation-contract failure (same chunk ID; attempt 2 also cited 2 more invented IDs) |
| 3 | accepted | 2 | 2 | Attempt 1: generation-contract failure (same chunk ID) |
| 4 | **exhausted** | 3 | — | All 3 attempts: generation-contract failure (same chunk ID, every single time) |
| 5 | accepted | 2 | 2 | Attempt 1: generation-contract failure (same chunk ID) |

Every accepted candidate (all 4) passed every validator (grounding/MCQ/category/quality/textbook) cleanly on its first real attempt - zero validator rejections anywhere in this sample.

## 2. Aggregate statistics

- Accepted: 4/5 (80%) - Exhausted: 1/5 (20%) - Operational failures: 0/5 (0%)
- Attempt distribution (accepted runs): attempt 2 -> 2, attempt 3 -> 2. Average attempts to acceptance: **2.50**. Max attempts used: 3.
- Total candidate attempts across all 5 runs: **13**. Generation-contract failures: **9** (69% of all attempts). Real candidates produced: 4. Attempts rejected by any validator: **0**.

## 3. Validator rejection distribution

Grounding: 0 - MCQ: 0 - Category: 0 - Quality: 0 - Textbook POTENTIAL_CONFLICT: 0. Multiple-validators-simultaneously: 0 (there was nothing to reject). The entire observed failure burden in this sample is generation-contract failures - none of it is validator rejection.

## 4. WP-019/020/021/022 observations

- **WP-019**: 9 generation-contract failures observed; 8 successfully recovered (runs 1, 2, 3, 5 all eventually produced an accepted candidate after 1-2 discarded attempts); 1 run (run 4) exhausted the 3-attempt budget with 3 consecutive contract failures - the exact class of exhaustion that caused the WP-022 40-question run to fail.
- **WP-020**: zero structured-output retry events in any of the 30 component-provider instances across all 5 runs - no malformed/truncated JSON occurred at all in this sample.
- **WP-021**: zero grounding or textbook provenance retries - every validator call that ran (on real, non-contract-failure candidates) returned valid provenance on the first try. WP-021 was simply never needed here; the problem is entirely upstream, at generation.
- **WP-022**: confirmed working correctly in every accepted attempt - `grounding_evidence_chunk_ids` were always genuine canonical `STUDENT_SUMMARY:...` strings correctly resolved from the model's `evidence_refs`; no local `Evidence N`/raw-integer reference ever appeared as canonical provenance anywhere in the captured data.

## 5. Repeated rejection patterns

**Observed repeatedly (9 of 9 failures, 100%)**: every single generation-contract failure across all 5 runs cited the exact same specific invented chunk ID - `STUDENT_SUMMARY:student_summary_1.pdf:0002:0002` - either alone (8 of 9 occurrences) or alongside 2 additional invented IDs once (1 of 9). This is not scattered/heterogeneous noise; it is one specific, highly reproducible hallucination the model repeatedly produces for this category. No other rejection pattern (ambiguous distractors, poor Hebrew, category drift, textbook conflict, etc.) was observed even once, since no validator ever rejected a candidate in this sample.

## 6. Comparison with the WP-022 40-question failure

1. **Did exhaustion happen again?** Yes.
2. **How often?** 1 of 5 runs (20%).
3. **Does one validator dominate?** No validator was involved at all - 100% of failures were generation-contract failures, not validator rejections.
4. **Similar or heterogeneous across runs?** Strikingly similar - the same specific invented chunk ID appears in every failed attempt across every run.
5. **Are generation-contract/provenance failures materially involved?** Yes - they are the entire observed failure mechanism; no provenance (WP-021) or structured-output (WP-020) failures occurred at all.
6. **Does this look systematically difficult for this category/mode?** The evidence points to something more specific than generic "difficulty": a recurring, specific hallucinated chunk ID (`...0002:0002`), not generally weak grounding, poor question quality, or category ambiguity - accepted candidates were uniformly clean.
7. **Consistent with stochastic variance?** Partially - acceptance still happens in most runs (4/5), and the exhaustion in run 4 is exactly "3 unlucky repeats of the same specific hallucination in a row," which is plausible under a per-call independent-probability model. But the fact that the same exact chunk ID recurs in 9/9 failures (not a variety of different invented IDs) is itself a notable, repeatable signal, not pure noise.

## 7. Final diagnostic classification

**B. POSSIBLE CATEGORY-SPECIFIC DIFFICULTY - MORE DATA NEEDED**

Evidence for a real, specific, reproducible issue: 100% of failures (9/9) cite the identical invented chunk ID, and it's plausible this maps to a genuine near-miss (e.g. `...0002:0001` is a real supplied chunk the model is off-by-one on) - but n=5 is too small to confirm this is category-specific versus a general generation-provenance pattern that happens to recur here by chance of retrieval content. No validator involvement was observed, so this is not evidence of quality/grounding/category difficulty specific to this topic - it is narrowly an upstream generation-provenance-hallucination signal.

No code, prompts, configuration, or retry behavior were changed. No fix implemented or recommended. Waiting for architect/user review.
