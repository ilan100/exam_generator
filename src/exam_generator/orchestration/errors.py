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


class ExamOrchestrationError(Exception):
    """Base class for all exam-orchestration-layer failures."""


class InvalidOrchestrationConfigurationError(ExamOrchestrationError):
    """The configured/supplied ``max_duplicate_replacement_attempts`` is
    invalid (must be >= 1)."""


class QuestionProductionFailedError(ExamOrchestrationError):
    """A system-level failure aborted exam generation entirely - the run
    could not safely continue at all, so no partial result is returned.

    Since WP-023, this exception represents *only* system-level failures
    (e.g. authentication, rate-limit, provider/connection, configuration,
    prompt-repository, or retrieval/corpus-initialization failures) -
    always carries ``operational_cause``, the original exception that
    triggered the abort. Question-local failures (WP-013 attempt-budget
    exhaustion, WP-021 provenance-recovery exhaustion, duplicate-
    replacement exhaustion, and similar per-candidate failures) no longer
    raise this exception at all - they are recorded as
    ``FailedPlannedQuestion`` entries and orchestration continues past
    them, per WP-023's question-local/system-level distinction.

    Always carries ``planned_question`` (the plan entry being produced
    when the abort happened) and ``completed_productions`` (every
    ``QuestionProductionRecord`` already successfully accepted into the
    exam before this failure), so the partial state remains available for
    diagnostics even though it is never returned as though it were a
    complete or partial exam.
    """

    def __init__(
        self,
        message: str,
        *,
        planned_question: "PlannedQuestion",
        completed_productions: tuple["QuestionProductionRecord", ...],
        operational_cause: Exception,
    ) -> None:
        super().__init__(message)
        self.planned_question = planned_question
        self.completed_productions = completed_productions
        self.operational_cause = operational_cause
