"""Internal traceability/audit contracts.

Kept structurally separate from the clean exam contract (``exam.ExamOutput``):
audit data is never mixed into, and does not itself contain, the clean exam.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from exam_generator.models._common import NonBlankStr, NonNegativeIntStrict, PositiveIntStrict, StrictBool, UnitInterval
from exam_generator.models.question import GenerationMode
from exam_generator.models.source import SourceEvidenceChunk
from exam_generator.models.validation import (
    CategoryValidationResult,
    GroundingValidationResult,
    MCQValidationResult,
    QualityValidationResult,
    TextbookCheckResult,
)


class ExamGenerationStatus(str, Enum):
    """WP-023: the outcome shape of one orchestration run that reached the
    end of its plan. ``COMPLETE`` means every planned question was
    accepted; ``PARTIAL`` means the plan was safely exhausted but one or
    more planned questions failed for question-local reasons. A
    system-level failure aborts the run entirely and never produces either
    status - there is no result to represent in that case."""

    COMPLETE = "COMPLETE"
    PARTIAL = "PARTIAL"


class QuestionAttemptAudit(BaseModel):
    """Traceability for one complete candidate-production attempt (WP-013)
    toward a single exam question, whether or not it was ultimately
    accepted.

    Added in WP-015 to preserve full per-attempt history in the audit -
    ``QuestionAudit``'s own ``grounding``/``mcq_validation``/etc. fields
    (unchanged since WP-002) continue to represent only the final,
    accepted attempt's results.

    Since WP-019, an attempt may instead represent a recoverable
    generation-contract failure (the model's structured response could not
    safely become a candidate, e.g. it claimed unsupplied evidence
    provenance) - honestly represented via ``generation_failure_type``/
    ``generation_failure_message`` with no validation results, since none
    were ever computed. Never fabricates a candidate or validator verdict
    for a response that never became one.
    """

    model_config = ConfigDict(extra="forbid")

    attempt_number: PositiveIntStrict
    accepted: StrictBool
    grounding: GroundingValidationResult | None = None
    mcq_validation: MCQValidationResult | None = None
    category_validation: CategoryValidationResult | None = None
    quality_validation: QualityValidationResult | None = None
    textbook_check: TextbookCheckResult | None = None
    generation_failure_type: NonBlankStr | None = None
    generation_failure_message: NonBlankStr | None = None

    @model_validator(mode="after")
    def _check_consistent_outcome(self) -> "QuestionAttemptAudit":
        if (self.generation_failure_type is None) != (self.generation_failure_message is None):
            raise ValueError(
                "generation_failure_type and generation_failure_message must both be set or both be None"
            )
        is_generation_failure = self.generation_failure_type is not None
        primary_results = (self.grounding, self.mcq_validation, self.category_validation, self.quality_validation)
        if is_generation_failure:
            if self.accepted:
                raise ValueError("a generation-contract-failure attempt can never be accepted")
            if any(result is not None for result in primary_results) or self.textbook_check is not None:
                raise ValueError("a generation-contract-failure attempt must not carry validation results")
        else:
            if any(result is None for result in primary_results):
                raise ValueError(
                    "a normal (non-generation-contract-failure) attempt must carry all four primary "
                    "validation results"
                )
        return self


class QuestionAudit(BaseModel):
    """Traceability/diagnostics for a single generated question."""

    model_config = ConfigDict(extra="forbid")

    number: PositiveIntStrict
    # WP-023: the position originally assigned in the deterministic plan.
    # Kept distinct from ``number`` (the final, contiguous clean-exam
    # number) since a question-local failure elsewhere in the plan can make
    # the two diverge - see ExamOrchestrator.generate_exam().
    planned_position: PositiveIntStrict
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


class FailedQuestionAudit(BaseModel):
    """WP-023: traceability for one planned question that failed for a
    question-local reason - orchestration continued past it rather than
    aborting the whole run. Preserves whatever attempt history actually
    exists (possibly none, if the failure happened before any attempt
    record could be built) - never fabricates a candidate or validation
    result for a question that never produced one."""

    model_config = ConfigDict(extra="forbid")

    planned_position: PositiveIntStrict
    category: NonBlankStr
    generation_mode: GenerationMode
    failure_type: NonBlankStr
    failure_message: NonBlankStr
    attempts: list[QuestionAttemptAudit] = Field(default_factory=list)


class ExamAudit(BaseModel):
    """Top-level audit contract for one exam-generation run.

    Since WP-023, a run that safely reached the end of its plan is always
    represented here, whether every planned question was accepted
    (``status=COMPLETE``) or one or more failed for a question-local
    reason (``status=PARTIAL``, with each failure recorded in
    ``failed_questions``). A system-level failure still aborts the run
    before any ``ExamAudit`` is built at all.
    """

    model_config = ConfigDict(extra="forbid")

    exam_id: NonBlankStr
    generated_at: datetime
    provider: NonBlankStr
    model: NonBlankStr
    status: ExamGenerationStatus
    planned_question_count: PositiveIntStrict
    accepted_count: NonNegativeIntStrict
    failed_count: NonNegativeIntStrict
    questions: list[QuestionAudit] = Field(default_factory=list)
    failed_questions: list[FailedQuestionAudit] = Field(default_factory=list)

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

    @model_validator(mode="after")
    def _check_counts_consistent(self) -> "ExamAudit":
        if self.accepted_count != len(self.questions):
            raise ValueError(
                f"accepted_count ({self.accepted_count}) must equal len(questions) ({len(self.questions)})"
            )
        if self.failed_count != len(self.failed_questions):
            raise ValueError(
                f"failed_count ({self.failed_count}) must equal len(failed_questions) ({len(self.failed_questions)})"
            )
        if self.planned_question_count != self.accepted_count + self.failed_count:
            raise ValueError(
                f"planned_question_count ({self.planned_question_count}) must equal "
                f"accepted_count + failed_count ({self.accepted_count} + {self.failed_count})"
            )
        if self.status == ExamGenerationStatus.COMPLETE and self.failed_count != 0:
            raise ValueError("status=COMPLETE requires failed_count == 0")
        if self.status == ExamGenerationStatus.PARTIAL and self.failed_count == 0:
            raise ValueError("status=PARTIAL requires at least one failed question")
        return self

    @model_validator(mode="after")
    def _check_planned_positions_partition_exactly(self) -> "ExamAudit":
        positions = [question.planned_position for question in self.questions] + [
            failed.planned_position for failed in self.failed_questions
        ]
        if len(positions) != len(set(positions)):
            raise ValueError(f"a planned position must not be represented more than once, got {positions}")
        expected = list(range(1, self.planned_question_count + 1))
        if sorted(positions) != expected:
            raise ValueError(
                f"planned positions must exactly cover 1..{self.planned_question_count}, got {sorted(positions)}"
            )
        return self
