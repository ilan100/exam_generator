"""Internal traceability/audit contracts.

Kept structurally separate from the clean exam contract (``exam.ExamOutput``):
audit data is never mixed into, and does not itself contain, the clean exam.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from exam_generator.models._common import NonBlankStr, PositiveIntStrict, StrictBool, UnitInterval
from exam_generator.models.question import GenerationMode
from exam_generator.models.source import SourceEvidenceChunk
from exam_generator.models.validation import (
    CategoryValidationResult,
    GroundingValidationResult,
    MCQValidationResult,
    QualityValidationResult,
    TextbookCheckResult,
)


class QuestionAttemptAudit(BaseModel):
    """Traceability for one complete generate-then-validate attempt
    (WP-013) toward a single exam question, whether or not it was
    ultimately accepted.

    Added in WP-015 to preserve full per-attempt history in the audit -
    ``QuestionAudit``'s own ``grounding``/``mcq_validation``/etc. fields
    (unchanged since WP-002) continue to represent only the final,
    accepted attempt's results.
    """

    model_config = ConfigDict(extra="forbid")

    attempt_number: PositiveIntStrict
    accepted: StrictBool
    grounding: GroundingValidationResult
    mcq_validation: MCQValidationResult
    category_validation: CategoryValidationResult
    quality_validation: QualityValidationResult
    textbook_check: TextbookCheckResult | None = None


class QuestionAudit(BaseModel):
    """Traceability/diagnostics for a single generated question."""

    model_config = ConfigDict(extra="forbid")

    number: PositiveIntStrict
    category: NonBlankStr
    generation_mode: GenerationMode
    historical_reference_id: PositiveIntStrict | None = None
    grounding: GroundingValidationResult
    evidence: list[SourceEvidenceChunk] = Field(default_factory=list)
    mcq_validation: MCQValidationResult
    category_validation: CategoryValidationResult
    quality_validation: QualityValidationResult
    textbook_check: TextbookCheckResult | None = None
    generation_attempts: PositiveIntStrict
    diversity_target: UnitInterval
    attempts: list[QuestionAttemptAudit] = Field(min_length=1)


class ExamAudit(BaseModel):
    """Top-level audit contract for one exam-generation run."""

    model_config = ConfigDict(extra="forbid")

    exam_id: NonBlankStr
    generated_at: datetime
    provider: NonBlankStr
    model: NonBlankStr
    questions: list[QuestionAudit] = Field(min_length=1)

    @field_validator("generated_at")
    @classmethod
    def _require_timezone_aware(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.tzinfo.utcoffset(value) is None:
            raise ValueError("generated_at must be a timezone-aware datetime")
        return value

    @field_validator("questions")
    @classmethod
    def _unique_question_numbers(cls, value: list[QuestionAudit]) -> list[QuestionAudit]:
        numbers = [question.number for question in value]
        if len(numbers) != len(set(numbers)):
            raise ValueError(f"exam audit question numbers must be unique, got {numbers}")
        return value
