# Exam Generator

Generates Hebrew neuroanatomy multiple-choice exams from supplied course material (student-summary PDFs, a secondary course-book PDF, and a historical question workbook), using retrieval-grounded LLM generation with independent multi-stage validation.

See `docs/MASTER_PROJECT_BRIEF.md` and `docs/ARCHITECTURE.md` for the full architecture, and `docs/PROJECT_STATUS.md` for current implementation status.

## Installation

```bash
pip install -e .
```

This installs the `exam-generator` console command (see `[project.scripts]` in `pyproject.toml`).

## Configuration

Application/LLM/category configuration lives in `config/` (`app.yaml`, `llm.yaml`, `category_mapping.yaml`) - not on the command line.

The OpenAI API key must come from the environment, never from a command-line argument:

```bash
export OPENAI_API_KEY="sk-..."
```

## Generating an exam

Write an exam request as UTF-8 JSON, matching the `ExamRequest` contract (`schemas/exam_request.schema.json`; example at `schemas/exam_request.example.json`):

```json
{
  "categories": {
    "גזע המוח": 2,
    "חומר לבן": 1
  }
}
```

Then run:

```bash
exam-generator generate \
    --request request.json \
    --exam-output exam.json \
    --audit-output audit.json
```

or, without installing:

```bash
python -m exam_generator.cli generate \
    --request request.json \
    --exam-output exam.json \
    --audit-output audit.json
```

`--exam-output`/`--audit-output` are optional and default to `exam.json`/`exam_audit.json` in the current directory. An existing output file is never silently overwritten - pass `--force` to replace it explicitly.

On success, two separate files are written:

* `exam.json` - the clean, student-facing exam (no internal generation/validation metadata).
* `audit.json` - the internal traceability record (generation mode, every production attempt, all five validation results, textbook check, etc.) for the same exam.

## Exit codes

* `0` - exam generated successfully.
* `1` - a generation/pipeline failure (e.g. a category's candidate quality could not be accepted within the configured attempt limit, or a provider/LLM error).
* `2` - a usage/request/configuration error (e.g. malformed request JSON, unknown category, missing `OPENAI_API_KEY`, or an existing output file without `--force`).

## Development

```bash
pip install -e ".[dev]"
pytest
```

The unit test suite runs fully offline and requires no `OPENAI_API_KEY`.
