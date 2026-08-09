"""The WP-032/WP-033/WP-034 category-generation services: the project's
primary generation API.

    CategoryQuestionSetRequest (WP-033) / CategoryGenerationRequest (WP-032)
         v
    extract_category_coverage(existing_questions)      (WP-034, reused)
         v
    QuestionTargetPlanner.plan_targets(count=1, coverage=...)  (WP-025/034)
         v
    QuestionProducer.produce_question(...)              (WP-013, reused -
                                                           generation +
                                                           all five
                                                           validators +
                                                           bounded quality
                                                           regeneration)
         v
    exact-duplicate check against request.existing_questions
    (bounded replacement if a duplicate - WP-014's policy, reused)
         v
    CategoryQuestionSetResponse (WP-033) / CategoryGenerationResponse (WP-032)

Produces exactly one additional accepted question for one category, given
every question already accepted for that category so far - or an honest,
question-local failure. Introduces no new generation, validation, target-
planning, or acceptance logic of its own; it only reorganizes existing
WP-013/WP-025 orchestration into a per-question API (WP-032 sections 1/6,
unchanged by WP-033).

WP-033 replaces ``CategoryGenerationRequest``/``Response`` with
``CategoryQuestionSetRequest``/``Response`` (``ExamQuestion``-shaped
existing/generated questions, WP-033's own permanent contract) as the
architecture's primary surface, but keeps ``CategoryGenerationService``
itself fully working, per WP-033 section 7's explicit backward-
compatibility requirement ("the previous request model should remain
temporarily supported internally"). Both services share one underlying
generation-cycle implementation (``_run_generation_cycle()``) - the actual
target-planning/production/duplicate-replacement/error-classification
decision logic exists exactly once, never duplicated between them.

WP-034 makes target planning coverage-aware: each service deterministically
extracts a ``CategoryCoverage`` from its own ``request.existing_questions``
(``exam_generator.planning.extract_category_coverage()`` - a plain-text
keyword heuristic, no LLM call and no vector/semantic-similarity technique
of any kind) and threads it through ``_run_generation_cycle()`` into
``QuestionTargetPlanner.plan_targets()``, purely as information for that
one planning call. Production, duplicate replacement, and error
classification are entirely unaffected - coverage never becomes a
validator (WP-034 section 6).
"""

from __future__ import annotations

from dataclasses import dataclass

from pydantic import ValidationError

from exam_generator.category_generation.errors import InvalidCategoryGenerationConfigurationError
from exam_generator.category_generation.models import (
    CategoryGenerationRequest,
    CategoryGenerationResponse,
    CategoryQuestionSetRequest,
    CategoryQuestionSetResponse,
)
from exam_generator.config import load_app_config
from exam_generator.generation import GenerationError
from exam_generator.llm import LLMError
from exam_generator.models import CategoryCoverage, GenerationMode, candidate_to_exam_question
from exam_generator.planning import QuestionTargetPlanner, extract_category_coverage
from exam_generator.production import QuestionAttemptsExhaustedError, QuestionProducer, QuestionProductionResult
from exam_generator.prompts import PromptError
from exam_generator.retrieval import CategoryResolver, RetrievalError, build_category_resolver
from exam_generator.validation import (
    GroundingValidationError,
    InvalidGroundingOutputError,
    InvalidTextbookOutputError,
    TextbookValidationError,
)

#: WP-023 (moved here from ``exam_generator.orchestration.orchestrator` by
#: WP-032, alongside the production logic it classifies): failures
#: demonstrably local to the one candidate/question being produced when
#: they occur - recorded as a question-local failure response
#: (``accepted=False``) rather than raised.
QUESTION_LOCAL_ERROR_TYPES: tuple[type[Exception], ...] = (
    InvalidGroundingOutputError,  # WP-021 grounding provenance recovery exhausted for this candidate
    InvalidTextbookOutputError,  # WP-021 textbook provenance recovery exhausted for this candidate
)

#: WP-023 (moved here from ``exam_generator.orchestration.orchestrator` by
#: WP-032): every other known-operational failure. Never caught by either
#: service - it propagates to the caller (e.g. ``ExamOrchestrator``),
#: which retains whatever session-level context (position in an overall
#: plan, questions already completed) it needs to contextualize an abort;
#: neither service, being a single stateless per-question call, has any
#: such context of its own.
SYSTEM_LEVEL_ERROR_TYPES: tuple[type[Exception], ...] = (
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
        raise InvalidCategoryGenerationConfigurationError(
            f"max_duplicate_replacement_attempts must be an integer >= 1, got {value!r}"
        )
    return value


def _normalize_question_text(text: str) -> str:
    """Deterministic exact-duplicate normalization (WP-014 section 12,
    moved here unchanged by WP-032): collapse all whitespace runs (which
    also trims leading/trailing whitespace) and case-fold, so two
    questions differing only in whitespace or English/Latin letter case
    are still treated as the same question. Not semantic similarity."""
    return " ".join(text.split()).casefold()


@dataclass(frozen=True)
class _GenerationCycleOutcome:
    """The shared, request-contract-agnostic result of one full
    target-plan-then-produce-then-duplicate-check cycle (WP-032, factored
    out unchanged by WP-033 so both ``CategoryGenerationService`` and
    ``CategoryQuestionSetService`` build their own response shape from one
    single source of truth, rather than each re-implementing the cycle)."""

    accepted: bool
    production: QuestionProductionResult | None = None
    duplicate_replacement_attempts: int = 0
    duplicate_productions: tuple[QuestionProductionResult, ...] = ()
    failure_type: str | None = None
    failure_message: str | None = None
    failure_attempts: tuple = ()


def _run_generation_cycle(
    *,
    category_resolver: CategoryResolver,
    target_planner: QuestionTargetPlanner,
    producer: QuestionProducer,
    max_duplicate_replacement_attempts: int,
    category: str,
    generation_mode: GenerationMode,
    seen_normalized_questions: set[str],
    coverage: CategoryCoverage = CategoryCoverage(),
) -> _GenerationCycleOutcome:
    """Plan exactly one target, produce exactly one accepted candidate
    distinct from ``seen_normalized_questions`` (bounded duplicate
    replacement), or fail for a question-local reason - see
    ``CategoryGenerationService.generate_next()``'s docstring (WP-032) for
    the full behavioral contract, unchanged here. Never catches
    ``SYSTEM_LEVEL_ERROR_TYPES`` - those propagate to the caller.

    Since WP-034, ``coverage`` (already deterministically extracted by the
    caller from its own ``existing_questions`` shape) is threaded into
    target planning as information only - see
    ``QuestionTargetPlanner.plan_targets()``'s own WP-034 docstring. It
    never affects production, duplicate replacement, or error
    classification - only which target planning happens to choose.
    """
    canonical_category = category_resolver.resolve(category)

    targets = target_planner.plan_targets(category=canonical_category, count=1, coverage=coverage)
    if not targets:
        return _GenerationCycleOutcome(
            accepted=False,
            failure_type="InsufficientDistinctTargetsError",
            failure_message=(
                f"category {canonical_category!r} evidence supports no further distinct question target"
            ),
        )
    target = targets[0]

    duplicate_productions: list[QuestionProductionResult] = []

    for _ in range(max_duplicate_replacement_attempts + 1):
        try:
            production = producer.produce_question(
                category=canonical_category, generation_mode=generation_mode, target=target
            )
        except QuestionAttemptsExhaustedError as exc:
            return _GenerationCycleOutcome(
                accepted=False,
                failure_type=type(exc).__name__,
                failure_message=(
                    f"generation attempts exhausted without an accepted candidate "
                    f"({len(exc.attempts)} attempt(s) made)"
                ),
                failure_attempts=exc.attempts,
                duplicate_replacement_attempts=len(duplicate_productions),
                duplicate_productions=tuple(duplicate_productions),
            )
        except QUESTION_LOCAL_ERROR_TYPES as exc:
            return _GenerationCycleOutcome(
                accepted=False,
                failure_type=type(exc).__name__,
                failure_message=str(exc),
                duplicate_replacement_attempts=len(duplicate_productions),
                duplicate_productions=tuple(duplicate_productions),
            )

        normalized = _normalize_question_text(production.candidate.question)
        if normalized not in seen_normalized_questions:
            return _GenerationCycleOutcome(
                accepted=True, production=production, duplicate_replacement_attempts=len(duplicate_productions)
            )

        duplicate_productions.append(production)

    return _GenerationCycleOutcome(
        accepted=False,
        failure_type="DuplicateReplacementExhausted",
        failure_message=(
            f"exhausted {max_duplicate_replacement_attempts} duplicate-replacement attempt(s) - "
            "every produced candidate duplicated a question already supplied as an existing question"
        ),
        duplicate_replacement_attempts=len(duplicate_productions),
        duplicate_productions=tuple(duplicate_productions),
    )


class CategoryGenerationService:
    """Application-facing entry point for the WP-032 generation API:
    produce exactly one additional accepted question for a category, given
    every question already accepted for that category so far.

    Superseded by ``CategoryQuestionSetService`` (WP-033) as the
    architecture's primary path - kept fully working here for backward
    compatibility (WP-033 section 7), unchanged in behavior. Every
    dependency is injected explicitly - never hidden global state - so
    tests can supply fakes/mocks. Use
    ``CategoryGenerationService.from_default_configuration()`` for the
    normal application wiring against real project configuration/data.
    """

    def __init__(
        self,
        *,
        category_resolver: CategoryResolver,
        target_planner: QuestionTargetPlanner,
        producer: QuestionProducer,
        max_duplicate_replacement_attempts: int,
    ) -> None:
        self._category_resolver = category_resolver
        self._target_planner = target_planner
        self._producer = producer
        self._max_duplicate_replacement_attempts = _validate_max_duplicate_replacement_attempts(
            max_duplicate_replacement_attempts
        )

    @classmethod
    def from_default_configuration(cls) -> "CategoryGenerationService":
        """Construct the normal application wiring: the real category
        resolver, a real ``QuestionTargetPlanner`` (WP-025), a real
        ``QuestionProducer`` (all five real validators, WP-013), and
        ``config/app.yaml``'s existing ``generation.max_duplicate_replacement_attempts``
        (WP-014) as the duplicate-replacement bound.

        Requires ``OPENAI_API_KEY`` to be set (resolved by
        ``QuestionTargetPlanner``/``QuestionProducer.from_default_configuration()``).
        """
        return cls(
            category_resolver=build_category_resolver(),
            target_planner=QuestionTargetPlanner.from_default_configuration(),
            producer=QuestionProducer.from_default_configuration(),
            max_duplicate_replacement_attempts=load_app_config().generation.max_duplicate_replacement_attempts,
        )

    def generate_next(self, request: CategoryGenerationRequest) -> CategoryGenerationResponse:
        """Produce exactly one additional accepted question for
        ``request.category``, distinct from every question already listed
        in ``request.existing_questions``. See ``_run_generation_cycle()``
        for the full shared behavioral contract."""
        coverage = extract_category_coverage(
            tuple((q.question, q.answers[q.correct_answer - 1]) for q in request.existing_questions)
        )
        outcome = _run_generation_cycle(
            category_resolver=self._category_resolver,
            target_planner=self._target_planner,
            producer=self._producer,
            max_duplicate_replacement_attempts=self._max_duplicate_replacement_attempts,
            category=request.category,
            generation_mode=request.generation_mode,
            seen_normalized_questions={
                _normalize_question_text(question.question) for question in request.existing_questions
            },
            coverage=coverage,
        )
        return CategoryGenerationResponse(
            accepted=outcome.accepted,
            production=outcome.production,
            duplicate_replacement_attempts=outcome.duplicate_replacement_attempts,
            duplicate_productions=outcome.duplicate_productions,
            failure_type=outcome.failure_type,
            failure_message=outcome.failure_message,
            failure_attempts=outcome.failure_attempts,
        )


class CategoryQuestionSetService:
    """WP-033: the project's permanent primary generation API. Receives a
    category question set (the category, every question already belonging
    to it, and generation options) and returns exactly one additional
    question - nothing more (WP-033 section 5).

    Identical underlying behavior to ``CategoryGenerationService``
    (same injected ``QuestionTargetPlanner``/``QuestionProducer``, same
    ``_run_generation_cycle()``); differs only in its request/response
    contract, which uses ``ExamQuestion`` (the production question schema,
    WP-002/WP-033) for both ``existing_questions`` and the freshly-
    generated question, instead of the internal ``CandidateQuestion``.
    """

    def __init__(
        self,
        *,
        category_resolver: CategoryResolver,
        target_planner: QuestionTargetPlanner,
        producer: QuestionProducer,
        max_duplicate_replacement_attempts: int,
    ) -> None:
        self._category_resolver = category_resolver
        self._target_planner = target_planner
        self._producer = producer
        self._max_duplicate_replacement_attempts = _validate_max_duplicate_replacement_attempts(
            max_duplicate_replacement_attempts
        )

    @classmethod
    def from_default_configuration(cls) -> "CategoryQuestionSetService":
        """Construct the normal application wiring - identical dependency
        set to ``CategoryGenerationService.from_default_configuration()``.

        Requires ``OPENAI_API_KEY`` to be set (resolved by
        ``QuestionTargetPlanner``/``QuestionProducer.from_default_configuration()``).
        """
        return cls(
            category_resolver=build_category_resolver(),
            target_planner=QuestionTargetPlanner.from_default_configuration(),
            producer=QuestionProducer.from_default_configuration(),
            max_duplicate_replacement_attempts=load_app_config().generation.max_duplicate_replacement_attempts,
        )

    def generate_next(self, request: CategoryQuestionSetRequest) -> CategoryQuestionSetResponse:
        """Produce exactly one additional accepted question for
        ``request.category``, distinct (exact-text match only, WP-014's
        existing policy) from every question already listed in
        ``request.existing_questions``. The accepted question is returned
        as an ``ExamQuestion`` with ``number=None`` (WP-033 section 4 -
        "generation is responsible only for the question content"; the
        orchestration layer assigns ``number`` when it is not already
        available). See ``_run_generation_cycle()`` for the full shared
        behavioral contract (target planning, production, bounded
        duplicate replacement, question-local vs. system-level failure
        classification - identical to ``CategoryGenerationService``)."""
        coverage = extract_category_coverage(
            tuple(
                (q.question, (q.answer1, q.answer2, q.answer3, q.answer4)[q.correct_answer - 1])
                for q in request.existing_questions
            )
        )
        outcome = _run_generation_cycle(
            category_resolver=self._category_resolver,
            target_planner=self._target_planner,
            producer=self._producer,
            max_duplicate_replacement_attempts=self._max_duplicate_replacement_attempts,
            category=request.category,
            generation_mode=request.generation_mode,
            seen_normalized_questions={
                _normalize_question_text(question.question) for question in request.existing_questions
            },
            coverage=coverage,
        )
        question = candidate_to_exam_question(outcome.production.candidate) if outcome.accepted else None
        return CategoryQuestionSetResponse(
            accepted=outcome.accepted,
            question=question,
            production=outcome.production,
            duplicate_replacement_attempts=outcome.duplicate_replacement_attempts,
            duplicate_productions=outcome.duplicate_productions,
            failure_type=outcome.failure_type,
            failure_message=outcome.failure_message,
            failure_attempts=outcome.failure_attempts,
        )
