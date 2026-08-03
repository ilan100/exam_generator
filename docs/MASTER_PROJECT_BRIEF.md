# Exam Generator — Master Project Brief

## Role and Development Model
Claude Code is the implementation engineer for this project. GPT is the architect/specification owner/reviewer. Implementation proceeds incrementally through numbered Work Packages (WP-xxx). Claude implements only the current WP; GPT reviews completion before the next WP is issued.

The repository and its documentation are the source of truth. Do not rely on conversational memory from earlier Claude or GPT sessions.

## Project Purpose
Build a Python application that generates Hebrew neuroanatomy multiple-choice exams from supplied course material.

## Information Sources and Authority
### 1. Hebrew student-summary PDFs — authoritative factual source
- Every generated question MUST be grounded in textual evidence from at least one student summary.
- A question without sufficient student-summary evidence is invalid.
- The combined set of student summaries forms the authoritative source corpus; individual summaries may overlap substantially.
- Summary chapter/category wording may differ from canonical exam category wording.

### 2. `course_book.pdf` — secondary reference
- English course textbook.
- May be used for secondary validation or clarification.
- MUST NOT independently justify or ground a generated question.
- A conflict with a student summary should be surfaced in audit information rather than silently resolved by replacing the summary as the authoritative exam source.

### 3. `questions_full_export.xlsx` — historical style reference
- Historical exam questions.
- Used to learn question style, structure, difficulty, distractor conventions, and terminology conventions.
- MUST NOT be treated as an authoritative factual source.
- Categories are fixed and originate from the workbook's `category` column.

## Question Requirements
- Questions are in Hebrew.
- Each question has exactly four answer choices.
- Exactly one answer is the best/correct answer.
- Preserve natural terminology conventions from historical exams. English anatomical terms, or Hebrew and English terms used together, should remain where appropriate rather than being mechanically translated.
- The correct answer must be supported by textual context from a student summary.
- The question must have one unambiguously best answer based on the supplied evidence.

## Exam Request
Generation input specifies the requested number of questions per canonical category in JSON.

Unknown categories must fail validation rather than be silently guessed or remapped.

## Generation Modes
Questions alternate between two modes within each category:

### `STYLE_SIMILAR`
- Historical question(s) from the relevant category are supplied as style/structure examples.
- Factual content still comes from student-summary evidence.
- Similarity to historical questions is allowed.

### `INDEPENDENT`
- Question is generated primarily from retrieved student-summary material.
- Historical questions may influence general exam style but are not factual sources.

## Diversity Policy
- Generated questions do NOT need to be unique from historical questions.
- Generated questions do NOT need to be strictly unique from other questions in the newly generated exam.
- A configurable differentiation/diversity target may be used.
- If insufficient sufficiently differentiated questions can be generated, the differentiation target may be progressively relaxed.
- Grounding requirements MUST NEVER be relaxed.

## Core Quality Rule
**Fail closed on factual validity; relax on stylistic diversity.**

A candidate question may be rejected for missing/insufficient grounding, ambiguous correct answer, invalid MCQ structure, or category mismatch. Low stylistic diversity alone is not grounds for permanent rejection when more questions are required.

## Output
Every successful exam generation produces two files:

1. `exam_<timestamp>.json`
   - Clean exam output only.
   - Follows the project's required question output contract.

2. `exam_<timestamp>.audit.json`
   - Internal traceability and diagnostics.
   - Should include, where applicable: source PDF, page, chunk ID, supporting passage, grounding result/score, generation mode, historical style reference, validation results, textbook check, model/provider information, generation attempts, and diversity target used.

## Architectural Principles
- Python application.
- CLI interface for V1.
- Separate ingestion/indexing from exam generation.
- Use retrieval/RAG rather than sending all source documents on every generation call.
- Preserve source PDF/page/chunk metadata through retrieval and validation.
- Keep LLM provider and model dynamically configurable in external configuration.
- Initial runtime provider may be OpenAI/GPT, but application logic must not depend directly on OpenAI outside the provider implementation.
- Prompts must live in external prompt files, not substantial Python string literals.
- Configuration and controllable data must live outside application logic.
- Credentials must come from environment variables and must never be committed.
- Domain models and structured LLM responses must be explicitly validated.
- Question generation and question validation are separate operations/calls.
- Never trust the generator's own claim that its question is grounded; validation must independently evaluate the evidence.
- Keep V1 infrastructure appropriately simple and local unless a later WP explicitly changes this.
- Components should be testable and provider-independent where practical.
- Manual category aliases/overrides should be possible without code changes.

## Development Process
Implementation is performed incrementally using numbered Work Packages.

For every WP Claude must:
1. Read the entire WP before modifying files.
2. Implement only the requested scope.
3. Do not implement future WPs early.
4. Do not silently change the architecture.
5. If the WP conflicts with this master brief, stop and report the conflict.
6. If an important requirement is ambiguous, report it instead of making a major architectural assumption.
7. Add/update tests required by the WP.
8. Run all verification commands specified by the WP.
9. Run existing relevant tests to detect regressions.
10. Update `docs/PROJECT_STATUS.md` after successful completion.
11. Report exactly what changed, files created/modified, tests run, results, and any unresolved issues.

Do not add features merely because they appear useful. Do not refactor unrelated working code unless the WP explicitly requires it.
