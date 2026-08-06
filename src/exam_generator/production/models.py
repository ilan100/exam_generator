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

from pydantic import BaseModel, ConfigDict, model_validator

from exam_generator.models import (
    CandidateQuestion,
    CategoryValidationResult,
    GroundingValidationResult,
    MCQValidationResult,
    QualityValidationResult,
    TextbookCheckResult,
    TextbookCheckStatus,
)
from exam_generator.models._common import NonBlankStr, PositiveIntStrict


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
    """One completed candidate-production attempt: either a generated
    candidate with its full independent validation bundle (and the
    resulting acceptance decision), or - since WP-019 - a recoverable
    generation-contract failure (the model's structured response could not
    safely become a ``CandidateQuestion``, e.g. it claimed unsupplied
    evidence provenance) that was discarded before any validator ran.
    Preserved for every attempt, accepted or not.

    Exactly one of ``(candidate, validations)`` or
    ``(generation_failure_type, generation_failure_message)`` is ever
    populated - a generation-contract failure never fabricates a candidate
    or validation results, and a real candidate never carries a failure
    description.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    attempt_number: PositiveIntStrict
    candidate: CandidateQuestion | None = None
    validations: CandidateValidationResults | None = None
    generation_failure_type: NonBlankStr | None = None
    generation_failure_message: NonBlankStr | None = None

    @model_validator(mode="after")
    def _check_exactly_one_outcome(self) -> "QuestionAttempt":
        if (self.candidate is None) != (self.validations is None):
            raise ValueError("candidate and validations must both be set or both be None")
        if (self.generation_failure_type is None) != (self.generation_failure_message is None):
            raise ValueError(
                "generation_failure_type and generation_failure_message must both be set or both be None"
            )
        is_candidate_attempt = self.candidate is not None
        is_failure_attempt = self.generation_failure_type is not None
        if is_candidate_attempt == is_failure_attempt:
            raise ValueError(
                "exactly one of (candidate, validations) or (generation_failure_type, "
                "generation_failure_message) must be set"
            )
        return self

    @property
    def is_generation_contract_failure(self) -> bool:
        return self.generation_failure_type is not None

    @property
    def accepted(self) -> bool:
        if self.validations is None:
            return False
        return self.validations.accepted


class QuestionProductionResult(BaseModel):
    """The outcome of one successful single-question production cycle: the
    accepted candidate plus every attempt (including earlier rejected
    ones) that led to it, in 1-based attempt order."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    candidate: CandidateQuestion
    attempts: tuple[QuestionAttempt, ...]
