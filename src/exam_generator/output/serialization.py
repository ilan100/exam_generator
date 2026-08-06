"""Deterministic JSON serialization/file-writing for the WP-015 output
boundary.

Uses pydantic's own JSON serialization exclusively (no hand-built
recursive dict/JSON conversion): enums serialize to their string value,
``datetime`` to ISO-8601, and non-ASCII (Hebrew) text is preserved
unescaped by default - never routed through anything that could introduce
provider clients, secrets, or arbitrary Python object representations.
"""

from __future__ import annotations

from pathlib import Path

from exam_generator.models import ExamAudit, ExamOutput
from exam_generator.output.models import ExamOutputBundle

_JSON_INDENT = 2


def serialize_exam_json(exam: ExamOutput) -> str:
    """Deterministically serialize a clean exam to a UTF-8/Unicode
    JSON string. Contains only the public ``ExamOutput``/``ExamQuestion``
    contract - no internal generation/validation metadata can appear,
    since ``ExamOutput`` structurally has no field for any."""
    return exam.model_dump_json(indent=_JSON_INDENT)


def serialize_audit_json(audit: ExamAudit) -> str:
    """Deterministically serialize the internal audit trail to a UTF-8/
    Unicode JSON string."""
    return audit.model_dump_json(indent=_JSON_INDENT)


def write_exam_json(path: Path | str, exam: ExamOutput) -> None:
    """Write the clean exam to exactly ``path`` (UTF-8), and nowhere else.

    ``path`` is entirely caller-controlled - no timestamp/random-name
    policy is applied here, and no other file is touched.
    """
    Path(path).write_text(serialize_exam_json(exam), encoding="utf-8")


def write_audit_json(path: Path | str, audit: ExamAudit) -> None:
    """Write the audit to exactly ``path`` (UTF-8), and nowhere else."""
    Path(path).write_text(serialize_audit_json(audit), encoding="utf-8")


def write_exam_output_bundle(*, exam_path: Path | str, audit_path: Path | str, bundle: ExamOutputBundle) -> None:
    """Write both halves of ``bundle`` to their respective caller-supplied
    paths, as two separate files - never merged into one.

    Since WP-023, ``bundle.exam`` is ``None`` only when zero planned
    questions were accepted - in that edge case there is no valid clean
    exam to write, so only the audit is written."""
    if bundle.exam is not None:
        write_exam_json(exam_path, bundle.exam)
    write_audit_json(audit_path, bundle.audit)
