"""The WP-014 control layer: turns an ``ExamRequest`` into a complete
``ExamOutput`` by planning, then sequentially invoking, WP-013's existing
``QuestionProducer`` once per requested question.

    ExamRequest
         v
    resolve categories (WP-006 CategoryResolver, counts combined)
         v
    build deterministic plan (category, generation_mode, position)
         v
    for each planned question:
        QuestionProducer.produce_question(...)   (WP-013: generation + all
                                                    five validators + bounded
                                                    quality regeneration)
             v
        exact-duplicate check (bounded replacement if a duplicate)
         v
    candidate_to_exam_question() (WP-002/WP-009 deterministic conversion)
         v
    ExamOutput

This module owns planning, sequencing, and exam-level duplicate protection
only - it introduces no new generation, validation, or acceptance logic,
and never mutates a candidate, plan entry, or validator/production result.
"""

from __future__ import annotations

from pydantic import ValidationError

from exam_generator.config import load_app_config
from exam_generator.generation import GenerationError
from exam_generator.llm import LLMError
from exam_generator.models import (
    ExamGenerationStatus,
    ExamOutput,
    ExamRequest,
    GenerationMode,
    candidate_to_exam_question,
)
from exam_generator.orchestration.errors import InvalidOrchestrationConfigurationError, QuestionProductionFailedError
from exam_generator.orchestration.models import (
    ExamGenerationResult,
    FailedPlannedQuestion,
    PlannedQuestion,
    QuestionProductionRecord,
)
from exam_generator.production import QuestionAttemptsExhaustedError, QuestionProducer, QuestionProductionResult
from exam_generator.prompts import PromptError
from exam_generator.retrieval import CategoryResolver, RetrievalError, build_category_resolver, resolve_exam_request_categories
from exam_generator.validation import GroundingValidationError, InvalidGroundingOutputError, InvalidTextbookOutputError, TextbookValidationError

#: WP-023: failures demonstrably local to the one candidate/question being
#: produced when they occur - never indicating a broader system/provider/
#: infrastructure problem. Orchestration records these as a
#: ``FailedPlannedQuestion`` and continues with the rest of the plan,
#: exactly as though this single planned question had been skipped.
#: ``QuestionAttemptsExhaustedError`` is handled separately (it carries its
#: own ``.attempts`` history) but is question-local in the same sense.
#:
#: Deliberately minimal (WP-023 section 6: "do not guess"): limited to
#: exactly the classes WP-023 section 4 names explicitly. Every other
#: previously-"known-operational" failure (including a validator's own raw
#: ``pydantic.ValidationError`` and a provider ``LLMResponseError``/
#: ``LLMStructuredOutputError``) stays system-level, matching pre-existing,
#: deliberately-written test expectations (see
#: ``test_invalid_structured_validator_output_is_an_operational_failure``
#: and ``test_structured_output_retry_exhaustion_is_a_contextualized_exam_failure``)
#: that were never asked to change.
_QUESTION_LOCAL_ERROR_TYPES: tuple[type[Exception], ...] = (
    InvalidGroundingOutputError,  # WP-021 grounding provenance recovery exhausted for this candidate
    InvalidTextbookOutputError,  # WP-021 textbook provenance recovery exhausted for this candidate
)

#: WP-023: every other known-operational failure - unchanged from what
#: WP-019 originally called "operational" before WP-023 split that single
#: bucket in two. Never specific to the one candidate/question being
#: produced when it happens; orchestration aborts the entire run
#: immediately via ``QuestionProductionFailedError``.
_SYSTEM_LEVEL_ERROR_TYPES: tuple[type[Exception], ...] = (
    LLMError,
    GenerationError,
    GroundingValidationError,
    TextbookValidationError,
    RetrievalError,
    PromptError,
    ValidationError,
)


def _validate_max_duplicate_replacement_attempts(value: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise InvalidOrchestrationConfigurationError(
            f"max_duplicate_replacement_attempts must be an integer >= 1, got {value!r}"
        )
    return value


def _normalize_question_text(text: str) -> str:
    """Deterministic exact-duplicate normalization (WP-014 section 12):
    collapse all whitespace runs (which also trims leading/trailing
    whitespace) and case-fold, so two questions differing only in
    whitespace or English/Latin letter case are still treated as the same
    question. Not semantic similarity - a genuinely different question
    that merely shares this normalized form is out of scope for WP-014."""
    return " ".join(text.split()).casefold()


def build_exam_plan(resolved_request: ExamRequest) -> tuple[PlannedQuestion, ...]:
    """Deterministically build the question-production plan for an
    already-canonicalized ``ExamRequest`` (see
    ``resolve_exam_request_categories`` - this function does not itself
    resolve aliases).

    Generation modes alternate *within each category*, starting at
    ``STYLE_SIMILAR`` for each category's first question - the master
    brief's established policy ("Questions alternate between two modes
    within each category"), applied independently per category rather
    than carried over globally. Position numbers are global, 1-based, and
    contiguous across the whole plan in request-dict iteration order,
    directly reusable as final ``ExamQuestion.number`` values. Identical
    input always produces an identical plan.
    """
    planned: list[PlannedQuestion] = []
    position = 1
    for category, count in resolved_request.categories.items():
        for index_in_category in range(count):
            mode = GenerationMode.STYLE_SIMILAR if index_in_category % 2 == 0 else GenerationMode.INDEPENDENT
            planned.append(PlannedQuestion(position=position, category=category, generation_mode=mode))
            position += 1
    return tuple(planned)


class ExamOrchestrator:
    """Application-facing entry point for one complete exam-generation run.

    Every dependency is injected explicitly - never hidden global state -
    so tests can supply fakes/mocks for the category resolver and the
    producer. Use ``ExamOrchestrator.from_default_configuration()`` for
    the normal application wiring against real project configuration/data.
    """

    def __init__(
        self,
        *,
        category_resolver: CategoryResolver,
        producer: QuestionProducer,
        max_duplicate_replacement_attempts: int,
    ) -> None:
        self._category_resolver = category_resolver
        self._producer = producer
        self._max_duplicate_replacement_attempts = _validate_max_duplicate_replacement_attempts(
            max_duplicate_replacement_attempts
        )

    @classmethod
    def from_default_configuration(cls) -> "ExamOrchestrator":
        """Construct the normal application wiring: the real category
        resolver, a real ``QuestionProducer`` (all five real validators),
        and ``config/app.yaml``'s ``generation.max_duplicate_replacement_attempts``
        as the duplicate-replacement bound - a new, small configuration
        value distinct from WP-013's own ``max_generation_attempts``.

        Requires ``OPENAI_API_KEY`` to be set (resolved by
        ``QuestionProducer.from_default_configuration()``).
        """
        return cls(
            category_resolver=build_category_resolver(),
            producer=QuestionProducer.from_default_configuration(),
            max_duplicate_replacement_attempts=load_app_config().generation.max_duplicate_replacement_attempts,
        )

    def _produce_unique_question(
        self,
        planned: PlannedQuestion,
        *,
        total_planned: int,
        completed_productions: tuple[QuestionProductionRecord, ...],
        seen_normalized_questions: set[str],
    ) -> QuestionProductionRecord | FailedPlannedQuestion:
        """Produce one planned question, replacing (bounded) any result
        that exactly duplicates a question already accepted into this
        exam.

        Since WP-023, a question-local failure (WP-013's own bounded
        regeneration exhausted, every duplicate-replacement attempt also
        duplicated an already-accepted question, or another failure
        demonstrably scoped to this one candidate - see
        ``_QUESTION_LOCAL_ERROR_TYPES``) is returned as a
        ``FailedPlannedQuestion`` rather than raised - a normal outcome the
        caller records and continues past, exactly as a validator's
        negative verdict is a normal result rather than an exception. A
        system-level failure (``_SYSTEM_LEVEL_ERROR_TYPES``) still raises
        ``QuestionProductionFailedError`` immediately, aborting the whole
        run, contextualized with this planned question's position/
        category/mode and how many questions were already completed, with
        the original failure preserved via exception chaining. A
        genuinely unexpected exception is left uncaught, propagating with
        its full traceback."""
        duplicate_productions: list[QuestionProductionResult] = []

        for _ in range(self._max_duplicate_replacement_attempts + 1):
            try:
                production = self._producer.produce_question(
                    category=planned.category, generation_mode=planned.generation_mode
                )
            except QuestionAttemptsExhaustedError as exc:
                return FailedPlannedQuestion(
                    planned=planned,
                    failure_type=type(exc).__name__,
                    failure_message=(
                        f"generation attempts exhausted without an accepted candidate "
                        f"({len(exc.attempts)} attempt(s) made)"
                    ),
                    attempts=exc.attempts,
                )
            except _QUESTION_LOCAL_ERROR_TYPES as exc:
                return FailedPlannedQuestion(
                    planned=planned,
                    failure_type=type(exc).__name__,
                    failure_message=str(exc),
                )
            except _SYSTEM_LEVEL_ERROR_TYPES as exc:
                raise QuestionProductionFailedError(
                    f"Exam generation failed at question {planned.position}/{total_planned} "
                    f"(category={planned.category!r}, generation_mode={planned.generation_mode.value}). "
                    f"Completed questions: {len(completed_productions)}. "
                    f"Cause: {type(exc).__name__}: {exc}",
                    planned_question=planned,
                    completed_productions=completed_productions,
                    operational_cause=exc,
                ) from exc

            normalized = _normalize_question_text(production.candidate.question)
            if normalized not in seen_normalized_questions:
                return QuestionProductionRecord(
                    planned=planned,
                    production=production,
                    duplicate_replacement_attempts=len(duplicate_productions),
                )

            duplicate_productions.append(production)

        return FailedPlannedQuestion(
            planned=planned,
            failure_type="DuplicateReplacementExhausted",
            failure_message=(
                f"exhausted {self._max_duplicate_replacement_attempts} duplicate-replacement attempt(s) - "
                "every produced candidate duplicated a question already accepted into this exam"
            ),
            duplicate_productions=tuple(duplicate_productions),
        )

    def generate_exam(self, request: ExamRequest) -> ExamGenerationResult:
        """Generate an exam for ``request``.

        Resolves aliases to canonical categories and combines their
        requested counts (WP-006, never reimplemented here), builds a
        deterministic plan, then sequentially calls WP-013's
        ``QuestionProducer`` once per planned question - never
        reimplementing generation/validation/acceptance/regeneration.
        Only an accepted, non-duplicate candidate enters the exam.

        Since WP-023, a question-local failure (see
        ``_QUESTION_LOCAL_ERROR_TYPES`` and ``_produce_unique_question``)
        no longer aborts the run: it is recorded as a
        ``FailedPlannedQuestion`` and the plan continues, yielding a
        ``PARTIAL`` result if the plan otherwise completes. A system-level
        failure still propagates immediately as
        ``QuestionProductionFailedError`` - no result is returned at all
        in that case. Accepted questions are renumbered contiguously
        1..N in plan order (never gap-preserving, since a failed planned
        position leaves no clean-exam slot to preserve); each accepted
        question's original planned position remains available via its
        ``QuestionProductionRecord.planned.position``, separate from its
        final exam number. Never mutates ``request`` or any production/
        validation result.
        """
        resolved_request = resolve_exam_request_categories(request, self._category_resolver)
        plan = build_exam_plan(resolved_request)

        productions: list[QuestionProductionRecord] = []
        failed_questions: list[FailedPlannedQuestion] = []
        seen_normalized_questions: set[str] = set()

        for planned in plan:
            result = self._produce_unique_question(
                planned,
                total_planned=len(plan),
                completed_productions=tuple(productions),
                seen_normalized_questions=seen_normalized_questions,
            )
            if isinstance(result, FailedPlannedQuestion):
                failed_questions.append(result)
                continue
            productions.append(result)
            seen_normalized_questions.add(_normalize_question_text(result.production.candidate.question))

        exam_questions = [
            candidate_to_exam_question(record.production.candidate, number)
            for number, record in enumerate(productions, start=1)
        ]
        exam = ExamOutput(questions=exam_questions) if exam_questions else None
        status = ExamGenerationStatus.PARTIAL if failed_questions else ExamGenerationStatus.COMPLETE

        return ExamGenerationResult(
            status=status,
            exam=exam,
            plan=plan,
            productions=tuple(productions),
            failed_questions=tuple(failed_questions),
        )
