# Exam Generator — Project Status

> This is the authoritative rolling implementation checkpoint shared by the user, GPT, and Claude Code. Claude updates it after every successfully completed Work Package. Keep it concise, factual, and current.

## Current State

* Last completed WP: **WP-004 — PDF text extraction and source document ingestion**
* Current/next planned WP: **WP-005**
* Overall phase: **Fresh implementation from approved project architecture**
* Repository implementation state: **WP-004 complete**

This repository is a clean reimplementation of the Exam Generator project on a new machine.

The project architecture and product requirements have already been established and MUST NOT be redesigned merely because the implementation is starting again.

Implementation will proceed sequentially from WP-005 using Work Packages supplied by GPT.

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

No retrieval, embeddings, chunking, indexing, LLM integration, prompts content, generation, validation behavior, orchestration, output-file writing, or CLI functionality has been implemented yet.

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

## Tests

* Total: **213** (10 from WP-001 + 97 from WP-002 + 59 from WP-003 + 47 from WP-004)
* Passing: **213**
* Failing: **0**

Verification commands and results:

* `.venv/bin/python --version` → `Python 3.12.3`
* `.venv/bin/python -c "import openpyxl; print(openpyxl.__version__)"` → `3.1.5`
* `.venv/bin/python -c "import pymupdf; print(pymupdf.__version__)"` → `1.28.0`
* `.venv/bin/python -m pytest -v` → 213 passed
* `.venv/bin/python scripts/generate_schemas.py` run twice in a row → byte-identical output (deterministic; unaffected by WP-003/WP-004).
* Real-workbook smoke test against `data/questions_full_export.xlsx` via the public `HistoricalQuestionRepository` API (see Real-Workbook Verification below); confirmed no wording corruption on a Hebrew question with embedded English terminology (`Corona radiata`) and English-only answer options.
* Real-source PDF verification against all four real PDFs via the public `exam_generator.ingestion` API (see Real-Source PDF Verification below); confirmed Hebrew and English/mixed content preserved without corruption.
* `git status --short` / `git add -A --dry-run` → only WP-004 files (plus intentional `pyproject.toml` dependency addition) staged; no PDFs, Excel, `data/question_format.json`, `.venv/`, secrets, or generated output/index artifacts.

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

## Known Issues / Open Questions

* **Python version deviation from WP-001 spec (carried forward).** WP-001.md specified Python 3.14 and assumed a pre-existing project-local `.venv` built with it. Neither a Python 3.14 interpreter nor a pre-existing `.venv` was actually present on this machine (only system `python3` / `python3.12` = 3.12.3, confirmed via `apt list --installed` and filesystem search). Per explicit user instruction, WP-001 through WP-004 were implemented and verified against **Python 3.12.3** instead, with `pyproject.toml` declaring `requires-python = ">=3.12"`. This is a factual correction of the WP's environment assumption, not an architectural change. `openpyxl` and `pymupdf` were both confirmed to install and work correctly under 3.12.3.
* No other known issues from WP-004.

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

WP-004 (new):
* `src/exam_generator/ingestion/__init__.py`
* `src/exam_generator/ingestion/errors.py`
* `src/exam_generator/ingestion/models.py`
* `src/exam_generator/ingestion/pdf.py`
* `src/exam_generator/ingestion/discovery.py`
* `tests/unit/test_ingestion.py`

## Files Significantly Modified

* `docs/PROJECT_STATUS.md` (this file).
* `docs/ARCHITECTURE.md` (WP-002: `SourceType` enum values spelled out under Retrieval. WP-003: new "Historical Question Ingestion" section. WP-004: new "PDF Text Extraction" section recording the PyMuPDF selection/rationale, extraction-layer vs. evidence-chunk separation, page-numbering/blank-page policy, and source-discovery policy).
* `pyproject.toml` (WP-003: added `openpyxl>=3.1`. WP-004: added `pymupdf>=1.24`).

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

WP-001 through WP-004 are complete. `src/exam_generator/config` provides configuration loading; `src/exam_generator/models` provides every domain contract; `src/exam_generator/historical` provides read-only access to the canonical category list and historical style/structure references; `src/exam_generator/ingestion` provides deterministic PDF text extraction stopping at page-aware `ExtractedDocument`/`ExtractedPage` objects. None of the following exists yet:

* `ExamRequest` still validates request *structure* only; it does **not** yet check requested category names against `HistoricalQuestionRepository.canonical_categories`. That cross-check is explicitly deferred to a later orchestration WP.
* **No chunking exists.** `ExtractedDocument`/`ExtractedPage` (WP-004) are extraction-layer-only representations; nothing converts them into `SourceEvidenceChunk` (WP-002) yet. A future WP must split extracted page text into chunks, assign `chunk_id`s, and produce `SourceEvidenceChunk` objects carrying `source_file`/`page`/`text`/`source_type` provenance forward from the `ExtractedPage`s that produced them.
* No embeddings, vector/keyword index, or retrieval exists yet (WP-005/WP-006 territory per the roadmap).
* All validation-result models (`GroundingValidationResult`, `MCQValidationResult`, `CategoryValidationResult`, `QualityValidationResult`, `TextbookCheckResult`) exist as contracts only; no validator logic exists yet.
* No historical-question selection/similarity logic exists — `HistoricalQuestionRepository` only provides data access, per WP-003's explicit non-goals.
* No LLM client/provider, prompts, generation, diversity/retry logic, exam orchestration, output-file writing, or CLI exists yet.

The environment's Python interpreter is 3.12.3, not 3.14 as WP-001.md assumed; see Known Issues above. `openpyxl>=3.1` (installed: 3.1.5) and `pymupdf>=1.24` (installed: 1.28.0) are now real runtime dependencies. The next WP's author should account for all of this when specifying dependencies/tooling.

Do not reconstruct implementation from memory or from another repository.

Do not copy implementation decisions that are not recorded in the approved architecture or explicitly specified by the Work Package.

The next implementation task is:

**WP-005** (per the roadmap: Chunking + indexing). Claude must not invent or begin WP-005's specification; wait for it to be supplied.

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

