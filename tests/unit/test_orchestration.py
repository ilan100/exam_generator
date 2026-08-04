import inspect
from unittest.mock import MagicMock

import pytest

from exam_generator.llm import LLMProviderError
from exam_generator.models import (
    CandidateQuestion,
    CategoryValidationResult,
    ExamRequest,
    GenerationMode,
    GroundingValidationResult,
    MCQValidationResult,
    QualityValidationResult,
    TextbookCheckResult,
    TextbookCheckStatus,
)
from exam_generator.orchestration import (
    ExamOrchestrator,
    InvalidOrchestrationConfigurationError,
    PlannedQuestion,
    QuestionProductionFailedError,
    build_exam_plan,
)
import exam_generator.orchestration.orchestrator as orchestrator_module
from exam_generator.production import (
    CandidateValidationResults,
    QuestionAttempt,
    QuestionAttemptsExhaustedError,
    QuestionProducer,
    QuestionProductionResult,
)
from exam_generator.retrieval import CategoryResolver, resolve_exam_request_categories

CATEGORY_A = "קליפת המוח"
CATEGORY_B = "גזע המוח"
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
    """A resolver stub where every requested category name is already
    canonical (no aliasing) - used by tests that are not exercising
    WP-006's own alias-resolution logic."""
    mock = MagicMock(spec=CategoryResolver)
    mock.resolve.side_effect = lambda category: category
    return mock


def _producer(*, return_value=None, side_effect=None) -> MagicMock:
    mock = MagicMock(spec=QuestionProducer)
    if side_effect is not None:
        mock.produce_question.side_effect = side_effect
    else:
        mock.produce_question.return_value = return_value or _production_result(_candidate())
    return mock


def _make_orchestrator(*, resolver=None, producer=None, max_duplicate_replacement_attempts=2) -> ExamOrchestrator:
    return ExamOrchestrator(
        category_resolver=resolver or _identity_resolver(),
        producer=producer or _producer(),
        max_duplicate_replacement_attempts=max_duplicate_replacement_attempts,
    )


# ---------------------------------------------------------------------------
# Planning
# ---------------------------------------------------------------------------


def test_plan_preserves_total_requested_count():
    request = ExamRequest(categories={CATEGORY_A: 3, CATEGORY_B: 2})
    plan = build_exam_plan(request)
    assert len(plan) == 5


def test_plan_alternates_modes_starting_style_similar_within_each_category():
    request = ExamRequest(categories={CATEGORY_A: 3, CATEGORY_B: 2})
    plan = build_exam_plan(request)
    category_a_modes = [p.generation_mode for p in plan if p.category == CATEGORY_A]
    category_b_modes = [p.generation_mode for p in plan if p.category == CATEGORY_B]
    assert category_a_modes == [
        GenerationMode.STYLE_SIMILAR,
        GenerationMode.INDEPENDENT,
        GenerationMode.STYLE_SIMILAR,
    ]
    assert category_b_modes == [GenerationMode.STYLE_SIMILAR, GenerationMode.INDEPENDENT]


def test_plan_positions_are_globally_contiguous_one_based():
    request = ExamRequest(categories={CATEGORY_A: 3, CATEGORY_B: 2})
    plan = build_exam_plan(request)
    assert [p.position for p in plan] == [1, 2, 3, 4, 5]


def test_plan_is_deterministic_for_identical_input():
    request = ExamRequest(categories={CATEGORY_A: 3, CATEGORY_B: 2})
    plan1 = build_exam_plan(request)
    plan2 = build_exam_plan(request)
    assert plan1 == plan2


def test_aliases_combine_counts_before_planning():
    resolver = CategoryResolver([CATEGORY_A], {"כינוי": CATEGORY_A})
    request = ExamRequest(categories={CATEGORY_A: 2, "כינוי": 1})
    resolved = resolve_exam_request_categories(request, resolver)
    plan = build_exam_plan(resolved)
    assert len(plan) == 3
    assert all(p.category == CATEGORY_A for p in plan)


# ---------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------


def test_one_requested_question_produces_one_clean_question():
    orchestrator = _make_orchestrator()
    result = orchestrator.generate_exam(ExamRequest(categories={CATEGORY_A: 1}))
    assert len(result.exam.questions) == 1
    assert result.exam.questions[0].question == QUESTION_TEXT


def test_multiple_categories_counts_produce_exact_requested_distribution():
    resolver = CategoryResolver([CATEGORY_A, CATEGORY_B], {})
    candidates = [_candidate(question=f"שאלה {i}", category=CATEGORY_A) for i in range(3)] + [
        _candidate(question=f"שאלה ב {i}", category=CATEGORY_B) for i in range(2)
    ]
    producer = _producer(side_effect=[_production_result(c) for c in candidates])
    orchestrator = _make_orchestrator(resolver=resolver, producer=producer)
    result = orchestrator.generate_exam(ExamRequest(categories={CATEGORY_A: 3, CATEGORY_B: 2}))
    assert len(result.exam.questions) == 5
    category_counts = {}
    for record in result.productions:
        category_counts[record.planned.category] = category_counts.get(record.planned.category, 0) + 1
    assert category_counts == {CATEGORY_A: 3, CATEGORY_B: 2}


def test_producer_receives_correct_category_and_generation_mode():
    candidates = [_candidate(question=f"שאלה {i}") for i in range(3)]
    producer = _producer(side_effect=[_production_result(c) for c in candidates])
    orchestrator = _make_orchestrator(producer=producer)
    orchestrator.generate_exam(ExamRequest(categories={CATEGORY_A: 3}))
    calls = producer.produce_question.call_args_list
    assert [c.kwargs["category"] for c in calls] == [CATEGORY_A, CATEGORY_A, CATEGORY_A]
    assert [c.kwargs["generation_mode"] for c in calls] == [
        GenerationMode.STYLE_SIMILAR,
        GenerationMode.INDEPENDENT,
        GenerationMode.STYLE_SIMILAR,
    ]


def test_established_candidate_to_exam_conversion_is_used():
    candidate = _candidate(answers=["1", "2", "3", "4"], correct_answer=3)
    producer = _producer(return_value=_production_result(candidate))
    orchestrator = _make_orchestrator(producer=producer)
    result = orchestrator.generate_exam(ExamRequest(categories={CATEGORY_A: 1}))
    question = result.exam.questions[0]
    assert question.number == 1
    assert (question.answer1, question.answer2, question.answer3, question.answer4) == ("1", "2", "3", "4")
    assert question.correct_answer == 3
    assert question.category == candidate.category


def test_final_exam_ordering_follows_plan_order():
    candidates = [_candidate(question=f"שאלה {i}") for i in range(4)]
    producer = _producer(side_effect=[_production_result(c) for c in candidates])
    orchestrator = _make_orchestrator(producer=producer)
    result = orchestrator.generate_exam(ExamRequest(categories={CATEGORY_A: 4}))
    assert [q.question for q in result.exam.questions] == [f"שאלה {i}" for i in range(4)]
    assert [q.number for q in result.exam.questions] == [1, 2, 3, 4]


def test_clean_exam_does_not_expose_internal_validation_metadata():
    orchestrator = _make_orchestrator()
    result = orchestrator.generate_exam(ExamRequest(categories={CATEGORY_A: 1}))
    assert "grounding" not in type(result.exam.questions[0]).model_fields
    assert "generation_mode" not in type(result.exam.questions[0]).model_fields


# ---------------------------------------------------------------------------
# Failure
# ---------------------------------------------------------------------------


def test_per_question_attempt_exhaustion_fails_exam_generation():
    producer = _producer(side_effect=QuestionAttemptsExhaustedError("exhausted", attempts=()))
    orchestrator = _make_orchestrator(producer=producer)
    with pytest.raises(QuestionProductionFailedError):
        orchestrator.generate_exam(ExamRequest(categories={CATEGORY_A: 1}))


def test_partial_exam_is_not_returned_on_failure():
    producer = _producer(side_effect=QuestionAttemptsExhaustedError("exhausted", attempts=()))
    orchestrator = _make_orchestrator(producer=producer)
    with pytest.raises(QuestionProductionFailedError):
        result = orchestrator.generate_exam(ExamRequest(categories={CATEGORY_A: 1}))
        assert result is None  # unreachable - documents intent


def test_failure_identifies_planned_question_category_and_mode():
    producer = _producer(side_effect=QuestionAttemptsExhaustedError("exhausted", attempts=()))
    orchestrator = _make_orchestrator(producer=producer)
    with pytest.raises(QuestionProductionFailedError) as excinfo:
        orchestrator.generate_exam(ExamRequest(categories={CATEGORY_A: 1}))
    assert excinfo.value.planned_question.category == CATEGORY_A
    assert excinfo.value.planned_question.generation_mode == GenerationMode.STYLE_SIMILAR
    assert excinfo.value.planned_question.position == 1


def test_exhaustion_preserves_attempts_exhausted_context():
    sentinel_attempts = (
        QuestionAttempt(
            attempt_number=1,
            candidate=_candidate(),
            validations=_production_result(_candidate()).attempts[0].validations,
        ),
    )
    producer = _producer(side_effect=QuestionAttemptsExhaustedError("exhausted", attempts=sentinel_attempts))
    orchestrator = _make_orchestrator(producer=producer)
    with pytest.raises(QuestionProductionFailedError) as excinfo:
        orchestrator.generate_exam(ExamRequest(categories={CATEGORY_A: 1}))
    assert excinfo.value.attempts_exhausted == sentinel_attempts
    assert excinfo.value.duplicate_productions == ()


def test_completed_productions_preserved_before_a_later_failure():
    good_candidate = _candidate(question="שאלה טובה")
    producer = _producer(
        side_effect=[_production_result(good_candidate), QuestionAttemptsExhaustedError("exhausted", attempts=())]
    )
    orchestrator = _make_orchestrator(producer=producer)
    with pytest.raises(QuestionProductionFailedError) as excinfo:
        orchestrator.generate_exam(ExamRequest(categories={CATEGORY_A: 2}))
    assert len(excinfo.value.completed_productions) == 1
    assert excinfo.value.completed_productions[0].production.candidate == good_candidate


def test_operational_failure_propagates_immediately():
    producer = _producer(side_effect=LLMProviderError("connection failed"))
    orchestrator = _make_orchestrator(producer=producer)
    with pytest.raises(LLMProviderError):
        orchestrator.generate_exam(ExamRequest(categories={CATEGORY_A: 1}))


# ---------------------------------------------------------------------------
# Duplicate protection
# ---------------------------------------------------------------------------


def test_exact_duplicate_accepted_question_is_rejected_and_replaced():
    duplicate_candidate = _candidate(question=QUESTION_TEXT)
    unique_candidate = _candidate(question="שאלה שונה לגמרי")
    producer = _producer(
        side_effect=[
            _production_result(_candidate(question=QUESTION_TEXT)),
            _production_result(duplicate_candidate),
            _production_result(unique_candidate),
        ]
    )
    orchestrator = _make_orchestrator(producer=producer, max_duplicate_replacement_attempts=2)
    result = orchestrator.generate_exam(ExamRequest(categories={CATEGORY_A: 2}))
    questions = [q.question for q in result.exam.questions]
    assert questions == [QUESTION_TEXT, "שאלה שונה לגמרי"]
    assert producer.produce_question.call_count == 3


def test_normalized_whitespace_case_duplicate_is_detected():
    original = _candidate(question="Medulla Oblongata תפקוד")
    padded_variant = _candidate(question="  medulla   oblongata   תפקוד  ")
    unique = _candidate(question="שאלה שונה")
    producer = _producer(side_effect=[_production_result(original), _production_result(padded_variant), _production_result(unique)])
    orchestrator = _make_orchestrator(producer=producer, max_duplicate_replacement_attempts=2)
    result = orchestrator.generate_exam(ExamRequest(categories={CATEGORY_A: 2}))
    assert [q.question for q in result.exam.questions] == ["Medulla Oblongata תפקוד", "שאלה שונה"]


def test_replacement_production_requested_for_same_category_and_mode():
    duplicate_candidate = _candidate(question=QUESTION_TEXT, category=CATEGORY_A)
    producer = _producer(
        side_effect=[
            _production_result(_candidate(question=QUESTION_TEXT)),
            _production_result(duplicate_candidate),
            _production_result(_candidate(question="שאלה ייחודית")),
        ]
    )
    orchestrator = _make_orchestrator(producer=producer, max_duplicate_replacement_attempts=2)
    orchestrator.generate_exam(ExamRequest(categories={CATEGORY_A: 2}))
    calls = producer.produce_question.call_args_list
    # First call is for planned position 1; the next two both retry planned
    # position 2 (same category/mode) after the duplicate.
    assert calls[1].kwargs["category"] == calls[2].kwargs["category"] == CATEGORY_A
    assert calls[1].kwargs["generation_mode"] == calls[2].kwargs["generation_mode"]


def test_unique_replacement_is_accepted_and_records_replacement_count():
    duplicate_candidate = _candidate(question=QUESTION_TEXT)
    unique_candidate = _candidate(question="שאלה ייחודית")
    producer = _producer(
        side_effect=[
            _production_result(_candidate(question=QUESTION_TEXT)),
            _production_result(duplicate_candidate),
            _production_result(unique_candidate),
        ]
    )
    orchestrator = _make_orchestrator(producer=producer, max_duplicate_replacement_attempts=2)
    result = orchestrator.generate_exam(ExamRequest(categories={CATEGORY_A: 2}))
    assert result.productions[1].duplicate_replacement_attempts == 1
    assert result.productions[1].production.candidate == unique_candidate


def test_duplicate_replacement_is_bounded():
    producer = _producer(
        side_effect=[
            _production_result(_candidate(question=QUESTION_TEXT)),
            *[_production_result(_candidate(question=QUESTION_TEXT)) for _ in range(3)],
        ]
    )
    orchestrator = _make_orchestrator(producer=producer, max_duplicate_replacement_attempts=2)
    with pytest.raises(QuestionProductionFailedError):
        orchestrator.generate_exam(ExamRequest(categories={CATEGORY_A: 2}))
    # 1 call for the first accepted question + 1 initial + 2 bounded replacement attempts for the second
    assert producer.produce_question.call_count == 1 + 1 + 2


def test_duplicate_exhaustion_fails_clearly_with_duplicate_context():
    producer = _producer(
        side_effect=[
            _production_result(_candidate(question=QUESTION_TEXT)),
            *[_production_result(_candidate(question=QUESTION_TEXT)) for _ in range(2)],
        ]
    )
    orchestrator = _make_orchestrator(producer=producer, max_duplicate_replacement_attempts=1)
    with pytest.raises(QuestionProductionFailedError) as excinfo:
        orchestrator.generate_exam(ExamRequest(categories={CATEGORY_A: 2}))
    assert len(excinfo.value.duplicate_productions) == 2
    assert excinfo.value.attempts_exhausted is None


def test_no_semantic_or_llm_duplicate_detector_introduced():
    source = inspect.getsource(orchestrator_module)
    assert "generate_structured" not in source
    assert "embed" not in source.lower()


# ---------------------------------------------------------------------------
# History
# ---------------------------------------------------------------------------


def test_production_history_retained_for_every_accepted_question():
    candidates = [_candidate(question=f"שאלה {i}") for i in range(3)]
    producer = _producer(side_effect=[_production_result(c) for c in candidates])
    orchestrator = _make_orchestrator(producer=producer)
    result = orchestrator.generate_exam(ExamRequest(categories={CATEGORY_A: 3}))
    assert len(result.productions) == 3
    for record, candidate in zip(result.productions, candidates):
        assert record.production.candidate == candidate
        assert len(record.production.attempts) == 1


def test_plan_retained_on_result():
    orchestrator = _make_orchestrator()
    result = orchestrator.generate_exam(ExamRequest(categories={CATEGORY_A: 1}))
    assert len(result.plan) == 1
    assert result.plan[0].category == CATEGORY_A


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------


def test_invalid_max_duplicate_replacement_attempts_is_rejected():
    with pytest.raises(InvalidOrchestrationConfigurationError):
        _make_orchestrator(max_duplicate_replacement_attempts=0)


def test_negative_max_duplicate_replacement_attempts_is_rejected():
    with pytest.raises(InvalidOrchestrationConfigurationError):
        _make_orchestrator(max_duplicate_replacement_attempts=-1)
