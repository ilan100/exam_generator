"""Regenerate the committed JSON Schema artifacts under schemas/ from the
authoritative Pydantic domain models.

Usage:
    python scripts/generate_schemas.py

No network access; safe to run repeatedly (deterministic output). Does not
touch data/.
"""

from __future__ import annotations

import json
from pathlib import Path

from exam_generator.config.loader import find_project_root
from exam_generator.models import ExamAudit, ExamOutput, ExamRequest

_MODELS_BY_FILENAME = {
    "exam_request.schema.json": ExamRequest,
    "exam_output.schema.json": ExamOutput,
    "exam_audit.schema.json": ExamAudit,
}


def generate(schemas_dir: Path) -> None:
    for filename, model in _MODELS_BY_FILENAME.items():
        schema = model.model_json_schema()
        text = json.dumps(schema, indent=2, ensure_ascii=False, sort_keys=False) + "\n"
        (schemas_dir / filename).write_text(text, encoding="utf-8")


def main() -> None:
    schemas_dir = find_project_root() / "schemas"
    generate(schemas_dir)
    for filename in _MODELS_BY_FILENAME:
        print(f"wrote {schemas_dir / filename}")


if __name__ == "__main__":
    main()
