# Exam Generator — Architecture Record

## Purpose
This file records enduring technical architecture and interface decisions. It is not a work log. Update it only when an accepted architectural decision changes or a Work Package establishes a new durable interface.

## System Context
The application generates Hebrew neuroanatomy MCQ exams using:
- Hebrew student-summary PDFs as authoritative factual grounding.
- `course_book.pdf` as secondary validation/reference.
- `questions_full_export.xlsx` as historical style/structure reference.
- A JSON exam request specifying question counts per category.

## High-Level Flow
### Ingestion
`PDFs -> text extraction -> page-preserving chunks -> metadata -> embeddings/index`

Ingestion is separate from exam generation and should be rerun only when relevant source material/index configuration changes.

### Generation
`exam request -> category validation -> retrieval -> mode selection -> candidate generation -> independent validation -> retry/diversity controller -> exam assembly -> exam JSON + audit JSON`

## Source Authority Boundary
1. Student summaries: authoritative factual evidence.
2. Course book: secondary consistency/reference check only.
3. Historical questions: style/structure/difficulty/terminology reference only.

The code and prompts must preserve this distinction explicitly.

## Retrieval
- Use a local searchable index for V1.
- Preserve at minimum: `chunk_id`, `source_file`, `page`, `text`, and `source_type`.
- `source_type` (`SourceType`, WP-002) is exactly `STUDENT_SUMMARY` or `COURSE_BOOK`; historical exam questions are never a `SourceType` value.
- `page` uses human-readable, 1-based PDF page numbering (frozen by WP-002's `SourceEvidenceChunk` domain model).
- Retrieval must be semantic enough to handle category/chapter wording differences.
- Support external category aliases/manual overrides via configuration.
- Historical exam questions are represented by a structurally separate domain model (`HistoricalStyleReference`, WP-002) and must never be exposed as, or mixed into, factual grounding evidence (`SourceEvidenceChunk`).

## Canonical Categories
Canonical categories are derived from the historical workbook's `category` column rather than duplicated as Python constants where avoidable.

## Historical Question Ingestion (WP-003)
`src/exam_generator/historical/` loads `data/questions_full_export.xlsx` (via `openpyxl`, not pandas) into WP-002 `HistoricalStyleReference` objects, exposed through a read-only `HistoricalQuestionRepository`.

- **V1 workbook contract**: only `id`, `category`, `question`, `answer1..4`, `correct_answer_id` are required headers; column order does not matter; extra columns (`categories_json`, `accuracy_values`, `distinction_values`, `source`, `uploaded_at`, `created_at`, `updated_at`, or any future addition) are ignored by this subsystem rather than part of the contract.
- Row-level structural validation is delegated to `HistoricalStyleReference` itself (not re-implemented at the ingestion boundary), so ingestion cannot silently diverge from the WP-002 domain contract. Ingestion fails closed: a malformed/partially-populated row raises a `HistoricalQuestionRowError` identifying the worksheet row rather than being skipped or repaired.
- Canonical categories are derived only from successfully ingested historical questions' `category` values, in **first-seen workbook order** (not alphabetical, not a `set`). Duplicate category text collapses to one canonical category; category text is preserved verbatim (no aliasing, no fuzzy matching at this layer).
- `HistoricalQuestionRepository.questions_for_category()` does exact string matching only; an unknown category returns an empty tuple rather than raising, since callers may legitimately probe availability. `ExamRequest` still does not validate against this list — that remains deferred to a later orchestration WP.
- Historical question order is preserved (workbook row order), both in `all_questions` and within `questions_for_category()`.
- The repository is read-only after construction (tuples / `MappingProxyType`); nothing in this subsystem constructs or exposes a `SourceEvidenceChunk` from historical data.

## PDF Text Extraction (WP-004)
`src/exam_generator/ingestion/` extracts the project's factual-source PDFs (student summaries and `course_book.pdf`) into typed, page-aware in-memory representations, stopping before chunking.

- **Library**: [PyMuPDF](https://pypi.org/project/PyMuPDF/) (`pymupdf`), not pypdf/pdfminer. Selected after directly comparing extraction of the real student-summary PDFs: PyMuPDF returns Hebrew/RTL text in correct logical reading order and extracts ~14x faster, whereas pypdf returned Hebrew visually reversed (e.g. `ןילוסא ריש` instead of `שיר אסולין`) and emitted xref warnings. `pymupdf.open(path, filetype="pdf")` is used explicitly (not relying on extension-based auto-detection) so a non-PDF file cannot be silently accepted as some other MuPDF-supported document type.
- **Extraction-layer models** (`ExtractedPage`, `ExtractedDocument`) are structurally separate from `SourceEvidenceChunk` (WP-002): they represent raw page-aware extraction output, not post-chunking factual evidence. Nothing in this subsystem constructs a `SourceEvidenceChunk`; chunking is an explicitly separate, later WP's responsibility.
- Page numbers are human-readable, 1-based, and must form the contiguous sequence `1..N` in physical PDF order - consistent with the 1-based page convention already established by `SourceEvidenceChunk` (WP-002).
- Text is preserved as extracted (no translation, lowercasing, or semantic normalization); only the underlying library's own text-layer extraction is used - no OCR.
- **Blank-page policy**: an individual page may legitimately have empty extracted text (real course-book/summary PDFs contain scattered blank/divider pages) without failing the document; page numbering and ordering are never altered because of a blank page. A whole document containing **no** usable text on any page fails closed (`PdfTextExtractionError`).
- **Source-discovery policy**: student-summary PDFs are every `*.pdf` file in the configured data directory except the fixed `course_book.pdf` filename, sorted lexically by filename for determinism; the course book is resolved via that same fixed filename. Source classification (`SourceType.STUDENT_SUMMARY` vs. `COURSE_BOOK`) happens only at this discovery boundary - the generic `extract_pdf()` API requires the caller to pass `source_type` explicitly and never infers it from a filename.
- Extracted documents/pages are read-only after construction (frozen models, `tuple` page sequence).

## Factual Source Chunking and Corpora (WP-005)
`src/exam_generator/chunking/` converts WP-004 `ExtractedDocument`/`ExtractedPage` output into WP-002 `SourceEvidenceChunk` objects, and assembles them into read-only `FactualSourceCorpus` instances (`build_student_summary_corpus()`, `build_course_book_corpus()`). `SourceEvidenceChunk` remains the sole authoritative factual-chunk model - no competing chunk model was introduced.

- **A chunk never spans more than one physical PDF page (frozen V1 decision).** Chunking runs independently within each non-blank `ExtractedPage`, so `chunk.page` always identifies the exact physical page containing all of that chunk's text.
- **Chunking is deterministic and character-based**, not token-based - no tokenizer/NLP/embedding dependency was introduced. Configured via `config/app.yaml`'s `chunking.chunk_size`/`chunking.chunk_overlap` (defaults: `1800`/`300` characters), validated by `ChunkingConfig` (positive `chunk_size`, non-negative `chunk_overlap`, `chunk_overlap` strictly less than `chunk_size`, bool rejected for both).
- **Boundary-aware splitting**: near the configured chunk end, a bounded backward search (a fixed fraction of `chunk_size`) prefers a newline, then Hebrew/English sentence-ending punctuation (`. ? !`), then any whitespace, before falling back to a hard character split. Adjacent chunks on the same page overlap by approximately `chunk_overlap` characters; overlap never crosses a page boundary, and the algorithm is guaranteed to make forward progress (no infinite loops) regardless of where a boundary is found.
- **Chunk IDs** are stable and deterministic: `"{source_type}:{source_file}:{page:04d}:{ordinal:04d}"` (e.g. `STUDENT_SUMMARY:student_summary_1.pdf:0005:0001`) - no UUIDs, no `hash()`, no process-dependent identifiers. `FactualSourceCorpus` construction validates chunk-ID uniqueness and raises `DuplicateChunkIdError` otherwise.
- **Blank pages produce zero chunks** but do not affect later pages' physical page numbers; a document that yields zero chunks overall fails closed (`ChunkingError`).
- **Corpus separation**: the student-summary corpus and course-book corpus are always built and returned separately (`build_student_summary_corpus()` / `build_course_book_corpus()`); nothing merges them. Corpus ordering is deterministic: source-file order → physical page order → within-page chunk ordinal order.
- Category assignment is explicitly out of scope for chunking; `SourceEvidenceChunk`/corpora carry no category field. Retrieval/indexing/ranking are downstream, later-WP responsibilities - this WP only produces the in-memory factual corpus.

## Local Retrieval and Category Integration (WP-006)
`src/exam_generator/retrieval/` builds a deterministic, local lexical retrieval baseline over a WP-005 `FactualSourceCorpus`, and activates canonical-category resolution/aliasing for `ExamRequest` (deferred by WP-002).

- **V1 retrieval baseline: character n-gram TF-IDF** (`scikit-learn`'s `TfidfVectorizer(analyzer="char_wb", ngram_range=(3, 5))`), not embeddings/vector search. Chosen because the corpus mixes Hebrew, English anatomical terminology, and mixed text; character n-grams need no language-specific stemming/stop-words/lemmatization. The analyzer is a fixed internal policy (not configuration); `top_k`/`ngram_min`/`ngram_max` are configured via `config/app.yaml`'s `retrieval` section (defaults `8`/`3`/`5`), validated by `RetrievalConfig`.
- **One retrieval index = one `SourceType` (frozen V1 rule).** `FactualRetrievalIndex.from_corpus()` requires an explicit `source_type` and rejects (`SourceTypeMismatchError`) any corpus containing a chunk of a different type - a single index can never silently mix student-summary and course-book material. `build_student_summary_retrieval_index()` / `build_course_book_retrieval_index()` are always separate; results are never combined.
- **`RetrievalResult` (`chunk`, `score`, `rank`) is structurally separate from `SourceEvidenceChunk`** - no retrieval metadata was added to the WP-002 chunk model. `score` is a `[0.0, 1.0]` lexical-similarity value only; it is explicitly **not** grounding confidence, factual confidence, or probability of correctness. No API interprets a score threshold as a grounding decision.
- **Zero-score results are never returned** (a tiny `1e-9` floating-point tolerance around true zero is used, not a meaningful similarity threshold - see `exam_generator.retrieval.index`); a query with no lexical overlap returns an empty result sequence rather than being padded to `top_k`.
- **Deterministic tie-breaking**: results are ordered by score descending, then original corpus position ascending, for reproducible ordering when scores are equal. No random tie-breaking.
- **Canonical categories always originate from `HistoricalQuestionRepository.canonical_categories`** (WP-003) - never duplicated as constants/YAML lists. `config/category_mapping.yaml` (`mapping: {alias: canonical_category}`, WP-001 placeholder) is now activated: `CategoryResolver` validates that every alias target is an actual canonical category and that no alias key collides with an existing canonical category name, failing clearly (`InvalidCategoryMappingError`) otherwise. Exact canonical names always resolve to themselves; unknown names fail (`UnknownCategoryError`) - no fuzzy matching, translation, or LLM-based guessing.
- **Canonical category text is the V1 baseline retrieval query** (`retrieve_for_category()`); no query expansion via historical questions, textbook text, or LLM synonyms. `resolve_exam_request_categories()` resolves every requested category (failing on any unknown one), combining counts when multiple requested categories (canonical + alias, or multiple aliases) collapse onto the same canonical category, while preserving the total requested count.
- Historical questions never enter factual retrieval: the historical repository participates in WP-006 only as the source of canonical category names, never as indexed content.
- No retrieval index is persisted; it is rebuilt in memory from the deterministic WP-005 corpus each time.

## LLM Boundary
Application logic uses an LLM abstraction/factory rather than provider SDK calls directly.

Target conceptual interface:
- provider-neutral client/interface
- OpenAI implementation initially
- future provider implementations can be added without redesigning generation/orchestration

Provider, model, and generation/validation parameters are external configuration.

### LLM Abstraction and OpenAI Provider (WP-007)
`src/exam_generator/llm/` (`errors.py`, `models.py`, `provider.py`, `factory.py`, `openai_provider.py`) implements this boundary concretely.

- **`LLMProvider`** (abstract base class) exposes `generate_structured(*, messages, response_model, profile) -> response_model instance`, `provider_name`, `model_name`. Only `openai_provider.py` imports the `openai` SDK; `models.py`/`provider.py`/`factory.py` are provider-independent and never import it, so a future provider can be added without touching those modules or any caller.
- **Structured output**: uses the OpenAI SDK's Responses API (`client.responses.parse(..., text_format=response_model)`), which returns a validated instance of the caller-supplied Pydantic model directly via `response.output_parsed` - no hand-maintained JSON Schema duplication, no `json.loads` of raw prose. Any arbitrary caller-supplied Pydantic model works; the provider never hard-codes a specific response model.
- **`LLMMessage`** (`role` ∈ `{system, user, assistant}`, non-blank `content`) is the provider-independent message contract; OpenAI SDK message/input types are never exposed to callers. **`LLMProfile`** (`GENERATION`, `VALIDATION`) selects the matching `config/llm.yaml` parameter section - generation and validation parameters can never be accidentally interchanged.
- **Provider construction**: `build_llm_provider(llm_config, api_key=None)` is a factory keyed on `llm_config.provider`; only `"openai"` is supported in V1, anything else fails clearly (`LLMConfigurationError`) rather than silently falling back. `OPENAI_API_KEY` is read from the environment only at provider-construction time, never during ordinary configuration loading (preserving the WP-001 decision that config loading never requires a key) and never accepted via `config/llm.yaml` or any committed file.
- **Retry policy (frozen V1 decision)**: the OpenAI client is constructed with `max_retries=0`, disabling the SDK's default transport-level retries. One `generate_structured()` call = exactly one logical application LLM call; future generation-attempt/retry/diversity control happens entirely outside the provider, with no hidden SDK-level retries to confuse attempt accounting.
- **Error hierarchy**: `LLMError` → `LLMConfigurationError`, `LLMRequestError` (invalid caller input, e.g. empty messages), `LLMProviderError` (→ `LLMAuthenticationError`, `LLMRateLimitError`), `LLMResponseError` (→ `LLMRefusalError`). Expected OpenAI SDK exceptions are translated with the original exception preserved as `__cause__`; secrets never appear in any exception message.
- Structured-output refusals (`content.type == "refusal"` in the Responses API output) are never parsed as if successful; they raise `LLMRefusalError`. A missing/absent parsed object, or a parsed object of the wrong type, raises `LLMResponseError` - the provider never returns `None`/a raw dict/raw text when a response model was requested, and never repairs an invalid parsed result.
- Synchronous V1 API only (no `async`); no production prompts exist yet (WP-008's responsibility) - WP-007 only makes arbitrary structured-output requests possible for later layers.

## Prompt Boundary
Substantial prompts are external files organized by purpose, for example:
- system
- generation (`STYLE_SIMILAR`, `INDEPENDENT`)
- grounding validation
- MCQ quality validation
- category validation
- textbook check
- ingestion/category classification if required

Python loads/render prompts; prompt content is not embedded as large literals in application logic.

## Candidate Question Validation
Generation and validation are separate operations.

A question is acceptable only if at minimum:
- student-summary grounding exists;
- claimed correct answer is supported by retrieved evidence;
- no alternative answer is equally correct based on the supplied context;
- exactly four choices exist;
- category is appropriate;
- structured output validates.

Frozen domain-contract decisions (WP-002):
- Answer IDs are 1-based (1..4) throughout the domain model, both in the external exam-question contract (`answer1`..`answer4` + `correct_answer`) and the internal `CandidateQuestion` representation.
- `GroundingValidationResult.passed` is centralized derived logic: a grounding result passes if and only if `grounded AND correct_answer_supported AND other_answers_not_equally_correct` are all true. Callers must use this property rather than re-deriving the rule.
- Grounding `confidence` is bounded to `[0.0, 1.0]` but does not by itself determine pass/fail.
- A candidate question's own generation output never carries a self-reported "grounded" claim; grounding is established only by the independent validator's result.

## Diversity and Retry
- Alternate `STYLE_SIMILAR` and `INDEPENDENT` generation modes per category.
- Similarity is allowed.
- A configurable diversity/differentiation target may be progressively relaxed if necessary to fulfill requested counts.
- Grounding and factual-validity requirements are never relaxed.

## Textbook Check
Secondary and initially non-authoritative. Statuses are frozen (WP-002) as exactly:
- `CONSISTENT`
- `NOT_FOUND`
- `POTENTIAL_CONFLICT`

A potential conflict is surfaced in audit data. It does not silently replace student-summary grounding. A `CONSISTENT` result does not itself satisfy student-summary grounding, and a missing/absent textbook check does not invalidate an otherwise properly grounded question.

## Output Contracts
Domain models: `src/exam_generator/models/`. Machine-readable JSON Schemas (generated from those models via `scripts/generate_schemas.py`): `schemas/exam_request.schema.json`, `schemas/exam_output.schema.json`, `schemas/exam_audit.schema.json`.

### Exam JSON
V1 top-level contract is `{"questions": [...]}` (an object with a `questions` array), not a bare JSON array — frozen by WP-002 (`ExamOutput`). Question numbers must be unique and form the contiguous sequence `1..N`. Each question contains only clean fields, no traceability/audit information:
- `number`
- `question`
- `answer1`
- `answer2`
- `answer3`
- `answer4`
- `correct_answer`
- `category`

### Audit JSON
Contains internal traceability, including source evidence and validation diagnostics. Top-level contract (`ExamAudit`, WP-002): `exam_id` (non-empty), `generated_at` (timezone-aware datetime; naive datetimes rejected), `provider`, `model`, and a non-empty `questions` list of per-question `QuestionAudit` entries (unique question numbers enforced). Does not contain the clean exam itself, and does not track token usage/cost in V1.

## CLI
V1 provides separate operations conceptually equivalent to:
- `ingest`
- `generate --request <exam_request.json>`

Exact command syntax is established by the CLI WP.

## Configuration
External configuration should cover, as appropriate:
- paths
- LLM provider/model
- generation parameters
- validation parameters
- retrieval parameters
- diversity/retry thresholds
- prompt filenames
- category aliases/overrides

Secrets come from environment variables, not configuration committed to source control.

## Testing Philosophy
- Unit-test deterministic logic and validation boundaries.
- Use fixtures for representative workbook/PDF/config behavior.
- Keep provider calls mockable.
- Add integration tests incrementally.
- End-to-end validation is a dedicated late-stage WP.

## Change Control
Do not change an architectural decision in this file merely because implementation would be easier another way. Material changes require explicit approval in a Work Package or by the project architect/user.
