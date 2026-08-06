"""The WP-015 output-bundle contract: associates one clean exam with its
one matching audit, without merging them into a single model."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from exam_generator.models import ExamAudit, ExamOutput


class ExamOutputBundle(BaseModel):
    """The two outputs of one exam-generation run that safely reached the
    end of its plan, kept structurally separate: ``exam`` is the public,
    student-facing contract (no internal generation/validation metadata);
    ``audit`` is the internal traceability record. Never constructed for
    anything other than an internally-consistent ``ExamGenerationResult``
    (see ``exam_generator.output.audit``).

    Since WP-023, ``exam`` is ``None`` only when zero planned questions
    were accepted (every planned question failed) - ``ExamOutput``
    structurally requires at least one question, so there is no valid
    clean exam to represent in that edge case; ``audit`` still fully
    describes the run, including every failed planned question."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    exam: ExamOutput | None
    audit: ExamAudit
