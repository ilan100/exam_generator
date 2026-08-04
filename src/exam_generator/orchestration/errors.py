"""Domain-specific exceptions for the WP-014 exam-orchestration layer.

Existing generation/validation/production error hierarchies are reused
where they already describe the failure - an operational LLM/provider/
prompt/retrieval failure raised anywhere beneath ``ExamOrchestrator``
simply propagates unchanged, exactly as it does through WP-013's
``QuestionProducer``. These are only for orchestration-layer concerns no
existing error hierarchy covers.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from exam_generator.orchestration.models import PlannedQuestion, QuestionProductionRecord
    from exam_generator.production import QuestionAttempt, QuestionProductionResult


class ExamOrchestrationError(Exception):
    """Base class for all exam-orchestration-layer failures."""


class InvalidOrchestrationConfigurationError(ExamOrchestrationError):
    """The configured/supplied ``max_duplicate_replacement_attempts`` is
    invalid (must be >= 1)."""


class QuestionProductionFailedError(ExamOrchestrationError):
    """A planned exam question could not be completed - the exam is never
    silently returned with fewer questions than requested.

    Exactly one of two underlying causes applies, distinguished by which
    optional context is populated:

    * WP-013's own bounded regeneration was exhausted for this planned
      question (``attempts_exhausted`` is that ``QuestionAttemptsExhaustedError``'s
      ``.attempts``, ``duplicate_productions`` is empty);
    * every production for this planned question - including every bounded
      duplicate-replacement attempt - yielded a candidate that duplicated a
      question already accepted into this exam (``duplicate_productions``
      holds each rejected ``QuestionProductionResult``, ``attempts_exhausted``
      is ``None``).

    Always carries ``planned_question`` (the failing plan entry) and
    ``completed_productions`` (every ``QuestionProductionRecord`` already
    successfully accepted into the exam before this failure), so the
    partial state remains available for diagnostics even though it is
    never returned as though it were a complete exam.
    """

    def __init__(
        self,
        message: str,
        *,
        planned_question: "PlannedQuestion",
        completed_productions: tuple["QuestionProductionRecord", ...],
        duplicate_productions: tuple["QuestionProductionResult", ...] = (),
        attempts_exhausted: tuple["QuestionAttempt", ...] | None = None,
    ) -> None:
        super().__init__(message)
        self.planned_question = planned_question
        self.completed_productions = completed_productions
        self.duplicate_productions = duplicate_productions
        self.attempts_exhausted = attempts_exhausted
