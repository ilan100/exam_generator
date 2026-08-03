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

## LLM Boundary
Application logic uses an LLM abstraction/factory rather than provider SDK calls directly.

Target conceptual interface:
- provider-neutral client/interface
- OpenAI implementation initially
- future provider implementations can be added without redesigning generation/orchestration

Provider, model, and generation/validation parameters are external configuration.

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
