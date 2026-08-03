# Exam Generator — GPT Architect/Reviewer Handoff

Use this file to resume the project in a new ChatGPT/GPT conversation.

## Roles
- **User:** product owner / final decision maker.
- **GPT:** architect, specification owner, Work Package author, and implementation reviewer.
- **Claude Code:** implementation engineer.

GPT should not implement the application itself unless the user explicitly asks it to. Claude Code receives one Work Package at a time. After Claude completes a WP, the user brings its completion report/results to GPT for review before GPT defines the next WP.

## Project Summary
The project is a Python application that generates Hebrew neuroanatomy multiple-choice exams.

### Source hierarchy
1. **Hebrew student-summary PDFs:** authoritative factual source. Every generated question must be grounded in textual evidence from at least one student summary.
2. **`course_book.pdf`:** English textbook; secondary reference/validation only. It cannot independently ground a generated question.
3. **`questions_full_export.xlsx`:** historical exam questions; used only for style, structure, terminology conventions, distractor patterns, and difficulty reference. It is not an authoritative factual source.

### Question requirements
- Hebrew multiple-choice questions.
- Exactly four answers.
- Exactly one best/correct answer.
- Preserve natural Hebrew/English anatomical terminology conventions found in historical questions.
- Categories are fixed and originate from the historical Excel `category` column.

### Generation modes
Questions alternate between:
- `STYLE_SIMILAR`
- `INDEPENDENT`

Similarity to historical or newly generated questions is allowed. If necessary, differentiation requirements may be progressively relaxed. Grounding/factual-validity requirements can never be relaxed.

**Core rule:** Fail closed on factual validity; relax on stylistic diversity.

### Output
Each exam generation produces:
- `exam_<timestamp>.json`
- `exam_<timestamp>.audit.json`

The audit file contains source/evidence traceability, generation mode, validation information, model/provider information, attempts, and other useful diagnostics.

### Architecture
- Python
- CLI V1
- RAG/retrieval architecture
- ingestion/indexing separated from generation
- local searchable index for V1
- source/page/chunk metadata preserved
- dynamic externally configured LLM provider/model
- OpenAI/GPT initially, replaceable later
- prompts external to Python
- configuration external to application logic
- credentials via environment variables
- generation and validation are separate LLM operations
- structured/validated LLM responses

## New GPT Session Resume Procedure
When the user provides this handoff in a new GPT conversation:

1. Treat this file as orientation, not as proof of current implementation state.
2. Ask the user for the current `docs/PROJECT_STATUS.md` if it has not already been supplied.
3. Read `PROJECT_STATUS.md` before proposing or generating the next WP.
4. If needed, ask for `docs/ARCHITECTURE.md` and only the specific repository files/tests required to understand or review the current state. Do not request the whole repository unnecessarily.
5. Reconstruct:
   - completed WPs;
   - current architecture/interfaces;
   - implementation state;
   - test status;
   - unresolved issues/deferred work;
   - next planned WP.
6. If `PROJECT_STATUS.md` says Claude just completed a WP, review that completion before proceeding.
7. If Claude's report and repository/status documents conflict, resolve the discrepancy with the user rather than assuming.
8. Do not rely on assumed memory from previous GPT conversations. Current repository documentation/code is the source of truth.
9. Briefly state the reconstructed state and what additional material, if any, is needed.
10. Generate the next WP only after the current state is sufficiently understood.

## Work Package Governance
Every WP authored by GPT should specify as appropriate:
- objective;
- scope;
- files/directories allowed to change;
- requirements;
- interfaces/contracts;
- tests required;
- acceptance criteria;
- explicit non-goals;
- verification commands;
- required `PROJECT_STATUS.md` update.

Do not give Claude the entire future roadmap as implementation instructions. Supply only the current WP while maintaining roadmap awareness on the GPT/user side.

## Planned Roadmap
The initial roadmap is:
- WP-001 Repository skeleton + configuration
- WP-002 Domain models and schemas
- WP-003 Historical Excel ingestion
- WP-004 PDF extraction
- WP-005 Chunking + indexing
- WP-006 Retrieval/category mapping
- WP-007 LLM abstraction + OpenAI provider
- WP-008 External prompt infrastructure
- WP-009 Question generation
- WP-010 Grounding validation
- WP-011 Additional MCQ/category validation
- WP-012 Textbook secondary validation
- WP-013 Diversity/retry controller
- WP-014 Exam orchestration
- WP-015 Exam + audit output
- WP-016 CLI
- WP-017 Integration tests
- WP-018 End-to-end validation

This roadmap may evolve only through explicit project decisions; `PROJECT_STATUS.md` is authoritative for what is actually next.
