"""Independent validation result contracts.

These models represent the *result* of future validation behavior (grounding,
MCQ structure, category, quality, textbook consistency). This module does not
implement any validation logic itself.
"""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, ConfigDict, Field

from exam_generator.models._common import NonBlankStr, PositiveIntStrict, StrictBool, UnitInterval


class GroundingValidationResult(BaseModel):
    """Result of independently checking a candidate against source evidence.

    A generator's own claim that its question is grounded is never trusted;
    this result is produced only by an independent validator.
    """

    model_config = ConfigDict(extra="forbid")

    grounded: StrictBool
    correct_answer_supported: StrictBool
    other_answers_not_equally_correct: StrictBool
    evidence_chunk_ids: list[NonBlankStr] = Field(default_factory=list)
    evidence_text: NonBlankStr | None = None
    reason: NonBlankStr
    confidence: UnitInterval

    @property
    def passed(self) -> bool:
        """Centralized pass rule - callers must use this, not re-derive it.

        Confidence is bounded but intentionally does not affect pass/fail.
        """
        return self.grounded and self.correct_answer_supported and self.other_answers_not_equally_correct


class MCQValidationResult(BaseModel):
    """Structural/semantic MCQ validation result."""

    model_config = ConfigDict(extra="forbid")

    valid: StrictBool
    exactly_four_answers: StrictBool
    single_best_answer: StrictBool
    reason: NonBlankStr


class CategoryValidationResult(BaseModel):
    """Category-appropriateness validation result."""

    model_config = ConfigDict(extra="forbid")

    valid: StrictBool
    requested_category: NonBlankStr
    assessed_category: NonBlankStr | None = None
    reason: NonBlankStr


class QualityValidationResult(BaseModel):
    """Minimal stylistic/quality validation result."""

    model_config = ConfigDict(extra="forbid")

    valid: StrictBool
    reason: NonBlankStr


class TextbookCheckStatus(str, Enum):
    """Secondary, non-authoritative textbook consistency status."""

    CONSISTENT = "CONSISTENT"
    NOT_FOUND = "NOT_FOUND"
    POTENTIAL_CONFLICT = "POTENTIAL_CONFLICT"


class TextbookCheckResult(BaseModel):
    """Secondary textbook validation result.

    A ``CONSISTENT`` result does not itself satisfy student-summary grounding,
    and a missing/absent textbook check does not invalidate an otherwise
    properly grounded question.
    """

    model_config = ConfigDict(extra="forbid")

    status: TextbookCheckStatus
    source_page: PositiveIntStrict | None = None
    reference_text: NonBlankStr | None = None
    reason: NonBlankStr
