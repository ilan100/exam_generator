"""Control-layer result contracts for WP-013's single-question production
cycle.

These wrap the five existing, unmodified WP-002 validation-result models
(``GroundingValidationResult``, ``MCQValidationResult``,
``CategoryValidationResult``, ``QualityValidationResult``,
``TextbookCheckResult``) plus a ``CandidateQuestion``; they do not replace
or redesign any of them. Acceptance is deterministic, rule-based Python
policy - never an LLM decision - and is centralized as a derived
``.accepted`` property (mirroring ``GroundingValidationResult.passed``)
rather than a caller-suppliable field, so it can never drift out of sync
with the validation results it summarizes.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from exam_generator.models import (
    CandidateQuestion,
    CategoryValidationResult,
    GroundingValidationResult,
    MCQValidationResult,
    QualityValidationResult,
    TextbookCheckResult,
    TextbookCheckStatus,
)
from exam_generator.models._common import PositiveIntStrict


class CandidateValidationResults(BaseModel):
    """All five independent validation outcomes for one generated candidate.

    Every field is the actual, unmodified result model produced by its own
    validator - no result is invented, aggregated into a score, or dropped.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    grounding: GroundingValidationResult
    mcq: MCQValidationResult
    category: CategoryValidationResult
    quality: QualityValidationResult
    textbook: TextbookCheckResult

    @property
    def accepted(self) -> bool:
        """Centralized V1 acceptance policy (WP-013 section 4/7) - callers
        must use this, not re-derive it.

        Grounding, MCQ, category, and quality are primary and must all
        pass. The textbook check is secondary: ``CONSISTENT`` and
        ``NOT_FOUND`` never block acceptance (absence of textbook support
        does not invalidate an otherwise properly grounded candidate - see
        WP-012), but an explicit ``POTENTIAL_CONFLICT`` does block it. No
        confidence threshold or weighted score is used anywhere here.
        """
        return (
            self.grounding.passed
            and self.mcq.valid
            and self.category.valid
            and self.quality.valid
            and self.textbook.status != TextbookCheckStatus.POTENTIAL_CONFLICT
        )


class QuestionAttempt(BaseModel):
    """One completed generate-then-validate attempt: the generated
    candidate, its full independent validation bundle, and the resulting
    acceptance decision. Preserved for every attempt, accepted or not."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    attempt_number: PositiveIntStrict
    candidate: CandidateQuestion
    validations: CandidateValidationResults

    @property
    def accepted(self) -> bool:
        return self.validations.accepted


class QuestionProductionResult(BaseModel):
    """The outcome of one successful single-question production cycle: the
    accepted candidate plus every attempt (including earlier rejected
    ones) that led to it, in 1-based attempt order."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    candidate: CandidateQuestion
    attempts: tuple[QuestionAttempt, ...]
