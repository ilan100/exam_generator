# WP-023 Completion Report — Partial Exam Completion and Per-Question Failure Reporting

## 1. Motivation

Every WP-018→WP-022 acceptance run fixed one specific failure mode only to have the next full 40-question run abort on a *different* one:

| WP | 40-question run result | Failure that aborted it |
|---|---|---|
| WP-019 | 16/40 | raw `pydantic.ValidationError` |
| WP-020 | 8/40 | `InvalidGroundingOutputError` |
| WP-021 | 26/40 | generation attempts exhausted (normal WP-013 mechanism) |
| WP-022 | 37/40 | generation attempts exhausted (`תאי מערכת העצבים`/INDEPENDENT) |

Rather than continuing to chase the next specific failure mode, WP-023 is a deliberate architectural pivot: an isolated **question-local** failure should no longer discard every other successfully-produced question in the run. Only a genuine **system-level** failure still aborts.

## 2. Question-local vs. system-level classification

Kept deliberately minimal (WP-023 section 6: "do not guess") — limited to exactly the classes the spec names explicitly:

**Question-local** (recorded as `FailedPlannedQuestion`, orchestration continues):
- `QuestionAttemptsExhaustedError` (WP-013's own bounded-regeneration exhaustion, which already subsumes WP-019 generation-contract failures within its attempt history)
- `InvalidGroundingOutputError` / `InvalidTextbookOutputError` (WP-021 provenance-recovery exhaustion)
- Duplicate-replacement exhaustion (WP-014's own exam-level duplicate protection)

**System-level** (still raises `QuestionProductionFailedError`, aborts the whole run — unchanged from WP-019's original `_KNOWN_OPERATIONAL_ERROR_TYPES`):
- `LLMError` (including `LLMResponseError`/`LLMStructuredOutputError`, `LLMAuthenticationError`, `LLMRateLimitError`, `LLMConfigurationError`, `LLMProviderError`)
- `GenerationError`, other `GroundingValidationError`/`TextbookValidationError` members (e.g. `NoValidationEvidenceError`)
- `RetrievalError`, `PromptError`
- a raw `pydantic.ValidationError`

**Correction made during implementation**: an earlier, broader draft additionally classified raw `ValidationError` and `LLMResponseError`/`LLMStructuredOutputError` as question-local (reasoning that they were "demonstrably local to one candidate/question"). This directly contradicted two pre-existing, deliberately-written tests (`test_invalid_structured_validator_output_is_an_operational_failure`, `test_structured_output_retry_exhaustion_is_a_contextualized_exam_failure`) that already asserted system-level/abort treatment for exactly these cases. The draft was reverted in favor of the minimal, spec-literal classification above.

## 3. Implementation summary

- `ExamOrchestrator._produce_unique_question()` no longer always raises on failure — it returns `QuestionProductionRecord | FailedPlannedQuestion`. A question-local failure is *returned*, not raised, mirroring the existing "a negative verdict is a normal result" principle one layer up. A system-level failure still raises `QuestionProductionFailedError` immediately; a genuinely unexpected exception still propagates uncaught.
- `QuestionProductionFailedError` was narrowed to represent only a system-level abort — `attempts_exhausted`/`duplicate_productions` fields removed (those cases no longer raise it at all), leaving `planned_question`, `completed_productions`, and a now-required `operational_cause`.
- `generate_exam()`'s loop continues past a question-local failure instead of propagating the first exception. Accepted questions are renumbered **contiguously 1..N** over accepted questions only (never gap-preserving) — each production's original planned position remains separately available (`QuestionProductionRecord.planned.position`).
- New models: `ExamGenerationStatus` (`COMPLETE`/`PARTIAL`, in `models/audit.py`), `FailedPlannedQuestion` (orchestration-level, reuses `QuestionAttempt`/`QuestionProductionResult`), `FailedQuestionAudit` (audit-level sibling to `QuestionAudit`).
- `ExamGenerationResult`/`ExamOutputBundle.exam` became `ExamOutput | None` — `None` only when every planned question failed (`ExamOutput.questions` structurally requires `min_length=1`, deliberately left unweakened per spec section 22).
- `QuestionAudit` gained `planned_position`, distinct from `number` (now purely the final clean-exam number) — the smallest extension avoiding overloading one field with two meanings.
- `ExamAudit` gained `status`, `planned_question_count`, `accepted_count`, `failed_count`, `failed_questions: list[FailedQuestionAudit]`; `questions`'s `min_length=1` relaxed to `default_factory=list` for the all-failed edge case. Two `model_validator`s enforce count bookkeeping and that every planned position 1..N is represented in exactly one of `questions`/`failed_questions`.
- `output/audit.py`'s `_validate_consistency()` extended to also check failed-question correspondence; its docstring's now-false "a rejected/exhausted result never reaches this layer" claim was corrected.
- CLI (`cli.py`) reports `COMPLETE` with the pre-existing one-line message; `PARTIAL` with `Requested:`/`Generated:`/`Failed:` counts plus each failed question's position/category/mode/reason — and **exits 0** in both cases, per the spec's explicit preference and to avoid conflating `PARTIAL` with the fatal case. The all-failed edge case writes only the audit file. `_classify_error()`'s now-unreachable `QuestionAttemptsExhaustedError`/`GenerationError`/`GroundingValidationError`/`TextbookValidationError` branches were removed.
- No retry-ownership changes anywhere — WP-013's `max_generation_attempts`, WP-019's generation-contract recovery, WP-020's structured-output retry, and WP-021's provenance retry are all completely unchanged.
- `schemas/exam_audit.schema.json` regenerated (`exam_output.schema.json`/`exam_request.schema.json` unaffected, confirmed byte-identical).

## 4. Testing

- Full regression: **940/940 passing** (up from the 917 baseline), zero network access, no `OPENAI_API_KEY` in the offline test shell.
- New/updated coverage: question-local vs. system-level orchestration scenarios (attempt exhaustion, provenance exhaustion, duplicate exhaustion, all-succeed, all-fail, mid-plan failure), renumbering-with-a-gap (explicit worked-example test), `ExamGenerationResult`/`ExamAudit`/`FailedQuestionAudit` model invariants, partial and all-failed audit/bundle construction and serialization round-trip, CLI `COMPLETE`/`PARTIAL`/all-failed/system-level-fatal behavior and exit codes, and one full-pipeline (`FakeLLMProvider`) integration test exercising a real `PARTIAL` result end-to-end through the output boundary.
- Existing tests that asserted abort-on-a-now-question-local-failure were updated (not weakened) to assert the new `PARTIAL`-result behavior instead, each with an explicit comment documenting the semantic change as intentional.

## 5. Live verification

**Smoke test** (1 category × 2 questions, real OpenAI API): exit 0, `status=COMPLETE`, `planned_question_count=2`, `accepted_count=2`, `failed_count=0`.

**Full 40-question acceptance run** (20 categories × 2 questions, real OpenAI API, no reruns/tuning/limit changes):

```
Exam generation completed with partial results.
Requested: 40
Generated: 39
Failed: 1

Failed planned questions:
  #2 - התעלה השדרתית ותכולתה - INDEPENDENT
    reason: QuestionAttemptsExhaustedError: generation attempts exhausted without an accepted candidate (3 attempt(s) made)
```

- **Exit code: 0** (previously, this exact failure would have aborted the entire 40-question exam at position 2/40 with zero usable output).
- Elapsed: ~14.8 minutes.
- `exam.json`: 39 questions, numbers contiguous 1..39.
- `audit.json`: `status=PARTIAL`, `planned_question_count=40`, `accepted_count=39`, `failed_count=1`; planned positions 1..40 verified to partition exactly across `questions`/`failed_questions` with no duplicates/gaps; numbering divergence confirmed correct (e.g. final `number=2` corresponds to `planned_position=3`, since planned position 2 failed).
- Human review: both `מבוא` questions (positions 38-39) are well-formed, unambiguous, and legible. No local `[Evidence N]`-style reference leaked into any canonical `evidence_chunk_ids` field anywhere in the audit (the one literal "Evidence" occurrence found was inside a model-generated `reason` prose string referencing the prompt-visible label — expected WP-022 behavior, not a provenance leak).

## 6. Explicitly deferred / out of scope

- The one failure observed in the acceptance run is WP-022's already-diagnosed residual issue (`evaluation/wp022_targeted_diagnostic_summary.md`): a highly reproducible generation-side hallucinated chunk ID for `תאי מערכת העצבים`-adjacent content. WP-023 does not fix this — it is now surfaced as one clearly-reported `PARTIAL` failure instead of aborting the whole exam. A possible future WP-024 could investigate generation-side local evidence references analogous to WP-022's validator-side fix.
- No change to `max_generation_attempts`, category-specific attempt budgets, retrieval/embeddings, acceptance policy, or validators.
- No REST API/GUI/checkpoint-resume/persistent-incremental-file features.

## 7. Status

WP-023 complete. Not starting WP-024 — awaiting architect/user review.
