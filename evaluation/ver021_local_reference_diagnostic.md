# VER-021 Diagnostic — Feasibility of Call-Local Evidence References (E1/E2/E3)

Read-only architecture/contract diagnostic. No source code, prompts, schemas, configuration, tests, retrieval, validators, or audit/output models were modified. No LLM/OpenAI/API calls were made. Nothing committed.

## 1. Current grounding provenance path (traced end to end)

1. **`SourceEvidenceChunk.chunk_id` origin**: `src/exam_generator/chunking/chunker.py::_build_chunk_id(source_type, source_file, page, ordinal)` — deterministic, format `{SOURCE_TYPE}:{source_file}:{page:04d}:{ordinal:04d}` (e.g. `STUDENT_SUMMARY:student_summary_2.pdf:0071:0001`). Uniqueness enforced at corpus-construction time by `chunking/corpus.py` (`DuplicateChunkIdError`).
2. **Prompt formatting**: `src/exam_generator/prompts/formatting.py::_format_evidence_chunk(chunk, position)`, called from `format_student_summary_evidence()`. **Key finding**: each chunk is already rendered with a 1-based, call-local positional label:
   ```
   [Evidence 1]
   Source: student_summary_2.pdf
   Page: 71
   Chunk: STUDENT_SUMMARY:student_summary_2.pdf:0071:0001
   Text:
   ...
   ```
   `format_student_summary_evidence()`'s own docstring guarantees "caller-supplied order is preserved exactly" (tested).
3. **Chunk ID in the prompt**: on the `Chunk:` line, full canonical string. `grounding.txt` explicitly instructs the model to copy this line's value character-for-character into `evidence_chunk_ids`.
4. **Response field carrying provenance**: `GroundingValidationResult.evidence_chunk_ids: list[NonBlankStr]` (`src/exam_generator/models/validation.py`).
5. **OpenAI schema derivation**: `OpenAIProvider.generate_structured()` (`src/exam_generator/llm/openai_provider.py`) passes `GroundingValidationResult` directly as `text_format` to `client.responses.parse()`; the JSON Schema sent to the model is auto-derived from the Pydantic model's own field types/descriptions - no hand-maintained schema exists anywhere.
6. **Where returned IDs are verified**: `_validate_supporting_evidence_ids()` (`src/exam_generator/validation/grounding.py`) — builds `supplied_ids = {chunk.chunk_id for chunk in validation_evidence}` and rejects any returned ID not in that set.
7. **Where `InvalidGroundingOutputError` is raised**: same function, on any invented ID; also raised again by WP-021's retry loop in `GroundingValidator.validate_grounding()` if the retry attempt also fails.
8. **Storage in `QuestionAttempt`/audit**: `GroundingValidationResult` (unchanged, canonical IDs) is stored directly on `CandidateValidationResults.grounding` (`production/models.py`), then copied unchanged into `QuestionAttemptAudit.grounding` (`output/audit.py::_build_question_attempt_audit()`).
9. **Serialization**: `QuestionAttemptAudit`/`QuestionAudit` → `ExamAudit` → `serialize_audit_json()` (pydantic `model_dump_json()`); `schemas/exam_audit.schema.json` reflects `GroundingValidationResult.evidence_chunk_ids` as `list[string]`, no special format constraint.
10. **Downstream consumers of canonical IDs**: `QuestionProducer._validate_candidate()` (passes the result through unchanged), `output/audit.py` (copies unchanged), evaluation layer (`CandidateAttemptRecord` doesn't touch evidence IDs directly). **No consumer anywhere parses, pattern-matches, or depends on the specific string *format* of `chunk_id`** beyond exact-membership-in-the-supplied-set checks.

## 2. Full canonical IDs required from the LLM, or just possessed by the application?

**Every single downstream consumer only requires (B): the application to ultimately possess the canonical `chunk_id`.** None requires (A): the LLM itself producing the canonical string.

- `_validate_supporting_evidence_ids()` only needs *a* correct mapping to a supplied chunk — the LLM's own string is never used for anything except set-membership testing.
- `GroundingValidationResult.evidence_chunk_ids` is stored/serialized as-is; nothing requires those values to have literally come from the model's own typing of the canonical string, only that they *are* valid canonical IDs by the time they reach that field.
- Audit/output/schema: identical — canonical strings are expected, not "canonical strings the model wrote out."

**No place breaks** if canonical IDs are supplied by the model only *implicitly* (via a short reference the application resolves) rather than explicitly typed out.

## 3. Call-local reference feasibility

- **Where the mapping should be created**: inside `GroundingValidator.validate_grounding()` (and `TextbookValidator.validate()`), immediately after `validation_evidence`/`course_book_evidence` is fixed (retrieval already happens exactly once, before any retry loop) — `{i+1: chunk for i, chunk in enumerate(validation_evidence)}`.
- **Deterministic by evidence order**: yes — retrieval order is already fixed and preserved exactly by `format_student_summary_evidence()`'s existing contract; nothing today reorders evidence between logical or physical calls.
- **Is `E1`/`E2` sufficient?** Yes — a small positive integer (or `"E{n}"` string) is sufficient; the existing `[Evidence N]` label already IS this numbering, just not currently the citation target.
- **String vs. other representation**: a small integer (`int`, 1-based) is simplest and matches the `[Evidence N]` label already rendered; a string like `"E1"` is equally fine and slightly more prompt-friendly (avoids ambiguity with other numeric fields). Either is a one-line schema/prompt decision, not an architectural one.
- **Prompt formatting change**: minimal — `grounding.txt`/`textbook.txt` would say "cite by its `[Evidence N]` label" instead of "copy the `Chunk:` line verbatim." `_format_evidence_chunk()` itself needs **no change at all** (the label already exists).
- **Response model change**: new field (e.g. `evidence_refs: list[int]`, or a small LLM-facing model — see §8) replacing `evidence_chunk_ids` as what the LLM produces.
- **Where local-ref validation occurs**: same place as today (`_validate_supporting_evidence_ids()`), just checking `1 <= ref <= len(validation_evidence)` (bounds) instead of set-membership against long strings.
- **Where conversion back to canonical IDs occurs**: immediately after validation, inside the same validator method, before constructing the (unchanged) `GroundingValidationResult`.
- **Should `GroundingValidationResult` keep exposing canonical chunk IDs?** Yes — this is explicitly preserved; nothing downstream should ever see `E1`.

**Recommendation**: keep the local-reference mechanism entirely inside the prompt/validator boundary, exactly as VER-021 prefers — fully achievable, since retrieval, evidence-tuple construction, and the retry loop are all already validator-internal.

## 4. Strict provenance invariant

**Fully preserved — the mechanism is at least as strict as today, arguably stricter.** The invariant ("every canonical `evidence_chunk_id` recorded must correspond to a chunk actually supplied to that exact call") is enforced by bounds-checking a small integer against a list built from the *same* `validation_evidence` tuple the prompt was rendered from — structurally impossible to satisfy with a chunk that wasn't supplied, since there is no string-matching step at all (today's mechanism could theoretically accept a shortened/prefixed string that *happens* to equal a supplied ID as a substring coincidence — not currently observed, but a local-integer-reference removes that entire class of ambiguity by construction). Today's known failure modes — invented ID, missing prefix, shortened ID — become the single, simpler case of "out-of-range or non-integer reference," equally fail-closed, with zero fuzzy-matching, nearest-match, prefix-completion, or repair introduced anywhere.

## 5. WP-021 retry interaction

**The existing WP-021 loop already naturally supports this, with no structural change.** In both `GroundingValidator.validate_grounding()` and `TextbookValidator.validate()`, retrieval happens once and `messages` is built once, **before** the `for attempt in range(1, max_calls + 1)` loop; every physical/logical retry resubmits the *same* `messages` object unchanged. Since the E1/E2/E3 mapping would be derived from the same fixed `validation_evidence` tuple used to build those same `messages` once, the mapping is automatically identical across every WP-021 retry attempt — no renumbering, re-retrieval, or reordering risk exists, because the code structure that would cause that (retrieval or evidence-tuple construction *inside* the loop) is not present today and would not need to be introduced.

## 6. WP-020 interaction

**Confirmed independent; no changes required.** WP-020's retry (`OpenAIProvider.generate_structured()`) operates purely on whether the raw response text parses as JSON at all (`_is_malformed_structured_output()`, checking for a single `json_invalid` pydantic-core error) — it has no awareness of field *contents*, only of syntactic parseability. A local reference like `"E9"` or `9` that doesn't correspond to any supplied evidence is **syntactically valid** JSON (a well-formed small int/string in a well-formed list) — it would parse fine and reach the validator's own bounds-check, exactly like an invented long-string ID does today. `malformed JSON → WP-020` and `valid JSON + nonexistent reference → validator check / WP-021` remain fully separate, unchanged.

## 7. Audit compatibility

**Fully possible, with no broad refactoring.** `GroundingValidationResult`/`TextbookCheckResult` (the models that flow into `QuestionAttempt`, `QuestionAttemptAudit`, `ExamAudit`, and serialization) would remain **completely unchanged** — same fields, same types, same canonical-ID semantics. The conversion point is a single, well-defined model boundary: **inside the validator method, immediately after the local-reference response is verified and before the existing result model is constructed.** Nothing above that boundary (producer, orchestrator, output, audit, CLI, schemas) needs to know a local-reference mechanism exists at all.

## 8. Response-model design

**Option B is the clear best fit**: introduce a small LLM-facing intermediate response model (e.g. `GroundingValidationResponse`, carrying `evidence_refs: list[int]` instead of `evidence_chunk_ids: list[str]`, everything else identical to today's fields), then deterministically convert it into the existing, unchanged `GroundingValidationResult` (canonical `evidence_chunk_ids`) inside the validator, immediately after ref-validation.

This is not a novel pattern for this codebase — it is **exactly** the shape already established and working for generation: `GeneratedQuestionResponse` (LLM-facing, WP-009) is never exposed beyond `QuestionGenerator`; it is deterministically converted into the stable, canonical `CandidateQuestion` at that same boundary. Reusing this precedent for grounding/textbook is the smallest-diff option and keeps E1/E2 entirely non-leaking, per VER-021's explicit preference.

Option A (change `GroundingValidationResult` itself) is rejected: it would leak `E1`/`E2` into the audit/output contract, which VER-021 explicitly wants avoided and which would be a genuine (if small) breaking schema change for `schemas/exam_audit.schema.json`.

## 9. Textbook provenance

Same trace, for `TextbookCheckResult` / `_validate_textbook_provenance()` (`src/exam_generator/validation/textbook.py`):

- **`evidence_chunk_ids`**: identical situation to grounding (WP-018's primary, strictly-verified signal) — same local-reference mechanism applies identically, same `[Evidence N]` labels already exist via `format_course_book_evidence()` (reuses the same `_format_evidence_chunk()`).
- **`source_page`** — current purpose: an optional secondary provenance signal, checked against supplied evidence pages if present. Downstream dependency: none beyond the check itself; nothing in `QuestionProducer`/acceptance policy/audit reads it for any decision. **Redundant** once `evidence_chunk_ids`/a resolved local reference identifies the canonical chunk — the chunk's `.page` is already directly available via the resolved `SourceEvidenceChunk`, without the model needing to report it separately. Has it historically caused failures? Rarely — one rejection class exists in tests, no live-run failures observed in any WP-017 through WP-021 evaluation.
- **`reference_text`** — current purpose: optional secondary human-readable excerpt (demoted from primary signal in WP-018). Downstream dependency: none beyond its own check. **Redundant** for provenance purposes once a canonical chunk is resolved (`.text` is already fully available); its only remaining value is showing a human a *short* excerpt rather than a whole chunk. **Has historically caused failures repeatedly and significantly** — this exact field's verbatim-quoting fragility was the subject of two prior live-test-driven prompt fixes (WP-013, WP-014) before WP-018 finally demoted it to optional/secondary specifically because of this history.
- This diagnostic does **not** recommend removing either field now, per VER-021's explicit instruction — only reports that both are structurally redundant once local-reference resolution is adopted, and that `reference_text` in particular has a real history of being the more fragile, failure-prone field.

## 10. Generation provenance feasibility

`QuestionGenerator.generate_candidate_question()` (`src/exam_generator/generation/generator.py`) uses the **same** `format_student_summary_evidence()` formatting (same `[Evidence N]` labels already present) and the same canonical-ID-copying instruction pattern in `question.txt`, verified by `_validate_generated_provenance()`. **Technically, the identical local-reference mechanism is equally applicable here** — no structural obstacle. However, per VER-021's explicit instruction, this diagnostic does **not** recommend including generation in a future WP-022; it is reported separately for completeness only, since a future WP may deliberately choose to scope the change to validators alone first.

**Summary**: Grounding validator — feasible. Textbook validator — feasible (identical mechanism). Question generator — technically feasible via the identical mechanism, but explicitly out of proposed scope; a separate, later decision.

## 11. Historical-reference IDs

`HistoricalStyleReference.historical_question_id: PositiveIntStrict` — already a small positive integer (e.g. `1`, `5`), supplied to the prompt via `format_historical_reference()`, returned by the model as `GeneratedQuestionResponse.historical_reference_id: PositiveIntStrict | None`, and validated by exact-match against the one specific reference actually supplied (`_validate_generated_provenance()`'s `STYLE_SIMILAR` branch — `INDEPENDENT` mode requires it be `None`). **This field is already exactly the short/simple local-reference shape the proposed mechanism would introduce for evidence** — no transformation would be needed even if the concept were generalized. No evaluation run across WP-017 through WP-021 has recorded an operational failure attributable to `historical_reference_id` specifically (all recorded provenance failures were `evidence_chunk_ids`- or `reference_text`-related). Consistent with VER-021's own caution, this diagnostic does not recommend generalizing the fix to a field with no evidence of being unreliable.

## 12. Required changes inventory (for a possible future WP-022)

**MUST CHANGE**
| File | Class/Function | Change |
|---|---|---|
| `prompts/validation/grounding.txt` | prompt text | Instruct citation by `[Evidence N]` label instead of verbatim `Chunk:` line copy |
| `prompts/validation/textbook.txt` | prompt text | Same, for course-book evidence |
| `src/exam_generator/models/validation.py` (or a new module) | new `GroundingValidationResponse` (LLM-facing) | `evidence_refs: list[int]` replacing `evidence_chunk_ids` as the LLM-facing field; everything else unchanged |
| same | new `TextbookCheckResponse` (LLM-facing) | Same idea for textbook |
| `src/exam_generator/validation/grounding.py` | `_validate_supporting_evidence_ids()` → new equivalent | Bounds-check `evidence_refs` against `len(validation_evidence)`, then resolve to canonical `evidence_chunk_ids`; construct existing `GroundingValidationResult` after resolution |
| `src/exam_generator/validation/textbook.py` | `_validate_textbook_provenance()` → new equivalent | Same for textbook |

**SHOULD CHANGE**
| File | Change |
|---|---|
| `docs/ARCHITECTURE.md` | Document the LLM-facing-response-vs-application-result distinction for grounding/textbook, mirroring the existing generation-layer note |
| `tests/unit/test_grounding_validation.py`, `test_textbook_validation.py` | New tests per §13 |
| `tests/integration/*` | New composition scenarios (local-ref + WP-020 + WP-021) |

**DOES NOT NEED TO CHANGE**
`response_models` used elsewhere (MCQ/Category/Quality — untouched, no provenance concept); `GroundingValidationResult`/`TextbookCheckResult` (public shape, canonical IDs, unchanged); `QuestionAttempt`/`QuestionAttemptAudit`/`ExamAudit` (unchanged, still receive canonical IDs); output serialization (unchanged); `schemas/exam_audit.schema.json` (unchanged, since the audited model is unchanged — only `schemas/` files for any NEW LLM-facing model would need generating, and those aren't part of the existing three audited/output/request schemas at all since LLM-facing models have never been schema-exported); CLI (no awareness of any of this); retrieval/TF-IDF/chunking (fully untouched — `chunk_id` construction and retrieval order are exactly what the local-reference mapping relies on, unchanged); WP-019 generation-contract recovery (operates on `GeneratedQuestionResponse`, untouched unless generation is separately, later, included); WP-020 structured-output retry (confirmed independent, §6); WP-021's retry loop structure (confirmed compatible as-is, §5).

## 13. Testing implications (minimum, for a future WP)

- E1/E2 (or ref `1`/`2`) valid mapping resolves to the correct canonical chunk IDs.
- Unknown ref (e.g. `9` when only 1-3 supplied) rejected, fail-closed.
- A canonical chunk-ID string returned instead of a local ref is rejected (no silent dual-format acceptance).
- Mapping is deterministic and matches evidence order exactly (including for a single-chunk case and a max-`top_k`-chunk case).
- WP-021 retry reuses the identical mapping across both logical attempts (same `messages`, same resolved evidence tuple).
- `GroundingValidationResult`/`TextbookCheckResult` continue to expose only canonical `evidence_chunk_ids` downstream — audit/output never contain `E1`/`E2` anywhere, verified by direct serialization inspection.
- Hebrew evidence text is unaffected (formatting change is confined to the identifier scheme, not the text itself).
- Textbook equivalent: same test set, plus confirming `source_page`/`reference_text` behavior is unchanged (still optional, still checked when present).
- No regression to WP-020 (malformed-JSON tests continue to pass unchanged - independent mechanisms).
- No regression to WP-019/generation-contract handling (untouched unless generation is separately included).

## 14. Final assessment

### A. FEASIBLE — SMALL, LOCALIZED CHANGE

Supported directly by the code: the positional `[Evidence N]` labeling already exists in `_format_evidence_chunk()` and is already order-guaranteed; retrieval and evidence-tuple construction already happen exactly once, before any retry loop, in both validators; the "LLM-facing response → deterministic conversion → stable canonical application model" pattern is already proven and working for generation (`GeneratedQuestionResponse` → `CandidateQuestion`). The change is confined to two prompts, two small new LLM-facing response models, and the two validators' own provenance-check/construction logic — nothing above the validator boundary (production, orchestration, audit, output, CLI, schemas, retrieval) requires any change.

### Explicit answers

1. **Can the LLM stop reproducing full canonical chunk IDs?** Yes.
2. **Can strict fail-closed provenance be preserved?** Yes — equally strict, arguably stricter (no string-matching ambiguity at all).
3. **Can downstream code/audit continue seeing canonical chunk IDs?** Yes, unchanged, via conversion at the validator boundary.
4. **Can E1/E2 remain entirely internal to the LLM-facing boundary?** Yes.
5. **Would WP-021 still work?** Yes, unmodified structurally — the existing loop already reuses the same fixed messages/evidence across retries.
6. **Would WP-020 require changes?** No — confirmed independent (operates on JSON syntax, not field semantics).
7. **Should textbook use the same mechanism?** Yes — identical failure class, identical existing `[Evidence N]` labeling already present via the same formatting function.
8. **Could generation use it later if desired?** Yes, technically identical mechanism available, but explicitly out of this diagnostic's recommended scope.
9. **Are `source_page`/`reference_text` still needed for textbook validation?** Not for provenance correctness (both become redundant once a canonical chunk is resolved) - but this diagnostic does not recommend removing them now; `reference_text` in particular has a real history (WP-013/WP-014) of being the more fragile field, worth the architect's attention when this is actually implemented.
10. **Smallest likely implementation scope for a future WP-022**: two prompt-wording changes, two new small LLM-facing response models (one for grounding, one for textbook), and a rewrite of each validator's own provenance-check-and-construct step to bounds-check-and-resolve instead of string-match - no changes anywhere else in the architecture.

Nothing was implemented. Waiting for architect/user review before any WP-022 is defined.
