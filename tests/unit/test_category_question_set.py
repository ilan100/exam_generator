import inspect
from unittest.mock import MagicMock

import pytest
from pydantic import ValidationError

from exam_generator.category_generation import (
    QUESTION_LOCAL_ERROR_TYPES,
    CategoryGenerationRequest,
    CategoryGenerationService,
    CategoryQuestionSetRequest,
    CategoryQuestionSetResponse,
    CategoryQuestionSetService,
    InvalidCategoryGenerationConfigurationError,
)
import exam_generator.category_generation.service as service_module
from exam_generator.llm import LLMProviderError
from exam_generator.models import (
    CandidateQuestion,
    CategoryValidationResult,
    ExamQuestion,
    GenerationMode,
    GroundingValidationResult,
    MCQValidationResult,
    QualityValidationResult,
    QuestionTarget,
    TextbookCheckResult,
    TextbookCheckStatus,
    candidate_to_exam_question,
)
from exam_generator.planning import QuestionTargetPlanner
from exam_generator.production import (
    CandidateValidationResults,
    QuestionAttempt,
    QuestionAttemptsExhaustedError,
    QuestionProducer,
    QuestionProductionResult,
)
from exam_generator.retrieval import CategoryResolver
from exam_generator.validation import InvalidGroundingOutputError

CATEGORY_A = "קליפת המוח"
QUESTION_TEXT = "מהו תפקידה העיקרי של קליפת המוח?"


# ---------------------------------------------------------------------------
# Fixture helpers
# ---------------------------------------------------------------------------


def _candidate(question: str = QUESTION_TEXT, **kwargs) -> CandidateQuestion:
    defaults = dict(
        question=question,
        answers=["תשובה א", "תשובה ב", "תשובה ג", "תשובה ד"],
        correct_answer=2,
        category=CATEGORY_A,
        generation_mode=GenerationMode.INDEPENDENT,
    )
    defaults.update(kwargs)
    return CandidateQuestion(**defaults)


def _exam_question(question: str = QUESTION_TEXT, *, number: int | None = None) -> ExamQuestion:
    return candidate_to_exam_question(_candidate(question=question), number)


def _production_result(candidate: CandidateQuestion) -> QuestionProductionResult:
    validations = CandidateValidationResults(
        grounding=GroundingValidationResult(
            grounded=True,
            correct_answer_supported=True,
            other_answers_not_equally_correct=True,
            reason="stub",
            confidence=0.9,
        ),
        mcq=MCQValidationResult(valid=True, exactly_four_answers=True, single_best_answer=True, reason="stub"),
        category=CategoryValidationResult(
            valid=True, requested_category=candidate.category, assessed_category=candidate.category, reason="stub"
        ),
        quality=QualityValidationResult(valid=True, reason="stub"),
        textbook=TextbookCheckResult(status=TextbookCheckStatus.CONSISTENT, reason="stub"),
    )
    attempt = QuestionAttempt(attempt_number=1, candidate=candidate, validations=validations)
    return QuestionProductionResult(candidate=candidate, attempts=(attempt,))


def _identity_resolver() -> MagicMock:
    mock = MagicMock(spec=CategoryResolver)
    mock.resolve.side_effect = lambda category: category
    return mock


def _target(*, category: str = CATEGORY_A, target_id: int = 1) -> QuestionTarget:
    return QuestionTarget(target_id=target_id, category=category, topic="topic", factual_focus="focus")


def _planner(*, side_effect=None) -> MagicMock:
    mock = MagicMock(spec=QuestionTargetPlanner)
    if side_effect is not None:
        mock.plan_targets.side_effect = side_effect
    else:
        mock.plan_targets.side_effect = lambda *, category, count, coverage=None: [_target(category=category, target_id=1)]
    return mock


def _producer(*, return_value=None, side_effect=None) -> MagicMock:
    mock = MagicMock(spec=QuestionProducer)
    if side_effect is not None:
        mock.produce_question.side_effect = side_effect
    else:
        mock.produce_question.return_value = return_value or _production_result(_candidate())
    return mock


def _make_service(
    *, resolver=None, planner=None, producer=None, max_duplicate_replacement_attempts=2
) -> CategoryQuestionSetService:
    return CategoryQuestionSetService(
        category_resolver=resolver or _identity_resolver(),
        target_planner=planner or _planner(),
        producer=producer or _producer(),
        max_duplicate_replacement_attempts=max_duplicate_replacement_attempts,
    )


def _request(*, category: str = CATEGORY_A, generation_mode=GenerationMode.STYLE_SIMILAR, existing_questions=()):
    return CategoryQuestionSetRequest(
        category=category, generation_mode=generation_mode, existing_questions=existing_questions
    )


# ---------------------------------------------------------------------------
# CategoryQuestionSetRequest: existing_questions count (section 2/8 - 0/1/2/3)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("count", [0, 1, 2, 3])
def test_request_accepts_any_existing_questions_count(count):
    existing = tuple(_exam_question(f"שאלה {i}", number=i + 1) for i in range(count))
    request = _request(existing_questions=existing)
    assert len(request.existing_questions) == count


def test_request_defaults_to_empty_existing_questions():
    request = CategoryQuestionSetRequest(category=CATEGORY_A, generation_mode=GenerationMode.STYLE_SIMILAR)
    assert request.existing_questions == ()


def test_request_is_frozen_and_forbids_unknown_fields():
    request = _request()
    with pytest.raises(ValidationError):
        request.category = "other"
    with pytest.raises(ValidationError):
        CategoryQuestionSetRequest(category=CATEGORY_A, generation_mode=GenerationMode.STYLE_SIMILAR, unexpected="x")


# ---------------------------------------------------------------------------
# Existing/generated question contract (section 3/4): the production
# schema (ExamQuestion) is reused, never duplicated.
# ---------------------------------------------------------------------------


def test_existing_questions_must_be_exam_question_shaped():
    # A CandidateQuestion (the internal, pre-acceptance shape) is not the
    # production schema and must be rejected - existing_questions must be
    # genuine ExamQuestion instances, not a lookalike.
    with pytest.raises(ValidationError):
        CategoryQuestionSetRequest(
            category=CATEGORY_A, generation_mode=GenerationMode.STYLE_SIMILAR, existing_questions=(_candidate(),)
        )


def test_existing_question_may_carry_a_real_number_or_none():
    numbered = _exam_question("שאלה א", number=5)
    unnumbered = _exam_question("שאלה ב", number=None)
    request = _request(existing_questions=(numbered, unnumbered))
    assert request.existing_questions[0].number == 5
    assert request.existing_questions[1].number is None


def test_generated_question_uses_the_production_schema():
    candidate = _candidate()
    producer = _producer(return_value=_production_result(candidate))
    service = _make_service(producer=producer)
    response = service.generate_next(_request())
    assert isinstance(response.question, ExamQuestion)
    assert response.question.question == candidate.question
    assert response.question.answer1 == candidate.answers[0]
    assert response.question.correct_answer == candidate.correct_answer
    assert response.question.category == candidate.category


def test_generated_question_number_is_none_generation_does_not_assign_it():
    # WP-033 section 4: generation is responsible only for the question
    # content - the orchestration layer assigns number/id.
    producer = _producer(return_value=_production_result(_candidate()))
    service = _make_service(producer=producer)
    response = service.generate_next(_request())
    assert response.question.number is None


# ---------------------------------------------------------------------------
# CategoryQuestionSetResponse: accepted/failed consistency
# ---------------------------------------------------------------------------


def test_accepted_response_requires_question_and_production():
    with pytest.raises(ValidationError):
        CategoryQuestionSetResponse(accepted=True)
    with pytest.raises(ValidationError):
        CategoryQuestionSetResponse(accepted=True, question=_exam_question())
    with pytest.raises(ValidationError):
        CategoryQuestionSetResponse(accepted=True, production=_production_result(_candidate()))


def test_rejected_response_requires_failure_type_and_message():
    with pytest.raises(ValidationError):
        CategoryQuestionSetResponse(accepted=False)


def test_rejected_response_rejects_question_and_production():
    with pytest.raises(ValidationError):
        CategoryQuestionSetResponse(
            accepted=False,
            question=_exam_question(),
            failure_type="X",
            failure_message="y",
        )


def test_attempts_property_counts_production_attempts():
    response = CategoryQuestionSetResponse(
        accepted=True, question=_exam_question(), production=_production_result(_candidate())
    )
    assert response.attempts == 1


# ---------------------------------------------------------------------------
# CategoryQuestionSetService: configuration (mirrors CategoryGenerationService)
# ---------------------------------------------------------------------------


def test_invalid_max_duplicate_replacement_attempts_is_rejected():
    with pytest.raises(InvalidCategoryGenerationConfigurationError):
        _make_service(max_duplicate_replacement_attempts=0)


# ---------------------------------------------------------------------------
# CategoryQuestionSetService: generation cycle (target planning, production,
# question-local vs. system-level classification) - identical underlying
# behavior to CategoryGenerationService, reused via _run_generation_cycle.
# ---------------------------------------------------------------------------


def test_target_planning_uses_count_one():
    planner = _planner()
    service = _make_service(planner=planner)
    service.generate_next(_request())
    assert planner.plan_targets.call_count == 1
    assert planner.plan_targets.call_args.kwargs["category"] == CATEGORY_A
    assert planner.plan_targets.call_args.kwargs["count"] == 1
    assert "coverage" in planner.plan_targets.call_args.kwargs


def test_zero_targets_planned_yields_insufficient_distinct_targets_failure():
    planner = _planner(side_effect=lambda *, category, count, coverage=None: [])
    producer = _producer()
    service = _make_service(planner=planner, producer=producer)
    response = service.generate_next(_request())
    assert response.accepted is False
    assert response.failure_type == "InsufficientDistinctTargetsError"
    assert producer.produce_question.call_count == 0


def test_attempt_exhaustion_is_a_question_local_failure_response():
    sentinel_attempts = (
        QuestionAttempt(
            attempt_number=1, candidate=_candidate(), validations=_production_result(_candidate()).attempts[0].validations
        ),
    )
    producer = _producer(side_effect=QuestionAttemptsExhaustedError("exhausted", attempts=sentinel_attempts))
    service = _make_service(producer=producer)
    response = service.generate_next(_request())
    assert response.accepted is False
    assert response.failure_type == "QuestionAttemptsExhaustedError"
    assert response.failure_attempts == sentinel_attempts


@pytest.mark.parametrize("error_type", QUESTION_LOCAL_ERROR_TYPES)
def test_question_local_error_types_yield_failure_response_not_raised(error_type):
    producer = _producer(side_effect=error_type("claimed unsupplied evidence"))
    service = _make_service(producer=producer)
    response = service.generate_next(_request())
    assert response.accepted is False
    assert response.failure_type == error_type.__name__


def test_system_level_production_failure_propagates_uncaught():
    producer = _producer(side_effect=LLMProviderError("connection failed"))
    service = _make_service(producer=producer)
    with pytest.raises(LLMProviderError):
        service.generate_next(_request())


# ---------------------------------------------------------------------------
# CategoryQuestionSetService: duplicate replacement, now scoped to
# ExamQuestion-shaped existing_questions
# ---------------------------------------------------------------------------


def test_exact_duplicate_of_an_existing_exam_question_is_replaced():
    unique_candidate = _candidate(question="שאלה שונה לגמרי")
    producer = _producer(
        side_effect=[_production_result(_candidate(question=QUESTION_TEXT)), _production_result(unique_candidate)]
    )
    service = _make_service(producer=producer, max_duplicate_replacement_attempts=2)
    response = service.generate_next(_request(existing_questions=(_exam_question(QUESTION_TEXT, number=1),)))
    assert response.accepted is True
    assert response.question.question == unique_candidate.question
    assert response.duplicate_replacement_attempts == 1


def test_duplicate_replacement_exhaustion_is_a_question_local_failure_response():
    producer = _producer(return_value=_production_result(_candidate(question=QUESTION_TEXT)))
    service = _make_service(producer=producer, max_duplicate_replacement_attempts=1)
    response = service.generate_next(_request(existing_questions=(_exam_question(QUESTION_TEXT, number=1),)))
    assert response.accepted is False
    assert response.failure_type == "DuplicateReplacementExhausted"
    assert producer.produce_question.call_count == 2


# ---------------------------------------------------------------------------
# Backward compatibility (section 7/8): CategoryGenerationService (WP-032)
# remains fully functional, unchanged, after the WP-033 refactor.
# ---------------------------------------------------------------------------


def _legacy_service(*, resolver=None, planner=None, producer=None, max_duplicate_replacement_attempts=2):
    return CategoryGenerationService(
        category_resolver=resolver or _identity_resolver(),
        target_planner=planner or _planner(),
        producer=producer or _producer(),
        max_duplicate_replacement_attempts=max_duplicate_replacement_attempts,
    )


def test_legacy_category_generation_service_still_accepts_a_candidate():
    candidate = _candidate()
    producer = _producer(return_value=_production_result(candidate))
    service = _legacy_service(producer=producer)
    response = service.generate_next(
        CategoryGenerationRequest(category=CATEGORY_A, generation_mode=GenerationMode.STYLE_SIMILAR)
    )
    assert response.accepted is True
    assert response.question == candidate


def test_legacy_category_generation_service_still_classifies_question_local_failures():
    producer = _producer(side_effect=InvalidGroundingOutputError("claimed unsupplied evidence"))
    service = _legacy_service(producer=producer)
    response = service.generate_next(
        CategoryGenerationRequest(category=CATEGORY_A, generation_mode=GenerationMode.STYLE_SIMILAR)
    )
    assert response.accepted is False
    assert response.failure_type == "InvalidGroundingOutputError"


def test_no_semantic_or_llm_duplicate_detector_introduced():
    source = inspect.getsource(service_module)
    assert "generate_structured" not in source
    assert "embed" not in source.lower()


# ---------------------------------------------------------------------------
# WP-034: coverage extraction is wired from request.existing_questions into
# plan_targets(), using the ExamQuestion shape
# ---------------------------------------------------------------------------


def test_coverage_extracted_from_existing_exam_questions_reaches_the_planner():
    existing = candidate_to_exam_question(
        _candidate(question="שאלה קודמת", answers=["א", "ב", "ג", "ד"], correct_answer=3), number=1
    )
    planner = _planner()
    service = _make_service(planner=planner)
    service.generate_next(_request(existing_questions=(existing,)))
    coverage = planner.plan_targets.call_args.kwargs["coverage"]
    assert coverage.tested_concepts == ("ג",)


def test_no_existing_questions_yields_empty_coverage_at_the_planner():
    planner = _planner()
    service = _make_service(planner=planner)
    service.generate_next(_request(existing_questions=()))
    coverage = planner.plan_targets.call_args.kwargs["coverage"]
    assert coverage.tested_concepts == ()
    assert coverage.tested_relationship_types == ()
