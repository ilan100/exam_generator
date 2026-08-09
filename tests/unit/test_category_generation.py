import inspect
from unittest.mock import MagicMock

import pytest
from pydantic import ValidationError

from exam_generator.category_generation import (
    QUESTION_LOCAL_ERROR_TYPES,
    SYSTEM_LEVEL_ERROR_TYPES,
    CategoryGenerationOptions,
    CategoryGenerationRequest,
    CategoryGenerationResponse,
    CategoryGenerationService,
    InvalidCategoryGenerationConfigurationError,
)
import exam_generator.category_generation.service as service_module
from exam_generator.generation import MissingEvidenceError
from exam_generator.llm import LLMProviderError
from exam_generator.models import (
    CandidateQuestion,
    CategoryValidationResult,
    GenerationMode,
    GroundingValidationResult,
    MCQValidationResult,
    QualityValidationResult,
    QuestionTarget,
    TextbookCheckResult,
    TextbookCheckStatus,
)
from exam_generator.production import (
    CandidateValidationResults,
    QuestionAttempt,
    QuestionAttemptsExhaustedError,
    QuestionProducer,
    QuestionProductionResult,
)
from exam_generator.planning import QuestionTargetPlanner
from exam_generator.retrieval import CategoryResolver
from exam_generator.validation import InvalidGroundingOutputError, InvalidTextbookOutputError

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
    """A fake ``QuestionTargetPlanner`` (WP-025). By default, always plans
    exactly one target for whatever category is asked."""
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
) -> CategoryGenerationService:
    return CategoryGenerationService(
        category_resolver=resolver or _identity_resolver(),
        target_planner=planner or _planner(),
        producer=producer or _producer(),
        max_duplicate_replacement_attempts=max_duplicate_replacement_attempts,
    )


def _request(*, category: str = CATEGORY_A, generation_mode=GenerationMode.STYLE_SIMILAR, existing_questions=()):
    return CategoryGenerationRequest(
        category=category, generation_mode=generation_mode, existing_questions=existing_questions
    )


# ---------------------------------------------------------------------------
# CategoryGenerationOptions / CategoryGenerationRequest
# ---------------------------------------------------------------------------


def test_generation_options_defaults_to_none_fields():
    options = CategoryGenerationOptions()
    assert options.difficulty is None
    assert options.style is None


def test_generation_options_rejects_unknown_fields():
    with pytest.raises(ValidationError):
        CategoryGenerationOptions(unexpected="x")


def test_request_defaults_to_no_existing_questions_and_default_options():
    request = CategoryGenerationRequest(category=CATEGORY_A, generation_mode=GenerationMode.STYLE_SIMILAR)
    assert request.existing_questions == ()
    assert request.generation_options == CategoryGenerationOptions()


def test_request_carries_supplied_existing_questions_unchanged():
    candidate = _candidate()
    request = _request(existing_questions=(candidate,))
    assert request.existing_questions == (candidate,)


def test_request_rejects_unknown_fields():
    with pytest.raises(ValidationError):
        CategoryGenerationRequest(category=CATEGORY_A, generation_mode=GenerationMode.STYLE_SIMILAR, unexpected="x")


def test_request_is_frozen():
    request = _request()
    with pytest.raises(ValidationError):
        request.category = "other"


# ---------------------------------------------------------------------------
# CategoryGenerationResponse
# ---------------------------------------------------------------------------


def test_accepted_response_requires_production():
    with pytest.raises(ValidationError):
        CategoryGenerationResponse(accepted=True)


def test_accepted_response_rejects_failure_fields():
    with pytest.raises(ValidationError):
        CategoryGenerationResponse(
            accepted=True, production=_production_result(_candidate()), failure_type="X", failure_message="y"
        )


def test_rejected_response_requires_failure_type_and_message():
    with pytest.raises(ValidationError):
        CategoryGenerationResponse(accepted=False)


def test_rejected_response_rejects_production():
    with pytest.raises(ValidationError):
        CategoryGenerationResponse(
            accepted=False,
            production=_production_result(_candidate()),
            failure_type="X",
            failure_message="y",
        )


def test_question_property_derives_from_production():
    candidate = _candidate()
    response = CategoryGenerationResponse(accepted=True, production=_production_result(candidate))
    assert response.question == candidate


def test_question_property_is_none_on_failure():
    response = CategoryGenerationResponse(accepted=False, failure_type="X", failure_message="y")
    assert response.question is None


def test_attempts_property_counts_production_attempts():
    candidate = _candidate()
    response = CategoryGenerationResponse(accepted=True, production=_production_result(candidate))
    assert response.attempts == 1


def test_attempts_property_counts_failure_attempts():
    sentinel_attempts = (
        QuestionAttempt(
            attempt_number=1, candidate=_candidate(), validations=_production_result(_candidate()).attempts[0].validations
        ),
    )
    response = CategoryGenerationResponse(
        accepted=False, failure_type="X", failure_message="y", failure_attempts=sentinel_attempts
    )
    assert response.attempts == 1


# ---------------------------------------------------------------------------
# CategoryGenerationService: configuration
# ---------------------------------------------------------------------------


def test_invalid_max_duplicate_replacement_attempts_is_rejected():
    with pytest.raises(InvalidCategoryGenerationConfigurationError):
        _make_service(max_duplicate_replacement_attempts=0)


def test_negative_max_duplicate_replacement_attempts_is_rejected():
    with pytest.raises(InvalidCategoryGenerationConfigurationError):
        _make_service(max_duplicate_replacement_attempts=-1)


def test_boolean_max_duplicate_replacement_attempts_is_rejected():
    with pytest.raises(InvalidCategoryGenerationConfigurationError):
        _make_service(max_duplicate_replacement_attempts=True)


# ---------------------------------------------------------------------------
# CategoryGenerationService: target planning (WP-025 integration)
# ---------------------------------------------------------------------------


def test_target_planning_happens_once_per_call_with_count_one():
    # WP-032: target planning granularity narrows from "once per category,
    # batched" to "once per generate_next() call, count=1" - each call
    # produces at most one question.
    planner = _planner()
    service = _make_service(planner=planner)
    service.generate_next(_request())
    assert planner.plan_targets.call_count == 1
    assert planner.plan_targets.call_args.kwargs["category"] == CATEGORY_A
    assert planner.plan_targets.call_args.kwargs["count"] == 1
    assert "coverage" in planner.plan_targets.call_args.kwargs


def test_producer_receives_the_single_planned_target():
    target = _target(target_id=7)
    planner = _planner(side_effect=lambda *, category, count, coverage=None: [target])
    producer = _producer()
    service = _make_service(planner=planner, producer=producer)
    service.generate_next(_request())
    assert producer.produce_question.call_args.kwargs["target"] is target


def test_target_remains_stable_across_duplicate_replacement_retries():
    # WP-025 section 9, preserved by WP-032: a duplicate-replacement retry
    # must reuse the same assigned target - never re-planned merely
    # because a candidate was rejected as a duplicate.
    target = _target(target_id=1)
    planner = _planner(side_effect=lambda *, category, count, coverage=None: [target])
    producer = _producer(
        side_effect=[
            _production_result(_candidate(question=QUESTION_TEXT)),
            _production_result(_candidate(question="שאלה שונה")),
        ]
    )
    service = _make_service(planner=planner, producer=producer, max_duplicate_replacement_attempts=2)
    service.generate_next(_request(existing_questions=(_candidate(question=QUESTION_TEXT),)))
    calls = producer.produce_question.call_args_list
    assert calls[0].kwargs["target"] is target
    assert calls[1].kwargs["target"] is target
    assert planner.plan_targets.call_count == 1


def test_zero_targets_planned_yields_insufficient_distinct_targets_failure():
    planner = _planner(side_effect=lambda *, category, count, coverage=None: [])
    producer = _producer()
    service = _make_service(planner=planner, producer=producer)
    response = service.generate_next(_request())
    assert response.accepted is False
    assert response.failure_type == "InsufficientDistinctTargetsError"
    # No candidate production is attempted at all - not a
    # candidate-production problem, so it never consumes WP-013's attempt
    # budget.
    assert producer.produce_question.call_count == 0


def test_target_planning_system_level_failure_propagates_uncaught():
    planner = _planner(side_effect=LLMProviderError("connection failed"))
    service = _make_service(planner=planner)
    with pytest.raises(LLMProviderError):
        service.generate_next(_request())


def test_target_planning_missing_evidence_propagates_uncaught():
    planner = _planner(side_effect=MissingEvidenceError("no evidence"))
    service = _make_service(planner=planner)
    with pytest.raises(MissingEvidenceError):
        service.generate_next(_request())


# ---------------------------------------------------------------------------
# CategoryGenerationService: production, question-local vs system-level
# classification (WP-023, moved here by WP-032)
# ---------------------------------------------------------------------------


def test_accepted_candidate_yields_accepted_response():
    candidate = _candidate()
    producer = _producer(return_value=_production_result(candidate))
    service = _make_service(producer=producer)
    response = service.generate_next(_request())
    assert response.accepted is True
    assert response.question == candidate
    assert response.attempts == 1


def test_producer_receives_requested_category_and_generation_mode():
    producer = _producer()
    service = _make_service(producer=producer)
    service.generate_next(_request(category=CATEGORY_A, generation_mode=GenerationMode.INDEPENDENT))
    call = producer.produce_question.call_args
    assert call.kwargs["category"] == CATEGORY_A
    assert call.kwargs["generation_mode"] == GenerationMode.INDEPENDENT


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


def test_grounding_provenance_recovery_exhaustion_is_question_local():
    producer = _producer(side_effect=InvalidGroundingOutputError("claimed unsupplied evidence"))
    service = _make_service(producer=producer)
    response = service.generate_next(_request())
    assert response.accepted is False
    assert response.failure_type == "InvalidGroundingOutputError"


def test_textbook_provenance_recovery_exhaustion_is_question_local():
    producer = _producer(side_effect=InvalidTextbookOutputError("claimed unsupplied evidence"))
    service = _make_service(producer=producer)
    response = service.generate_next(_request())
    assert response.accepted is False
    assert response.failure_type == "InvalidTextbookOutputError"


def test_system_level_production_failure_propagates_uncaught():
    producer = _producer(side_effect=LLMProviderError("connection failed"))
    service = _make_service(producer=producer)
    with pytest.raises(LLMProviderError):
        service.generate_next(_request())


def test_unexpected_exception_propagates_uncaught():
    producer = _producer(side_effect=RuntimeError("genuinely unexpected"))
    service = _make_service(producer=producer)
    with pytest.raises(RuntimeError):
        service.generate_next(_request())


def test_system_level_error_types_tuple_matches_documented_set():
    # Regression guard: SYSTEM_LEVEL_ERROR_TYPES must never silently grow
    # or shrink without deliberate review - it defines exactly which
    # failures the caller is responsible for contextualizing.
    from exam_generator.generation import GenerationError
    from exam_generator.llm import LLMError
    from exam_generator.prompts import PromptError
    from exam_generator.retrieval import RetrievalError
    from exam_generator.validation import GroundingValidationError, TextbookValidationError
    from pydantic import ValidationError as PydanticValidationError

    assert set(SYSTEM_LEVEL_ERROR_TYPES) == {
        LLMError,
        GenerationError,
        GroundingValidationError,
        TextbookValidationError,
        RetrievalError,
        PromptError,
        PydanticValidationError,
    }


# ---------------------------------------------------------------------------
# CategoryGenerationService: duplicate replacement (WP-014, moved here by
# WP-032 - now scoped to request.existing_questions rather than an
# exam-wide set)
# ---------------------------------------------------------------------------


def test_exact_duplicate_of_an_existing_question_is_replaced():
    unique_candidate = _candidate(question="שאלה שונה לגמרי")
    producer = _producer(
        side_effect=[_production_result(_candidate(question=QUESTION_TEXT)), _production_result(unique_candidate)]
    )
    service = _make_service(producer=producer, max_duplicate_replacement_attempts=2)
    response = service.generate_next(_request(existing_questions=(_candidate(question=QUESTION_TEXT),)))
    assert response.accepted is True
    assert response.question == unique_candidate
    assert response.duplicate_replacement_attempts == 1


def test_normalized_whitespace_case_duplicate_is_detected():
    padded_variant = _candidate(question="  medulla   oblongata   תפקוד  ")
    unique = _candidate(question="שאלה שונה")
    producer = _producer(side_effect=[_production_result(padded_variant), _production_result(unique)])
    service = _make_service(producer=producer, max_duplicate_replacement_attempts=2)
    response = service.generate_next(
        _request(existing_questions=(_candidate(question="Medulla Oblongata תפקוד"),))
    )
    assert response.accepted is True
    assert response.question == unique


def test_duplicate_replacement_reuses_category_and_mode():
    producer = _producer(
        side_effect=[
            _production_result(_candidate(question=QUESTION_TEXT)),
            _production_result(_candidate(question="שאלה ייחודית")),
        ]
    )
    service = _make_service(producer=producer, max_duplicate_replacement_attempts=2)
    service.generate_next(
        _request(
            category=CATEGORY_A,
            generation_mode=GenerationMode.INDEPENDENT,
            existing_questions=(_candidate(question=QUESTION_TEXT),),
        )
    )
    calls = producer.produce_question.call_args_list
    assert calls[0].kwargs["category"] == calls[1].kwargs["category"] == CATEGORY_A
    assert calls[0].kwargs["generation_mode"] == calls[1].kwargs["generation_mode"] == GenerationMode.INDEPENDENT


def test_duplicate_replacement_exhaustion_is_a_question_local_failure_response():
    producer = _producer(return_value=_production_result(_candidate(question=QUESTION_TEXT)))
    service = _make_service(producer=producer, max_duplicate_replacement_attempts=2)
    response = service.generate_next(_request(existing_questions=(_candidate(question=QUESTION_TEXT),)))
    assert response.accepted is False
    assert response.failure_type == "DuplicateReplacementExhausted"
    # 1 initial attempt + 2 bounded replacement attempts, all duplicates.
    assert producer.produce_question.call_count == 3
    assert response.duplicate_replacement_attempts == 3
    assert len(response.duplicate_productions) == 3


def test_no_existing_questions_means_no_duplicate_rejection_possible():
    candidate = _candidate(question=QUESTION_TEXT)
    producer = _producer(return_value=_production_result(candidate))
    service = _make_service(producer=producer)
    response = service.generate_next(_request(existing_questions=()))
    assert response.accepted is True
    assert producer.produce_question.call_count == 1


def test_no_semantic_or_llm_duplicate_detector_introduced():
    source = inspect.getsource(service_module)
    assert "generate_structured" not in source
    assert "embed" not in source.lower()


# ---------------------------------------------------------------------------
# WP-034: coverage extraction is wired from request.existing_questions into
# plan_targets()
# ---------------------------------------------------------------------------


def test_coverage_extracted_from_existing_questions_reaches_the_planner():
    existing = _candidate(question="שאלה קודמת", answers=["א", "ב", "ג", "ד"], correct_answer=3)
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
