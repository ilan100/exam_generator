"""Control-layer result contracts for WP-014's exam orchestration.

These wrap the existing, unmodified ``ExamRequest``/``ExamOutput``/
``CandidateQuestion`` (WP-002) and ``QuestionProductionResult`` (WP-013)
contracts; they do not replace or redesign any of them, and they carry no
final-audit-serialization fields - that remains a later output-focused WP.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, model_validator

from exam_generator.models import ExamGenerationStatus, ExamOutput, GenerationMode
from exam_generator.models._common import NonBlankStr, NonNegativeIntStrict, PositiveIntStrict
from exam_generator.production import QuestionAttempt, QuestionProductionResult


class PlannedQuestion(BaseModel):
    """One deterministically-planned exam question slot: a global 1-based
    position (directly reusable as the final ``ExamQuestion.number``), its
    canonical category, and its assigned generation mode."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    position: PositiveIntStrict
    category: NonBlankStr
    generation_mode: GenerationMode


class QuestionProductionRecord(BaseModel):
    """One planned question's successful production outcome: the plan
    entry it fulfills, WP-013's full production result (accepted candidate
    plus every attempt that led to it), and how many exam-level duplicate
    replacements were needed before this result was accepted. Preserved
    for future audit assembly (WP-015+)."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    planned: PlannedQuestion
    production: QuestionProductionResult
    duplicate_replacement_attempts: NonNegativeIntStrict


class FailedPlannedQuestion(BaseModel):
    """WP-023: one planned question that failed for a question-local
    reason (WP-013 attempt-budget exhaustion, WP-021 provenance-recovery
    exhaustion, duplicate-replacement exhaustion, or another failure
    demonstrably scoped to this one candidate/question) - orchestration
    continues past it rather than aborting the whole run. Reuses the
    existing ``QuestionAttempt``/``QuestionProductionResult`` models rather
    than duplicating them; carries whatever history actually exists, which
    may be empty if the failure happened before any attempt record could
    be built.

    ``attempts`` is populated for a WP-013 attempt-budget exhaustion (every
    discarded attempt that led to it); ``duplicate_productions`` is
    populated for a duplicate-replacement exhaustion (every accepted-but-
    duplicate candidate produced while trying to replace it). At most one
    of the two is ever non-empty."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    planned: PlannedQuestion
    failure_type: NonBlankStr
    failure_message: NonBlankStr
    attempts: tuple[QuestionAttempt, ...] = ()
    duplicate_productions: tuple[QuestionProductionResult, ...] = ()


class ExamGenerationResult(BaseModel):
    """The outcome of one WP-014 orchestration run that safely reached the
    end of its plan: the plan itself, every successful production, and
    (since WP-023) every planned question that failed for a question-local
    reason. ``exam`` is the clean output built from accepted productions
    only, renumbered contiguously 1..N - it is ``None`` only when zero
    planned questions were accepted, since ``ExamOutput`` structurally
    requires at least one question.

    A system-level failure never reaches this model at all - it aborts the
    run before any result can be constructed."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    status: ExamGenerationStatus
    exam: ExamOutput | None
    plan: tuple[PlannedQuestion, ...]
    productions: tuple[QuestionProductionRecord, ...]
    failed_questions: tuple[FailedPlannedQuestion, ...] = ()

    @model_validator(mode="after")
    def _check_consistent(self) -> "ExamGenerationResult":
        if len(self.plan) != len(self.productions) + len(self.failed_questions):
            raise ValueError("plan length must equal len(productions) + len(failed_questions)")
        if self.exam is None and self.productions:
            raise ValueError("exam must not be None when there are successful productions")
        if self.status == ExamGenerationStatus.COMPLETE and self.failed_questions:
            raise ValueError("status=COMPLETE requires no failed questions")
        if self.status == ExamGenerationStatus.PARTIAL and not self.failed_questions:
            raise ValueError("status=PARTIAL requires at least one failed question")
        return self
