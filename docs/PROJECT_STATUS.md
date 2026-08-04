# Exam Generator — Project Status

> This is the authoritative rolling implementation checkpoint shared by the user, GPT, and Claude Code. Claude updates it after every successfully completed Work Package. Keep it concise, factual, and current.

## Current State

* Last completed WP: **WP-017 — V1 integration and quality evaluation**
* Current/next planned WP: **WP-018**
* Overall phase: **Fresh implementation from approved project architecture**
* Repository implementation state: **WP-017 complete**

This repository is a clean reimplementation of the Exam Generator project on a new machine.

The project architecture and product requirements have already been established and MUST NOT be redesigned merely because the implementation is starting again.

Implementation will proceed sequentially from WP-008 using Work Packages supplied by GPT.

## Implemented

* Src-layout Python package skeleton (`src/exam_generator/`).
* External YAML configuration: `config/app.yaml`, `config/llm.yaml`, `config/category_mapping.yaml`.
* Typed/validated configuration models (`exam_generator.config.models`): `PathsConfig`, `GenerationBehaviorConfig`, `AppConfig`, `LLMGenerationParams`, `LLMValidationParams`, `LLMConfig`.
* Configuration loader (`exam_generator.config.loader`): `load_app_config()`, `load_llm_config()`, `find_project_root()`, `ConfigError`. Resolves the project root by walking upward for `pyproject.toml`, so it does not depend on the process's current working directory.
* `.env.example` documenting `OPENAI_API_KEY` (no real secret committed).
* `.gitignore` excluding `.venv/`, `.env`, `data/*` (source PDFs/Excel), and generated `output/`/`index/` contents, while keeping `config/`, `prompts/`, `schemas/`, `docs/`, `src/`, `tests/`, and `.gitkeep` placeholders trackable.
* Directory placeholders: `prompts/{system,generation,validation,ingestion}/`, `schemas/`, `output/`, `index/` (empty, `.gitkeep`-tracked where needed).
* Unit tests for configuration (`tests/unit/test_config.py`), 10 tests.
* Core domain models (`src/exam_generator/models/`): `GenerationMode`, `ExamQuestion`, `CandidateQuestion`, `candidate_to_exam_question()` (question.py); `ExamRequest`, `ExamOutput` (exam.py); `SourceType`, `SourceEvidenceChunk`, `HistoricalStyleReference` (source.py); `GroundingValidationResult` (with `.passed`), `MCQValidationResult`, `CategoryValidationResult`, `QualityValidationResult`, `TextbookCheckStatus`, `TextbookCheckResult` (validation.py); `QuestionAudit`, `ExamAudit` (audit.py). Shared strict-validation helpers (bool-rejecting positive ints, non-blank text, unit-interval floats, strict bool) live in the private `_common.py`.
* JSON Schema artifacts generated from the Pydantic models via `scripts/generate_schemas.py` (no network access, deterministic, re-running produces byte-identical output): `schemas/exam_request.schema.json`, `schemas/exam_output.schema.json`, `schemas/exam_audit.schema.json`, plus a hand-written `schemas/exam_request.example.json`.
* Unit tests for all new contracts (`tests/unit/test_models.py`), 97 tests, covering every case enumerated in WP-002 section 25.
* Historical workbook ingestion (`src/exam_generator/historical/`): loads `data/questions_full_export.xlsx` via `openpyxl` into WP-002 `HistoricalStyleReference` objects, and a read-only `HistoricalQuestionRepository` exposing all questions, canonical categories (first-seen order), exact per-category lookup, and total/per-category statistics. Fails closed with domain-specific exceptions on malformed workbooks/rows.
* Unit tests for historical ingestion (`tests/unit/test_historical.py`), 59 tests, using synthetic in-memory `.xlsx` fixtures built with `openpyxl.Workbook()` (no dependency on the real workbook for correctness tests).
* PDF text extraction (`src/exam_generator/ingestion/`): deterministic page-aware extraction of student-summary PDFs and `course_book.pdf` via PyMuPDF, into typed `ExtractedPage`/`ExtractedDocument` models; deterministic student-summary discovery and course-book resolution using the WP-001 configured data directory; domain-specific error hierarchy; fails closed when a document has no usable text anywhere.
* Unit tests for PDF ingestion (`tests/unit/test_ingestion.py`), 47 tests, using synthetic in-memory PDFs built with `pymupdf` itself (no extra test-only dependency, no committed binary fixtures).
* Factual-source chunking and corpora (`src/exam_generator/chunking/`): deterministic, character-based, boundary-aware chunking of `ExtractedDocument` pages into `SourceEvidenceChunk` objects (never spanning physical pages), stable deterministic chunk IDs, and read-only `FactualSourceCorpus` construction with per-source/per-page querying and statistics. `build_student_summary_corpus()`/`build_course_book_corpus()` provide the application-level entry points. New `chunking` section added to `config/app.yaml`/`ChunkingConfig`.
* Unit tests for chunking (`tests/unit/test_chunking.py`), 80 tests, using synthetic `ExtractedDocument` objects (no dependency on the real PDFs for correctness tests).
* Local lexical retrieval and category integration (`src/exam_generator/retrieval/`): deterministic character n-gram TF-IDF retrieval (`scikit-learn`) over a WP-005 `FactualSourceCorpus`, one-source-type-per-index enforcement, deterministic tie-breaking, zero-score filtering; canonical-category resolution/alias handling activating `config/category_mapping.yaml`; `ExamRequest` category resolution (with alias-count combination); category-based student-summary retrieval. New `retrieval` config section added to `config/app.yaml`/`AppConfig`; `config/category_mapping.yaml` schema changed from the WP-001 placeholder `aliases: {}` to the now-activated `mapping: {}`.
* Unit tests for retrieval/categories (`tests/unit/test_retrieval.py`), 71 tests, using synthetic corpora/resolvers (no dependency on the real PDFs/workbook for correctness tests).
* Provider-independent LLM abstraction + OpenAI provider (`src/exam_generator/llm/`): `LLMProvider` (abstract), `LLMMessage`/`MessageRole`/`LLMProfile` contracts, `build_llm_provider()` factory, `OpenAIProvider` using the OpenAI SDK's Responses API structured-output mechanism (`client.responses.parse(..., text_format=<any Pydantic model>)`). Focused LLM error hierarchy with OpenAI exception translation. `scripts/smoke_openai.py`: optional, non-pytest, one-request manual live smoke test.
* Unit tests for the LLM layer (`tests/unit/test_llm.py`), 49 tests, all OpenAI calls mocked - zero network access, no API key required.
* External prompt infrastructure (`src/exam_generator/prompts/`): `PromptId` (7 identities), immutable `PromptTemplate` (`prompt_id`, `text`, `required_variables`, `version`), `PromptRepository` (`.from_directory()`, `.from_default_location()`, `.get()`, `.prompt_ids`) that loads/validates/hashes every required prompt up front (fail-closed on missing/empty/whitespace-only/malformed files), strict `render_prompt()` (required-variable set must equal supplied set exactly), `build_prompt_messages()` (reuses WP-007 `LLMMessage`/`MessageRole`, never calls a provider), deterministic evidence/historical-reference/candidate-question/exam-question formatting helpers with explicit `--- BEGIN/END ... ---` source-role delimiting, and two prompt-context value objects (`GenerationPromptContext`, `GroundingPromptContext`) enforcing the `STYLE_SIMILAR`/`INDEPENDENT` × historical-reference invariant. Seven production prompt files added under `prompts/{system,generation,validation}/`.
* Unit tests for the prompt infrastructure (`tests/unit/test_prompts.py`), 110 tests, zero LLM/provider calls, zero network access, no API key required.
* First real question-generation path (`src/exam_generator/generation/`): `QuestionGenerator` (`generate_candidate_question(*, category, generation_mode) -> CandidateQuestion`, `.from_default_configuration()`), a new LLM-facing `GeneratedQuestionResponse` model (`src/exam_generator/models/question.py`), deterministic historical-reference selection for `STYLE_SIMILAR`, and application-side provenance validation that rejects any LLM-claimed evidence-chunk-id/historical-reference-id not matching the actual generation context. Wires together WP-006 retrieval, WP-003 historical data, WP-008 prompt infrastructure, and WP-007's LLM abstraction into exactly one LLM call per invocation - no retry loop.
* Unit tests for question generation (`tests/unit/test_generation.py`), 28 tests, LLM fully mocked, zero network access, no API key required.
* Independent grounding validation (`src/exam_generator/validation/`): `GroundingValidator` (`validate_grounding(candidate) -> GroundingValidationResult`, `.from_default_configuration()`), independent deterministic student-summary retrieval (never trusting generation-time claims), and provenance verification identical in spirit to WP-009's (any LLM-claimed supporting-evidence id not actually supplied is rejected). A negative grounding verdict is a normal return value, never an exception; provider/LLM failures remain distinguishable operational errors.
* Unit tests for grounding validation (`tests/unit/test_grounding_validation.py`), 22 tests, LLM fully mocked, zero network access, no API key required.
* **Live-test-driven prompt fix (WP-010, applies retroactively to WP-008/WP-009's prompt content)**: `prompts/generation/question.txt` and `prompts/validation/grounding.txt` were both updated to instruct the model to copy evidence-chunk identifiers character-for-character (including the `SourceType:` prefix) - the live smoke test found the model otherwise sometimes drops that prefix, which the (correct, working-as-designed) provenance checks in both WP-009 and WP-010 then reject as an invented id. See "Decisions Made (WP-010)" below.
* The three remaining primary candidate-quality validators (`src/exam_generator/validation/{mcq,category,quality}.py`): `MCQValidator.validate(candidate) -> MCQValidationResult`, `CategoryValidator.validate(candidate) -> CategoryValidationResult`, `QualityValidator.validate(candidate) -> QualityValidationResult`, each a small independently-constructible class (`from_default_configuration()` plus explicit DI), sibling to WP-010's `GroundingValidator`. No retrieval, no cross-validator dependency, no new prompt-context value object (reuses WP-008's `format_candidate_question()` directly).
* Unit tests for the three new validators plus cross-validator independence checks (`tests/unit/test_mcq_validation.py`, `tests/unit/test_category_validation.py`, `tests/unit/test_quality_validation.py`, `tests/unit/test_validation_independence.py`), 43 tests, LLM fully mocked, zero network access, no API key required.
* Secondary textbook consistency validation (`src/exam_generator/validation/textbook.py`): `TextbookValidator` (`validate(candidate) -> TextbookCheckResult`, `.from_default_configuration()`), independent deterministic course-book-only retrieval (never the student-summary index), and provenance verification of `source_page`/`reference_text` against the actual independently-retrieved course-book chunks. Empty course-book retrieval returns `TextbookCheckStatus.NOT_FOUND` directly without an LLM call (secondary evidence is optional, unlike primary grounding); a negative/inconclusive textbook verdict is a normal return value, never an exception, and never modifies or overrides `GroundingValidationResult`.
* Unit tests for textbook validation (`tests/unit/test_textbook_validation.py`), 25 tests, LLM fully mocked, zero network access, no API key required.
* Single-question production control layer (`src/exam_generator/production/`): `QuestionProducer.produce_question(*, category, generation_mode) -> QuestionProductionResult`, coordinating `QuestionGenerator` and all five validators into bounded, deterministic-acceptance regeneration. `CandidateValidationResults.accepted` (centralized derived property, mirroring `GroundingValidationResult.passed`) implements the V1 acceptance policy in plain Python - no LLM ever decides acceptance. Reuses the existing WP-001 `generation.max_generation_attempts` config value (no new configuration). `QuestionAttempt`/`QuestionProductionResult` preserve full attempt history; `QuestionAttemptsExhaustedError` (carrying every completed attempt) is raised if all attempts are rejected.
* Unit tests for the production control layer (`tests/unit/test_production.py`), 30 tests, LLM fully mocked, zero network access, no API key required.
* **Live-test-driven prompt fix (WP-013, applies retroactively to WP-008/WP-012's `prompts/validation/textbook.txt`)**: updated to require `source_page`/`reference_text` to correspond exactly to supplied evidence (character-for-character verbatim quoting, or left empty) - the live smoke test found the model otherwise sometimes paraphrases cited course-book text, which WP-012's existing provenance check then correctly rejects as unverifiable. See "Decisions Made (WP-013)" below.
* Exam orchestration (`src/exam_generator/orchestration/`): `ExamOrchestrator.generate_exam(request: ExamRequest) -> ExamGenerationResult`, turning a complete exam request into a complete `ExamOutput` by building a deterministic question plan (`build_exam_plan()`) and sequentially invoking WP-013's `QuestionProducer` once per planned question - never reimplementing generation/validation/acceptance/regeneration. Category/count resolution reuses WP-006's `resolve_exam_request_categories()` unchanged; generation-mode allocation follows the master brief's "alternate within each category" policy exactly (restarting at `STYLE_SIMILAR` per category); candidate → clean conversion reuses WP-002's `candidate_to_exam_question()` unmodified. Adds simple deterministic exact-duplicate protection (normalized-text comparison) with bounded, configuration-controlled replacement (`config/app.yaml`'s new `generation.max_duplicate_replacement_attempts`, distinct from WP-013's `max_generation_attempts`). Exam-level failure (`QuestionProductionFailedError`) preserves full diagnostic context (planned question, completed productions, and either the underlying attempt-exhaustion or duplicate-rejection history) rather than ever returning a silently partial exam.
* Unit tests for exam orchestration (`tests/unit/test_orchestration.py`), 28 tests, LLM fully mocked, zero network access, no API key required.
* **Live-test-driven prompt fix #2 (WP-014, applies to the same `prompts/validation/textbook.txt` WP-013 already modified once)**: fixed an ambiguity in WP-013's own just-added wording ("leave reference_text empty") that caused the model to return an empty string rather than omitting the field, which the existing `NonBlankStr` type correctly rejected as an operational failure. See "Decisions Made (WP-014)" below.
* `config/app.yaml`/`GenerationBehaviorConfig` gained one new field: `max_duplicate_replacement_attempts` (WP-014, `Field(gt=0)`, default `2`).
* Exam output and audit trail (`src/exam_generator/output/`): `build_exam_audit(generation_result, *, exam_id, generated_at, llm_config, diversity_target) -> ExamAudit` and `build_exam_output_bundle(...) -> ExamOutputBundle`, a pure, deterministic, **zero-LLM-call** transformation from a successful WP-014 `ExamGenerationResult` into the two separate WP-002 output contracts (clean `ExamOutput`, internal `ExamAudit`), plus `serialize_exam_json()`/`serialize_audit_json()`/`write_exam_json()`/`write_audit_json()`. `QuestionAudit` gained one new field (`attempts: list[QuestionAttemptAudit]`, min length 1) to preserve full per-attempt history, the smallest justified extension to the existing WP-002 contract. `historical_reference_id`/`evidence` are populated as `None`/`[]` - genuinely unavailable from current production history, represented honestly rather than fabricated (see "Decisions Made (WP-015)"). Deterministic cross-consistency checking (`AuditConsistencyError`) guards against a malformed `ExamGenerationResult`.
* Unit tests for the output/audit layer (`tests/unit/test_output.py`), 35 tests, plus 7 new tests in `tests/unit/test_models.py` for the new `QuestionAttemptAudit` model and `QuestionAudit.attempts` field - all offline, zero network access, no API key required (this WP makes no LLM calls at all, mocked or real).
* CLI and application entry point (`src/exam_generator/cli.py`): `exam-generator generate --request <path> [--exam-output <path>] [--audit-output <path>] [--force]` (installed console entry point via `pyproject.toml`'s `[project.scripts]`; also runnable as `python -m exam_generator.cli generate ...`). A thin adapter only: parses the request into the existing `ExamRequest`, calls `ExamOrchestrator.from_default_configuration().generate_exam()` and WP-015's `build_exam_output_bundle()`/`serialize_exam_json()`/`serialize_audit_json()` unchanged, writes both outputs atomically (temp file + `os.replace()`) only after both are fully serialized. Existing output files are never silently overwritten (`--force` required). `OPENAI_API_KEY` comes only from the environment (no `--api-key` argument exists); a missing key fails clearly (`LLMConfigurationError`) as soon as the orchestrator is constructed, before any real generation attempt. Three-value exit-code policy (`0`/`1`/`2`) via an ordered, most-specific-first exception-to-exit-code mapping; unrecognized exception types are deliberately re-raised with full traceback, never swallowed.
* Unit tests for the CLI (`tests/unit/test_cli.py`), 27 tests, orchestration boundary fully mocked, zero network access, no API key required; every test runs in an isolated `tmp_path` working directory (autouse fixture) so default-output-path tests can never touch the real project directory.
* `README.md` (new): user-facing CLI usage documentation, installation, configuration, exit codes.
* Evaluation layer (`src/exam_generator/evaluation/`): `CandidateEvaluationRunner` (wraps an existing `QuestionProducer`, recording every attempt/operational-failure without retrying), `RetrievalEvaluationRunner` (corpus-grounded, zero-LLM), `build_evaluation_plan()`, pure `metrics` functions, a 37-query corpus-grounded retrieval fixture (`retrieval_fixture.py`, every expected term independently verified present in the real corpus, re-checked fresh at evaluation time rather than hardcoded), and `render_markdown_report()`. `scripts/run_evaluation.py`: manual, non-pytest driver. Read-only observer over the existing pipeline - introduces no new generation/validation/retrieval/acceptance policy.
* `tests/integration/test_end_to_end_pipeline.py` (new `tests/integration/` directory): 10 end-to-end tests wiring real components (retrieval, prompts, provenance validation, acceptance, planning, duplicate detection, audit construction) with only the LLM call itself replaced by a small scripted `FakeLLMProvider`. No API key/network required.
* Unit tests for the evaluation layer (`tests/unit/test_evaluation.py`), 26 tests, synthetic data only, zero network access, no API key required.
* **Offline retrieval evaluation** (real corpus, no API key needed): Recall@3=86.5%, Recall@5=94.6%, Recall@8=94.6% across all 37 fixture queries spanning all 20 canonical categories; only 2 misses (`Cerebellum`, `Basal Ganglia`).
* **Live reduced-baseline evaluation** (2 runs, identical config: 5 categories x 2 questions/run = 20 planned questions total): found and fixed one evaluation-instrumentation gap (raw `pydantic.ValidationError` wasn't in the runner's known-operational-error set, so it crashed run 1 after processing most of the plan - a narrow fix per WP-017 section 3, not a production-code change) before completing run 2 cleanly. Combined result: **14 of 20 planned questions (70%) hit an operational failure**, 9 of those 14 (45% of all 20) the exact same root cause - an empty-string `QualityValidationResult.reason` field, at `validation_temperature=0.0`. Of the 7 attempts that *did* complete operationally, 6 (85.7%) were accepted, 5 of them on the first try - candidate *quality* was not the bottleneck in this sample; *operational reliability* was. See "Live Evaluation Baseline (WP-017)" below for full findings/recommendations.

No embeddings, vector databases, or semantic/neural retrieval have been implemented. All five candidate-quality validators (grounding, MCQ, category, quality, textbook) exist as independent single-purpose checks; WP-013 combines them into a working single-question production cycle; WP-014 combines multiple production cycles into a complete, deterministically-planned, duplicate-protected exam; WP-015 turns a successful exam-generation result into the two final, separated output artifacts; WP-016 exposes the complete pipeline as a real, installable command-line tool; WP-017 measured the assembled V1 system end-to-end and found its primary bottleneck to be operational reliability (a specific, reproducible structured-output failure mode), not retrieval quality or candidate-generation quality. The V1 architecture described in the master brief is fully implemented; WP-018 is expected to be reliability-hardening focused rather than another feature WP.

## Important Interfaces

Public domain models, importable from `exam_generator.models`:

* `GenerationMode` (str enum: `STYLE_SIMILAR`, `INDEPENDENT`)
* `ExamRequest` — `{"categories": {name: count}}`, structural validation only
* `ExamQuestion` — clean external question contract (`number`, `question`, `answer1..4`, `correct_answer` 1-4, `category`)
* `CandidateQuestion` — internal pre-acceptance representation (`question`, `answers` list[4], `correct_answer`, `category`, `generation_mode`)
* `candidate_to_exam_question(candidate, number)` — deterministic conversion
* `ExamOutput` — `{"questions": [ExamQuestion, ...]}`, enforces unique contiguous `1..N` numbering
* `SourceType` (str enum: `STUDENT_SUMMARY`, `COURSE_BOOK`)
* `SourceEvidenceChunk` — `chunk_id`, `source_file`, `page` (1-based), `text`, `source_type`
* `HistoricalStyleReference` — `historical_question_id` (positive int), `category`, `question`, `answers` list[4], `correct_answer`; structurally separate from `SourceEvidenceChunk`
* `GroundingValidationResult` — `grounded`, `correct_answer_supported`, `other_answers_not_equally_correct`, `evidence_chunk_ids`, `evidence_text`, `reason`, `confidence`; centralized `.passed` property
* `MCQValidationResult`, `CategoryValidationResult`, `QualityValidationResult`, `TextbookCheckStatus` (str enum: `CONSISTENT`, `NOT_FOUND`, `POTENTIAL_CONFLICT`), `TextbookCheckResult`
* `QuestionAudit`, `ExamAudit` — per-question and top-level audit contracts

JSON Schemas (regenerate via `python scripts/generate_schemas.py`, no network access, deterministic): `schemas/exam_request.schema.json`, `schemas/exam_output.schema.json`, `schemas/exam_audit.schema.json`; example request at `schemas/exam_request.example.json`.

Historical ingestion, importable from `exam_generator.historical`:

* `HistoricalQuestionRepository.from_workbook(path, sheet_name=None)` — load from an explicit path (used by tests/fixtures)
* `HistoricalQuestionRepository.from_default_location()` — load from the WP-001-configured `data` directory + fixed filename `questions_full_export.xlsx`
* Repository API: `.all_questions` (tuple, workbook order), `.canonical_categories` (tuple, first-seen order), `.questions_for_category(name)` (tuple, exact match only, empty tuple if unknown), `.total_questions`, `.category_count`, `.counts_per_category` (read-only `Mapping`)
* `load_historical_questions(path, sheet_name=None)` — lower-level function returning `(questions, categories_order)`
* `default_workbook_path()`, `DEFAULT_WORKBOOK_FILENAME`
* Error hierarchy: `HistoricalIngestionError` → `WorkbookNotFoundError`, `WorkbookFormatError`, `WorkbookSchemaError`, `HistoricalQuestionRowError`

PDF ingestion, importable from `exam_generator.ingestion`:

* `extract_pdf(path, source_type)` — required explicit `SourceType`; returns `ExtractedDocument`
* `ExtractedPage` — `page` (1-based), `text` (may be empty for a legitimate blank page); frozen
* `ExtractedDocument` — `source_file`, `source_type`, `pages` (`tuple[ExtractedPage, ...]`, min 1, enforced contiguous `1..N`); frozen
* `discover_student_summary_pdfs(data_dir=None)` — every `*.pdf` in the data dir except `course_book.pdf`, sorted by filename
* `default_course_book_path(data_dir=None)`, `DEFAULT_COURSE_BOOK_FILENAME`
* `load_student_summaries(data_dir=None)` / `load_course_book(data_dir=None)` — discovery/resolution + extraction combined
* Error hierarchy: `PdfIngestionError` → `PdfNotFoundError`, `PdfFormatError`, `PdfEncryptedError`, `PdfTextExtractionError`

Chunking/corpora, importable from `exam_generator.chunking`:

* `chunk_document(document, *, chunk_size, chunk_overlap) -> tuple[SourceEvidenceChunk, ...]`
* `FactualSourceCorpus` — `.all_chunks`, `.total_chunks`, `.source_files`, `.source_types`, `.chunks_for_source(name)`, `.chunks_for_source_and_page(name, page)`, `.chunk_count_per_source`, `.min_chunk_length`, `.max_chunk_length`, `.average_chunk_length`
* `build_student_summary_corpus(chunk_size=None, chunk_overlap=None, data_dir=None)` / `build_course_book_corpus(...)` — default chunk params come from `config/app.yaml`'s `chunking` section when not supplied
* Error hierarchy: `ChunkingError`; `CorpusConstructionError` → `DuplicateChunkIdError`
* Config: `exam_generator.config.models.ChunkingConfig` (`chunk_size`, `chunk_overlap`), new `AppConfig.chunking` field, `config/app.yaml`'s `chunking:` section (defaults `1800`/`300`)

Retrieval/categories, importable from `exam_generator.retrieval`:

* `FactualRetrievalIndex.from_corpus(corpus, *, source_type, top_k, ngram_range)` — one index = one `SourceType`, rejects mixed-source corpora
* `FactualRetrievalIndex.search(query, *, top_k=None) -> tuple[RetrievalResult, ...]` — best-first, rank starts at 1, zero-score results omitted, deterministic tie-break by corpus position
* `RetrievalResult` (`chunk`, `score` in `[0.0, 1.0]`, `rank`) — frozen, structurally separate from `SourceEvidenceChunk`
* `build_student_summary_retrieval_index(top_k=None, ngram_range=None, data_dir=None)` / `build_course_book_retrieval_index(...)`
* `CategoryResolver(canonical_categories, aliases)` — `.resolve(category)`, `.canonical_categories`
* `build_category_resolver()` — wires the real `HistoricalQuestionRepository` + `config/category_mapping.yaml`
* `resolve_exam_request_categories(request, resolver) -> ExamRequest` — combines alias-collapsed counts, preserves total
* `retrieve_for_category(category, resolver, index, *, top_k=None) -> tuple[RetrievalResult, ...]`
* Error hierarchy: `RetrievalError` → `RetrievalIndexError` (→ `SourceTypeMismatchError`), `RetrievalQueryError`; `CategoryResolutionError` → `UnknownCategoryError`, `InvalidCategoryMappingError`
* Config: `RetrievalConfig` (`top_k`, `ngram_min`, `ngram_max`), `AppConfig.retrieval`; `CategoryMappingConfig` (`mapping: dict[str,str]`), `load_category_mapping()`

LLM abstraction, importable from `exam_generator.llm`:

* `LLMProvider` (ABC) — `.provider_name`, `.model_name`, `.generate_structured(*, messages, response_model, profile)`
* `LLMMessage(role, content)` — `role` ∈ `MessageRole.{SYSTEM, USER, ASSISTANT}`, non-blank content, frozen
* `LLMProfile.{GENERATION, VALIDATION}` — selects the matching `config/llm.yaml` parameter section
* `build_llm_provider(llm_config, api_key=None) -> LLMProvider` — factory keyed on `llm_config.provider`; only `"openai"` supported
* `OpenAIProvider` (concrete) — `.from_config(llm_config, api_key=None, client=None)`, constructor accepts an injectable `client` for tests
* `API_KEY_ENV_VAR = "OPENAI_API_KEY"`
* Error hierarchy: `LLMError` → `LLMConfigurationError`, `LLMRequestError`, `LLMProviderError` (→ `LLMAuthenticationError`, `LLMRateLimitError`), `LLMResponseError` (→ `LLMRefusalError`)
* `scripts/smoke_openai.py` — optional manual live smoke test (not part of pytest)

External prompt infrastructure, importable from `exam_generator.prompts`:

* `PromptId` (str enum) — `SYSTEM`, `QUESTION_GENERATION`, `GROUNDING_VALIDATION`, `MCQ_VALIDATION`, `CATEGORY_VALIDATION`, `QUALITY_VALIDATION`, `TEXTBOOK_VALIDATION`
* `PromptTemplate` (frozen dataclass) — `prompt_id`, `text`, `required_variables` (`tuple[str, ...]`, derived from the template's actual placeholders), `version` (SHA-256 hex digest of the exact file bytes)
* `PromptRepository.from_directory(path)` / `.from_default_location()` (uses `config/app.yaml`'s existing `paths.prompts_dir`) — `.get(prompt_id) -> PromptTemplate` (raises `PromptNotFoundError` for an unknown id), `.prompt_ids`; construction fails closed on any missing/empty/whitespace-only/malformed required prompt file
* `render_prompt(template, **variables) -> str` — strict: supplied variables must equal `required_variables` exactly, or `PromptRenderError`; exactly one `str.format()` substitution pass, `{{`/`}}` is the literal-brace escape
* `build_prompt_messages(*, system_template, task_template, variables) -> (LLMMessage, LLMMessage)` — always `(SYSTEM, USER)`, reuses WP-007's `LLMMessage`/`MessageRole` directly, never calls a provider
* Formatting helpers (all pure/deterministic, no retrieval/selection, caller order preserved): `format_student_summary_evidence(chunks)` (≥1 chunk required), `format_course_book_evidence(chunks)` (empty allowed), `format_historical_reference(reference_or_None)`, `format_candidate_question(candidate)`, `format_exam_question(question)` — each evidence formatter labels its `--- BEGIN/END ... ---` section and rejects a chunk of the wrong `SourceType`
* `GenerationPromptContext(category, generation_mode, source_evidence, historical_reference=None)` / `GroundingPromptContext(candidate, source_evidence)` (frozen dataclasses) — `.render_variables() -> dict[str, str]`; `GenerationPromptContext` enforces `STYLE_SIMILAR` requires and `INDEPENDENT` forbids a `historical_reference`
* Error hierarchy: `PromptError` → `PromptRepositoryError` (→ `PromptNotFoundError`, `PromptTemplateError`), `PromptRenderError`, `PromptContextError`
* Production prompt files: `prompts/system/exam_generator.txt`, `prompts/generation/question.txt`, `prompts/validation/{grounding,mcq,category,quality,textbook}.txt`

Question generation, importable from `exam_generator.generation`:

* `QuestionGenerator(*, category_resolver, student_summary_index, historical_repository, prompt_repository, llm_provider)` — every dependency injected explicitly; `.generate_candidate_question(*, category, generation_mode) -> CandidateQuestion` makes exactly one `LLMProfile.GENERATION` call and performs no downstream validation
* `QuestionGenerator.from_default_configuration()` — normal application wiring (real resolver/index/historical repository/prompt repository/OpenAI provider); requires `OPENAI_API_KEY`
* Error hierarchy: `GenerationError` → `GenerationContextError`, `MissingEvidenceError`, `MissingHistoricalReferenceError`, `InvalidGeneratedOutputError`
* `GeneratedQuestionResponse` (in `exam_generator.models`) — the LLM-facing structured-output contract: `question`, `answers` (list[4]), `correct_answer` (1-4), `evidence_chunk_ids` (list, may be empty), `historical_reference_id` (optional); deliberately excludes `category`/`generation_mode`, which are always application-assigned

Independent grounding validation, importable from `exam_generator.validation`:

* `GroundingValidator(*, student_summary_index, prompt_repository, llm_provider)` — every dependency injected explicitly; `.validate_grounding(candidate: CandidateQuestion) -> GroundingValidationResult` makes exactly one `LLMProfile.VALIDATION` call, independently retrieves its own evidence, and performs no other validation stage
* `GroundingValidator.from_default_configuration()` — normal application wiring (real student-summary index/prompt repository/OpenAI provider); requires `OPENAI_API_KEY`
* Error hierarchy: `GroundingValidationError` → `NoValidationEvidenceError`, `InvalidGroundingOutputError`
* Deterministic V1 validation-retrieval query: `f"{candidate.category} {candidate.question} {<intended correct answer text>}"` (distractor text excluded)

MCQ/category/quality candidate-quality validation, also importable from `exam_generator.validation`:

* `MCQValidator(*, prompt_repository, llm_provider)` — `.validate(candidate: CandidateQuestion) -> MCQValidationResult`; `.from_default_configuration()`; exactly one `LLMProfile.VALIDATION` call using `PromptId.MCQ_VALIDATION`; no retrieval dependency
* `CategoryValidator(*, prompt_repository, llm_provider)` — `.validate(candidate: CandidateQuestion) -> CategoryValidationResult`; `.from_default_configuration()`; exactly one `LLMProfile.VALIDATION` call using `PromptId.CATEGORY_VALIDATION`; supplies only `candidate.category` as the judged category (`expected_category` prompt variable) — no alias resolution/reclassification dependency of any kind
* `QualityValidator(*, prompt_repository, llm_provider)` — `.validate(candidate: CandidateQuestion) -> QualityValidationResult`; `.from_default_configuration()`; exactly one `LLMProfile.VALIDATION` call using `PromptId.QUALITY_VALIDATION`; no retrieval dependency
* All three: dependencies injected explicitly (constructor DI, matching `GroundingValidator`'s pattern), `.from_default_configuration()` requires `OPENAI_API_KEY`, never mutate the candidate, make no other validator's LLM call, and a negative verdict (`valid=False`) is a normal successful return value — never an exception

Secondary textbook consistency validation, also importable from `exam_generator.validation`:

* `TextbookValidator(*, course_book_index, prompt_repository, llm_provider)` — `.validate(candidate: CandidateQuestion) -> TextbookCheckResult`; `.from_default_configuration()` (real course-book retrieval index/prompt repository/OpenAI provider; requires `OPENAI_API_KEY`); independently retrieves its own course-book-only evidence, never the student-summary index; makes **at most one** `LLMProfile.VALIDATION` call using `PromptId.TEXTBOOK_VALIDATION` — zero calls when independent retrieval finds no evidence at all (returns `TextbookCheckStatus.NOT_FOUND` directly instead)
* Error hierarchy: `TextbookValidationError` → `InvalidTextbookOutputError` (raised when a returned `source_page`/`reference_text` does not correspond to a course-book chunk actually supplied to the validator)
* Deterministic V1 textbook-retrieval query: `f"{candidate.category} {candidate.question} {<intended correct answer text>}"` (identical in shape to `GroundingValidator`'s, applied to the course-book index instead)
* Never mutates the candidate, never invokes `GroundingValidator`/`MCQValidator`/`CategoryValidator`/`QualityValidator`, never modifies a `GroundingValidationResult`; a `NOT_FOUND`/`POTENTIAL_CONFLICT` verdict is a normal successful return value — never an exception

Single-question production control layer, importable from `exam_generator.production`:

* `QuestionProducer(*, generator, grounding_validator, mcq_validator, category_validator, quality_validator, textbook_validator, max_attempts)` — every dependency injected explicitly; `.produce_question(*, category: str, generation_mode: GenerationMode) -> QuestionProductionResult`; `.from_default_configuration()` (real generator/all five real validators/`config/app.yaml`'s `generation.max_generation_attempts`; requires `OPENAI_API_KEY`)
* `CandidateValidationResults(grounding, mcq, category, quality, textbook)` — bundles the five existing, unmodified validator result models; `.accepted` (derived property, centralized V1 acceptance policy): `grounding.passed AND mcq.valid AND category.valid AND quality.valid AND textbook.status != POTENTIAL_CONFLICT`
* `QuestionAttempt(attempt_number, candidate, validations)` — one completed generate-then-validate attempt (1-based `attempt_number`); `.accepted` delegates to `validations.accepted`
* `QuestionProductionResult(candidate, attempts: tuple[QuestionAttempt, ...])` — the accepted candidate plus every attempt (including earlier rejections) that led to it
* Error hierarchy: `ProductionError` → `InvalidProductionConfigurationError` (`max_attempts < 1`), `QuestionAttemptsExhaustedError` (carries `.attempts`, every completed `QuestionAttempt`, when all attempts are rejected)
* `category`/`generation_mode` held fixed across every attempt; validators always run in the fixed order grounding → MCQ → category → quality → textbook, to completion, for every generated candidate; no LLM ever decides acceptance; operational failures (from generation or any validator) propagate immediately and consume no attempts; never mutates a candidate or validator result

Exam orchestration, importable from `exam_generator.orchestration`:

* `ExamOrchestrator(*, category_resolver, producer, max_duplicate_replacement_attempts)` — every dependency injected explicitly; `.generate_exam(request: ExamRequest) -> ExamGenerationResult`; `.from_default_configuration()` (real category resolver, real `QuestionProducer`, `config/app.yaml`'s `generation.max_duplicate_replacement_attempts`; requires `OPENAI_API_KEY`)
* `build_exam_plan(resolved_request: ExamRequest) -> tuple[PlannedQuestion, ...]` — pure, deterministic function; expects an already-canonicalized request (apply `resolve_exam_request_categories()` first); alternates `STYLE_SIMILAR`/`INDEPENDENT` starting at `STYLE_SIMILAR` for each category's own first question; `position` is global/1-based/contiguous across the whole plan
* `PlannedQuestion(position, category, generation_mode)` — one plan entry
* `QuestionProductionRecord(planned, production: QuestionProductionResult, duplicate_replacement_attempts)` — one accepted question's full production history
* `ExamGenerationResult(exam: ExamOutput, plan: tuple[PlannedQuestion, ...], productions: tuple[QuestionProductionRecord, ...])` — only ever constructed for a complete exam
* Error hierarchy: `ExamOrchestrationError` → `InvalidOrchestrationConfigurationError` (`max_duplicate_replacement_attempts < 1`), `QuestionProductionFailedError` (carries `.planned_question`, `.completed_productions`, and either `.attempts_exhausted` (WP-013 exhaustion) or `.duplicate_productions` (duplicate-replacement exhaustion) - never both)
* Duplicate detection: `_normalize_question_text()` (whitespace-collapse + casefold) exact-match only, no embeddings/semantic similarity/extra LLM call; bounded by `max_duplicate_replacement_attempts`, distinct from `QuestionProducer`'s own `max_attempts`
* Candidate → clean conversion via WP-002's unmodified `candidate_to_exam_question(candidate, number)`; `number` is always the plan's `position`, so exam ordering is exactly plan order
* Sequential (non-parallel) question production; category/count distribution always matches the canonicalized request exactly, never rebalanced across categories; a partial exam is never returned as complete

Exam output and audit trail, importable from `exam_generator.output`:

* `build_exam_audit(generation_result: ExamGenerationResult, *, exam_id: str, generated_at: datetime, llm_config: LLMConfig, diversity_target: float) -> ExamAudit` — pure/deterministic; every input beyond `generation_result` is caller-supplied, nothing invented internally (no `datetime.now()`, no internal config loading); raises `AuditConsistencyError` if the audit it would build does not correspond exactly to `generation_result.exam`
* `build_exam_output_bundle(generation_result, *, exam_id, generated_at, llm_config, diversity_target) -> ExamOutputBundle` — pairs `generation_result.exam` (reused unmodified) with the built audit
* `ExamOutputBundle(exam: ExamOutput, audit: ExamAudit)` — the two outputs kept structurally separate, never merged
* `serialize_exam_json(exam) -> str`, `serialize_audit_json(audit) -> str` — pydantic `model_dump_json(indent=2)`; non-ASCII/Hebrew preserved unescaped, enums as plain string values, `datetime` as ISO-8601
* `write_exam_json(path, exam)`, `write_audit_json(path, audit)`, `write_exam_output_bundle(*, exam_path, audit_path, bundle)` — write to exactly the caller-supplied path(s) (UTF-8), no timestamp/random-name policy, no other file touched
* Error hierarchy: `OutputError` → `AuditConsistencyError`
* Makes **zero LLM calls** — `llm_config: LLMConfig` is plain configuration data (`provider`/`model` strings from `config/llm.yaml`, no API key needed, no real `LLMProvider`/client ever constructed); no module in this package imports `exam_generator.llm`
* `QuestionAudit` (WP-002, extended WP-015) gained `attempts: list[QuestionAttemptAudit]` (new sibling model, min length 1) preserving every attempt (accepted or rejected); its pre-existing `grounding`/`mcq_validation`/`category_validation`/`quality_validation`/`textbook_check` fields continue to represent only the final/accepted attempt, unchanged in meaning; `historical_reference_id`/`evidence` are always `None`/`[]` from `build_exam_audit()` — genuinely unavailable from current production history, honestly represented as absent rather than fabricated

CLI, importable from `exam_generator.cli` (also the installed console entry point):

* `main(argv: Sequence[str] | None = None) -> int` — parses arguments, runs the `generate` subcommand, returns the process exit code; `if __name__ == "__main__": sys.exit(main())` for `python -m exam_generator.cli`
* `exam-generator generate --request <path> [--exam-output <path>] [--audit-output <path>] [--force]` — `--exam-output`/`--audit-output` default to `exam.json`/`exam_audit.json` in the current directory; no `--api-key` argument exists
* Exit codes: `EXIT_SUCCESS = 0`; `EXIT_GENERATION_FAILURE = 1` (`QuestionAttemptsExhaustedError`, `QuestionProductionFailedError`, `GenerationError`, `GroundingValidationError`, `TextbookValidationError`, `RetrievalError`, `PromptError`, `LLMError` (minus `LLMConfigurationError`), `AuditConsistencyError`); `EXIT_USAGE_ERROR = 2` (malformed/missing/invalid request JSON, `ConfigError`, `LLMConfigurationError`, `CategoryResolutionError`, existing output without `--force`, output-write `OSError`, `CliUsageError`)
* `CliUsageError` — local CLI-only exception for request/output-target problems that have no existing domain exception of their own
* Never accepts, prints, logs, or serializes `OPENAI_API_KEY`; a missing key surfaces as `LLMConfigurationError` as soon as `ExamOrchestrator.from_default_configuration()` is constructed, before any generation attempt
* Output-target existence is checked before calling the orchestrator (fails fast, avoids wasted API calls); both outputs are fully serialized before either is written; each file write is atomic (temp file + `os.replace()`)
* No new generation/validation/retrieval/acceptance/planning/duplicate policy of any kind — every step delegates to the already-existing `ExamOrchestrator`/WP-015 output functions unchanged

Evaluation layer, importable from `exam_generator.evaluation` (read-only observer; never imported by `production`/`orchestration`/`output`/`cli`):

* `CandidateEvaluationRunner(producer: QuestionProducer).run(plan) -> (list[CandidateAttemptRecord], list[OperationalFailureRecord])` — calls `produce_question()` once per planned item; catches `QuestionAttemptsExhaustedError` (records `.attempts` normally) and every type in `KNOWN_OPERATIONAL_ERROR_TYPES` (`LLMError`, `GenerationError`, `GroundingValidationError`, `TextbookValidationError`, `RetrievalError`, `PromptError`, `pydantic.ValidationError`) as an `OperationalFailureRecord`; never retries; anything else propagates
* `RetrievalEvaluationRunner(index, corpus).run(queries, top_k=8) -> list[RetrievalEvalResult]` — zero LLM calls; raises `UngroundedRetrievalQueryError` if a fixture entry's `expected_literal_term` is not actually present in the corpus being evaluated
* `build_evaluation_plan(categories, questions_per_category) -> tuple[(category, mode, position), ...]` — pure/deterministic, alternates `STYLE_SIMILAR`/`INDEPENDENT` per category (mirrors `orchestration.build_exam_plan()`'s policy without importing it)
* `RETRIEVAL_EVAL_QUERIES` — 37 corpus-grounded queries (`retrieval_fixture.py`), covering all 20 canonical categories (17 by exact category-name match, 3 by verified alternate term), Hebrew/English/mixed
* `metrics` module — pure functions: `candidate_acceptance_rate()`, `first_attempt_acceptance_rate()`, `attempts_per_accepted_question_stats()`, `exhaustion_rate()`, `validator_failure_counts()`, `textbook_status_distribution()`, `build_category_results()`, `recall_at_k()`, `retrieval_misses()`
* `CandidateAttemptRecord` — includes `question_text`/`answers`/`correct_answer` (populated only when `accepted=True`), added specifically to support WP-017's required human quality review
* `EvaluationConfig`/`EvaluationReport` — reproducibility metadata (model/params/chunking/retrieval/attempt-limit settings, canonical vs. evaluated categories, baseline type) plus the full structured result; `render_markdown_report()` formats a human-readable report; entirely separate from WP-002/WP-015's `QuestionAudit`/`ExamAudit`/`ExamOutputBundle` (never reused, never modified)
* `scripts/run_evaluation.py` — manual, non-pytest driver (`--categories`, `--questions-per-category`, `--baseline-type`, `--skip-generation`, `--output-dir`); writes `evaluation_report.{json,md}`, sequential only, no automatic reruns

## Established Requirements / Decisions

The following requirements and architectural decisions already exist and remain authoritative for this fresh implementation.

### Development Model

* User: product owner / final decision maker.
* GPT: architect, specification owner, Work Package author, and implementation reviewer.
* Claude Code: implementation engineer.
* Claude implements only the currently supplied Work Package.
* GPT reviews each completed WP before the next WP is issued.
* Do not implement future Work Packages early.
* Do not silently redesign established architecture.

### Application

* Python application.
* CLI interface for V1.
* Hebrew neuroanatomy multiple-choice exam generator.
* Ingestion/indexing is separate from exam generation.
* Local searchable index for V1.
* Retrieval/RAG architecture.
* Prompts and controllable configuration live outside Python application logic.
* Runtime LLM provider/model is externally configurable and replaceable.
* Initial provider may be OpenAI/GPT.
* Application logic must not depend directly on OpenAI outside the provider implementation.
* Credentials come from environment variables and must never be committed.

### Source Authority

1. Hebrew student-summary PDFs are the authoritative factual source.
2. Every accepted generated question must be grounded in textual evidence from at least one student summary.
3. `course_book.pdf` is secondary reference/validation only and cannot independently ground a question.
4. `questions_full_export.xlsx` is historical style/structure/difficulty/terminology reference only and must not be treated as factual grounding.
5. Categories are fixed and originate from the historical workbook's `category` column.

### Question Requirements

* Questions are written in Hebrew.
* Exactly four answer choices.
* Exactly one best/correct answer.
* Natural Hebrew/English anatomical terminology conventions should be preserved.
* The correct answer must be supported by student-summary evidence.
* The question must have one unambiguously best answer based on supplied evidence.

### Generation

Generation alternates within each category between:

* `STYLE_SIMILAR`
* `INDEPENDENT`

Similarity to historical questions or other newly generated questions is allowed.

Differentiation/diversity requirements may be progressively relaxed when necessary to fulfill requested counts.

Grounding and factual-validity requirements may never be relaxed.

Core rule:

**Fail closed on factual validity; relax on stylistic diversity.**

### Validation

* Generation and validation are separate LLM operations.
* The generator's own claim that a question is grounded must never be trusted as validation.
* Grounding must be independently evaluated against retrieved student-summary evidence.
* Structured LLM outputs must be explicitly validated.

### Output

Each successful exam generation eventually produces:

* `exam_<timestamp>.json`
* `exam_<timestamp>.audit.json`

The clean exam and internal audit/traceability information remain separate.

## Important Architectural Contracts

The durable architecture is defined by:

* `docs/MASTER_PROJECT_BRIEF.md`
* `docs/ARCHITECTURE.md`

These documents represent approved project decisions and remain authoritative even though implementation progress has been reset.

`docs/PROJECT_STATUS.md` represents only the implementation state of this new repository.

If implementation convenience conflicts with an established architectural decision, Claude must report the conflict rather than silently changing the architecture.

## Decisions Made (WP-002)

* `HistoricalStyleReference.historical_question_id` is typed as a strict positive integer. This was chosen after narrowly inspecting `data/questions_full_export.xlsx`'s `id` column (header + first rows only, via a temporarily-installed, not-committed `openpyxl`, immediately uninstalled afterward) to confirm real IDs are plain positive integers (1, 2, 3, ...) — no Excel ingestion was implemented, and no new project dependency was added.
* Domain modules are split as `models/{question,exam,source,validation,audit}.py` plus a private `models/_common.py` holding shared strict-validation type aliases (`NonBlankStr`, `PositiveIntStrict`, `CorrectAnswerId`, `UnitInterval`, `StrictBool`) used across the other five modules to avoid repeating the same bool-rejection/blank-rejection logic in ~15 places.
* `docs/ARCHITECTURE.md` updated with one small addition: `SourceType`'s exact enum values (`STUDENT_SUMMARY`, `COURSE_BOOK`) are now spelled out under Retrieval; all other WP-002 contract decisions were already pre-documented there ahead of this implementation and matched exactly, so no other architecture edits were needed.

## Decisions Made (WP-003)

* Row-level validation is delegated entirely to the existing `HistoricalStyleReference` pydantic model rather than re-implemented in the ingestion loader (e.g. no custom numeric-coercion function was written): pydantic v2's built-in lax `int` handling already coerces exact-integral floats (`3.0` → `3`) and clean numeric strings, rejects fractional floats (`3.5`) and non-numeric strings, and our existing `_reject_bool` before-validator already rejects `bool`. This matches WP-003's numeric-handling requirements exactly with no new code, and keeps ingestion unable to silently diverge from the WP-002 domain contract.
* Worksheet selection policy: if the workbook has exactly one worksheet, it is auto-selected; if more than one, an explicit `sheet_name` must be passed or ingestion fails clearly (`WorkbookFormatError`) rather than guessing. The real workbook (`data/questions_full_export.xlsx`) has exactly one worksheet, named `"Questions - Full"`.
* Canonical category ordering policy: first-seen order in workbook row order (not alphabetical, not a `set`), matching the WP's stated V1 preference.
* Duplicate-ID and unknown-category behavior: duplicate `id` values fail ingestion immediately (reporting the duplicated ID and both the duplicate and first-occurrence row numbers); `questions_for_category()` for an unknown category returns an empty tuple rather than raising, per the WP's stated preferred behavior.
* Default workbook filename (`questions_full_export.xlsx`) is a fixed constant (`DEFAULT_WORKBOOK_FILENAME`) combined with WP-001's configured `paths.data_dir`, rather than a new `config/app.yaml` field — there is only one historical workbook in V1, so a dedicated config field would add complexity without benefit (per the WP's own guidance not to add configuration without clear benefit). `config/app.yaml` and the WP-001 config model/tests were therefore left unchanged.
* `openpyxl` added as a genuine runtime dependency in `pyproject.toml` (`openpyxl>=3.1`, installed version `3.1.5`), verified working under the project's Python 3.12.3 environment.

## Decisions Made (WP-004)

* **PDF library: PyMuPDF (`pymupdf`)**, not pypdf/pdfminer/pdfplumber. Chosen after directly extracting from the real `student_summary_1.pdf` with both PyMuPDF and pypdf: PyMuPDF returned Hebrew in correct logical reading order and ran in ~0.17s for 77 pages, while pypdf returned Hebrew *visually reversed* (e.g. `ןילוסא ריש` instead of `שיר אסולין`), emitted dozens of "Ignoring wrong pointing object" xref warnings, and took ~2.3s (≈14x slower) for the same file. pypdf was installed only for this comparison and uninstalled immediately after; it was never added as a project dependency.
* `pymupdf.open(path, filetype="pdf")` is called with an explicit `filetype="pdf"` rather than relying on PyMuPDF's extension-based auto-detection. Discovered during testing: MuPDF auto-detects format from the file extension, so a plain `.txt` file was silently "opened" as a one-page text document instead of failing — forcing `filetype="pdf"` makes any non-PDF content fail clearly with `PdfFormatError`, as WP-004 requires.
* Blank-page policy: an individual page may have empty extracted text without failing the document (real PDFs have legitimate blank/divider pages — e.g. course_book.pdf has 18, confirmed to be section-boundary pages by inspection, not extraction failures); only a document with **zero** non-blank pages fails (`PdfTextExtractionError`).
* Encrypted-PDF detection: `document.is_encrypted and not document.authenticate("")` — checked immediately after opening, before any per-page extraction is attempted, so encrypted input never reaches the extraction loop.
* Source discovery: every `*.pdf` file in the configured data directory is treated as a student summary except the fixed `course_book.pdf` filename (mirrors WP-003's fixed-filename pattern for the historical workbook — no new `config/app.yaml` field, since there is exactly one course book by design). Discovery ordering is lexical by filename.
* Package structure deviates slightly from the WP's suggested `{__init__, pdf, models, errors}.py`: a `discovery.py` module was added to separate source-discovery/resolution policy (which PDFs count as "student summary", where the course book lives) from the generic, source-agnostic `extract_pdf()` API in `pdf.py` — mirroring the loader/repository separation already used in WP-003's `historical` package.
* Zero-page-PDF handling (`PdfFormatError` on `page_count == 0`) is implemented defensively but **not exercised by a real test**: PyMuPDF itself refuses to save a zero-page document (`ValueError: cannot save with zero pages`), so no such fixture is constructible with the selected library, matching WP-004's own "if constructible with the selected library" qualifier on that test case.

## Decisions Made (WP-005)

* **Chunk-ID format**: `"{source_type}:{source_file}:{page:04d}:{ordinal:04d}"` — chosen for readability (matches the WP's own suggested example) and because it structurally guarantees uniqueness whenever source type, source file, page, or within-page ordinal differs, without any hashing/UUID component.
* **Boundary search window**: `max(1, chunk_size // 4)` characters, a fixed fraction of the configured `chunk_size` rather than a separate config knob — kept as a private, documented constant per the WP's own preference ("a clearly named constant/private policy" over "a large configuration surface").
* **Boundary preference order**: newline → Hebrew/English sentence-ending punctuation (`. ? !`) → any whitespace → hard split, implemented as a bounded backward search from the tentative chunk end (never earlier than `start + 1`, guaranteeing forward progress even in pathological configurations like `chunk_overlap = chunk_size - 1`).
* Package structure: `chunking/{errors,chunker,corpus}.py` plus `__init__.py` — mirrors the `historical`/`ingestion` packages' loader/repository-style separation (generic algorithm vs. corpus abstraction vs. errors).
* A single generic `FactualSourceCorpus` class backs both corpora (per the WP's explicit option to avoid over-engineering two near-identical wrapper classes); separation between student-summary and course-book material is enforced entirely by construction (`build_student_summary_corpus()`/`build_course_book_corpus()` never mix chunks from the two source types into one corpus instance), not by the class itself refusing mixed `source_type`s.
* `ChunkingConfig`'s bool-rejection helper (`_reject_bool`) is defined locally in `config/models.py` rather than imported from `exam_generator.models._common`, to avoid introducing a `config → models` package dependency; this duplicates ~3 lines of logic already used by the domain-model layer, which was judged preferable to a cross-layer import for a foundational config module.
* Chunk text is `.strip()`-ped only at emission time (leading/trailing whitespace); all boundary-offset arithmetic operates on the original untouched page text, so overlap/boundary calculations are unaffected by the trim.

## Decisions Made (WP-006)

* **Retrieval baseline: `scikit-learn` char n-gram TF-IDF** (`analyzer="char_wb"`, `ngram_range=(3,5)`), installed version **1.9.0**. The analyzer is kept as a fixed internal constant rather than configuration (explicitly permitted by the WP when only one analyzer is supported in V1), keeping the validated config surface to just `top_k`/`ngram_min`/`ngram_max`.
* **Zero-score tolerance**: `1e-9`, applied to absorb floating-point noise around true-zero cosine similarity (not a meaningful similarity threshold) - documented in `exam_generator/retrieval/index.py` and `docs/ARCHITECTURE.md`.
* **`config/category_mapping.yaml` schema changed** from WP-001's placeholder `aliases: {canonical: [alias, ...]}` shape (never populated, never consumed by any code) to the WP-006-suggested `mapping: {alias: canonical}` shape, since this WP is the one that "activates" the file and no real content existed to migrate. `CategoryMappingConfig` validates structural non-emptiness only; cross-checking alias targets against real canonical categories happens in `CategoryResolver`, which needs the historical repository.
* **Alias-collision rule**: any alias *key* that equals an existing canonical category name is rejected outright at resolver construction (`InvalidCategoryMappingError`), rather than only rejecting when its target differs from itself. This is a stricter, simpler, and unambiguous reading of the WP's rule ("an alias key that exactly equals an existing canonical category must not redirect that canonical name to a different category") - a same-name self-alias would be redundant configuration with zero benefit.
* `CategoryMappingConfig`'s bool/blank-rejection helpers are defined locally in `config/models.py` (not imported from `exam_generator.models._common`), continuing the same config-layer-purity rationale already established for `ChunkingConfig` in WP-005. `RetrievalResult.rank`, by contrast, *does* import `PositiveIntStrict` from `exam_generator.models._common`, since `exam_generator.retrieval` is an application-level package that (like `historical`/`ingestion`/`chunking`) already legitimately depends on `exam_generator.models` - only `config` avoids that dependency direction.
* Package structure: `retrieval/{errors,models,index,categories}.py` (matches the WP's own suggested structure exactly).

## Known Retrieval-Quality Observations (WP-006, for architect review)

* **Canonical-category retrieval (the actual production use case) is healthy**: querying every one of the 20 real canonical categories against the student-summary index returned 8/8 positive results for all 20 - zero categories with no results. Scores ranged `0.088`–`0.486`; the weakest were `מבוא` ("Introduction", 0.088 - a generic/short category name with little distinctive vocabulary) and `חדרי המוח` ("ventricles", 0.136).
* **Short/common-term exact-match ranking is imperfect**: for single short terms (e.g. `trabeculae`, `קליפת המוח`), the literal containing chunk is reliably present in the top 3–5 results but not always ranked #1 - a different chunk with more overlapping character n-grams can score marginally higher. Longer, more distinctive queries (full canonical category names, two-word English terms like `Medulla Oblongata`) rank the correct chunk #1 reliably. This is an expected characteristic of a character-n-gram TF-IDF baseline on short queries, not a broken implementation, and is exactly the kind of finding WP-006 asked to be surfaced honestly rather than tuned around.
* **Multi-column PDF text interleaving**: one inspected student-summary chunk (page 32) showed Hebrew "קליפה" (cortex) and its English gloss "cortex" interleaved/fragmented mid-word (`"קליפ cort ex"`), apparently from PyMuPDF's default reading-order handling of a multi-column layout. The chunk remains topically on-subject (discusses gray/white matter and cortex) and is not corrupted Unicode - just non-linear reading order in that specific passage. This is an extraction-layer (WP-004) characteristic, not something WP-006 attempted to fix; noted here since it surfaced during retrieval-quality inspection.
* No category or query produced garbled/corrupted Unicode; no action was taken to "fix" any of the above per the WP's explicit instruction not to solve retrieval-quality issues in this WP.

## Decisions Made (WP-007)

* **Structured-output mechanism: the OpenAI Responses API** (`client.responses.parse(model=..., input=[...], text_format=response_model, temperature=..., max_output_tokens=...)`), inspected directly on the installed SDK rather than assumed from older documentation/examples (the SDK also exposes the older `client.beta.chat.completions.parse`/`client.chat.completions.parse`, but Responses + `text_format` is the current first-class mechanism and returns `response.output_parsed` as a ready validated Pydantic instance).
* **`max_retries=0` on the constructed OpenAI client** (SDK default is 2): explicitly disables transport-level retries so `generate_structured()` always corresponds to exactly one logical application LLM call, per the WP's own preferred architecture ("provider call = one logical application LLM call") - documented in `docs/ARCHITECTURE.md` per the WP's explicit request to record this decision.
* **Error hierarchy nesting** (WP's suggested list was flat): `LLMAuthenticationError`/`LLMRateLimitError` nested under `LLMProviderError`; `LLMRefusalError` nested under `LLMResponseError`. One addition beyond the WP's suggested names: `LLMRequestError` (direct child of `LLMError`) for caller-input problems that must fail before any provider call (currently: empty message sequence) - mirrors `RetrievalQueryError`'s role from WP-006.
* **`LLMProvider` is an ABC**, not a `Protocol` - the WP explicitly permitted this "if there is a clear reason"; a concrete factory-constructed hierarchy (one real implementation today, future providers subclassing it) fits an ABC more naturally than structural typing.
* Refusal detection inspects `response.output` for any `content.type == "refusal"` item *before* falling back to `response.output_parsed is None`, so a refusal produces a specific, informative `LLMRefusalError` (with the model's stated refusal reason) rather than a generic "no parsed response" error.
* Package structure: `llm/{errors,models,provider,factory,openai_provider}.py` (matches the WP's own suggested structure exactly). Only `openai_provider.py` imports the `openai` SDK.

## Decisions Made (WP-008)

* **`PromptTemplate` is a frozen `dataclass`, not a pydantic `BaseModel`.** Every other domain contract in this project is pydantic, but a prompt template is infrastructure metadata (a loaded file's text/derived variables/hash), not a validated data-exchange contract with JSON-schema needs - a plain immutable dataclass is simpler and avoids implying the template itself should be serialized/exchanged like a domain model.
* **`required_variables` derivation rejects more than the WP's minimum example.** Beyond positional/numbered fields (`{0}`, `{}`), attribute/index access (`{x.y}`, `{x[0]}`) and format specs (`{x:>10}`) are also rejected as malformed, not merely "unsupported but ignored" - chosen because WP-008 section 6 explicitly says the template system supports only static text plus named placeholders ("no expressions"), and a format spec or attribute path is exactly the kind of mini-expression that section rules out.
* **`PromptId.SYSTEM` was added** even though the WP's own conceptual `PromptId` example (section 8) lists only the six task-specific prompts. The system prompt is a real, separately-hashed, separately-loaded production prompt file (`prompts/system/exam_generator.txt`) that the repository must load and fail closed on exactly like the other six; giving it no identifier would have meant special-casing it outside the `PromptId` → path mapping that section 8 establishes as the single source of truth.
* **`PromptRepository` construction takes no cross-file dependency**: all seven prompt files are loaded independently and construction fails on the first missing/empty/malformed one encountered in `PromptId` enum-definition order (not aggregated into a single "here is everything wrong" error) - matches WP-002/WP-003's existing fail-closed-on-first-problem convention rather than introducing new aggregate-error handling.
* **Evidence/reference formatting owns its own delimiters, not the prompt text.** `format_student_summary_evidence()`/`format_course_book_evidence()`/`format_historical_reference()` each embed their own `--- BEGIN/END ... ---` markers around the content they produce, and the production prompt text simply references `{source_evidence}`/`{historical_reference}` without re-adding its own delimiter lines. This keeps the delimiter text defined in exactly one place (the formatter) rather than duplicated/risking drift between a prompt file's literal markers and a formatter's markers.
* **`format_student_summary_evidence()`/`format_course_book_evidence()` reject a chunk whose `SourceType` does not match the formatter being called** (`PromptContextError`), even though the WP does not explicitly demand this check. Added because WP-008's own objective explicitly asks for "tests ensuring prompt/source-role boundaries remain explicit" - a mismatched `SourceType` reaching the wrong formatter is exactly the kind of source-role confusion that boundary is meant to prevent, and the check is a few lines against a field that already exists on `SourceEvidenceChunk`.
* **`GenerationPromptContext` enforces the mode/historical-reference invariant in both directions**: `STYLE_SIMILAR` requires a `historical_reference` (explicit in WP-008 section 44), and `INDEPENDENT` must not be supplied one at all (stricter than the WP's literal wording, which only says `INDEPENDENT` must not *fabricate* one). Chosen to give test 69 ("invalid mode/context combination fails") an unambiguous, symmetric rule to test in both directions, and because a caller that already has a resolved historical reference but requests `INDEPENDENT` generation almost certainly has a caller-side bug worth failing loudly on rather than silently discarding the reference.
* **No context object was introduced for MCQ/category/quality/textbook validation** - only `GenerationPromptContext`/`GroundingPromptContext` exist, matching WP-008 section 45's explicit example list. Those four prompts' inputs (a formatted candidate question, plus a plain string or already-formatted course-book evidence) have no invalid-combination invariant analogous to the generation-mode/historical-reference rule, so a dedicated value object would only wrap `render_prompt()` without preventing any additional invalid state.
* Package structure: `prompts/{errors,models,repository,renderer,formatting,context}.py` (`renderer.py`/`formatting.py`/`context.py` split beyond the WP's minimum suggested `{errors,models,repository,renderer}.py` to keep source-role formatting and mode-invariant context construction each in their own focused module, mirroring the loader/repository-style separation already used by `historical`/`ingestion`/`chunking`). Only `renderer.py` imports from `exam_generator.llm` (for `LLMMessage`/`MessageRole`); nothing in the package imports the `openai` SDK.

## Decisions Made (WP-009)

* **`GeneratedQuestionResponse` added to `models/question.py`, next to `CandidateQuestion`** (as the WP's own section 4 explicitly directed: "add it to the appropriate existing domain/model layer"). It excludes `category`/`generation_mode` entirely - both are dictated to the model as fixed prompt inputs already, so asking the LLM to also *output* them would be redundant and would reopen exactly the "can the LLM invent/falsify provenance" risk the WP explicitly warns against. `extra="forbid"` on the model means an attempt to construct it with a `category`/`generation_mode` kwarg raises `ValidationError` immediately - verified directly in `tests/unit/test_generation.py`.
* **`evidence_chunk_ids` is optional (`default_factory=list`), not required.** WP-009 section 3 states "the generator *may* report which supplied evidence it used, but that claim is not authoritative" - phrased as optional, not mandatory. Any ids that *are* reported are still fully validated against the actual supplied evidence (`InvalidGeneratedOutputError` on any id not present); an empty list is not itself an error in this WP (grounding sufficiency is WP-010's job, not WP-009's).
* **Reported provenance is validated but not persisted onto `CandidateQuestion`.** `CandidateQuestion` (frozen WP-002 contract) has no `evidence_ids`/`historical_reference_id` fields, and WP-009 explicitly does not ask to change that. `evidence_chunk_ids`/`historical_reference_id` from `GeneratedQuestionResponse` are therefore used only as a validation gate inside `generate_candidate_question()` (reject the whole call on a falsified claim) - they are not exposed to the caller in this WP. Later audit-assembly work will decide how/whether to carry this provenance forward (likely via `QuestionAudit.evidence`/`historical_reference_id`, which already exist for exactly this purpose).
* **Historical-reference selection policy: first result of `HistoricalQuestionRepository.questions_for_category(canonical_category)`, i.e. first workbook-order occurrence in that category.** Chosen because it is trivially deterministic (a hard WP-009 requirement - "the selection must be deterministic for identical inputs/state"), requires no new sorting/ranking logic, and reuses an existing repository method verbatim rather than adding a new one. Diversity/repeat-avoidance across multiple questions is explicitly WP-013's job, not WP-009's (WP-009 generates exactly one question per call with no memory of prior calls).
* **`QuestionGenerator` is a small DI class, not a bare function**, matching the WP's explicit allowance ("the exact constructor/dependency-injection design is Claude's engineering decision") and the existing codebase convention (`OpenAIProvider`, `HistoricalQuestionRepository`, `FactualRetrievalIndex` are all constructed the same way): an explicit-dependency `__init__` for testability plus a `.from_default_configuration()` classmethod for the normal real-project wiring - mirroring `OpenAIProvider.from_config()`/`HistoricalQuestionRepository.from_default_location()` exactly.
* **`retrieve_for_category()` is called with no explicit `top_k` override**, letting the injected `FactualRetrievalIndex`'s own configured default (resolved once, at index-construction time, from `config/app.yaml`'s `retrieval.top_k`) govern result count - per the WP's explicit instruction not to introduce another generation-specific retrieval constant.
* **No course-book retrieval index is a constructor dependency of `QuestionGenerator` at all** (not merely "unused") - there is no parameter through which one could even be supplied, which is the simplest possible way to guarantee WP-009's "do not retrieve course-book evidence" rule structurally rather than by convention. Verified by a test that inspects `QuestionGenerator.__init__`'s parameter names directly.
* Package structure: `generation/{errors,generator}.py` (a `historical_selection.py`/`context.py` split was considered but rejected as premature - the selection policy is four lines and has no independent invariant worth a dedicated module, unlike WP-008's `context.py`, which enforces a real mode/reference invariant across multiple call sites).

## Decisions Made (WP-010)

* **Deterministic validation-retrieval query: `f"{candidate.category} {candidate.question} {<intended correct answer text>}"`, distractors excluded.** The WP explicitly left this as an engineering decision requiring documentation/tests. Category text is included for the same "category-aware retrieval" reason WP-006's `retrieve_for_category()` uses canonical category text as its query; only the *intended* correct answer's text is included (not the three distractors) because that is the specific factual claim actually being validated - adding wrong-answer text would only dilute the TF-IDF query with text the validator does not need to confirm.
* **No `candidate.evidence_chunk_ids`/`historical_reference_id` exist to "not blindly trust" in the first place - this WP-010 invariant is structurally guaranteed, not enforced by validator logic.** `CandidateQuestion` (frozen WP-002/WP-009 contract) carries neither field; `GroundingValidator.validate_grounding(candidate)` and `GroundingPromptContext` also have no parameter for either. This was verified directly in tests (`CandidateQuestion.model_fields`, `inspect.signature()`, `dataclasses.fields()`) rather than merely asserted in prose, since the WP's own pseudocode ("do not simply take `candidate.evidence_chunk_ids`") describes a field that does not actually exist on the real domain model - see WP-009's own parallel note about this in its Decisions Made section.
* **`GroundingValidator` has no course-book retrieval dependency at all** (no constructor parameter, matching `QuestionGenerator`'s identical WP-009 decision) - the simplest structural guarantee that course-book evidence is never used for primary grounding, rather than relying on the validator simply choosing not to call one.
* **Two already-shipped production prompts were modified during this WP's live smoke test**: `prompts/generation/question.txt` (WP-008/WP-009) and `prompts/validation/grounding.txt` (WP-008). Both were found, live, to cause a reproducible failure - the model reports an `evidence_chunk_ids` value with the `SourceType:` prefix dropped (e.g. `student_summary_2.pdf:0008:0001` instead of the real `STUDENT_SUMMARY:student_summary_2.pdf:0008:0001`), which the (intentionally strict) provenance checks in both WP-009 and WP-010 then correctly reject as an invented id - confirmed reproducible across two consecutive live generation attempts before the fix, and confirmed resolved by a subsequent successful live generation-then-validation call after it. This is the specific, narrow exception both WPs' "do not tune prompts speculatively" rules explicitly carve out ("unless the live smoke test exposes a clear correctness/contract defect" / "a genuine API/model compatibility problem") - the fix only clarifies that `evidence_chunk_ids` must be copied character-for-character from the evidence's `Chunk:` line, and changes no other prompt content, requirement, or policy. The user was asked before this change was made (an already-shipped, committed prompt file), and explicitly chose to have it fixed rather than retried-as-is or deferred. New prompt version hashes: `QUESTION_GENERATION` → `d4f9940c31f9d703`, `GROUNDING_VALIDATION` → `c1b8df1b03518333` (both prefixes; supersede the ones recorded in WP-008's "Real Prompt Verification" table, which remains an accurate snapshot of that file's content *at that time*, not the current content).
* One WP-008 test (`tests/unit/test_prompts.py::test_grounding_prompt_evidence_ids_must_come_from_supplied_evidence`) asserted the exact old wording of the changed sentence; updated to assert the equivalent new wording rather than being weakened or removed.
* Package structure: `validation/{errors,grounding}.py` - `errors.py`'s base class is named `GroundingValidationError`, not the more generic `ValidationError`, specifically to avoid colliding with `pydantic.ValidationError`, which this exact same module already imports/uses throughout (`GroundingValidationResult` construction, `CandidateQuestion`, etc.). Future validation stages (WP-011 MCQ/category/quality, WP-012 textbook) are expected to land as sibling modules in this same `validation/` package.

## Decisions Made (WP-011)

* **No new prompt-context value object was introduced for MCQ/category/quality**, continuing WP-008's own explicit decision on this exact point (see "Decisions Made (WP-008)"): none of the three has an invalid-combination invariant analogous to `GenerationPromptContext`'s mode/reference rule, so each validator just builds its small, fixed `dict[str, str]` of prompt variables inline in `validate()` rather than wrapping it in a dataclass that would add a layer without preventing any additional invalid state.
* **No generic `Validator` base class/framework was introduced.** `MCQValidator`, `CategoryValidator`, `QualityValidator` are three independent classes with no shared parent beyond ordinary Python object identity - each has its own `validate(candidate) -> <its own Result type>` method (not a shared abstract signature), matching the WP's explicit instruction that "three small explicit validators are preferable to an abstraction that obscures their different responsibilities." Some duplication exists across the three modules' `__init__`/`from_default_configuration()` boilerplate as a direct consequence - judged the correct trade-off given the WP's explicit anti-abstraction guidance, exactly mirroring `GroundingValidator`'s own already-established shape.
* **`CategoryValidator` supplies `candidate.category` to the prompt's `expected_category` variable verbatim, with no resolver/alias-table dependency of any kind** - the simplest structural guarantee that this validator can neither perform alias resolution nor silently substitute a different canonical category, matching WP-009's/WP-010's established pattern of proving a scope boundary via "no constructor parameter exists for this at all" rather than "the code simply doesn't call it."
* **No new domain-specific error classes were added to `validation/errors.py` for MCQ/category/quality.** Unlike WP-010's `GroundingValidator` (which independently retrieves evidence and therefore has two retrieval/provenance-specific failure modes - `NoValidationEvidenceError`, `InvalidGroundingOutputError`), none of the three WP-011 validators perform retrieval or claim evidence-chunk provenance, so they introduce no new failure mode beyond what `exam_generator.llm`'s existing error hierarchy (`LLMProviderError`, `LLMResponseError`, etc.) and pydantic's own `ValidationError` already cover for a malformed/failed structured-output call.
* **Method name is `.validate(candidate)` on all three validators** (not `.validate_mcq()`/`.validate_category()`/`.validate_quality()`), matching WP-011 section 5's own suggested interface shape exactly; `GroundingValidator.validate_grounding()` keeps its existing, already-shipped WP-010 name unchanged rather than being renamed for surface consistency, since renaming an already-approved public method was out of this WP's scope.
* Package structure: `validation/{errors,grounding,mcq,category,quality}.py` - three new sibling modules, exactly as WP-010's own "Decisions Made" note anticipated.

## Decisions Made (WP-012)

* **Empty course-book retrieval short-circuits to `TextbookCheckStatus.NOT_FOUND` without any LLM call, rather than calling the LLM with an explicit "no evidence" sentinel.** This deliberately diverges from `GroundingValidator`'s fail-closed-with-an-exception behavior on empty retrieval (`NoValidationEvidenceError`): primary grounding is mandatory, so empty retrieval there is an operational problem worth surfacing loudly, but course-book coverage is explicitly optional secondary material (WP-012 section 8), and there is nothing for a model to judge when zero evidence was found - the outcome is deterministic either way, so skipping the call avoids a pointless request. This is the literal reading of the WP's own "at most one" LLM-call phrasing (contrasted with WP-009's/WP-010's/WP-011's "exactly one"), which was the strongest textual signal that a zero-call path was intended here specifically.
* **`TextbookCheckResult`'s existing `source_page`/`reference_text` fields are the provenance-verification target, not an invented `evidence_chunk_ids` list.** WP-012 section 4 explicitly warns against redesigning the existing contract to fit preferred terminology; inspection confirmed `TextbookCheckResult` (unlike `GroundingValidationResult`) has no chunk-id list at all, only a single optional page number and a single optional quoted-text field - matching `prompts/validation/textbook.txt`'s own existing instruction ("If you report a supporting page or quoted text, it must come from the supplied evidence below only"). `_validate_textbook_provenance()` therefore checks each field independently, only when non-`None`: `source_page` must equal a supplied chunk's page; `reference_text` must be a verbatim substring of a supplied chunk's text. Neither check assumes the other field is present, since the prompt allows either, both, or neither to be populated depending on status.
* **No new prompt-context value object was introduced**, continuing the same WP-008/WP-011 precedent - `TextbookValidator` builds its `{"candidate_question": ..., "course_book_evidence": ...}` variable dict inline, reusing WP-008's `format_candidate_question()`/`format_course_book_evidence()` directly with no new invariant to enforce.
* **`TextbookValidationError`/`InvalidTextbookOutputError` were added to the existing `validation/errors.py` module** (not a new `textbook_errors.py` file), and that module's docstring was broadened from "grounding validation" to "candidate-quality validation" generally, since it now legitimately hosts two independent error hierarchies (`GroundingValidationError`'s and `TextbookValidationError`'s) rather than one - splitting into per-validator error files was considered and rejected as unnecessary ceremony for two small, independent, four/two-line hierarchies in one already-small module.
* **The retrieval query policy is identical in shape to WP-010's** (`f"{candidate.category} {candidate.question} {<intended correct answer text>}"`, distractors excluded) - the WP explicitly suggested this as "a reasonable V1 query" and gave no reason for course-book retrieval to need a different policy than student-summary retrieval; reusing the identical shape (against a different index) keeps the two independent evidence paths easy to compare and reason about.
* No overall candidate-acceptance rule combining all five validators (grounding/MCQ/category/quality/textbook) was implemented or even sketched, per the WP's explicit section 16 prohibition - `TextbookValidator.validate()` returns its own `TextbookCheckResult` and nothing else observes or combines it with any other validator's result.
* Package structure: `validation/{errors,grounding,mcq,category,quality,textbook}.py` - one new sibling module, continuing the established pattern.

## Decisions Made (WP-013)

* **`CandidateValidationResults.accepted` is a derived property, not a caller-suppliable field**, even though the WP's own section 12 pseudocode shows `QuestionAttempt(..., accepted=False)` as a constructor argument. Deriving it (and `QuestionAttempt.accepted` delegating to it) instead follows this project's own established "centralize derived logic" convention (`GroundingValidationResult.passed` is the precedent this directly mirrors) - it makes an inconsistent-with-its-inputs `accepted` value structurally impossible, which a plain stored field would not guarantee.
* **No new configuration was added.** WP-013 section 9 explicitly said to inspect existing configuration first; `config/app.yaml`'s `generation.max_generation_attempts` (already present since WP-001, validated `Field(gt=0)` via `GenerationBehaviorConfig`) is exactly the "bounded generation attempts" setting the WP asked for, and was reused as-is via `load_app_config().generation.max_generation_attempts` in `QuestionProducer.from_default_configuration()`. `QuestionProducer.__init__` additionally validates any directly-injected `max_attempts` (`InvalidProductionConfigurationError` if not an int `>= 1`), since constructor-DI test/caller paths bypass `AppConfig`'s own pydantic validation.
* **New top-level `exam_generator.production` package, not folded into `exam_generator.generation` or `exam_generator.validation`.** The WP explicitly says "do not place this logic inside `QuestionGenerator`" and that generation/control remain separate responsibilities; a new package (mirroring the project's existing one-package-per-responsibility convention: `historical`, `ingestion`, `chunking`, `retrieval`, `llm`, `prompts`, `generation`, `validation`) keeps the control layer a peer of, not a subordinate of, the six components it coordinates.
* **`QuestionProducer.produce_question()` has no `try`/`except` at all around generation or validation.** This is the simplest possible way to guarantee WP-013's operational-failure-vs-quality-rejection distinction: an operational exception from any component structurally cannot be caught, silently retried, or reinterpreted as a rejection, because there is no exception-handling code path present to do so - the same "prove the boundary structurally, not by convention" pattern used throughout WP-009/WP-010/WP-012 (e.g. "no course-book retrieval parameter exists at all").
* **Validator invocation order (grounding, MCQ, category, quality, textbook) is a fixed sequence of five plain method calls in `_validate_candidate()`**, exactly the WP's own recommended order - not a configurable or data-driven list, since WP-013 explicitly asked for a deterministic order and gave no reason for it to vary.
* Package structure: `production/{errors,models,producer}.py` - `models.py` holds the three new result contracts (`CandidateValidationResults`, `QuestionAttempt`, `QuestionProductionResult`) as pydantic `BaseModel`s (`extra="forbid", frozen=True`), matching this project's existing convention for structured result contracts (e.g. `RetrievalResult`) rather than plain dataclasses; `producer.py` holds only `QuestionProducer`.

### Live-Test-Driven Textbook Prompt Fix (WP-013)

The WP-013 live smoke test's first production-cycle run raised `InvalidTextbookOutputError` from an already-passing WP-012 component (`TextbookValidator`), not from any new WP-013 code. Investigation (several manual, non-pytest debug calls against a fixed real candidate + fixed real course-book evidence, outside the bounded production cycle itself) reproduced the cause directly: the model, when populating `reference_text`, sometimes paraphrased/summarized course-book content instead of quoting it verbatim - one reproduced case cited a real supplied page (`source_page=354`) with a `reference_text` that did not appear anywhere in that page's actual supplied chunk text. `TextbookValidator`'s existing WP-012 provenance check was working exactly as designed by correctly rejecting this as unverifiable; the defect was in the prompt's instruction clarity, not in WP-012's or WP-013's logic.

This is the same category of issue WP-010 found and fixed for `evidence_chunk_ids` (an implicit "don't invent evidence" instruction that the model does not reliably follow without an explicit "copy character-for-character" directive). Per that same established precedent, the user was asked before modifying an already-shipped prompt file, and explicitly chose to have it fixed. `prompts/validation/textbook.txt`'s closing instruction was replaced: `source_page` must exactly match a supplied evidence item's `Page:` value; `reference_text` must be a contiguous, character-for-character excerpt of that item's `Text:` content, or left empty if no exact quote is available - never paraphrased, translated, or reconstructed from memory, and never combining wording from more than one evidence item. New version hash prefix: `de8e3f35c8b6fd2c` (supersedes the hash recorded in "Real Prompt Verification (WP-008)" below, which remains an accurate snapshot of that file's content *at that time*, not its current content). No other prompt content, requirement, or policy was changed; the fix was verified not to break any existing offline test (full 672-test suite re-run clean), and the subsequent full live production-cycle smoke test (see below) completed with no operational textbook-provenance error.

## Decisions Made (WP-014)

* **`ExamOrchestrator` is a new top-level `exam_generator.orchestration` package, not folded into `exam_generator.production`.** Continues the same one-package-per-responsibility rationale as WP-013's own `production` package decision: exam-level planning/sequencing/duplicate-protection is a distinct responsibility layered *on top of* single-question production, not a variant of it - `orchestrator.py` depends on `exam_generator.production` (imports `QuestionProducer`/`QuestionProductionResult`/`QuestionAttemptsExhaustedError`) but nothing in `production` depends back on `orchestration`.
* **Generation-mode alternation restarts at `STYLE_SIMILAR` for every category's own first question, rather than carrying one running parity counter across the whole exam.** The master brief's exact wording - "Questions alternate between two modes within each category" - is explicitly scoped per-category; a single exam-wide counter would let one category's assigned modes depend on how many questions preceded it in a *different* category, which is not what "within each category" says and would make a category's own plan non-reproducible in isolation. `STYLE_SIMILAR` (not `INDEPENDENT`) was chosen as each category's starting mode because the master brief's own "## Generation Modes" section lists it first - an arbitrary but documented tie-break, since the brief does not otherwise state which mode should lead.
* **`QuestionProductionFailedError` is a single error class with two mutually-exclusive optional context fields (`attempts_exhausted` / `duplicate_productions`), not two separate exception classes.** Both represent the same outer fact - "this planned question could not be completed, and the exam is not silently returned partial" - differing only in *why*; introducing a two-class hierarchy for that distinction would add ceremony without adding any information a caller couldn't get by checking which field is populated. This mirrors `QuestionAttemptsExhaustedError`'s own single-class-with-context shape from WP-013.
* **New configuration value `generation.max_duplicate_replacement_attempts` (default `2`), distinct from `max_generation_attempts`.** WP-014 section 13 explicitly requires this distinction ("WP-013 max_generation_attempts = attempts to make one acceptable candidate" vs. "WP-014 duplicate replacement = accepted candidate rejected because exam already contains it") and explicitly forbids silently reusing/inflating WP-013's own limit. The three pre-existing `diversity_*` placeholder fields in `GenerationBehaviorConfig` were inspected and deliberately left unused (see below) - they don't fit WP-014's much simpler *exact*-duplicate requirement.
* **The pre-existing `initial_diversity_target`/`minimum_diversity_target`/`diversity_relaxation_step` config fields were not wired into WP-014.** They read as placeholders for a future *fuzzy/scored* diversity system (a "target" implies a continuous measure to relax, not a hard yes/no duplicate check), while WP-014 section 14 explicitly limits this WP to exact normalized-duplicate detection only and explicitly forbids embedding/semantic/scored diversity. Reusing them for a boolean check would have overloaded a "target" field with a meaning it wasn't designed for; they remain unused, exactly as before.
* **`PositiveIntStrict`'s new sibling, `NonNegativeIntStrict`, was added to the shared `exam_generator.models._common` module** (not duplicated locally in `orchestration/models.py`), to type `QuestionProductionRecord.duplicate_replacement_attempts` (`0` is a valid, common value - most accepted questions need zero replacements). This follows the exact same "application-level packages may import `_common` directly" precedent WP-006's `RetrievalResult.rank` already established, rather than either duplicating the bool-rejection logic locally or loosening the field to a plain unvalidated `int`.
* **`build_exam_plan()` is a standalone pure function, not a method on `ExamOrchestrator`.** It has no dependency on any injected component (category resolver, producer) - it only transforms an already-canonicalized `ExamRequest` into a plan - so keeping it as a free function makes its determinism and lack of side effects/dependencies obvious at the call site and trivially unit-testable without constructing an `ExamOrchestrator` at all.
* Package structure: `orchestration/{errors,models,orchestrator}.py`, directly mirroring `production/{errors,models,producer}.py`'s own established shape.

### Live-Test-Driven Textbook Prompt Fix #2 (WP-014)

The WP-014 live smoke test's first several runs hit a *new* operational failure distinct from WP-013's already-fixed paraphrasing issue: a raw pydantic `ValidationError` on `TextbookCheckResult.reference_text` - the model returned `""` (empty string) rather than omitting the field, and the field's existing `NonBlankStr` type correctly rejects empty strings. Root cause: WP-013's own just-added closing instruction, "...leave reference_text empty rather than approximating one," is genuinely ambiguous between "omit the field" (the intended meaning - `reference_text` is `Optional`/`None` by default) and "set it to an empty string" (what at least one live response actually did). This is a narrow, mechanical wording defect in a sentence added earlier in this same WP-013→WP-014 arc, not a new design question - fixed (with explicit user approval) by rewording to "omit reference_text entirely (return null, not an empty string)". New version hash prefix: `192b24c66a7bc404`. Full offline suite re-verified clean (701 tests) after this change too.

**A second, distinct live-observed issue was investigated but deliberately not fixed further**: even after both textbook-prompt fixes, a small number of live calls (across several different real categories, both before and after this second fix) still hit `InvalidTextbookOutputError` on a non-empty `reference_text` that did not verbatim-match its cited evidence - the same underlying phenomenon the first WP-013 fix targeted, evidently not eliminated to 100% reliability by clearer wording alone. A live comparison specifically ruled out a plausible alternative *implementation* explanation (a Unicode-normalization false-mismatch in `_validate_textbook_provenance()`'s plain substring check) - repeated debug calls against fixed real evidence produced either a clean `NOT_FOUND` with no citation, or (rarely) a citation that was a genuine semantic paraphrase, never a near-miss explainable by encoding/whitespace differences. Separately, one live call also hit a pre-existing `InvalidGeneratedOutputError` (an invented `evidence_chunk_ids` value) from the WP-009 generator - the same failure *class* WP-010 fixed once for a different specific wording symptom, recurring here for a different category. Neither issue was judged to have an identifiable, narrow, mechanical wording defect the way the two fixed issues did; both are exactly the kind of operational failure this project's validators are deliberately designed to surface rather than silently tolerate (see "Known Issues" below for the full honest accounting, per this project's established "record honestly rather than chase" philosophy - WP-006's retrieval-quality section and WP-011's live-observation section are the direct precedent for this same choice).

## Decisions Made (WP-015)

* **`historical_reference_id` and `evidence` are always `None`/`[]` in WP-015's audit construction - a deliberate honest-absence choice, not the WP's alternative-sanctioned "smallest architectural addition" path.** WP-015 section 4/9/10 explicitly offers two options when an existing audit field can't be populated: extend production history to capture it, or represent the gap honestly if the contract allows absence. Making `QuestionGenerator` return which evidence chunks it used, and persist `historical_reference_id` onto something the caller can see, would require threading new return values through `QuestionGenerator` (WP-009), `GroundingValidator`/`TextbookValidator` (WP-010/WP-012), and every WP-013/WP-014 model built on top of them (`QuestionAttempt`, `QuestionProductionResult`, `QuestionProductionRecord`) - exactly the "broad refactoring of previous WPs" WP-015 section 10 explicitly discourages, for two fields the existing WP-002 contract already tolerates being absent (both were already `| None`/`default_factory=list` before this WP touched them). Grounding-evidence *identity* specifically is not actually lost by this choice - `GroundingValidationResult.evidence_chunk_ids`/`.evidence_text` remain fully intact, just nested inside each attempt's own `grounding` result (`attempts[i].grounding.evidence_chunk_ids`) rather than duplicated into a separate top-level list.
* **`QuestionAudit.attempts: list[QuestionAttemptAudit]` was added as a genuinely new field, not a reinterpretation of the five pre-existing `grounding`/`mcq_validation`/etc. fields.** Those five fields already existed in WP-002 with a clear implied meaning (a question's audit results) but could only hold one set of results - never enough to represent WP-013's multi-attempt history. Rather than repurpose them to mean "the accepted attempt's results" retroactively (backwards-incompatible in spirit) or invent a competing top-level model, the smallest change was: keep them meaning exactly what they always meant (mirror the final/accepted attempt), and add one new field carrying the complete list. `QuestionAttemptAudit` deliberately duplicates the five-validator-field shape rather than referencing WP-013's own `QuestionAttempt`/`CandidateValidationResults` models directly, because `exam_generator.models` (the foundational domain layer) must not depend upward on `exam_generator.production` (an application layer built on top of it) - the dependency direction established since WP-001 stays intact.
* **Model/provider provenance uses `LLMConfig` (plain config data), never a constructed `LLMProvider`.** `load_llm_config()` (WP-001) was already documented as deliberately not requiring `OPENAI_API_KEY`; reading `.provider`/`.model` off it (rather than off a real `OpenAIProvider.provider_name`/`.model_name`, which would require constructing a client and therefore an API key) means `build_exam_audit()` can run with zero API key and zero LLM-capable object ever created, matching WP-015's "zero LLM calls" requirement in the strongest possible sense - not just "no calls are made" but "nothing capable of making a call is even constructed."
* **Prompt-version/hash provenance (WP-015 section 10) was investigated and deliberately not implemented.** No current validator/generator call site returns which `PromptTemplate.version` it used for a given attempt, and neither `QuestionAudit` nor `ExamAudit` has an existing field requiring this information - so per section 10's own explicit permission ("if the existing audit contract allows absence... explicitly document the gap if the existing audit contract does not require them"), nothing was added or fabricated. This is a known, documented gap for a future WP to close if prompt-level audit granularity is ever prioritized.
* **`diversity_target` is a required caller-supplied parameter to `build_exam_audit()`, not loaded internally from `config/app.yaml`.** Keeping `build_exam_audit()` a pure function of its explicit arguments (no internal file/config I/O) makes "identical inputs -> identical output" trivially true by construction rather than by convention. In practice, callers are expected to pass `load_app_config().generation.initial_diversity_target` (confirmed working in the live smoke test) - the same pre-existing, still-unused-for-relaxation config value WP-013's "Decisions Made" section already discussed.
* **Cross-consistency validation (`AuditConsistencyError`) lives inside `build_exam_audit()` itself, not as a separate opt-in step.** Since `ExamGenerationResult` is always available at audit-construction time, checking `generation_result.exam` against the audit being built right there means the check can never be forgotten by a caller, at negligible cost (a handful of equality checks over data already in memory) - it only ever fires on a genuinely tampered/hand-constructed `ExamGenerationResult`, confirmed by test.
* **No dedicated failure-diagnostics serialization function was added**, per WP-015 section 16's explicit warning not to broaden this WP into "a general exception-reporting framework." `QuestionProductionFailedError` (WP-014) already exposes fully structured, already-pydantic-modeled attributes (`planned_question`, `completed_productions`, `attempts_exhausted`/`duplicate_productions`); a caller can already inspect or serialize these today with existing tools (e.g. `[p.model_dump() for p in exc.completed_productions]`) without any new WP-015 code.
* **Package structure: `output/{errors,models,audit,bundle,serialization}.py`.** Splits slightly finer than `production`/`orchestration`'s three-file shape, since WP-015 has three genuinely distinct concerns worth their own module (deterministic audit construction, the small bundle-pairing convenience wrapper, and JSON serialization/file-writing) rather than one `producer.py`-sized file that would otherwise mix pure transformation logic with I/O.

## Decisions Made (WP-016)

* **A single `src/exam_generator/cli.py` module, not a `cli/` package.** The entire CLI is one subcommand (`generate`) with a handful of small functions (arg parsing, request loading, output-target checking, atomic writing, error classification, `main()`) - small enough that splitting into a package would add navigation overhead without a corresponding benefit, unlike the multi-concern application-layer packages (`production`, `orchestration`, `output`) that each own several genuinely distinct responsibilities.
* **Error classification is one ordered, most-specific-first `isinstance` chain (`_classify_error()`) returning `(exit_code, message) | None`, not a dict/registry keyed by exception type.** Several of the exception hierarchies this CLI must distinguish are nested (`LLMConfigurationError` is a subclass of `LLMError`; `UnknownCategoryError`/`InvalidCategoryMappingError` are subclasses of `CategoryResolutionError`), so a plain `{type: (code, prefix)}` lookup would silently misclassify a subclass under its base class's entry unless carefully ordered anyway - an explicit ordered `isinstance` chain makes that ordering requirement visible in the code itself rather than implicit in dict-insertion order. Returning `None` for anything unrecognized (rather than a wildcard "unexpected error" branch) is what lets `main()` re-raise genuinely unexpected exceptions with their full traceback, per the WP's explicit "do not implement a giant catch-all that hides defects" instruction.
* **Existing-output-file checking happens before constructing `ExamOrchestrator`, not after generation.** Beyond simply avoiding a stale-output problem, checking first also avoids wasting real, costly API calls generating an exam that the CLI already knows it cannot write - a concrete cost saving on top of correctness, given how much a full production cycle can cost per WP-013/WP-014's own live-testing notes.
* **Atomicity is implemented in the CLI itself (a small `_atomic_write_text()` using a same-directory `.tmp` file plus `os.replace()`), not added to WP-015's `write_exam_json()`/`write_audit_json()`.** WP-015 was explicitly told to "keep file-system concerns minimal," and WP-016 section 18 is the one that actually asks for atomicity - so the natural owner of that extra robustness is the CLI layer that introduced the requirement, not a retroactive change to an already-shipped, already-tested WP-015 helper. The CLI calls WP-015's pure `serialize_exam_json()`/`serialize_audit_json()` directly (not `write_exam_json()`/`write_audit_json()`) and does its own writing, so both serializations complete successfully before either file write is attempted.
* **`exam_id` is derived from the current UTC timestamp (`f"exam-{generated_at:%Y%m%dT%H%M%SZ}"`), even though WP-016 section 6 explicitly forbids timestamp-based *filenames*.** That rule is scoped to on-disk output file names (`exam.json`/`exam_audit.json` remain fixed, non-random defaults, exactly as required); `exam_id` is internal *data* inside the audit JSON's `exam_id` field, not a filename, so deriving it from the generation timestamp is unaffected by that rule and gives every generated audit a distinguishing identity without needing a UUID dependency or any new configuration surface.
* **`LLMConfigurationError`/`ConfigError`/`CategoryResolutionError` all map to `EXIT_USAGE_ERROR` (2), even though some of them (e.g. an unknown category) are only actually raised partway through `ExamOrchestrator.generate_exam()`, not during argument/request parsing.** The WP's own section 13 explicitly buckets "missing/invalid configuration," "missing `OPENAI_API_KEY`," and "unknown category" under expected *input/configuration* problems rather than generation-content problems - a user fixes these by editing their request file or environment, not by hoping a different LLM sample succeeds - so they get exit code 2 regardless of which call frame happens to raise them.
* **`AuditConsistencyError` (WP-015) is treated as a known, classified failure (exit 1) rather than left to propagate as an "unexpected" traceback.** Although it should never actually fire via the CLI's own correct, unmodified usage of `ExamOrchestrator`/`build_exam_output_bundle()`, it is a real, already-documented, already-tested WP-015 exception type with a clear meaning - not a truly unclassifiable programming bug - so giving it a clean one-line message is more consistent with how every other known domain exception is handled than singling it out for a raw traceback.
* **Every CLI test runs inside an autouse `_isolated_cwd` fixture (`monkeypatch.chdir(tmp_path)`).** Discovered necessary during implementation: several tests exercise the *default* `exam.json`/`exam_audit.json` output paths, and without forcing an isolated working directory those tests would read/write files directly in the real project repository root (confirmed happening once during development - `exam.json`/`exam_audit.json` were briefly created in the repo root by an early, not-yet-isolated test run, and immediately deleted, not committed). An autouse fixture applied to every test in the module was chosen over patching each individual test, since forgetting it even once on a future added test would silently reintroduce the same repo-pollution risk.

## Decisions Made (WP-017)

* **`question_position` was added to `CandidateAttemptRecord`/`OperationalFailureRecord`, not derivable purely from `(category, generation_mode)`.** A category evaluated with more than one question in the same generation mode (e.g. 4 requested questions per category, alternating modes, means 2 questions share each mode) cannot be disambiguated by category+mode alone; `question_position` (mirroring `orchestration.PlannedQuestion.position`'s role) makes attempt-grouping for the attempts-per-question/exhaustion-rate metrics unambiguous regardless of sample size.
* **`build_evaluation_plan()` is a local reimplementation of `orchestration.build_exam_plan()`'s alternating-mode policy, not an import.** The evaluation layer is designed as a strictly read-only observer with zero dependency on `production`/`orchestration`/`output` internals (only on their *public* `QuestionProducer`/`FactualRetrievalIndex` interfaces) - importing `build_exam_plan()` directly would be harmless today but would create a dependency edge from "observability tooling" back into "control-layer implementation detail," which this WP deliberately avoids given evaluation code should never be able to influence, or be broken by, unrelated refactoring of the orchestration layer's internals.
* **`RetrievalEvalQuery.expected_literal_term` is checked fresh against the corpus at evaluation time, never pre-computed into a stored chunk-id list.** WP-017 section 12 explicitly forbids fabricating expected answers from general knowledge; the only way to guarantee that constraint holds indefinitely (not just at fixture-authoring time) is to make the fixture describe *what to check for*, not a frozen answer, so the fixture cannot silently go stale if chunking/PDF content ever changes. `UngroundedRetrievalQueryError` fails loudly rather than silently reporting a meaningless "miss" if a fixture entry's term is ever not found at all.
* **The 37-query retrieval fixture was built by direct corpus inspection (literal Python substring search over real chunk text), not by trusting TF-IDF's own top-ranked result as ground truth.** Using the system under test's own output to validate itself would be circular and would measure nothing. 17 of 20 canonical categories' exact name text was confirmed to literally appear in the corpus; the other 3 (`מיפוי ודימות מוחי`, `קרומים וסינוסים דוראליים`, `מסילות עצביות`) do not appear verbatim anywhere (a real, useful finding on its own, consistent with the master brief's own "summary chapter/category wording may differ from canonical exam category wording" - a verified alternate term was used for those 3 instead).
* **`pydantic.ValidationError` was added to `KNOWN_OPERATIONAL_ERROR_TYPES` mid-WP, after the first live baseline run crashed on it.** This is the narrowly-scoped "correctness/instrumentation fix... necessary to obtain valid measurements" WP-017 section 3 explicitly pre-authorizes - it changes only the evaluation runner's own error classification, touching no generation/validation/retrieval/prompt/acceptance code at all. Documented in-line in `runner.py` and here, per that section's explicit "must be explicitly documented" requirement.
* **`CandidateAttemptRecord.question_text`/`.answers`/`.correct_answer` were added (populated only for accepted attempts) after discovering the initial schema made WP-017's own required human quality review (section 19) impossible - the original design captured only boolean validator outcomes.** This is the same category of narrow, necessary-for-measurement fix as the `ValidationError` one above, made before the second live run so that run's accepted candidates could actually be reviewed.
* **Two independent live baseline runs (identical configuration/categories/counts) were merged into one combined dataset for the final report, rather than reported as two separate baselines or only the second run being kept.** Both runs used the exact same 5-category, 2-question-per-category plan; merging strengthens the statistical evidence for the dominant finding (operational-failure rate) without cherry-picking - the combination was decided *before* looking at which numbers would look better, and both runs individually are also preserved (`evaluation/evaluation_report_run1.{json,md}`, `evaluation/evaluation_report_run2.{json,md}`) for full transparency.
* **The evaluation output directory (`evaluation/`) is a new, git-tracked top-level directory, distinct from the gitignored `output/` directory used for real exam-generation runs.** `output/` is explicitly for ephemeral, user-generated exam/audit artifacts (gitignored since WP-001); this WP's evaluation reports are durable *evidence for architect/user review*, analogous to how `docs/PROJECT_STATUS.md` itself is committed - so `evaluation/` is deliberately trackable, not excluded.
* **`scripts/run_evaluation.py` supports `--skip-generation` for a retrieval-only run (no API key needed) as a first-class mode, not an afterthought.** This mirrors WP-017 section 23's explicit cost-control requirement ("so a developer can first run a small sample") and lets retrieval-quality regression checks run offline/in CI-like conditions independently of live generation cost.

## Live Evaluation Baseline (WP-017)

**Baseline type: REDUCED** (WP-017 section 24's explicit fallback - not all 20 canonical categories were evaluated live, per the cost/time constraints that section anticipates). 5 canonical categories x 2 requested questions/category, run **twice** with identical configuration (the second run followed the `pydantic.ValidationError`/question-text-capture instrumentation fixes described above) = 20 total planned questions across both runs. Categories evaluated: `התעלה השדרתית ותכולתה`, `מיפוי ודימות מוחי`, `קרומים וסינוסים דוראליים`, `המוח הקטן`, `טופוגרפיה של ההמיספרות`. Both generation modes were exercised (each category alternates `STYLE_SIMILAR`/`INDEPENDENT`). Full data: `evaluation/evaluation_report_combined.{json,md}` (merged), plus each individual run preserved separately.

### Retrieval Evaluation (offline, real corpus, no API key)

* **Recall@3 = 86.5%, Recall@5 = 94.6%, Recall@8 = 94.6%**, across all 37 fixture queries spanning all 20 canonical categories (17 by exact category-name match, 3 by verified alternate term, plus 17 more granular Hebrew/English/mixed anatomical-term queries).
* Only 2 misses at K=8: `Cerebellum` and `Basal Ganglia` (both real, verified-present terms that simply didn't rank in the top 8 for their own bare-term query - consistent with WP-006's own previously-documented "short/common-term exact-match ranking is imperfect" characteristic, not a new problem).
* **Conclusion (WP-017 section 14's embedding decision gate): TF-IDF retrieval appears sufficient for V1.** High Recall@5/@8 with only 2 non-catastrophic misses (both terms are common enough that they very likely also appear in whichever chunk the query's *actual* generation-time context - full category+question+answer text, not a bare term - ultimately retrieves) does not support prioritizing embeddings/hybrid retrieval over other findings below. No embeddings were implemented, per the WP's explicit prohibition.

### Candidate Generation/Validation Evaluation (live, real OpenAI API, combined across both runs)

* **14 of 20 planned questions (70%) hit an operational failure** before any validation verdict was ever recorded for that planned question. **9 of those 14 (45% of all 20 planned questions) shared the exact same root cause**: an empty-string `QualityValidationResult.reason` field, rejected by the existing (correct) `NonBlankStr` schema constraint - at `validation_temperature=0.0`, nominally the most deterministic setting available. This is a substantially higher rate than the scattered, occasional instances of this same *failure class* noted in WP-013/WP-014's own live testing (which affected `reason` fields on other validators, not concentrated on `QualityValidationResult` specifically).
* Remaining 5 operational failures were already-known issue classes: 2x invented `evidence_chunk_ids` (`InvalidGeneratedOutputError`, the WP-010-class provenance issue, both for the same category/content), 2x non-verbatim textbook `reference_text` (`InvalidTextbookOutputError`, the WP-012/WP-013-class issue, one per run), 1x malformed/truncated JSON from the provider (`GroundingValidationResult` parse failure) - the remaining 9 were all the empty-string `QualityValidationResult.reason` failure described above.
* **Of the 7 attempts that *did* complete operationally, 6 (85.7%) were accepted**, 5 of them (83.3%) on the first attempt; the sole rejection was a `Quality` failure. **Exhaustion rate (of units that got at least one attempt): 0%** - no planned question that reached actual validation ever ran out of WP-013's 3 configured attempts without an acceptable candidate.
* **The clear, evidence-backed conclusion: in this baseline, operational reliability - not candidate quality - is the dominant bottleneck.** When the pipeline completes an attempt operationally, it succeeds the great majority of the time; the system is instead frequently prevented from ever reaching a validation verdict at all by a specific, reproducible structured-output failure.
* Category-level results were too thin per category (1-2 requested questions/category/run) to support category-specific conclusions beyond the aggregate; no category showed a qualitatively different pattern from the others.

### Provenance/Operational Reliability Summary

* Invalid **generation** evidence IDs: 2 occurrences (same category/content both times - `Generated response claims evidence chunk id(s) that were not supplied`).
* Invalid **textbook** provenance: 2 occurrences (non-verbatim `reference_text`, one per run - the already-known WP-012/013 issue class).
* **Structured-output schema failures** (raw `pydantic.ValidationError`, not a project `LLMError`): 10 occurrences - 9x empty-string `reason` (all `QualityValidationResult`), 1x malformed/truncated response JSON (`GroundingValidationResult`) - see full breakdown in `evaluation/evaluation_report_combined.json`.
* No authentication, rate-limit, or connection failures were observed in either run.
* **These are kept strictly separate from validator-rejection metrics throughout** (an operational failure never contributes to `validator_failure_counts()`), per WP-017 section 15's explicit requirement.

### Human Quality Review

4 of the 6 accepted candidates were reviewed in full (text capture was only added before the second run; the 2 accepted candidates from the first run have no persisted text). 3 of 4 were genuinely solid, exam-ready material with meaningful, non-trivial distractors (a spinal-nerve/nerve-root question, a CT-vs-MRI imaging-advantage question, and a dural-sinus-vs-subarachnoid-space question). **The fourth surfaced a real construction defect the automated `QualityValidator` did not catch**: each answer choice was redundantly numbered *inside its own text* (`"1. לטרלית ל-..."`, `"2. מדיאלית ל-..."`, etc.) in addition to the exam format's own `answer1..answer4` numbering - `quality_valid` was `True` for this candidate. Full text and reasoning for all 4 reviewed questions are in `evaluation/evaluation_report_combined.md`'s "Human Quality Observations" section. This is a small sample (4 questions), not a systematic quality measurement, but a concrete, reproducible example of exactly the automated-validator gap WP-017 section 19 asks this review to surface.

### Exam-Level Quality Observations

Sample too small (4 reviewed questions, all from different categories) to meaningfully assess repeated patterns, near-duplicates, or systematic answer-position concentration - no repetition was observed, but this reflects sample size, not confirmed diversity at scale. No corrective diversity logic was implemented, per WP-017 section 20's explicit instruction.

### Findings Classification

* **Reliability issue (highest priority)**: the empty-string-required-field structured-output failure, concentrated on `QualityValidationResult`, at 45% of all planned questions in this baseline. Not classified as a "blocking defect" because the system *does* still function - `CandidateEvaluationRunner`/the CLI both correctly treat it as an operational failure rather than corrupting state - but its frequency is high enough to seriously limit real-world throughput today.
* **Reliability issue**: the two already-known provenance-fidelity issue classes (invented evidence IDs, non-verbatim textbook citations) remain non-negligible in aggregate (4 of 20 planned questions), consistent with WP-013/WP-014's own prior observations that these were never fully eliminated.
* **Enhancement (not currently justified)**: embedding/hybrid retrieval - Recall@5/@8 are both strong (94.6%) with only 2 non-catastrophic misses.
* **Quality issue (minor, low sample confidence)**: automated MCQ/Quality validators occasionally miss real construction defects (the duplicated-numbering example) - worth a human spot-check habit, not evidence of a systemic generation-quality problem given the otherwise-good review results.
* No blocking defects were found in this baseline - the assembled V1 pipeline (retrieval -> generation -> five validators -> acceptance -> exam orchestration -> output -> CLI) itself functioned correctly and consistently across both runs; every operational failure was correctly caught, classified, and non-corrupting.

### Recommended WP-018 Scope

Primarily a **reliability-hardening WP**, not a new feature WP: investigate and reduce the empty-required-string-field failure rate (top priority, by far the largest observed bottleneck), continue hardening structured-output provenance for the two already-known issue classes, and treat retrieval/embeddings as explicitly not justified by current evidence. Given the small live sample (20 planned questions across two runs), WP-018 should very plausibly begin by *widening* this same evaluation (reusing the runner/fixture introduced here, more categories/questions) to confirm the ~50% empty-reason rate holds at larger scale before committing to a specific root-cause fix - this baseline is suggestive and reproducible-so-far, but not yet large enough to be fully decisive on its own.

### Limitations of This Evaluation

* REDUCED baseline (5 of 20 canonical categories; 20 total planned questions, not the ~40 a FULL baseline would target) - a deliberate, documented cost/time tradeoff per WP-017 section 24's own explicit allowance, not an oversight.
* The two live runs used the *same* 5 categories both times (not a random resample), so the combined 20-question sample is not fully independent across categories - it does, however, give genuine within-run-to-run reproducibility evidence for the dominant failure-rate finding specifically.
* Only 4 accepted questions received full human review (not the ~10 the WP recommends "if enough are available" - only 6 were accepted at all, and only 4 of those have persisted text due to the mid-WP schema fix timing).
* No production/prompt tuning was performed in response to any finding, per WP-017 sections 3/25's explicit instruction - every fix made during this WP was to the new evaluation-instrumentation code only, never to generation/validation/retrieval/prompt/acceptance logic.

## Live Smoke Test (WP-007)

**Executed successfully** by the user with a real `OPENAI_API_KEY`, once against the live OpenAI API:

```
provider: openai
model: gpt-4o-mini
response type: _SmokeTestResponse
response.value: 'ok'
```

This confirms the configured `gpt-4o-mini` model, the Responses API structured-output mechanism (`client.responses.parse(..., text_format=...)`), and the configured `temperature`/`max_output_tokens` generation parameters all work correctly together end-to-end against the live API - not just in mocked tests. `scripts/smoke_openai.py` was also manually verified beforehand (before a key was available) to fail with a clean, project-specific `LLMConfigurationError` rather than a raw SDK exception or a hang when `OPENAI_API_KEY` is absent, confirming the missing-key path behaves as designed too. Only one live request was made, per the WP's cost/frequency constraint.

## Live Generation Smoke Test (WP-009)

**Executed successfully** after WP-009's initial completion report, once the user supplied a real `OPENAI_API_KEY` (via a local, gitignored `.env` file - not committed, not printed). One real call: `QuestionGenerator.from_default_configuration().generate_candidate_question(category=<first real canonical category>, generation_mode=GenerationMode.INDEPENDENT)`.

* Category used: `התעלה השדרתית ותכולתה` (first canonical category from the real historical workbook).
* Generated question: `מהו המבנה שמכיל את מוח השדרה וממוקם בתוך החוליות?`
* Answers:
  1. עצב השדרה
  2. **התעלה השדרתית** (`correct_answer` = 2)
  3. החומר האפור
  4. החומר הלבן
* `category` = `התעלה השדרתית ותכולתה` (matches the requested category exactly), `generation_mode` = `INDEPENDENT`.
* Structural checks: a valid `CandidateQuestion` was returned (pydantic-validated); Hebrew question/answer text present; exactly four answers; `correct_answer` is a valid 1-based position (2); category/mode provenance correct; no `InvalidGeneratedOutputError` was raised, confirming any evidence/historical-reference provenance the model claimed (if any) was consistent with what was actually supplied - `INDEPENDENT` claimed no historical reference, as required.
* Only one live request was made, per the WP's cost/frequency constraint ("do not make repeated live calls trying to improve the question"). Generation success is **not** treated as proof of factual grounding - that remains WP-010's job.

## Live Grounding Smoke Test (WP-010)

**Executed successfully**, once the two prompt fixes described in "Decisions Made (WP-010)" above were applied. One real generate-then-validate pair: `QuestionGenerator.from_default_configuration().generate_candidate_question(category=<first real canonical category>, generation_mode=GenerationMode.INDEPENDENT)` immediately followed by `GroundingValidator.from_default_configuration().validate_grounding(candidate)`.

* Category used: `התעלה השדרתית ותכולתה` (same first canonical category as the WP-009 live test).
* Generated question: `מהו המבנה של התעלה השדרתית?`
* Answers:
  1. **מקום מושבו של מוח השדרה, העובר דרך ה-Vertebral Foramen** (`correct_answer` = 1)
  2. מבנה של החוליות הצוואריות בלבד
  3. מקום לעצבוב גפיים תחתונות בלבד
  4. חלק מהחוליות המותניות בלבד
* Grounding verdict: **`passed = True`** (`grounded=True`, `correct_answer_supported=True`, `other_answers_not_equally_correct=True`), `confidence = 0.95`.
* Reason (verbatim): "The candidate question about the structure of the spinal canal is supported by the evidence, which states that the spinal canal is the location of the spinal cord passing through the vertebral foramen. The intended correct answer (Answer 1) is also supported by this evidence. Other answers do not have equivalent support, as they either misrepresent the structure or limit it incorrectly to specific vertebrae or functions."
* Supporting evidence ids returned by the validator (all verified against the actual independently-retrieved evidence, per WP-010's provenance check): `STUDENT_SUMMARY:student_summary_2.pdf:0003:0001`, `STUDENT_SUMMARY:student_summary_1.pdf:0003:0001`.
* **Attempt history (recorded honestly, per the WP's explicit instruction not to hide observations)**: this succeeded on the third live generation attempt. The first two attempts (before the prompt fix) failed *during generation* with `InvalidGeneratedOutputError` - not a grounding failure - because the model reported an `evidence_chunk_ids` value with the `SourceType:` prefix dropped, which WP-009's provenance check correctly rejected. See "Decisions Made (WP-010)" for the fix and full reasoning. No attempt was made to re-roll for a "better" question once a structurally valid one was produced; the smoke test stopped at the first successful generate-then-validate pair.
* This is one observation, not a systematic grounding-quality measurement - a `passed=True` result here says nothing about the validator's or generator's behavior across many questions/categories. No prompt/retrieval tuning was performed in response to this specific outcome (there was nothing to react to - it passed).

## Live Candidate-Quality Validation Smoke Test (WP-011)

**Executed successfully**, once each, against a freshly generated candidate (a new generate call, not a reused prior candidate - not readily reproducible from an in-process object across separate WP runs). One real generate-then-validate-four-ways sequence: `QuestionGenerator.from_default_configuration().generate_candidate_question(category=<first real canonical category>, generation_mode=GenerationMode.INDEPENDENT)`, immediately followed by `GroundingValidator`, `MCQValidator`, `CategoryValidator`, and `QualityValidator`, each `.from_default_configuration()`, each invoked exactly once.

* Category used: `התעלה השדרתית ותכולתה` (same first canonical category as the WP-009/WP-010 live tests).
* Generated question: `מהו התפקיד של החוליות בעמוד השדרה?`
* Answers:
  1. לספק מבנה ותמיכה לגוף
  2. למנוע תנועות בלתי רצויות של הגוף
  3. **לשמש כמקום מושב למוח השדרה** (`correct_answer` = 3)
  4. למנוע כאבים בעמוד השדרה
* Results (all four independent, all executed successfully as normal results - no exception raised by any validator):

  | Validator | Verdict | Reason (verbatim) |
  |---|---|---|
  | Grounding | **FAIL** | "The question about the role of vertebrae in the spine is supported by the evidence, which describes the structure and function of vertebrae, including their role in forming the spinal canal. However, the intended correct answer (3) states that vertebrae serve as a seat for the spinal cord, which is not explicitly supported by the evidence. Other answers, such as (1) providing structure and support to the body, are supported by the evidence, making them equally valid. Therefore, the intended correct answer is not the only supported answer." |
  | MCQ | **FAIL** | "More than one answer choice could reasonably be defended as correct. Answers 1 and 3 both provide plausible roles of the vertebrae, making it unclear which is the single best answer." |
  | Category | **FAIL** | "The question focuses on the role of vertebrae in the spine, which does not directly pertain to the spinal canal and its contents." |
  | Quality | **FAIL** | "The question is clear and unambiguous, but the intended correct answer (Answer 3) is factually incorrect... Additionally, Answer 4... could be interpreted as a role of the vertebrae... This creates ambiguity regarding the correct answer." |

* This is a genuinely weak candidate on all four independent axes at once, not a validator malfunction: MCQ correctly flags the same answer-1-vs-3 ambiguity that Grounding independently flags via unsupported-exclusivity, and Category correctly flags that the question is really about general vertebral function rather than the requested "spinal canal and its contents" category. This is exactly the kind of honest, informative multi-axis failure WP-011 explicitly asks to be surfaced rather than hidden - **per WP-011 section 15, this is a successful smoke test of the implementation, not a failed WP.** No prompt was tuned in response, and no repeated generation was attempted to find a "better" candidate.
* Only one live generate-then-validate sequence was made, per this project's established cost/frequency constraint for live smoke tests.

## Live Textbook Validation Smoke Test (WP-012)

**Executed successfully**, once, against a freshly generated candidate (a new generate call, not the WP-011 candidate - not readily reproducible from an in-process object across separate WP runs, per WP-012 section 15's own "if readily reproducible" qualifier). One real generate-then-textbook-validate sequence: `QuestionGenerator.from_default_configuration().generate_candidate_question(category=<first real canonical category>, generation_mode=GenerationMode.INDEPENDENT)`, immediately followed by `TextbookValidator.from_default_configuration().validate(candidate)`, invoked exactly once. Per WP-012 section 15's own instruction not to make extra API calls merely to reconstruct them, the other four (WP-010/WP-011) validators were **not** re-run against this candidate - only the textbook result is reported here.

* Category used: `התעלה השדרתית ותכולתה` (same first canonical category as the WP-009/WP-010/WP-011 live tests).
* Generated question: `מהו המבנה הממוקם בתעלה השדרתית ומה תפקידו?`
* Answers:
  1. **המוח השדרה - מעביר מידע סנסורי ומוטורי** (`correct_answer` = 1)
  2. החוליה - תומכת במבנה השדרה
  3. השרירים - מאפשרים תנועה
  4. העורקים - מספקים דם למוח השדרה
* Course-book evidence ids independently retrieved and supplied to the LLM call (3): `COURSE_BOOK:course_book.pdf:0128:0002`, `COURSE_BOOK:course_book.pdf:0132:0002`, `COURSE_BOOK:course_book.pdf:0119:0002`.
* Textbook verdict: **`NOT_FOUND`** (`source_page=None`, `reference_text=None` - both correctly absent, matching a `NOT_FOUND` status's own semantics of "no confident page/quote to cite").
* Reason (verbatim): "The course-book evidence does not provide relevant information regarding the structure located in the spinal canal or its function."
* This is a legitimate, informative result per WP-012 sections 8/15 explicitly, not an implementation defect: three course-book chunks were retrieved and genuinely considered (the LLM call *was* made - retrieval was not empty), but the model judged them insufficient to confidently support or contradict the specific candidate. No prompt was tuned in response, and no repeated generation/retrieval was attempted to find a "better" result.
* Only one live generate-then-validate call was made, per this project's established cost/frequency constraint for live smoke tests.

## Live Production Cycle Smoke Test (WP-013)

**Executed successfully**, once, using `QuestionProducer.from_default_configuration().produce_question(category=<first real canonical category>, generation_mode=GenerationMode.INDEPENDENT)` with the configured `max_attempts=3` (`config/app.yaml`'s existing `generation.max_generation_attempts`). Ran after the live-test-driven textbook prompt fix described above (the *first* run of this smoke test surfaced that defect via `InvalidTextbookOutputError`, before any candidate reached an acceptance decision; this is the subsequent, complete run).

* Category used: `התעלה השדרתית ותכולתה` (same first canonical category as every prior live test).
* Outcome: **exhausted** - all 3 attempts completed operationally successfully (no exceptions), all 3 rejected by the deterministic acceptance policy. `QuestionAttemptsExhaustedError` was raised carrying all 3 completed `QuestionAttempt` records, exactly as designed.

  | Attempt | Grounding | MCQ | Category | Quality | Textbook | Accepted |
  |---|---|---|---|---|---|---|
  | 1 | PASS | PASS | PASS | **FAIL** | NOT_FOUND | NO |
  | 2 | PASS | **FAIL** | PASS | **FAIL** | NOT_FOUND | NO |
  | 3 | PASS | **FAIL** | PASS | **FAIL** | NOT_FOUND | NO |

* Representative reasons: Attempt 1 Quality FAIL - "The question lacks clarity and specificity regarding the role of the התעלה השדרתית. The answer choices are ambiguous and do not clearly differentiate the functions of the spinal canal..."; Attempt 2/3 MCQ FAIL - "More than one answer choice could reasonably be defended as correct..."; all three Textbook results were `NOT_FOUND` because independent course-book retrieval returned zero chunks for each of the three generated question phrasings (the empty-retrieval short-circuit path from "Decisions Made (WP-012)" - no LLM call was made for textbook validation on any of the three attempts).
* This is a legitimate, informative "exhausted" result per WP-013 section 20 explicitly ("An exhausted live test is useful baseline data and does not mean WP-013 failed") - not an implementation defect. Grounding passed in all three attempts (generation is reliably producing factually-grounded questions), but MCQ/Quality repeatedly failed on genuine construction weaknesses (ambiguous best-answer, unclear question phrasing) - consistent with, and reinforcing, the same generation-quality weaknesses WP-011's own live smoke test already observed independently. No prompt was tuned in response to this outcome, and the smoke test was not rerun to try to force an accepted result.
* Only one production-cycle invocation was made, per WP-013 section 20's explicit "keep the smoke test to one production cycle" instruction - it nonetheless made 15 real LLM calls under the hood (3 attempts × [1 generation + 4 always-called validators], with the 5th validator, textbook, making zero calls on all three attempts since its own independent retrieval found nothing each time).

## Live Exam Orchestration Smoke Test (WP-014)

**Executed successfully**, once (after the two prompt fixes described above), using `ExamOrchestrator.from_default_configuration().generate_exam(ExamRequest(categories={<category 16>: 1, <category 17>: 1}))` - 2 questions total, per WP-014 section 20's recommended small smoke-test size.

* **Attempt history, reported honestly per this project's established practice**: several earlier attempts against different real category pairs (the 1st/2nd, 3rd/4th, and 10th/11th canonical categories) hit real operational failures before this successful run - see "Decisions Made (WP-014)" above for the full accounting (one genuinely fixed defect, two investigated-but-not-fixed reliability issues in already-approved components). These are not WP-014 orchestration defects: in every case, `ExamOrchestrator`'s own logic behaved exactly as designed (no `try`/`except` swallowed the failure; it propagated immediately, exactly as WP-014 section 18 requires) - the failures originated inside already-approved WP-009/WP-012 components several layers below the orchestrator. The final run used the 16th/17th canonical categories (`אמבריולוגיה`, `טופוגרפיה של ההמיספרות`) and completed cleanly with no retries needed.
* Requested: 2 questions total (`{"אמבריולוגיה": 1, "טופוגרפיה של ההמיספרות": 1}`). Completed: **2/2**.
* Plan: position 1 = `אמבריולוגיה` / `STYLE_SIMILAR`; position 2 = `טופוגרפיה של ההמיספרות` / `STYLE_SIMILAR` (each category's own first question, so both correctly started at `STYLE_SIMILAR` per the per-category-restart policy).
* Per-question production: **both accepted on the first attempt** (1 attempt each, 0 duplicate replacements each) - Grounding/MCQ/Category/Quality all PASS, Textbook `NOT_FOUND` for both (independent course-book retrieval found nothing for either generated question - the empty-retrieval short-circuit path, no LLM call made for textbook validation on either).
* No duplicate replacements were needed or observed.
* Final exam (2 questions, in plan order, numbered 1-2):

  1. **(אמבריולוגיה)** מהו השם של התהליך שבו מתפתח דיסק תלת שכבתי מהדיסק הדו שכבתי במהלך האמבריאולוגיה?
     1. **גסטרולציה** (correct) 2. היפובלסטציה 3. אפיבלסטציה 4. דיפרנציאציה
  2. **(טופוגרפיה של ההמיספרות)** מהו הסולקוס המרכזי המחלק את האונה הפרונטלית מהאונה הפריאטלית במוח?
     1. **סולקוס צנטרלי** (correct) 2. סולקוס פריאטו-אוקסיפיטלי 3. סולקוס סילביאן 4. סולקוס אינטרפריאטלי

* This is a clean, complete, first-attempt success for both planned questions - a useful positive data point (unlike WP-013's own exhausted-baseline observation), though still just one exam/one category pair, not a systematic acceptance-rate measurement. No prompt was tuned to force this specific outcome; the two prompt fixes made beforehand addressed genuinely reproducible defects unrelated to *this* run's content, and category selection changed across attempts only to get a informative complete run for the report (not to cherry-pick an easy pass - several of the earlier, failed attempts used different categories for the same reason: to distinguish "is this categorical/content-specific" from "is this systemic").

## Real-Data Smoke Test (WP-015)

**Executed successfully**, once, using a real `ExamOrchestrator.from_default_configuration().generate_exam()` call (2 questions, categories 16/17 - the same pair that produced WP-014's clean live result) piped directly into `build_exam_output_bundle()`. WP-015 itself makes zero LLM calls; the only live API usage in this smoke test is the WP-014 exam-generation step that produces the `ExamGenerationResult` WP-015 then transforms. The live exam generation succeeded cleanly on the first attempt (no operational failures this run, unlike several of WP-014's own earlier attempts) - a realistic-fixture fallback (explicitly permitted by WP-015 section 20) was not needed.

* Clean exam (`bundle.exam`, `serialize_exam_json()`): 2 questions, numbered 1-2, categories `אמבריולוגיה`/`טופוגרפיה של ההמיספרות`, Hebrew fully readable (no `\uXXXX` escaping), no validation/generation-mode/evidence field present anywhere in the JSON (structurally impossible - `ExamQuestion` has no such fields).
* Audit (`bundle.audit`, `serialize_audit_json()`): 2 corresponding `QuestionAudit` records (`exam_id="exam-wp015-smoke"`, `provider="openai"`, `model="gpt-4o-mini"`), each with a complete `attempts` list (1 attempt each, both accepted on the first try, matching the WP-014 result), all five validation results present per attempt, `historical_reference_id: null` and `evidence: []` (the honestly-represented gaps - see "Decisions Made (WP-015)"), grounding-evidence identity intact and visible (`grounding.evidence_chunk_ids` - three real `STUDENT_SUMMARY:...` chunk ids for question 1's embryology grounding), and `textbook_check.status: "NOT_FOUND"` for both (empty course-book retrieval, matching WP-012's/WP-014's own short-circuit design).
* Cross-consistency check passed silently (no `AuditConsistencyError`) - confirming, on real (not synthetic) data, that `build_exam_audit()`'s invariant checks hold for actual `ExamOrchestrator` output, not just the hand-constructed fixtures used in unit tests.
* `AuditConsistencyError`'s failure-path behavior (mismatched question count/text/category/correct-answer, and rejected-attempt-as-accepted) was verified only via the unit-test fixtures in `tests/unit/test_output.py`, not against a real tampered result - deliberately constructing a real inconsistent `ExamGenerationResult` live would require no additional LLM calls to test meaningfully (the check operates on already-in-memory data), so no live coverage was needed here.
* No file-writing (`write_exam_json`/`write_audit_json`) was exercised against real output paths during this specific smoke run (only in the offline test suite, via `tmp_path`) - deferred to a natural point once WP-016's CLI has a real caller-supplied output location; the serialization functions those file-writers call (`serialize_exam_json`/`serialize_audit_json`) were exercised directly against this real data.

## CLI Smoke Test (WP-016)

**Executed successfully**, once, running the real installed-equivalent command (`python -m exam_generator.cli generate --request ... --exam-output ... --audit-output ...`) end-to-end against the real OpenAI API - the first genuinely full pipeline run through the actual CLI entry point (not Python API calls), with 1 requested question (category `אמבריולוגיה`, per WP-016 section 21's "prefer 1 question to limit cost").

* Exit code: **0**. Console output showed the expected stage sequence (`Loading request...` / `Initializing exam generator...` / `Generating exam...` / `Writing exam output...` / `Writing audit output...` / `Done.`) followed by the success summary (`Exam generated successfully: 1 question(s)`, both output paths).
* Both `exam.json` and `audit.json` were created, both valid UTF-8 JSON, Hebrew fully readable in both (no `\uXXXX` escaping) - confirmed by `json.load()` round-tripping successfully and a direct substring check.
* Clean exam contained exactly the public `ExamQuestion` fields (`number`, `question`, `answer1..4`, `correct_answer`, `category`) - no audit internals present.
* Audit corresponded to the generated question: same category/question/answers, `exam_id` derived from the run's timestamp, `provider="openai"`/`model="gpt-4o-mini"`, and - a genuinely useful real-data finding - **`generation_attempts: 2`** (the first attempt was rejected, `attempts[0].accepted == false`; the second was accepted, `attempts[1].accepted == true`), directly confirming that WP-013's bounded quality-regeneration loop, WP-016's "don't write output until the whole pipeline succeeds" guarantee, and WP-015's full-attempt-history preservation all worked correctly together on one real run - the CLI reported only the final accepted result cleanly, while the audit still preserved the rejected first attempt's complete validation detail.
* No secrets (`OPENAI_API_KEY` value, "sk-" prefix) appeared anywhere in either output file - confirmed by direct grep.
* One real invocation was made, per the WP's explicit "one real invocation is enough" instruction; no repeated reruns were performed to chase a different outcome.

## Tests

* Total: **806** (10 from WP-001 + 97+7 from WP-002/WP-015 model additions + 59 from WP-003 + 47 from WP-004 + 80 from WP-005 + 71 from WP-006 + 1 category-mapping config test + 49 from WP-007 + 110 from WP-008 + 28 from WP-009 + 22 from WP-010 + 43 from WP-011 + 25 from WP-012 + 30 from WP-013 + 1 max_duplicate_replacement_attempts config test + 28 from WP-014 + 35 from WP-015 + 27 from WP-016 + 26 from WP-017 unit + 10 from WP-017 integration)
* Passing: **806**
* Failing: **0**

Verification commands and results:

* `.venv/bin/python --version` → `Python 3.12.3`
* `.venv/bin/python -c "import openpyxl; print(openpyxl.__version__)"` → `3.1.5`
* `.venv/bin/python -c "import pymupdf; print(pymupdf.__version__)"` → `1.28.0`
* `.venv/bin/python -c "import sklearn; print(sklearn.__version__)"` → `1.9.0`
* `.venv/bin/python -c "import openai; print(openai.__version__)"` → `2.52.0`
* `.venv/bin/python -m pytest -v` → 806 passed, in ~4s with zero network access and no `OPENAI_API_KEY` set in the shell used for the offline run - satisfies the WP's mandatory offline-test requirement.
* `.venv/bin/python -m pytest tests/unit/test_llm.py -v` → 49 passed.
* `.venv/bin/python -m pytest tests/unit/test_prompts.py -v` → 110 passed, zero network access, no API key required, no `LLMProvider.generate_structured()` call anywhere in the WP-008 test suite (includes one WP-010 wording update - see Decisions Made).
* `.venv/bin/python -m pytest tests/unit/test_generation.py -v` → 28 passed, LLM provider fully mocked (`MagicMock(spec=LLMProvider)`), zero network access, no API key required.
* `.venv/bin/python -m pytest tests/unit/test_grounding_validation.py -v` → 22 passed, LLM provider fully mocked, zero network access, no API key required.
* `.venv/bin/python -m pytest tests/unit/test_mcq_validation.py tests/unit/test_category_validation.py tests/unit/test_quality_validation.py tests/unit/test_validation_independence.py -v` → 43 passed (13 MCQ + 13 category + 12 quality + 5 cross-validator independence), LLM provider fully mocked, zero network access, no API key required.
* `.venv/bin/python -m pytest tests/unit/test_textbook_validation.py -v` → 25 passed, LLM provider fully mocked, zero network access, no API key required.
* `.venv/bin/python -m pytest tests/unit/test_production.py -v` → 30 passed, generator and all five validators fully mocked, zero network access, no API key required.
* `.venv/bin/python -m pytest tests/unit/test_orchestration.py -v` → 28 passed, category resolver and producer fully mocked (a real `CategoryResolver` is used in a small number of alias/distribution tests, with no LLM involvement), zero network access, no API key required.
* `.venv/bin/python -m pytest tests/unit/test_output.py -v` → 35 passed, zero LLM/provider calls of any kind (mocked or real) - this WP makes none - zero network access, no API key required.
* `.venv/bin/python -m pytest tests/unit/test_models.py -v` → 104 passed (97 WP-002 + 7 new WP-015 `QuestionAttemptAudit`/`QuestionAudit.attempts` tests), zero network access, no API key required.
* `.venv/bin/python -m pytest tests/unit/test_cli.py -v` → 27 passed, orchestration boundary fully mocked, zero network access, no API key required.
* `.venv/bin/python -m pytest tests/unit/test_evaluation.py -v` → 26 passed, synthetic data only, zero network access, no API key required.
* `.venv/bin/python -m pytest tests/integration/test_end_to_end_pipeline.py -v` → 10 passed, real components wired together with only the LLM call scripted/faked, zero network access, no API key required.
* `.venv/bin/python scripts/run_evaluation.py --skip-generation` → real corpus/retrieval evaluation, no API key needed; Recall@3=86.5%/Recall@5=94.6%/Recall@8=94.6% across 37 fixture queries, 0 `UngroundedRetrievalQueryError`.
* `.venv/bin/python scripts/generate_schemas.py` run twice in a row → byte-identical output (deterministic; unaffected - `GeneratedQuestionResponse`/`GroundingValidationResult` are not newly schema-exported).
* `.venv/bin/python scripts/generate_schemas.py` re-run for WP-015 (`QuestionAttemptAudit`/`QuestionAudit.attempts` changed `ExamAudit`'s shape): `schemas/exam_audit.schema.json` updated; `schemas/exam_request.schema.json`/`schemas/exam_output.schema.json` byte-identical (unaffected, as expected - `ExamRequest`/`ExamOutput` were not touched). Re-run twice in a row afterward → byte-identical output both times (still deterministic).
* Real-workbook smoke test against `data/questions_full_export.xlsx`; confirmed no wording corruption.
* Real-source PDF verification against all four real PDFs; confirmed Hebrew/English/mixed content preserved.
* Real corpus + real retrieval-index verification against all four real PDFs; confirmed coverage invariants, ID uniqueness/determinism, and 20/20 canonical categories returning positive retrieval results.
* Real production-prompt-repository verification and real-data prompt-formatting smoke test (WP-008) - see "Real Prompt Verification (WP-008)" below.
* Live OpenAI smoke test: **not executed this WP** (see Live Smoke Test section above) - WP-008 makes no LLM/provider call at all, live or mocked, per its own explicit non-goals.
* `git status --short` / `git add -A --dry-run` → only WP-007 files (plus intentional `pyproject.toml` change) staged; no PDFs, Excel, `data/question_format.json`, `.venv/`, secrets, or generated output/index artifacts.
* Live candidate-quality validation smoke test (WP-011): one real generate-then-validate-four-ways sequence against the real OpenAI API - see "Live Candidate-Quality Validation Smoke Test (WP-011)" above.
* Live textbook validation smoke test (WP-012): one real generate-then-textbook-validate sequence against the real OpenAI API, including genuine (non-empty) course-book retrieval - see "Live Textbook Validation Smoke Test (WP-012)" above.
* Live production-cycle smoke test (WP-013): one real `QuestionProducer.produce_question()` call (3 bounded attempts, 15 real LLM calls) against the real OpenAI API - see "Live Production Cycle Smoke Test (WP-013)" above.
* Live exam-orchestration smoke test (WP-014): one real `ExamOrchestrator.generate_exam()` call (2 questions, both accepted first-attempt) against the real OpenAI API, after several earlier attempts surfaced and (partly) resolved real operational issues - see "Live Exam Orchestration Smoke Test (WP-014)" above and "Known Issues" below.
* Real-data smoke test (WP-015): one real `ExamOrchestrator.generate_exam()` call piped directly through `build_exam_output_bundle()`/serialization - see "Real-Data Smoke Test (WP-015)" above. WP-015 itself made zero LLM calls.
* CLI smoke test (WP-016): one real, full, end-to-end `python -m exam_generator.cli generate ...` invocation against the real OpenAI API - exit code 0, both output files valid/correct, one candidate rejected + one accepted preserved correctly in the audit - see "CLI Smoke Test (WP-016)" above.

## Real-Workbook Verification (WP-003)

Against the actual `data/questions_full_export.xlsx` (not modified):

* Worksheet selected: `Questions - Full` (the workbook's only worksheet)
* Total questions loaded: **459**
* Total canonical categories: **20**
* Category names and counts (first-seen workbook order):
  * התעלה השדרתית ותכולתה: 35
  * לוקליזציה פונקציונלית: 36
  * חומר לבן: 32
  * עצבים קרניאליים: 26
  * מיפוי ודימות מוחי: 24
  * היסטולוגיה: 33
  * המערכת הלימבית: 7
  * אספקת דם: 27
  * קרומים וסינוסים דוראליים: 19
  * גזע המוח: 17
  * מסילות עצביות: 23
  * גרעיני הבסיס: 34
  * המוח הקטן: 19
  * מערכת העצבים ההיקפית: 13
  * דיאנצפלון: 15
  * אמבריולוגיה: 34
  * טופוגרפיה של ההמיספרות: 30
  * חדרי המוח: 6
  * תאי מערכת העצבים: 18
  * מבוא: 11
* First loaded historical question: id=1, category=`התעלה השדרתית ותכולתה`
* Last loaded historical question (last workbook row, id is not sequential): id=471, category=`היסטולוגיה`
* All 459 rows loaded with native-integer `id`/`correct_answer_id` cells (no fractional or numeric-string values encountered); no duplicate IDs; no blank rows present in the real workbook.

These figures (459 questions / 20 categories) match the WP's stated expectation ("approximately 459 questions / 20 categories") — no discrepancy to investigate.

## Real-Source PDF Verification (WP-004)

Against the actual PDFs in `data/` (none modified), via `exam_generator.ingestion`'s public API:

* Student summaries: **3** (`student_summary_1.pdf`, `student_summary_2.pdf`, `student_summary_3.pdf`)

| filename | source_type | pages | non_empty_pages | empty_pages |
|---|---|---|---|---|
| student_summary_1.pdf | STUDENT_SUMMARY | 77 | 77 | 0 |
| student_summary_2.pdf | STUDENT_SUMMARY | 156 | 156 | 0 |
| student_summary_3.pdf | STUDENT_SUMMARY | 176 | 172 | 4 |
| course_book.pdf | COURSE_BOOK | 435 | 417 | 18 |

* Total student-summary pages: **409**
* Page counts for every document match `pdfinfo`'s independently-reported physical page count exactly (77 / 156 / 176 / 435).
* None of the four PDFs are encrypted (confirmed via `pdfinfo`); none are scanned/image-only (ordinary embedded-text extraction succeeded for all four; `pdftotext` cross-check also succeeded before implementation).
* **Hebrew verification**: 77/77 pages of `student_summary_1.pdf` contain Hebrew characters; a representative page (id/page 5) contains readable Hebrew text with embedded English terms (`trabeculae`, `Pia`) in correct logical reading order, not corrupted or reversed.
* **English/mixed terminology verification**: 417/435 `course_book.pdf` pages contain English text runs (exactly matching its non-empty-page count); anatomical terms (e.g. "Medulla Oblongata", "spinal cord") appear intact and untranslated. A mixed Hebrew/English excerpt from a student summary (`... Corona radiata ...`) was also confirmed intact.
* The empty pages found (18 in `course_book.pdf`: pages 1, 2, 4, 12, 44, 72, 98, 168, 210, 238, 270, 278, 294, 314, 330, 366, 380, 434; 4 in `student_summary_3.pdf`: pages 31, 137, 147, 176) were individually inspected and are consistent with legitimate blank/section-divider pages in a textbook/summary, not extraction failures — no document has zero non-empty pages.

## Real Corpus Verification (WP-005)

Built via `build_student_summary_corpus()` / `build_course_book_corpus()` (chunk_size=1800, chunk_overlap=300, from `config/app.yaml`):

**Student summary corpus:**
* source_files: 3
* physical pages with chunks: 405 (matches the 405 non-blank student-summary pages from WP-004's verification: 77+156+172)
* chunks: 506
* min/max/avg chunk length (chars): 47 / 1799 / 1089.3
* per-file: `student_summary_1.pdf`: 156, `student_summary_2.pdf`: 178, `student_summary_3.pdf`: 172
* first_chunk_id: `STUDENT_SUMMARY:student_summary_1.pdf:0001:0001`
* last_chunk_id: `STUDENT_SUMMARY:student_summary_3.pdf:0175:0001`
* unique_chunk_ids: **true**

**Course book corpus:**
* physical pages with chunks: 417 (matches the 417 non-blank course-book pages from WP-004's verification)
* chunks: 994
* min/max/avg chunk length (chars): 42 / 1799 / 1464.0
* first_chunk_id: `COURSE_BOOK:course_book.pdf:0003:0001`
* last_chunk_id: `COURSE_BOOK:course_book.pdf:0435:0005`
* unique_chunk_ids: **true**

**Programmatic coverage verification** (all four real documents): every non-blank `ExtractedPage` produced ≥1 chunk; every blank page produced exactly 0 chunks; every emitted chunk's `page` exists in its source document and is ≥1; rebuilding both corpora from scratch produced byte-identical chunk IDs and ordering.

**Manual quality inspection** (student_summary_1.pdf beginning/middle/end, a mixed Hebrew/English page, and course_book.pdf): chunks read as coherent Hebrew/English prose, not arbitrarily truncated mid-boundary; page-5 mixed content (`trabeculae`, `Pia`, `Ventral root`) preserved intact. Precisely verified overlap on page 5: chunk 2 begins at character offset 1454 within chunk 1 (length 1752) - a ~298-character overlap, matching the configured 300, with the shared Hebrew/English text identical in both chunks.

## Real Retrieval Verification (WP-006)

Built via `build_student_summary_retrieval_index()` / `build_course_book_retrieval_index()` (top_k=8, ngram_range=(3,5), from `config/app.yaml`):

**Student-summary index:** 506 indexed chunks (matches WP-005's corpus exactly), 3 source files, 98,105 TF-IDF features, source_type=STUDENT_SUMMARY, construction ~1.66s, deterministic reconstruction confirmed (identical chunk IDs/scores/ranks across two independent builds).

**Course-book index:** 994 indexed chunks (matches exactly), 1 source file, 84,211 TF-IDF features, source_type=COURSE_BOOK, construction ~1.94s, deterministic reconstruction confirmed.

**Canonical-category retrieval smoke test** (all 20 real canonical categories, top_k=8, against the student-summary index): **all 20 returned 8/8 positive-score results — zero categories with no results.** Scores ranged 0.088–0.486. Full table (category: result_count, top_score, top_chunk_id):

| category | results | top_score | top_chunk_id |
|---|---|---|---|
| התעלה השדרתית ותכולתה | 8 | 0.3029 | STUDENT_SUMMARY:student_summary_2.pdf:0003:0001 |
| לוקליזציה פונקציונלית | 8 | 0.3394 | STUDENT_SUMMARY:student_summary_2.pdf:0049:0001 |
| חומר לבן | 8 | 0.2694 | STUDENT_SUMMARY:student_summary_2.pdf:0032:0001 |
| עצבים קרניאליים | 8 | 0.3680 | STUDENT_SUMMARY:student_summary_3.pdf:0124:0001 |
| מיפוי ודימות מוחי | 8 | 0.3243 | STUDENT_SUMMARY:student_summary_3.pdf:0080:0001 |
| היסטולוגיה | 8 | 0.3273 | STUDENT_SUMMARY:student_summary_2.pdf:0047:0001 |
| המערכת הלימבית | 8 | 0.4416 | STUDENT_SUMMARY:student_summary_2.pdf:0139:0001 |
| אספקת דם | 8 | 0.4301 | STUDENT_SUMMARY:student_summary_2.pdf:0069:0001 |
| קרומים וסינוסים דוראליים | 8 | 0.2197 | STUDENT_SUMMARY:student_summary_2.pdf:0070:0001 |
| גזע המוח | 8 | 0.4855 | STUDENT_SUMMARY:student_summary_2.pdf:0089:0001 |
| מסילות עצביות | 8 | 0.3774 | STUDENT_SUMMARY:student_summary_2.pdf:0108:0001 |
| גרעיני הבסיס | 8 | 0.3282 | STUDENT_SUMMARY:student_summary_2.pdf:0036:0001 |
| המוח הקטן | 8 | 0.2441 | STUDENT_SUMMARY:student_summary_2.pdf:0120:0001 |
| מערכת העצבים ההיקפית | 8 | 0.4124 | STUDENT_SUMMARY:student_summary_2.pdf:0149:0001 |
| דיאנצפלון | 8 | 0.4808 | STUDENT_SUMMARY:student_summary_2.pdf:0113:0001 |
| אמבריולוגיה | 8 | 0.2069 | STUDENT_SUMMARY:student_summary_2.pdf:0011:0001 |
| טופוגרפיה של ההמיספרות | 8 | 0.3991 | STUDENT_SUMMARY:student_summary_2.pdf:0018:0001 |
| חדרי המוח | 8 | 0.1361 | STUDENT_SUMMARY:student_summary_2.pdf:0089:0001 |
| תאי מערכת העצבים | 8 | 0.3735 | STUDENT_SUMMARY:student_summary_1.pdf:0024:0002 |
| מבוא | 8 | 0.0878 | STUDENT_SUMMARY:student_summary_2.pdf:0001:0001 |

Total query time for all 20 categories: ~0.17s (~8.4ms/query average).

**Representative content smoke tests** (see Known Retrieval-Quality Observations below for the honest ranking-quality finding):
* Hebrew term `קליפת המוח` (cerebral cortex) → top chunk `STUDENT_SUMMARY:student_summary_3.pdf:0032:0001`, score 0.1421, topically relevant (discusses gray/white matter and cortex) though the literal phrase isn't in the #1 chunk specifically - the literal phrase appears in 18 chunks corpus-wide, three of which appear at ranks 3-5.
* English term `Medulla Oblongata` → top chunk `COURSE_BOOK:course_book.pdf:0091:0001`, score 0.3097, contains the exact phrase.
* Mixed-content term `trabeculae` (confirmed present in exactly 1 real chunk, from WP-005's precise overlap verification) → that exact chunk (`STUDENT_SUMMARY:student_summary_1.pdf:0005:0001`) appears at rank 3, score 0.0777; no Unicode corruption in any result.

## Real Prompt Verification (WP-008)

Loaded every production prompt through the real `PromptRepository.from_default_location()` (no LLM call):

| prompt_id | file | required_variables | version prefix |
|---|---|---|---|
| SYSTEM | system/exam_generator.txt | (none) | f40c13486d0701aa |
| QUESTION_GENERATION | generation/question.txt | category, generation_mode, source_evidence, historical_reference | fddc0c1a31190b4d |
| GROUNDING_VALIDATION | validation/grounding.txt | candidate_question, source_evidence | bb53657ee4749edc |
| MCQ_VALIDATION | validation/mcq.txt | candidate_question | 67db50ecbe0d1aa7 |
| CATEGORY_VALIDATION | validation/category.txt | candidate_question, expected_category | 7ae0b7235c0b358d |
| QUALITY_VALIDATION | validation/quality.txt | candidate_question | 1199c691ec0b3a6e |
| TEXTBOOK_VALIDATION | validation/textbook.txt | candidate_question, course_book_evidence | a169fcd5c4179c25 |

**Real-data formatting smoke test** (formatting/rendering only - zero LLM calls), using real project data via the existing WP-003/WP-005/WP-006 subsystems:

* Real canonical category used: `התעלה השדרתית ותכולתה` (first canonical category from the real workbook).
* Real student-summary evidence: top-3 `retrieve_for_category()` results against the real student-summary retrieval index (3 chunks).
* Real historical reference: `historical_question_id=1`, the first real historical question in that category.
* Real course-book chunk: `COURSE_BOOK:course_book.pdf:0003:0001` (page 3), taken directly from the real course-book corpus.
* `QUESTION_GENERATION` rendered successfully for both `STYLE_SIMILAR` (5,779 chars, with the real historical reference; confirmed `NOT FACTUAL EVIDENCE` and `AUTHORITATIVE` markers both present and distinct) and `INDEPENDENT` (5,543 chars; confirmed the "No historical style reference is supplied" sentinel present, no fabricated reference).
* `GROUNDING_VALIDATION`, `MCQ_VALIDATION`, `CATEGORY_VALIDATION`, `QUALITY_VALIDATION` all rendered successfully against a real candidate built from the real historical reference's text.
* `TEXTBOOK_VALIDATION` rendered successfully against the real course-book chunk; confirmed the real chunk ID appears in the rendered text and the `SECONDARY` label is present.
* Hebrew characters confirmed present and intact in the rendered `STYLE_SIMILAR` generation prompt (spot-checked via Hebrew Unicode block membership).
* No corruption, truncation, or mis-delimiting observed in any of the above.

## Known Issues / Open Questions

* **Python version deviation from WP-001 spec (carried forward).** WP-001.md specified Python 3.14 and assumed a pre-existing project-local `.venv` built with it. Neither a Python 3.14 interpreter nor a pre-existing `.venv` was actually present on this machine (only system `python3` / `python3.12` = 3.12.3, confirmed via `apt list --installed` and filesystem search). Per explicit user instruction, WP-001 through WP-007 were implemented and verified against **Python 3.12.3** instead, with `pyproject.toml` declaring `requires-python = ">=3.12"`. This is a factual correction of the WP's environment assumption, not an architectural change. `openpyxl`, `pymupdf`, `scikit-learn`, and now `openai` were all confirmed to install and work correctly under 3.12.3.
* See "Known Retrieval-Quality Observations" above for WP-006-specific findings (all explicitly non-blocking per the WP's own acceptance criteria - honest reporting was required, not resolution).
* No open issues from WP-007. Live OpenAI compatibility (`gpt-4o-mini` + Responses API + `temperature` + structured output) was verified end-to-end against the real API by the user after this WP's initial completion report - see Live Smoke Test above.
* No open issues from WP-008. The real course-book retrieval index returned zero results for the specific canonical-category text queried during the real-data smoke test (a known, previously-documented WP-006 short-query ranking characteristic, not a WP-008 defect); the smoke test used a real course-book chunk taken directly from the real corpus instead so `TEXTBOOK_VALIDATION` was still exercised against genuine course-book content.
* No open issues from WP-009. The live generation smoke test (initially skipped - no key available at implementation time) was run successfully once the user supplied `OPENAI_API_KEY` - see "Live Generation Smoke Test (WP-009)" above for the generated question/answers.
* No open issues from WP-010. The live smoke test initially exposed a real, reproducible provenance-check failure caused by prompt wording (see "Decisions Made (WP-010)"); it was fixed (with explicit user approval, since it meant editing already-shipped WP-008 prompt files) and confirmed resolved by a subsequent successful live call. Only one real grounding verdict has been observed so far (`passed=True`, high confidence) - this is not a quality/accuracy measurement across multiple questions or categories, just a confirmation that the pipeline works end-to-end. WP-013 (diversity/retry) and broader manual review will be where real grounding-quality patterns get surfaced.
* No open issues from WP-011. The live smoke test's candidate happened to fail all four independent validators at once (Grounding/MCQ/Category/Quality) - this is an honest, self-consistent negative result about that one generated candidate (all four reasons independently converge on the same underlying weakness: the correct answer isn't the only defensible one, and the question is really about general vertebral function, not the requested category), not a validator defect, and per WP-011 section 15 is an explicitly acceptable, informative smoke-test outcome. No prompt was tuned in response. Only one real four-way verdict combination has been observed so far - not a systematic quality measurement across multiple candidates/categories.
* No open issues from WP-012. The live smoke test's textbook verdict was `NOT_FOUND` despite genuine (non-empty, 3-chunk) course-book retrieval - the LLM judged the retrieved material insufficient to confidently support or contradict the specific candidate, which is a legitimate `NOT_FOUND` use case distinct from the empty-retrieval short-circuit path (both were exercised: the empty-retrieval path in unit tests, the LLM-judged-insufficient path live). This contrasts with WP-008's own real-data smoke test, which saw zero course-book retrieval results for a bare category-name query (a documented WP-006 short-query ranking characteristic); WP-012's query additionally includes the full question and answer text, which was sufficient to retrieve real candidates in the live test. Only one real textbook verdict has been observed so far - not a systematic quality measurement across multiple candidates/categories.
* No open implementation issues from WP-013, but the live smoke test surfaced two real, worth-recording observations. First, a genuine prompt-contract defect in `prompts/validation/textbook.txt` (see "Decisions Made (WP-013)" - fixed with explicit user approval). Second, an honest quality-baseline data point: the one live production cycle exhausted all 3 attempts without an accepted candidate - Grounding passed all three times, but MCQ and/or Quality failed on all three, reinforcing (not merely repeating) the same generation-construction weaknesses WP-011's independent live smoke test already observed. This is not a WP-013 defect - it is exactly the honest baseline measurement WP-013 section 15 explicitly asks for ("This also gives us an honest baseline for how often repeated independent model generations pass"). Only one real production-cycle outcome has been observed so far - not a systematic acceptance-rate measurement across multiple categories/runs; sophisticated validator-feedback regeneration (which might improve this rate) is explicitly deferred, per the WP's own scope.
* **No open implementation issues from WP-014's own orchestration logic** - every live failure encountered during smoke testing propagated correctly and immediately, exactly as designed, from components several layers below `ExamOrchestrator`. Two distinct operational-reliability issues were surfaced and are recorded here rather than chased further, per this project's established "record honestly rather than tune prompts to force a pass" philosophy:
  * **`TextbookValidator`'s `reference_text` verbatim-quoting instruction is not 100%-reliable even after two prompt fixes.** WP-013 fixed a clear paraphrasing defect; WP-014 fixed a clear empty-string-vs-null ambiguity in that same fix's own wording (see "Decisions Made (WP-014)"). After both fixes, a small number of live calls (across several different real categories, both before and after the second fix) still hit `InvalidTextbookOutputError` on a `reference_text` that did not verbatim-match its cited evidence. A live investigation specifically ruled out a plausible *implementation* bug (Unicode-normalization false-mismatch in the plain-substring provenance check) - repeated debug calls against fixed real evidence produced either a clean `NOT_FOUND` with no citation, or a citation that was a genuine semantic paraphrase. This looks like an inherent `gpt-4o-mini` reliability ceiling for this specific instruction, not a wording defect with an obvious further fix - the correct system response (which is exactly what happens today) is to reject the unverifiable citation as an operational failure, not to weaken the provenance check.
  * **The WP-009 generator's evidence-id provenance check (fixed once already in WP-010) was seen to reject an invented `evidence_chunk_ids` value once more, live, for a different category** than WP-010's original finding. This is the same failure *class*, recurring for different specific content - not investigated further as a distinct new wording defect, since (like the textbook case above) it reflects the same class of imperfect, non-zero model non-compliance that these provenance checks exist specifically to catch rather than eliminate.
  * Neither issue blocks correct operation - both are correctly-propagated operational failures, exactly matching this project's designed fail-closed behavior throughout the validation/production/orchestration stack. A future WP could reasonably consider an explicit *operational*-failure retry policy (distinct from WP-013's quality-regeneration and WP-014's duplicate-replacement bounds, both of which are deliberately quality-only per their own explicit scope), if live reliability at this rate is judged unacceptable for production use - not attempted here, since WP-014 section 21 explicitly excludes "global API retry."
  * One clean, complete, first-attempt-success 2-question exam was still produced live (see "Live Exam Orchestration Smoke Test (WP-014)") - these reliability observations describe the frequency of a known failure mode across ~10 live calls made during this WP's testing, not a claim that the system cannot succeed.
* **No open issues from WP-015.** The one real-data smoke test succeeded cleanly on the first attempt (no operational failures this time), and the deterministic transformation/serialization logic is fully covered offline. Two known, deliberate scope gaps are documented rather than hidden: `historical_reference_id`/`evidence` are honestly represented as absent (not derivable without broader refactoring of already-shipped WP-009/WP-010/WP-012 components - see "Decisions Made (WP-015)"), and prompt-version/hash provenance was investigated and found genuinely unavailable, with no existing contract field requiring it. Neither is a defect in WP-015's own logic; both are candidates for a future WP if richer audit provenance is ever prioritized.
* **No open issues from WP-016.** The one real CLI smoke test succeeded cleanly (exit 0, both outputs correct) on the first attempt - no repeated invocations were needed this time, unlike several earlier WPs' live testing. One genuinely useful real-data observation surfaced (not a defect): the smoke test's single requested question needed 2 internal `QuestionProducer` attempts (one rejected, one accepted) before the CLI could report success, directly demonstrating live that the CLI's "only write output once the whole pipeline has fully succeeded" behavior and WP-015's full-attempt-history preservation both work correctly together, not just in mocked tests. During implementation, an early test-isolation bug caused two files (`exam.json`, `exam_audit.json`) to be briefly created in the real project repository root by a not-yet-isolated CLI test run; caught and deleted immediately, never committed, and fixed permanently with an autouse `_isolated_cwd` fixture applied to the whole test module (see "Decisions Made (WP-016)") - noted here for transparency, not because any trace of it remains.
* **The most significant finding of the whole project so far surfaced in WP-017**: a very high (45% of all planned questions across two independent live runs) empty-required-string-field structured-output failure rate, concentrated on `QualityValidationResult.reason` specifically, at `validation_temperature=0.0`. This is not a new failure *class* (the same class was noted occasionally in WP-013/WP-014), but its frequency here is much higher than any prior scattered observation - see "Live Evaluation Baseline (WP-017)" above for full data and "Decisions Made (WP-017)" for the two narrow instrumentation fixes (catching `pydantic.ValidationError`, capturing accepted-candidate text) this WP made to obtain a valid measurement of it. **No production/prompt tuning was performed in response to this finding**, per WP-017's own explicit "measure before improving" rule - this is exactly the kind of evidence WP-017 exists to surface for WP-018 to act on, not a WP-017 defect. The CLI's own error classification (`exam_generator/cli.py::_classify_error()`, WP-016) does not currently have a specific branch for a raw `pydantic.ValidationError` reaching it from deep in the pipeline (as opposed to the request-parsing case, which is already handled via `CliUsageError`) - it would currently propagate as an "unexpected" traceback rather than a clean `EXIT_GENERATION_FAILURE` message; not fixed here (WP-016 is already-shipped, out of scope for this WP's narrow instrumentation-only fixes), but worth WP-018 considering alongside the underlying reliability fix.

## Files Added

WP-001 (carried forward, unchanged this WP):
* `pyproject.toml`, `.gitignore`, `.env.example`
* `config/app.yaml`, `config/llm.yaml`, `config/category_mapping.yaml`
* `src/exam_generator/__init__.py`, `src/exam_generator/config/__init__.py`, `src/exam_generator/config/models.py`, `src/exam_generator/config/loader.py`
* `tests/unit/test_config.py`
* `output/.gitkeep`, `index/.gitkeep`

WP-002 (carried forward, unchanged this WP):
* `src/exam_generator/models/__init__.py`
* `src/exam_generator/models/_common.py`
* `src/exam_generator/models/question.py`
* `src/exam_generator/models/exam.py`
* `src/exam_generator/models/source.py`
* `src/exam_generator/models/validation.py`
* `src/exam_generator/models/audit.py`
* `scripts/generate_schemas.py`
* `schemas/exam_request.schema.json`
* `schemas/exam_output.schema.json`
* `schemas/exam_audit.schema.json`
* `schemas/exam_request.example.json`
* `tests/unit/test_models.py`

WP-003 (carried forward, unchanged this WP):
* `src/exam_generator/historical/__init__.py`
* `src/exam_generator/historical/errors.py`
* `src/exam_generator/historical/loader.py`
* `src/exam_generator/historical/repository.py`
* `tests/unit/test_historical.py`

WP-004 (carried forward, unchanged this WP):
* `src/exam_generator/ingestion/__init__.py`
* `src/exam_generator/ingestion/errors.py`
* `src/exam_generator/ingestion/models.py`
* `src/exam_generator/ingestion/pdf.py`
* `src/exam_generator/ingestion/discovery.py`
* `tests/unit/test_ingestion.py`

WP-005 (carried forward, unchanged this WP):
* `src/exam_generator/chunking/__init__.py`
* `src/exam_generator/chunking/errors.py`
* `src/exam_generator/chunking/chunker.py`
* `src/exam_generator/chunking/corpus.py`
* `tests/unit/test_chunking.py`

WP-006 (carried forward, unchanged this WP):
* `src/exam_generator/retrieval/__init__.py`
* `src/exam_generator/retrieval/errors.py`
* `src/exam_generator/retrieval/models.py`
* `src/exam_generator/retrieval/index.py`
* `src/exam_generator/retrieval/categories.py`
* `tests/unit/test_retrieval.py`

WP-007 (carried forward, unchanged this WP):
* `src/exam_generator/llm/__init__.py`
* `src/exam_generator/llm/errors.py`
* `src/exam_generator/llm/models.py`
* `src/exam_generator/llm/provider.py`
* `src/exam_generator/llm/factory.py`
* `src/exam_generator/llm/openai_provider.py`
* `scripts/smoke_openai.py`
* `tests/unit/test_llm.py`

WP-008 (carried forward, unchanged this WP):
* `src/exam_generator/prompts/__init__.py`
* `src/exam_generator/prompts/errors.py`
* `src/exam_generator/prompts/models.py`
* `src/exam_generator/prompts/repository.py`
* `src/exam_generator/prompts/renderer.py`
* `src/exam_generator/prompts/formatting.py`
* `src/exam_generator/prompts/context.py`
* `prompts/system/exam_generator.txt`
* `prompts/generation/question.txt`
* `prompts/validation/grounding.txt`
* `prompts/validation/mcq.txt`
* `prompts/validation/category.txt`
* `prompts/validation/quality.txt`
* `prompts/validation/textbook.txt`
* `tests/unit/test_prompts.py`

WP-009 (carried forward, unchanged this WP):
* `src/exam_generator/generation/__init__.py`
* `src/exam_generator/generation/errors.py`
* `src/exam_generator/generation/generator.py`
* `tests/unit/test_generation.py`

WP-010 (carried forward, unchanged this WP):
* `src/exam_generator/validation/__init__.py` (further modified this WP - see WP-011 below)
* `src/exam_generator/validation/errors.py`
* `src/exam_generator/validation/grounding.py`
* `tests/unit/test_grounding_validation.py`

WP-011 (carried forward, unchanged this WP):
* `src/exam_generator/validation/mcq.py`
* `src/exam_generator/validation/category.py`
* `src/exam_generator/validation/quality.py`
* `tests/unit/test_mcq_validation.py`
* `tests/unit/test_category_validation.py`
* `tests/unit/test_quality_validation.py`
* `tests/unit/test_validation_independence.py`

WP-012 (carried forward, unchanged this WP):
* `src/exam_generator/validation/textbook.py`
* `tests/unit/test_textbook_validation.py`

WP-013 (carried forward, unchanged this WP):
* `src/exam_generator/production/__init__.py`
* `src/exam_generator/production/errors.py`
* `src/exam_generator/production/models.py`
* `src/exam_generator/production/producer.py`
* `tests/unit/test_production.py`

WP-014 (carried forward, unchanged this WP):
* `src/exam_generator/orchestration/__init__.py`
* `src/exam_generator/orchestration/errors.py`
* `src/exam_generator/orchestration/models.py`
* `src/exam_generator/orchestration/orchestrator.py`
* `tests/unit/test_orchestration.py`

WP-015 (carried forward, unchanged this WP):
* `src/exam_generator/output/__init__.py`
* `src/exam_generator/output/errors.py`
* `src/exam_generator/output/models.py`
* `src/exam_generator/output/audit.py`
* `src/exam_generator/output/bundle.py`
* `src/exam_generator/output/serialization.py`
* `tests/unit/test_output.py`

WP-016 (carried forward, unchanged this WP):
* `src/exam_generator/cli.py`
* `tests/unit/test_cli.py`
* `README.md`

WP-017 (new):
* `src/exam_generator/evaluation/__init__.py`
* `src/exam_generator/evaluation/errors.py`
* `src/exam_generator/evaluation/models.py`
* `src/exam_generator/evaluation/metrics.py`
* `src/exam_generator/evaluation/runner.py`
* `src/exam_generator/evaluation/retrieval_fixture.py`
* `src/exam_generator/evaluation/report.py`
* `scripts/run_evaluation.py`
* `tests/unit/test_evaluation.py`
* `tests/integration/test_end_to_end_pipeline.py`
* `evaluation/evaluation_report_run1.json`, `evaluation/evaluation_report_run1.md` (first live baseline run - instrumentation-incomplete, preserved for transparency)
* `evaluation/evaluation_report_run2.json`, `evaluation/evaluation_report_run2.md` (second live baseline run, complete instrumentation)
* `evaluation/evaluation_report_combined.json`, `evaluation/evaluation_report_combined.md` (merged dataset - the authoritative baseline report)

## Files Significantly Modified

* `docs/PROJECT_STATUS.md` (this file).
* `docs/ARCHITECTURE.md` (WP-002: `SourceType` enum values spelled out under Retrieval. WP-003: new "Historical Question Ingestion" section. WP-004: new "PDF Text Extraction" section. WP-005: new "Factual Source Chunking and Corpora" section. WP-006: new "Local Retrieval and Category Integration" section. WP-007: expanded the existing "LLM Boundary" section with a new "LLM Abstraction and OpenAI Provider" subsection. WP-008: expanded the existing "Prompt Boundary" section with a new "External Prompt Infrastructure" subsection. WP-009: new "Question Generation" section. WP-010: new "Independent Grounding Validation" section, plus an evidence-identifier-fidelity note appended to the WP-009 section. WP-011: new "MCQ, Category, and Quality Validation" section. WP-012: new "Secondary Textbook Consistency Validation" section. WP-013: new "Single-Question Production Control Layer" section plus a "Live-Test-Driven Textbook Prompt Fix" subsection. WP-014: new "Exam Orchestration" section plus a "Live-Test-Driven Textbook Prompt Fix #2" subsection. WP-015: new "Exam Output and Audit Trail" section, plus an `attempts`/gap note appended to the existing "Audit JSON" subsection. WP-016: new "CLI and Application Entry Point" section, plus the pre-existing placeholder "CLI" section rewritten to reflect the actual implemented command. WP-017: new "Evaluation Layer" section).
* `pyproject.toml` (WP-003: added `openpyxl>=3.1`. WP-004: added `pymupdf>=1.24`. WP-005: no new dependency. WP-006: added `scikit-learn>=1.4`. WP-007: added `openai>=2.0`. WP-008: no new dependency. WP-009: no new dependency. WP-010: no new dependency. WP-011: no new dependency. WP-012: no new dependency. WP-013: no new dependency. WP-014: no new dependency. WP-015: no new dependency. WP-016: no new dependency - added `[project.scripts]` entry point only, no new package dependency. WP-017: no new dependency).
* `src/exam_generator/models/audit.py` (WP-015: added `QuestionAttemptAudit`; `QuestionAudit` gained `attempts: list[QuestionAttemptAudit]`, min length 1).
* `src/exam_generator/models/__init__.py` (WP-015: exported `QuestionAttemptAudit`).
* `tests/unit/test_models.py` (WP-015: added `make_question_attempt_audit()` factory, updated `make_question_audit()` to supply `attempts=[...]`, added 7 new tests for the new model/field).
* `schemas/exam_audit.schema.json` (WP-015: regenerated via `scripts/generate_schemas.py` to reflect `QuestionAudit.attempts`/`QuestionAttemptAudit`; `exam_request.schema.json`/`exam_output.schema.json` unaffected, confirmed byte-identical).
* `src/exam_generator/validation/__init__.py` (WP-011: exported `MCQValidator`, `CategoryValidator`, `QualityValidator` alongside the existing WP-010 `GroundingValidator`/error exports. WP-012: further exported `TextbookValidator`, `TextbookValidationError`, `InvalidTextbookOutputError`).
* `src/exam_generator/validation/errors.py` (WP-012: added `TextbookValidationError` → `InvalidTextbookOutputError`; module docstring broadened from "grounding validation" to "candidate-quality validation" generally, now that it hosts two independent error hierarchies).
* `prompts/validation/textbook.txt` (WP-008/WP-012, content changed in WP-013: `source_page`/`reference_text` guidance now requires exact, character-for-character correspondence to supplied evidence (or left empty) rather than the previous looser "must come from the supplied evidence" wording - see "Decisions Made (WP-013)". New version hash prefix: `de8e3f35c8b6fd2c`. Content changed again in WP-014: fixed an empty-string-vs-null ambiguity in that same WP-013 wording - see "Decisions Made (WP-014)". New version hash prefix: `192b24c66a7bc404`).
* `config/app.yaml` (WP-014: added `generation.max_duplicate_replacement_attempts: 2`, and clarified the `generation:` section's comment now that two of its five fields are actively used).
* `src/exam_generator/config/models.py` (WP-014: `GenerationBehaviorConfig` gained `max_duplicate_replacement_attempts: int = Field(gt=0)`).
* `src/exam_generator/models/_common.py` (WP-014: added `NonNegativeIntStrict`, a sibling to the existing `PositiveIntStrict`, for `QuestionProductionRecord.duplicate_replacement_attempts`).
* `tests/unit/test_config.py` (WP-014: added `max_duplicate_replacement_attempts` assertions/rejection test).
* `config/app.yaml` (WP-006: added `retrieval:` section: `top_k: 8`, `ngram_min: 3`, `ngram_max: 5`).
* `config/category_mapping.yaml` (WP-006: schema changed from placeholder `aliases: {}` to activated `mapping: {}` - see Decisions Made).
* `src/exam_generator/config/models.py` (WP-006: added `RetrievalConfig`, `CategoryMappingConfig`, `NonBlankConfigStr`/`_reject_blank` helpers, `AppConfig.retrieval` field).
* `src/exam_generator/config/loader.py` (WP-006: added `load_category_mapping()`).
* `src/exam_generator/config/__init__.py` (WP-006: exported `RetrievalConfig`, `CategoryMappingConfig`, `load_category_mapping`).
* `tests/unit/test_config.py` (WP-006: added `retrieval` field assertions and a `load_category_mapping()` test).
* `src/exam_generator/models/question.py` (WP-009: added `GeneratedQuestionResponse`, the LLM-facing structured-output contract for generation).
* `src/exam_generator/models/__init__.py` (WP-009: exported `GeneratedQuestionResponse`).
* `prompts/generation/question.txt` (WP-008, content changed in WP-010: the `evidence_chunk_ids` guidance now requires copying the identifier character-for-character including the `SourceType:` prefix - see Decisions Made. New version hash prefix: `d4f9940c31f9d703`).
* `prompts/validation/grounding.txt` (WP-008, content changed in WP-010: identical `evidence_chunk_ids` fidelity fix - see Decisions Made. New version hash prefix: `c1b8df1b03518333`).
* `tests/unit/test_prompts.py` (WP-010: one assertion in `test_grounding_prompt_evidence_ids_must_come_from_supplied_evidence` updated to match the new grounding-prompt wording; no test coverage removed).

## Deferred Work

Implementation roadmap:

* WP-001 Repository skeleton + configuration
* WP-002 Domain models and schemas
* WP-003 Historical Excel ingestion
* WP-004 PDF extraction
* WP-005 Chunking + indexing
* WP-006 Retrieval/category mapping
* WP-007 LLM abstraction + OpenAI provider
* WP-008 External prompt infrastructure
* WP-009 Question generation
* WP-010 Grounding validation
* WP-011 Additional MCQ/category validation
* WP-012 Textbook secondary validation
* WP-013 Diversity/retry controller
* WP-014 Exam orchestration
* WP-015 Exam + audit output
* WP-016 CLI
* WP-017 Integration tests
* WP-018 End-to-end validation

The roadmap provides architectural planning context only.

Claude must implement only the Work Package currently supplied by GPT.

## Next WP Context

WP-001 through WP-017 are complete. Every layer through `src/exam_generator/cli` (the installed `exam-generator generate` command) exists and has been confirmed working end-to-end, both via the CLI directly (WP-016) and via a dedicated offline integration suite plus two independent live evaluation runs (WP-017). `src/exam_generator/evaluation` now provides a reusable, read-only evaluation runner/metrics/retrieval-fixture layer (`CandidateEvaluationRunner`, `RetrievalEvaluationRunner`, `metrics`, `RETRIEVAL_EVAL_QUERIES`) and `scripts/run_evaluation.py` as its manual driver. The V1 architecture described in the master brief is fully implemented and has now been *measured*, not just built. The single most important thing for WP-018's author to know:

* **The dominant, measured bottleneck is operational reliability, not candidate quality, retrieval quality, or a missing feature.** Across 20 live-evaluated planned questions (two independent runs, identical config), 70% hit an operational failure before any validation verdict was recorded, 45% (9/20) from one specific, reproducible cause: an empty-string `QualityValidationResult.reason` field at `validation_temperature=0.0`. When the pipeline *did* complete an attempt operationally, 85.7% were accepted. See "Live Evaluation Baseline (WP-017)" above for full data, and "Decisions Made (WP-017)" for the two narrow evaluation-instrumentation fixes made to obtain this measurement (neither touched generation/validation/retrieval/prompt/acceptance code).
* **TF-IDF retrieval is evidenced as sufficient for V1** - Recall@3=86.5%, Recall@5/@8=94.6% across 37 corpus-grounded queries spanning all 20 canonical categories. No evidence supports prioritizing embeddings/hybrid retrieval.
* **A concrete automated-validator gap was found via human review**: one accepted candidate had answer choices redundantly numbered inside their own text (in addition to the exam format's own numbering) - `QualityValidator` did not catch it. A small, low-confidence data point (n=4 reviewed), not a systemic quality problem.
* **No exam-level semantic diversity, historical-reference rotation, or answer-position balancing exists** - unchanged from the WP-014/WP-015 notes, still out of scope, still deferred.
* **No global operational-failure retry exists at any layer**, by design (WP-013/WP-014 both explicitly exclude it) - WP-017's baseline is the strongest evidence yet that this now matters in practice, given the measured 70% operational-failure rate. Whether a bounded, clearly-scoped retry belongs at some future layer remains an open, evidence-backed question for WP-018 to decide, not resolved here per WP-017's own "measure before improving" rule.
* **Two audit-provenance gaps remain open, by deliberate WP-015 scope decision** - unchanged: `QuestionAudit.historical_reference_id`/`.evidence` are always `None`/`[]`; prompt-version/hash provenance is not captured anywhere.
* **The WP-016 CLI's error classifier (`_classify_error()`) has no specific branch for a raw `pydantic.ValidationError` reaching it from deep in the pipeline** (as opposed to request-parsing, which is already handled) - discovered while building WP-017's own evaluation runner, not fixed (out of scope for this WP's narrow instrumentation-only changes), but directly relevant if WP-018 addresses the underlying reliability issue, since a real fix there would also naturally reduce how often a CLI user hits this specific gap.

The environment's Python interpreter is 3.12.3, not 3.14 as WP-001.md assumed; see Known Issues above. `openpyxl>=3.1` (3.1.5), `pymupdf>=1.24` (1.28.0), `scikit-learn>=1.4` (1.9.0), and `openai>=2.0` (2.52.0) are the real runtime dependencies so far; WP-008 through WP-017 all added none. The next WP's author should account for the environment note when specifying dependencies/tooling.

Do not reconstruct implementation from memory or from another repository.

Do not copy implementation decisions that are not recorded in the approved architecture or explicitly specified by the Work Package.

The next implementation task is:

**WP-018.** Per the roadmap this was planned as "end-to-end validation," but WP-017's own measured evidence recommends a **reliability-hardening** scope instead (see "Recommended WP-018 Scope" above) - Claude must not invent or begin WP-018's specification either way; wait for it to be supplied, and flag this evidence-vs-roadmap-label discrepancy to the architect/user if WP-018 is issued with the original "end-to-end validation" framing unchanged.

---

## Required Update Template for Future WPs

After every successfully completed Work Package, update the relevant sections above and record:

### Current State

* Last completed WP
* Next planned WP
* Overall phase

### Implemented

Concise list of behavior actually implemented.

### Important Interfaces

New/changed public classes, functions, commands, schemas, configuration contracts, or file formats needed by later WPs.

### Tests

* Total
* Passing
* Failing
* Verification commands/results

### Decisions Made

Only decisions actually established during implementation.

### Known Issues

Current unresolved defects/risks.

### Files Added

Files created by the WP.

### Files Significantly Modified

Existing files materially changed.

### Deferred Work

Anything intentionally left for later WPs.

### Next WP Context

Facts the next WP author/implementer must know. Do not invent the next WP specification.

