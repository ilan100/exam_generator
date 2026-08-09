from unittest.mock import MagicMock

import pytest

from exam_generator.category_generation import CategoryQuestionSetResponse, CategoryQuestionSetService
from exam_generator.llm import LLMProviderError
from exam_generator.models import (
    CandidateQuestion,
    CategoryValidationResult,
    ExamGenerationStatus,
    ExamRequest,
    GenerationMode,
    GroundingValidationResult,
    MCQValidationResult,
    QualityValidationResult,
    TextbookCheckResult,
    TextbookCheckStatus,
    candidate_to_exam_question,
)
from exam_generator.orchestration import ExamOrchestrator, QuestionProductionFailedError, build_exam_plan
from exam_generator.production import CandidateValidationResults, QuestionAttempt, QuestionProductionResult
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


def _accepted_response(candidate: CandidateQuestion, *, duplicate_replacement_attempts: int = 0):
    return CategoryQuestionSetResponse(
        accepted=True,
        question=candidate_to_exam_question(candidate),
        production=_production_result(candidate),
        duplicate_replacement_attempts=duplicate_replacement_attempts,
    )


def _failed_response(
    *,
    failure_type: str = "QuestionAttemptsExhaustedError",
    failure_message: str = "exhausted",
    failure_attempts: tuple = (),
):
    return CategoryQuestionSetResponse(
        accepted=False, failure_type=failure_type, failure_message=failure_message, failure_attempts=failure_attempts
    )


def _identity_resolver() -> MagicMock:
    """A resolver stub where every requested category name is already
    canonical (no aliasing) - used by tests that are not exercising
    WP-006's own alias-resolution logic."""
    mock = MagicMock(spec=CategoryResolver)
    mock.resolve.side_effect = lambda category: category
    return mock


def _service(*, return_value=None, side_effect=None) -> MagicMock:
    mock = MagicMock(spec=CategoryQuestionSetService)
    if side_effect is not None:
        mock.generate_next.side_effect = side_effect
    else:
        mock.generate_next.return_value = return_value or _accepted_response(_candidate())
    return mock


def _make_orchestrator(*, resolver=None, service=None) -> ExamOrchestrator:
    return ExamOrchestrator(
        category_resolver=resolver or _identity_resolver(),
        category_question_set_service=service or _service(),
    )


# ---------------------------------------------------------------------------
# Planning (build_exam_plan - unchanged by WP-032)
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
# Orchestration: delegation to CategoryQuestionSetService (WP-032/WP-033)
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
    service = _service(side_effect=[_accepted_response(c) for c in candidates])
    orchestrator = _make_orchestrator(resolver=resolver, service=service)
    result = orchestrator.generate_exam(ExamRequest(categories={CATEGORY_A: 3, CATEGORY_B: 2}))
    assert len(result.exam.questions) == 5
    category_counts = {}
    for record in result.productions:
        category_counts[record.planned.category] = category_counts.get(record.planned.category, 0) + 1
    assert category_counts == {CATEGORY_A: 3, CATEGORY_B: 2}


def test_service_receives_correct_category_and_generation_mode():
    candidates = [_candidate(question=f"שאלה {i}") for i in range(3)]
    service = _service(side_effect=[_accepted_response(c) for c in candidates])
    orchestrator = _make_orchestrator(service=service)
    orchestrator.generate_exam(ExamRequest(categories={CATEGORY_A: 3}))
    calls = service.generate_next.call_args_list
    requests = [c.args[0] for c in calls]
    assert [r.category for r in requests] == [CATEGORY_A, CATEGORY_A, CATEGORY_A]
    assert [r.generation_mode for r in requests] == [
        GenerationMode.STYLE_SIMILAR,
        GenerationMode.INDEPENDENT,
        GenerationMode.STYLE_SIMILAR,
    ]


def test_existing_questions_accumulate_within_category_across_calls():
    # WP-033: the orchestrator threads every question already accepted for
    # a category so far (as ExamQuestion - the production schema, number
    # still None at this point) into the next CategoryQuestionSetRequest
    # for that same category - and never leaks across a different category.
    candidates_a = [_candidate(question=f"שאלה א {i}", category=CATEGORY_A) for i in range(2)]
    candidates_b = [_candidate(question=f"שאלה ב {i}", category=CATEGORY_B) for i in range(2)]
    resolver = CategoryResolver([CATEGORY_A, CATEGORY_B], {})
    service = _service(side_effect=[_accepted_response(c) for c in (*candidates_a, *candidates_b)])
    orchestrator = _make_orchestrator(resolver=resolver, service=service)
    orchestrator.generate_exam(ExamRequest(categories={CATEGORY_A: 2, CATEGORY_B: 2}))
    requests = [c.args[0] for c in service.generate_next.call_args_list]
    assert requests[0].existing_questions == ()
    assert requests[1].existing_questions == (candidate_to_exam_question(candidates_a[0]),)
    assert requests[2].existing_questions == ()
    assert requests[3].existing_questions == (candidate_to_exam_question(candidates_b[0]),)


def test_established_candidate_to_exam_conversion_is_used():
    candidate = _candidate(answers=["1", "2", "3", "4"], correct_answer=3)
    service = _service(return_value=_accepted_response(candidate))
    orchestrator = _make_orchestrator(service=service)
    result = orchestrator.generate_exam(ExamRequest(categories={CATEGORY_A: 1}))
    question = result.exam.questions[0]
    assert question.number == 1
    assert (question.answer1, question.answer2, question.answer3, question.answer4) == ("1", "2", "3", "4")
    assert question.correct_answer == 3
    assert question.category == candidate.category


def test_final_exam_ordering_follows_plan_order():
    candidates = [_candidate(question=f"שאלה {i}") for i in range(4)]
    service = _service(side_effect=[_accepted_response(c) for c in candidates])
    orchestrator = _make_orchestrator(service=service)
    result = orchestrator.generate_exam(ExamRequest(categories={CATEGORY_A: 4}))
    assert [q.question for q in result.exam.questions] == [f"שאלה {i}" for i in range(4)]
    assert [q.number for q in result.exam.questions] == [1, 2, 3, 4]


def test_clean_exam_does_not_expose_internal_validation_metadata():
    orchestrator = _make_orchestrator()
    result = orchestrator.generate_exam(ExamRequest(categories={CATEGORY_A: 1}))
    assert "grounding" not in type(result.exam.questions[0]).model_fields
    assert "generation_mode" not in type(result.exam.questions[0]).model_fields


def test_duplicate_replacement_attempts_recorded_from_service_response():
    service = _service(return_value=_accepted_response(_candidate(), duplicate_replacement_attempts=2))
    orchestrator = _make_orchestrator(service=service)
    result = orchestrator.generate_exam(ExamRequest(categories={CATEGORY_A: 1}))
    assert result.productions[0].duplicate_replacement_attempts == 2


# ---------------------------------------------------------------------------
# Question-local failures (WP-023): recorded as FailedPlannedQuestion,
# orchestration continues rather than aborting the whole run. Since
# WP-032, classifying and catching the underlying exception is
# CategoryQuestionSetService's job (see test_category_question_set.py) - the
# orchestrator only ever sees the resulting accepted=False response.
# ---------------------------------------------------------------------------


def test_question_local_failure_response_yields_partial_result():
    service = _service(return_value=_failed_response(failure_type="QuestionAttemptsExhaustedError"))
    orchestrator = _make_orchestrator(service=service)
    result = orchestrator.generate_exam(ExamRequest(categories={CATEGORY_A: 1}))
    assert result.status == ExamGenerationStatus.PARTIAL
    assert result.exam is None
    assert len(result.failed_questions) == 1
    assert result.failed_questions[0].failure_type == "QuestionAttemptsExhaustedError"


def test_failed_question_identifies_planned_question_category_and_mode():
    service = _service(return_value=_failed_response())
    orchestrator = _make_orchestrator(service=service)
    result = orchestrator.generate_exam(ExamRequest(categories={CATEGORY_A: 1}))
    failed = result.failed_questions[0]
    assert failed.planned.category == CATEGORY_A
    assert failed.planned.generation_mode == GenerationMode.STYLE_SIMILAR
    assert failed.planned.position == 1


def test_failed_question_preserves_attempts_from_service_response():
    sentinel_attempts = (
        QuestionAttempt(
            attempt_number=1,
            candidate=_candidate(),
            validations=_production_result(_candidate()).attempts[0].validations,
        ),
    )
    service = _service(return_value=_failed_response(failure_attempts=sentinel_attempts))
    orchestrator = _make_orchestrator(service=service)
    result = orchestrator.generate_exam(ExamRequest(categories={CATEGORY_A: 1}))
    assert result.failed_questions[0].attempts == sentinel_attempts


def test_orchestration_continues_past_a_question_local_failure_to_later_questions():
    good_candidate = _candidate(question="שאלה טובה")
    service = _service(side_effect=[_failed_response(), _accepted_response(good_candidate)])
    orchestrator = _make_orchestrator(service=service)
    result = orchestrator.generate_exam(ExamRequest(categories={CATEGORY_A: 2}))
    assert result.status == ExamGenerationStatus.PARTIAL
    assert len(result.failed_questions) == 1
    assert result.failed_questions[0].planned.position == 1
    assert len(result.productions) == 1
    assert result.productions[0].planned.position == 2
    assert result.exam is not None
    # Accepted questions are renumbered contiguously 1..N, not gap-preserving.
    assert result.exam.questions[0].number == 1


def test_middle_failure_leaves_no_gap_in_final_exam_numbering():
    # WP-023 section 15 worked example: planned 1(ok)/2(fails)/3(ok)/4(ok)
    # must renumber the clean exam 1,2,3 - not 1,3,4 - while each
    # production's original planned position is separately preserved.
    candidates = [_candidate(question=f"שאלה {i}") for i in range(3)]
    service = _service(
        side_effect=[
            _accepted_response(candidates[0]),
            _failed_response(),
            _accepted_response(candidates[1]),
            _accepted_response(candidates[2]),
        ]
    )
    orchestrator = _make_orchestrator(service=service)
    result = orchestrator.generate_exam(ExamRequest(categories={CATEGORY_A: 4}))
    assert result.status == ExamGenerationStatus.PARTIAL
    assert [q.number for q in result.exam.questions] == [1, 2, 3]
    assert [r.planned.position for r in result.productions] == [1, 3, 4]
    assert result.failed_questions[0].planned.position == 2


def test_completed_productions_preserved_alongside_a_later_question_local_failure():
    good_candidate = _candidate(question="שאלה טובה")
    service = _service(side_effect=[_accepted_response(good_candidate), _failed_response()])
    orchestrator = _make_orchestrator(service=service)
    result = orchestrator.generate_exam(ExamRequest(categories={CATEGORY_A: 2}))
    assert result.status == ExamGenerationStatus.PARTIAL
    assert len(result.productions) == 1
    assert result.productions[0].production.candidate == good_candidate
    assert len(result.failed_questions) == 1
    assert result.failed_questions[0].planned.position == 2


def test_all_planned_questions_failing_yields_partial_with_no_exam():
    service = _service(return_value=_failed_response())
    orchestrator = _make_orchestrator(service=service)
    result = orchestrator.generate_exam(ExamRequest(categories={CATEGORY_A: 2}))
    assert result.status == ExamGenerationStatus.PARTIAL
    assert result.exam is None
    assert len(result.productions) == 0
    assert len(result.failed_questions) == 2


def test_all_accepted_yields_complete_status_and_no_failed_questions():
    orchestrator = _make_orchestrator()
    result = orchestrator.generate_exam(ExamRequest(categories={CATEGORY_A: 1}))
    assert result.status == ExamGenerationStatus.COMPLETE
    assert result.failed_questions == ()


def test_shortfall_in_one_category_does_not_affect_another_category():
    resolver = CategoryResolver([CATEGORY_A, CATEGORY_B], {})
    candidates_b = [_candidate(question=f"שאלה ב {i}", category=CATEGORY_B) for i in range(2)]

    def side_effect(request):
        if request.category == CATEGORY_A:
            return _failed_response(failure_type="InsufficientDistinctTargetsError")
        return _accepted_response(candidates_b.pop(0))

    service = _service(side_effect=side_effect)
    orchestrator = _make_orchestrator(resolver=resolver, service=service)
    result = orchestrator.generate_exam(ExamRequest(categories={CATEGORY_A: 2, CATEGORY_B: 2}))
    assert result.status == ExamGenerationStatus.PARTIAL
    assert len(result.failed_questions) == 2
    assert all(f.planned.category == CATEGORY_A for f in result.failed_questions)
    assert len(result.productions) == 2
    assert all(r.planned.category == CATEGORY_B for r in result.productions)


# ---------------------------------------------------------------------------
# System-level failures (WP-023): still abort the whole run immediately.
# Since WP-032, these propagate uncaught from
# ``CategoryQuestionSetService.generate_next()`` - the orchestrator's own
# job is only to catch and contextualize them.
# ---------------------------------------------------------------------------


def test_operational_failure_after_completed_questions_preserves_context():
    # A system-level failure's context (position/category/mode/completed
    # count/cause) must be preserved even when it occurs after one or more
    # questions were already successfully completed.
    good_candidate = _candidate(question="שאלה טובה")
    service = _service(side_effect=[_accepted_response(good_candidate), LLMProviderError("connection failed")])
    orchestrator = _make_orchestrator(service=service)
    with pytest.raises(QuestionProductionFailedError) as excinfo:
        orchestrator.generate_exam(ExamRequest(categories={CATEGORY_A: 2}))
    assert isinstance(excinfo.value.operational_cause, LLMProviderError)
    assert len(excinfo.value.completed_productions) == 1
    assert excinfo.value.completed_productions[0].production.candidate == good_candidate
    assert excinfo.value.planned_question.position == 2
    assert excinfo.value.planned_question.category == CATEGORY_A


def test_system_level_failure_propagates_immediately():
    # No retry occurs at the orchestrator level (the service is called
    # exactly once), and the failure is contextualized
    # (QuestionProductionFailedError) rather than the raw
    # LLMProviderError propagating unwrapped - the original cause remains
    # inspectable via .operational_cause and exception chaining.
    service = _service(side_effect=LLMProviderError("connection failed"))
    orchestrator = _make_orchestrator(service=service)
    with pytest.raises(QuestionProductionFailedError) as excinfo:
        orchestrator.generate_exam(ExamRequest(categories={CATEGORY_A: 1}))
    assert isinstance(excinfo.value.operational_cause, LLMProviderError)
    assert isinstance(excinfo.value.__cause__, LLMProviderError)
    assert service.generate_next.call_count == 1


def test_unexpected_exception_propagates_uncaught():
    service = _service(side_effect=RuntimeError("genuinely unexpected"))
    orchestrator = _make_orchestrator(service=service)
    with pytest.raises(RuntimeError):
        orchestrator.generate_exam(ExamRequest(categories={CATEGORY_A: 1}))


def test_failure_in_second_category_preserves_first_categorys_completed_context():
    resolver = CategoryResolver([CATEGORY_A, CATEGORY_B], {})
    service = _service(
        side_effect=[_accepted_response(_candidate(category=CATEGORY_A)), LLMProviderError("connection failed")]
    )
    orchestrator = _make_orchestrator(resolver=resolver, service=service)
    with pytest.raises(QuestionProductionFailedError) as excinfo:
        orchestrator.generate_exam(ExamRequest(categories={CATEGORY_A: 1, CATEGORY_B: 1}))
    assert len(excinfo.value.completed_productions) == 1
    assert excinfo.value.planned_question.category == CATEGORY_B


# ---------------------------------------------------------------------------
# History
# ---------------------------------------------------------------------------


def test_production_history_retained_for_every_accepted_question():
    candidates = [_candidate(question=f"שאלה {i}") for i in range(3)]
    service = _service(side_effect=[_accepted_response(c) for c in candidates])
    orchestrator = _make_orchestrator(service=service)
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
