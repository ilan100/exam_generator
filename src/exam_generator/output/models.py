"""The WP-015 output-bundle contract: associates one clean exam with its
one matching audit, without merging them into a single model."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from exam_generator.models import ExamAudit, ExamOutput


class ExamOutputBundle(BaseModel):
    """The two outputs of one successful exam-generation run, kept
    structurally separate: ``exam`` is the public, student-facing contract
    (no internal generation/validation metadata); ``audit`` is the
    internal traceability record. Never constructed for anything other
    than a fully successful, internally-consistent
    ``ExamGenerationResult`` (see ``exam_generator.output.audit``)."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    exam: ExamOutput
    audit: ExamAudit
