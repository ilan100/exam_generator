# WP-024 Completion Report — Generation-Side Local Evidence References

## 1. Implementation Summary

WP-022 removed fragile canonical chunk-ID reproduction from grounding/textbook *validation* by having the LLM cite small, call-local `evidence_refs` (matching the "[Evidence N]" prompt labels) instead of reproducing a canonical `SourceEvidenceChunk.chunk_id` string, with the application resolving those references deterministically. Question *generation* still used the older mechanism, and a post-WP-022 diagnostic (`evaluation/wp022_targeted_diagnostic_summary.md`) found this was now the dominant remaining generation reliability problem: repeated generation-contract failures caused by the model inventing a canonical chunk ID rather than selecting one actually supplied.

WP-024 applies the identical, already-proven WP-022 pattern to generation:

```
LLM (generation)
    evidence_refs: list[int]          (1-based, matching [Evidence N])
         ↓
QuestionGenerator._resolve_generated_evidence_refs()
    bounds-check against 1..len(supplied evidence)
         ↓
    resolve to genuine canonical SourceEvidenceChunk.chunk_id
         ↓
CandidateQuestion                     (unchanged - no evidence field, never has had one)
```

The LLM is never trusted to manufacture canonical provenance; an invalid reference fails closed exactly as an invented canonical string did before.

## 2. Exact Model/Contract Changes

- **`src/exam_generator/models/question.py`** — `GeneratedQuestionResponse.evidence_chunk_ids: list[NonBlankStr]` replaced with `evidence_refs: list[int]` (field description adapted from WP-022's grounding/textbook wording: cite the "[Evidence N]" number only, never a chunk identifier, never invent a number outside the supplied range, empty list preferred over guessing). Every other field on `GeneratedQuestionResponse` is unchanged. Docstring updated to describe the new resolution boundary.
- **`CandidateQuestion` is unchanged** — it carried no evidence field before WP-024 (a pre-existing WP-009/WP-015 decision: `QuestionGenerator` already validated-then-discarded any claimed provenance, since independent grounding validation never trusts generation's claims) and still does not. This was a deliberate design decision, not an oversight: the spec explicitly requires "Do not change `CandidateQuestion`'s canonical provenance contract," and the resolved canonical ids are used only transiently, inside the function that validates them, never attached to anything downstream.

## 3. Prompt Changes

`prompts/generation/question.txt` — the "if you report which evidence supports your answer" instruction was rewritten from "copy each identifier exactly, character for character, from that evidence item's 'Chunk:' line" to: cite the "[Evidence N]" number only, exactly as labeled; do not report the "Chunk:" identifier, a source file name, or any other text; never invent a number for an item not shown; leave `evidence_refs` empty rather than guessing. No other generation instruction was touched. The shared evidence formatter (`_format_evidence_chunk()`, `prompts/formatting.py`) was **not** modified — it still renders the canonical `Chunk:` line as informational text (shared with grounding/textbook validation and generation alike); the prompt now explicitly instructs the model not to reproduce that line.

## 4. Deterministic Local-Ref → Canonical-ID Mapping

`_resolve_generated_evidence_refs()` (`src/exam_generator/generation/generator.py`), called from `_validate_generated_provenance()` immediately after the structured response returns:

```python
def _resolve_generated_evidence_refs(evidence_refs, *, source_evidence):
    invalid_refs = [ref for ref in evidence_refs if not (1 <= ref <= len(source_evidence))]
    if invalid_refs:
        raise InvalidGeneratedOutputError(...)
    deduplicated_refs = list(dict.fromkeys(evidence_refs))
    return [source_evidence[ref - 1].chunk_id for ref in deduplicated_refs]
```

Mirrors WP-022's `_resolve_grounding_response()`/`_resolve_textbook_response()` pattern exactly, adapted for generation's shape (no result model to populate — the resolved list is used only to trigger the fail-closed check, then discarded, since `CandidateQuestion` has nowhere to put it).

## 5. Invalid-Reference Behavior

`0`, negative values, and out-of-range values (`> len(source_evidence)`) are all rejected identically — no special-casing between them — raising the existing, unchanged `InvalidGeneratedOutputError` (no new exception subtype was introduced; the existing hierarchy was judged sufficient, matching the spec's "reuse the existing `InvalidGeneratedOutputError` unless the current hierarchy strongly justifies a narrower subtype"). No fuzzy-matching, repair, clamping, or substitution exists anywhere in this path.

## 6. Duplicate-Reference Decision

A repeated reference (e.g. `[1, 1, 3]`) resolves to its canonical id only once, preserving first-occurrence order (`dict.fromkeys()` on the raw ref list before resolution) — matching the spec's preference ("preserving first occurrence while deduplicating canonical provenance"). Rationale: a duplicate citation is not additional evidence of anything a single citation didn't already establish. Directly tested (`test_resolve_generated_evidence_refs_deduplicates_preserving_first_occurrence`).

## 7. Historical-Reference Confirmation

`historical_reference_id` validation (`_validate_generated_provenance()`'s remaining logic, unchanged) was **not** touched or generalized to the local-reference pattern, per the spec's explicit instruction — historical-reference ids are small integers and were never identified as a reliability problem by the WP-022 diagnostic. Existing tests (`test_wrong_historical_reference_id_rejected`, `test_correct_historical_reference_id_accepted`, `test_independent_response_claiming_historical_reference_id_rejected`) pass unchanged.

## 8. WP-019/020/021/022/023 Interaction — Confirmed

- **WP-019**: an invalid `evidence_refs` value still raises `InvalidGeneratedOutputError`, so `QuestionProducer`'s existing bounded generation-contract recovery (discard, retry within the same `max_generation_attempts` budget) continues to work automatically with **zero code change**. Confirmed via existing WP-019 integration tests (`test_generation_provenance_violation_is_recovered_within_the_attempt_budget`, `test_generation_provenance_violation_exhausts_when_every_attempt_is_invalid`, `test_generation_provenance_violation_then_quality_rejection_then_accepted`), updated only to use an out-of-range `evidence_refs=[99]` instead of an invented string id, and passing unchanged in behavior.
- **WP-020**: structured-output retry remains fully independent — a syntactically valid but out-of-range `evidence_refs` value is ordinary JSON, never seen by `_is_malformed_structured_output()` (keyed on a single `json_invalid` pydantic-core error). No change was needed or made.
- **WP-021/WP-022**: grounding/textbook validator behavior is completely untouched. Their local-reference resolvers (`_resolve_grounding_response()`/`_resolve_textbook_response()`) were **not** refactored to share code with the new `_resolve_generated_evidence_refs()`, per the spec's explicit "avoid premature abstraction" instruction — each function is a handful of lines, tied to a different response/result model shape (grounding/textbook populate an existing result model; generation only needs the fail-closed check).
- **WP-023**: `PARTIAL`-result semantics are exercised unchanged — an exhausted generation-contract recovery from an invalid local reference is still question-local via `QuestionAttemptsExhaustedError`, exactly as before WP-024. No orchestration-layer code was touched.
- No additional retry layer was introduced anywhere.

## 9. Files Created/Modified

**Modified:**
- `src/exam_generator/models/question.py` — `GeneratedQuestionResponse.evidence_refs` field
- `src/exam_generator/generation/generator.py` — `_resolve_generated_evidence_refs()`, `_validate_generated_provenance()` updated
- `prompts/generation/question.txt` — evidence-citation instruction rewritten
- `docs/ARCHITECTURE.md` — new "Generation-Side Local Evidence References (WP-024)" section
- `docs/PROJECT_STATUS.md` — Current State, Implemented list, Tests section, Next WP Context
- `tests/unit/test_generation.py` — provenance tests rewritten for `evidence_refs`; new resolution-function tests
- `tests/unit/test_prompts.py` — new generation-prompt wording assertion
- `tests/integration/test_end_to_end_pipeline.py` — `_generated_response()` helper and invented-evidence scenarios updated; new no-leak integration test
- `tests/integration/test_structured_output_recovery.py` — `_generated_response()` helper and one invented-evidence scenario updated

**Created:**
- `implementation/WP-024_COMPLETION_REPORT.md` (this file)

**No changes:** `src/exam_generator/models/__init__.py` (no new exports needed), `src/exam_generator/validation/*` (WP-021/022 untouched), `src/exam_generator/orchestration/*`/`output/*` (WP-023 untouched), `src/exam_generator/retrieval/*` (unchanged), `schemas/*.schema.json` (confirmed byte-identical — `GeneratedQuestionResponse` is never exported into any schema).

## 10. Tests Added/Changed

- Unit (`test_generation.py`): replaced the four old string-based provenance tests with `test_valid_evidence_ref_accepted`, `test_multiple_valid_evidence_refs_accepted`, `test_empty_evidence_refs_accepted`, `test_zero_evidence_ref_rejected`, `test_negative_evidence_ref_rejected`, `test_out_of_range_evidence_ref_rejected`, `test_llm_cannot_inject_arbitrary_canonical_chunk_id`; added direct resolution-function tests: `test_resolve_generated_evidence_refs_preserves_supplied_ordering`, `test_resolve_generated_evidence_refs_deduplicates_preserving_first_occurrence`, `test_resolve_generated_evidence_refs_rejects_zero`, `test_resolve_generated_evidence_refs_rejects_negative`, `test_resolve_generated_evidence_refs_rejects_out_of_range`, `test_resolve_generated_evidence_refs_empty_list_resolves_to_empty`.
- Unit (`test_prompts.py`): `test_generation_prompt_asks_for_local_evidence_refs_not_canonical_ids`.
- Integration (`test_end_to_end_pipeline.py`): updated `_generated_response()` and 5 invented-evidence scenarios to use `evidence_refs=[99]`; added `test_generation_local_reference_never_leaks_downstream`.
- Integration (`test_structured_output_recovery.py`): updated `_generated_response()` helper and one invented-evidence scenario.
- All existing STYLE_SIMILAR/INDEPENDENT/Hebrew-mixed-terminology/historical-reference tests pass unchanged, confirming no regression in unrelated behavior.

## 11. Full Regression Result

**951 / 951 passing** (up from the 940 baseline entering WP-024; +11 net from WP-024's own additions), zero network access, no `OPENAI_API_KEY` in the offline test shell.

`scripts/generate_schemas.py` re-run: all three schema files (`exam_request.schema.json`, `exam_output.schema.json`, `exam_audit.schema.json`) byte-identical to before — confirmed, not assumed, via `git diff --stat schemas/` showing no changes.

## 12. Live Verification

### Small smoke test (1 category × 2 questions, real OpenAI API)

- Exit code: **0**
- `status=COMPLETE`, `accepted_count=2`, `failed_count=0`
- Resolved grounding evidence ids confirmed genuine canonical `STUDENT_SUMMARY:...` strings
- Zero `evidence_refs` occurrences in the serialized audit

### Full 2-per-category acceptance run (20 categories × 2 questions = 40 planned, real OpenAI API)

- **Planned count: 40**
- **Accepted count: 40**
- **Failed count: 0**
- **Status: COMPLETE**
- **Runtime: ~13.6 minutes** (816 seconds, START_TS=1786000196, END_TS=1786001012)
- **Exit code: 0**
- **Output files**: both `exam.json` (40 questions) and `exam_audit.json` written successfully
- **Generation-contract failures observed: 0** — zero invalid/out-of-range local evidence references occurred anywhere in this run
- **Invalid local-reference failures observed: 0** (same as above — no distinct category of this failure occurred)
- **Accepted-attempt distribution**: 31 questions accepted on attempt 1, 8 on attempt 2, 1 on attempt 3 (50 total attempts across 40 accepted questions)
- **Validator rejection distribution** (among the 10 "extra" non-first-attempt real attempts; a single attempt can trigger more than one validator's rejection simultaneously): quality 6, MCQ 4, grounding 2, textbook-conflict 1
- **WP-020/WP-021 retry observations**: not independently observable from the CLI/audit output for this run (the CLI does not expose `StructuredOutputRetryEvent`/`ProvenanceRetryEvent` counts, and no diagnostic script was run alongside it) — not fabricated, reported as unavailable per the spec's own instruction
- **Failed planned questions: none** (all 40 succeeded)

## 13. Human Review Findings

- Clean exam contains accepted questions only (40/40), zero structural defects (every question has exactly 4 distinct answers and a correct-answer id in 1-4).
- Numbering is contiguous 1..40, confirmed by direct check.
- No failed planned questions to represent in the audit (this run was fully `COMPLETE`).
- Canonical evidence ids confirmed real supplied chunk ids throughout the audit — a regex check against every `evidence_chunk_ids` entry in every attempt (grounding and textbook) found zero non-canonical (non-`STUDENT_SUMMARY:`/`COURSE_BOOK:`-prefixed) values anywhere.
- Zero `evidence_refs` or `[Evidence` leakage into either `exam.json` or `exam_audit.json`, confirmed by direct text search.
- Hebrew renders correctly throughout (spot-checked 6 questions across different categories); zero `\u`-escaped characters found in `exam.json` (`grep -c '\\u'` returned 0).
- The two `מבוא` questions (positions 39-40) are well-formed, unambiguous, and meaningfully distinct from each other (foramen magnum anatomical position vs. the midline separating brain hemispheres).
- Checked question-text distinctness across all 20 categories' 2-question pairs: zero identical pairs found.
- No obvious regression in question quality was observed in the reviewed sample.

## 14. Known Limitations / Deviations

- This is a single live acceptance run (n=1 at the full-exam level); the underlying stochastic generation-hallucination risk WP-022's diagnostic identified is reduced by removing the string-reproduction requirement, not proven eliminated at scale. WP-023's `PARTIAL`-result handling remains the system's safety net if the failure recurs in a future run.
- WP-020/WP-021 retry counts were not independently captured for this specific live run (the production CLI path does not surface them); this is a reporting limitation of the CLI, not a WP-024 defect, and matches the instruction not to fabricate unobserved metrics.
- No deviations from the WP-024 specification were made.

## 15. Confirmations

- **Retrieval/TF-IDF unchanged**: no file under `src/exam_generator/retrieval/` was modified; `FactualRetrievalIndex`, category resolution, and chunking are untouched by this WP.
- **No embeddings/vector DB introduced**: no new dependency was added (`pyproject.toml` unchanged); retrieval remains the existing TF-IDF mechanism exclusively.

---

WP-024 complete. Not starting WP-025 — waiting for architect/user review.
