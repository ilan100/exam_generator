import inspect
from unittest.mock import MagicMock

import pytest

from exam_generator.generation import InvalidGeneratedOutputError, QuestionGenerator
from exam_generator.llm import LLMAuthenticationError, LLMProviderError, LLMRateLimitError
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
    InvalidProductionConfigurationError,
    QuestionAttempt,
    QuestionAttemptsExhaustedError,
    QuestionProducer,
)
import exam_generator.production.producer as producer_module
from exam_generator.validation import CategoryValidator, GroundingValidator, MCQValidator, QualityValidator, TextbookValidator

CATEGORY = "קליפת המוח"
QUESTION_TEXT = "מהו תפקידה העיקרי של קליפת המוח?"


# ---------------------------------------------------------------------------
# Fixture helpers
# ---------------------------------------------------------------------------


def _candidate(**kwargs) -> CandidateQuestion:
    defaults = dict(
        question=QUESTION_TEXT,
        answers=["תשובה א", "תשובה ב", "תשובה ג", "תשובה ד"],
        correct_answer=2,
        category=CATEGORY,
        generation_mode=GenerationMode.INDEPENDENT,
    )
    defaults.update(kwargs)
    return CandidateQuestion(**defaults)


def _target(**kwargs) -> QuestionTarget:
    defaults = dict(
        target_id=1,
        category=CATEGORY,
        topic="topic",
        factual_focus="factual focus",
    )
    defaults.update(kwargs)
    return QuestionTarget(**defaults)


def _grounding_result(passed: bool = True, **kwargs) -> GroundingValidationResult:
    defaults = dict(
        grounded=passed,
        correct_answer_supported=passed,
        other_answers_not_equally_correct=passed,
        evidence_chunk_ids=[],
        reason="stub",
        confidence=0.9,
    )
    defaults.update(kwargs)
    return GroundingValidationResult(**defaults)


def _mcq_result(valid: bool = True, **kwargs) -> MCQValidationResult:
    defaults = dict(valid=valid, exactly_four_answers=True, single_best_answer=valid, reason="stub")
    defaults.update(kwargs)
    return MCQValidationResult(**defaults)


def _category_result(valid: bool = True, **kwargs) -> CategoryValidationResult:
    defaults = dict(valid=valid, requested_category=CATEGORY, assessed_category=CATEGORY, reason="stub")
    defaults.update(kwargs)
    return CategoryValidationResult(**defaults)


def _quality_result(valid: bool = True, **kwargs) -> QualityValidationResult:
    defaults = dict(valid=valid, reason="stub")
    defaults.update(kwargs)
    return QualityValidationResult(**defaults)


def _textbook_result(status: TextbookCheckStatus = TextbookCheckStatus.CONSISTENT, **kwargs) -> TextbookCheckResult:
    defaults = dict(status=status, source_page=None, reference_text=None, reason="stub")
    defaults.update(kwargs)
    return TextbookCheckResult(**defaults)


def _validations(**overrides) -> CandidateValidationResults:
    defaults = dict(
        grounding=_grounding_result(True),
        mcq=_mcq_result(True),
        category=_category_result(True),
        quality=_quality_result(True),
        textbook=_textbook_result(TextbookCheckStatus.CONSISTENT),
    )
    defaults.update(overrides)
    return CandidateValidationResults(**defaults)


def _passing_generator(candidate: CandidateQuestion | None = None, *, side_effect=None) -> MagicMock:
    mock = MagicMock(spec=QuestionGenerator)
    if side_effect is not None:
        mock.generate_candidate_question.side_effect = side_effect
    else:
        mock.generate_candidate_question.return_value = candidate or _candidate()
    return mock


def _passing_validator(spec, method_name: str, result, *, side_effect=None) -> MagicMock:
    mock = MagicMock(spec=spec)
    method = getattr(mock, method_name)
    if side_effect is not None:
        method.side_effect = side_effect
    else:
        method.return_value = result
    return mock


def _make_producer(
    *,
    generator=None,
    grounding=None,
    mcq=None,
    category=None,
    quality=None,
    textbook=None,
    max_attempts=3,
) -> QuestionProducer:
    return QuestionProducer(
        generator=generator or _passing_generator(),
        grounding_validator=grounding
        or _passing_validator(GroundingValidator, "validate_grounding", _grounding_result(True)),
        mcq_validator=mcq or _passing_validator(MCQValidator, "validate", _mcq_result(True)),
        category_validator=category or _passing_validator(CategoryValidator, "validate", _category_result(True)),
        quality_validator=quality or _passing_validator(QualityValidator, "validate", _quality_result(True)),
        textbook_validator=textbook
        or _passing_validator(TextbookValidator, "validate", _textbook_result(TextbookCheckStatus.CONSISTENT)),
        max_attempts=max_attempts,
    )


# ---------------------------------------------------------------------------
# Acceptance policy (CandidateValidationResults.accepted)
# ---------------------------------------------------------------------------


def test_all_primary_pass_textbook_consistent_is_accepted():
    assert _validations(textbook=_textbook_result(TextbookCheckStatus.CONSISTENT)).accepted is True


def test_all_primary_pass_textbook_not_found_is_accepted():
    assert _validations(textbook=_textbook_result(TextbookCheckStatus.NOT_FOUND)).accepted is True


def test_grounding_failure_is_rejected():
    assert _validations(grounding=_grounding_result(False)).accepted is False


def test_mcq_failure_is_rejected():
    assert _validations(mcq=_mcq_result(False)).accepted is False


def test_category_failure_is_rejected():
    assert _validations(category=_category_result(False)).accepted is False


def test_quality_failure_is_rejected():
    assert _validations(quality=_quality_result(False)).accepted is False


def test_textbook_potential_conflict_is_rejected():
    assert _validations(textbook=_textbook_result(TextbookCheckStatus.POTENTIAL_CONFLICT)).accepted is False


def test_question_attempt_accepted_delegates_to_validations():
    attempt = QuestionAttempt(attempt_number=1, candidate=_candidate(), validations=_validations())
    assert attempt.accepted == attempt.validations.accepted


# ---------------------------------------------------------------------------
# QuestionAttempt: WP-019 generation-contract-failure representation
# ---------------------------------------------------------------------------


def test_question_attempt_generation_failure_is_not_accepted():
    attempt = QuestionAttempt(
        attempt_number=1,
        generation_failure_type="InvalidGeneratedOutputError",
        generation_failure_message="invented evidence id",
    )
    assert attempt.accepted is False
    assert attempt.is_generation_contract_failure is True
    assert attempt.candidate is None
    assert attempt.validations is None


def test_question_attempt_normal_outcome_is_not_a_contract_failure():
    attempt = QuestionAttempt(attempt_number=1, candidate=_candidate(), validations=_validations())
    assert attempt.is_generation_contract_failure is False


def test_question_attempt_cannot_carry_both_candidate_and_failure():
    with pytest.raises(ValueError):
        QuestionAttempt(
            attempt_number=1,
            candidate=_candidate(),
            validations=_validations(),
            generation_failure_type="InvalidGeneratedOutputError",
            generation_failure_message="invented evidence id",
        )


def test_question_attempt_cannot_carry_neither_candidate_nor_failure():
    with pytest.raises(ValueError):
        QuestionAttempt(attempt_number=1)


def test_question_attempt_candidate_without_validations_rejected():
    with pytest.raises(ValueError):
        QuestionAttempt(attempt_number=1, candidate=_candidate())


def test_question_attempt_failure_type_without_message_rejected():
    with pytest.raises(ValueError):
        QuestionAttempt(attempt_number=1, generation_failure_type="InvalidGeneratedOutputError")


# ---------------------------------------------------------------------------
# Attempts
# ---------------------------------------------------------------------------


def test_first_candidate_accepted_makes_exactly_one_generation_attempt():
    generator = _passing_generator()
    producer = _make_producer(generator=generator, max_attempts=3)
    result = producer.produce_question(category=CATEGORY, generation_mode=GenerationMode.INDEPENDENT, target=_target())
    assert generator.generate_candidate_question.call_count == 1
    assert len(result.attempts) == 1
    assert result.attempts[0].accepted is True


def test_first_rejected_second_accepted_makes_exactly_two_attempts():
    candidate1, candidate2 = _candidate(question="שאלה ראשונה"), _candidate(question="שאלה שנייה")
    generator = _passing_generator(side_effect=[candidate1, candidate2])
    grounding = _passing_validator(
        GroundingValidator, "validate_grounding", None, side_effect=[_grounding_result(False), _grounding_result(True)]
    )
    producer = _make_producer(generator=generator, grounding=grounding, max_attempts=3)
    result = producer.produce_question(category=CATEGORY, generation_mode=GenerationMode.INDEPENDENT, target=_target())
    assert generator.generate_candidate_question.call_count == 2
    assert len(result.attempts) == 2
    assert result.attempts[0].accepted is False
    assert result.attempts[1].accepted is True
    assert result.candidate == candidate2


def test_acceptance_stops_further_generation():
    candidate1, candidate2 = _candidate(question="שאלה ראשונה"), _candidate(question="שאלה שנייה")
    generator = _passing_generator(side_effect=[candidate1, candidate2])
    producer = _make_producer(generator=generator, max_attempts=5)
    producer.produce_question(category=CATEGORY, generation_mode=GenerationMode.INDEPENDENT, target=_target())
    assert generator.generate_candidate_question.call_count == 1


def test_attempt_numbering_is_one_based():
    candidate1, candidate2 = _candidate(question="שאלה ראשונה"), _candidate(question="שאלה שנייה")
    generator = _passing_generator(side_effect=[candidate1, candidate2])
    grounding = _passing_validator(
        GroundingValidator, "validate_grounding", None, side_effect=[_grounding_result(False), _grounding_result(True)]
    )
    producer = _make_producer(generator=generator, grounding=grounding, max_attempts=3)
    result = producer.produce_question(category=CATEGORY, generation_mode=GenerationMode.INDEPENDENT, target=_target())
    assert [attempt.attempt_number for attempt in result.attempts] == [1, 2]


def test_failed_candidate_records_are_preserved():
    candidate1, candidate2 = _candidate(question="שאלה ראשונה"), _candidate(question="שאלה שנייה")
    generator = _passing_generator(side_effect=[candidate1, candidate2])
    grounding = _passing_validator(
        GroundingValidator, "validate_grounding", None, side_effect=[_grounding_result(False), _grounding_result(True)]
    )
    producer = _make_producer(generator=generator, grounding=grounding, max_attempts=3)
    result = producer.produce_question(category=CATEGORY, generation_mode=GenerationMode.INDEPENDENT, target=_target())
    assert result.attempts[0].candidate == candidate1
    assert result.attempts[0].accepted is False


def test_validation_results_are_preserved_for_every_completed_attempt():
    candidate1, candidate2 = _candidate(question="שאלה ראשונה"), _candidate(question="שאלה שנייה")
    generator = _passing_generator(side_effect=[candidate1, candidate2])
    failing_grounding = _grounding_result(False, reason="not supported")
    passing_grounding = _grounding_result(True)
    grounding = _passing_validator(
        GroundingValidator, "validate_grounding", None, side_effect=[failing_grounding, passing_grounding]
    )
    producer = _make_producer(generator=generator, grounding=grounding, max_attempts=3)
    result = producer.produce_question(category=CATEGORY, generation_mode=GenerationMode.INDEPENDENT, target=_target())
    assert result.attempts[0].validations.grounding == failing_grounding
    assert result.attempts[1].validations.grounding == passing_grounding


def test_maximum_attempts_is_never_exceeded():
    generator = _passing_generator(side_effect=[_candidate() for _ in range(3)])
    grounding = _passing_validator(GroundingValidator, "validate_grounding", _grounding_result(False))
    producer = _make_producer(generator=generator, grounding=grounding, max_attempts=3)
    with pytest.raises(QuestionAttemptsExhaustedError):
        producer.produce_question(category=CATEGORY, generation_mode=GenerationMode.INDEPENDENT, target=_target())
    assert generator.generate_candidate_question.call_count == 3


def test_all_rejected_raises_exhausted_attempts_error():
    generator = _passing_generator(side_effect=[_candidate() for _ in range(3)])
    grounding = _passing_validator(GroundingValidator, "validate_grounding", _grounding_result(False))
    producer = _make_producer(generator=generator, grounding=grounding, max_attempts=3)
    with pytest.raises(QuestionAttemptsExhaustedError):
        producer.produce_question(category=CATEGORY, generation_mode=GenerationMode.INDEPENDENT, target=_target())


def test_exhaustion_preserves_diagnostic_attempt_history():
    generator = _passing_generator(side_effect=[_candidate() for _ in range(3)])
    grounding = _passing_validator(GroundingValidator, "validate_grounding", _grounding_result(False))
    producer = _make_producer(generator=generator, grounding=grounding, max_attempts=3)
    with pytest.raises(QuestionAttemptsExhaustedError) as excinfo:
        producer.produce_question(category=CATEGORY, generation_mode=GenerationMode.INDEPENDENT, target=_target())
    assert len(excinfo.value.attempts) == 3
    assert all(attempt.accepted is False for attempt in excinfo.value.attempts)
    assert [attempt.attempt_number for attempt in excinfo.value.attempts] == [1, 2, 3]


def test_exhaustion_never_returns_a_rejected_candidate_as_accepted():
    generator = _passing_generator(side_effect=[_candidate()])
    grounding = _passing_validator(GroundingValidator, "validate_grounding", _grounding_result(False))
    producer = _make_producer(generator=generator, grounding=grounding, max_attempts=1)
    with pytest.raises(QuestionAttemptsExhaustedError):
        producer.produce_question(category=CATEGORY, generation_mode=GenerationMode.INDEPENDENT, target=_target())


# ---------------------------------------------------------------------------
# WP-019: bounded generation-contract recovery
# ---------------------------------------------------------------------------


def test_recoverable_generation_contract_failure_is_retried_and_succeeds():
    good_candidate = _candidate(question="שאלה תקינה")
    generator = _passing_generator(
        side_effect=[InvalidGeneratedOutputError("invented evidence id"), good_candidate]
    )
    mcq = _passing_validator(MCQValidator, "validate", _mcq_result(True))
    producer = _make_producer(generator=generator, mcq=mcq, max_attempts=3)

    result = producer.produce_question(category=CATEGORY, generation_mode=GenerationMode.INDEPENDENT, target=_target())

    assert generator.generate_candidate_question.call_count == 2
    assert len(result.attempts) == 2
    assert result.attempts[0].is_generation_contract_failure is True
    assert result.attempts[0].candidate is None
    assert result.attempts[0].validations is None
    assert result.attempts[0].accepted is False
    assert result.attempts[1].accepted is True
    assert result.candidate == good_candidate
    # The recovered attempt ran the normal validator flow.
    assert mcq.validate.call_count == 1


def test_generation_contract_failure_records_type_and_message():
    generator = _passing_generator(
        side_effect=[InvalidGeneratedOutputError("invented evidence id: foo"), _candidate()]
    )
    producer = _make_producer(generator=generator, max_attempts=3)
    result = producer.produce_question(category=CATEGORY, generation_mode=GenerationMode.INDEPENDENT, target=_target())
    failed_attempt = result.attempts[0]
    assert failed_attempt.generation_failure_type == "InvalidGeneratedOutputError"
    assert failed_attempt.generation_failure_message == "invented evidence id: foo"


def test_multiple_generation_contract_failures_then_success():
    generator = _passing_generator(
        side_effect=[
            InvalidGeneratedOutputError("invented id 1"),
            InvalidGeneratedOutputError("invented id 2"),
            _candidate(question="שאלה תקינה"),
        ]
    )
    producer = _make_producer(generator=generator, max_attempts=3)
    result = producer.produce_question(category=CATEGORY, generation_mode=GenerationMode.INDEPENDENT, target=_target())
    assert generator.generate_candidate_question.call_count == 3
    assert len(result.attempts) == 3
    assert result.attempts[0].is_generation_contract_failure is True
    assert result.attempts[1].is_generation_contract_failure is True
    assert result.attempts[2].accepted is True
    assert [attempt.attempt_number for attempt in result.attempts] == [1, 2, 3]


def test_mixed_contract_failure_and_quality_rejection_share_one_budget():
    candidate2 = _candidate(question="שאלה שנייה")
    candidate3 = _candidate(question="שאלה שלישית")
    generator = _passing_generator(
        side_effect=[InvalidGeneratedOutputError("invented id"), candidate2, candidate3]
    )
    mcq = _passing_validator(MCQValidator, "validate", None, side_effect=[_mcq_result(False), _mcq_result(True)])
    producer = _make_producer(generator=generator, mcq=mcq, max_attempts=3)

    result = producer.produce_question(category=CATEGORY, generation_mode=GenerationMode.INDEPENDENT, target=_target())

    assert generator.generate_candidate_question.call_count == 3
    assert len(result.attempts) == 3
    assert result.attempts[0].is_generation_contract_failure is True
    assert result.attempts[1].is_generation_contract_failure is False
    assert result.attempts[1].accepted is False
    assert result.attempts[2].accepted is True
    assert result.candidate == candidate3


def test_generation_contract_failures_exhaust_the_shared_attempt_budget():
    generator = _passing_generator(
        side_effect=[InvalidGeneratedOutputError(f"invented id {i}") for i in range(3)]
    )
    producer = _make_producer(generator=generator, max_attempts=3)
    with pytest.raises(QuestionAttemptsExhaustedError) as excinfo:
        producer.produce_question(category=CATEGORY, generation_mode=GenerationMode.INDEPENDENT, target=_target())
    assert generator.generate_candidate_question.call_count == 3
    assert len(excinfo.value.attempts) == 3
    assert all(attempt.is_generation_contract_failure for attempt in excinfo.value.attempts)
    assert all(attempt.accepted is False for attempt in excinfo.value.attempts)


def test_no_validator_is_called_for_a_generation_contract_failure_attempt():
    generator = _passing_generator(
        side_effect=[InvalidGeneratedOutputError("invented id"), _candidate()]
    )
    grounding = _passing_validator(GroundingValidator, "validate_grounding", _grounding_result(True))
    mcq = _passing_validator(MCQValidator, "validate", _mcq_result(True))
    category = _passing_validator(CategoryValidator, "validate", _category_result(True))
    quality = _passing_validator(QualityValidator, "validate", _quality_result(True))
    textbook = _passing_validator(TextbookValidator, "validate", _textbook_result(TextbookCheckStatus.CONSISTENT))
    producer = _make_producer(
        generator=generator, grounding=grounding, mcq=mcq, category=category, quality=quality, textbook=textbook,
        max_attempts=3,
    )
    producer.produce_question(category=CATEGORY, generation_mode=GenerationMode.INDEPENDENT, target=_target())
    # Exactly one validation cycle occurred - the discarded attempt never
    # reached any validator.
    assert grounding.validate_grounding.call_count == 1
    assert mcq.validate.call_count == 1
    assert category.validate.call_count == 1
    assert quality.validate.call_count == 1
    assert textbook.validate.call_count == 1


@pytest.mark.parametrize(
    "exc",
    [
        LLMAuthenticationError("bad key"),
        LLMRateLimitError("rate limited"),
        LLMProviderError("connection failed"),
    ],
)
def test_non_recoverable_generator_errors_are_never_retried(exc):
    generator = _passing_generator(side_effect=exc)
    producer = _make_producer(generator=generator, max_attempts=3)
    with pytest.raises(type(exc)):
        producer.produce_question(category=CATEGORY, generation_mode=GenerationMode.INDEPENDENT, target=_target())
    assert generator.generate_candidate_question.call_count == 1


# ---------------------------------------------------------------------------
# Operational behavior
# ---------------------------------------------------------------------------


def test_all_five_validators_run_even_after_an_early_negative_verdict():
    grounding = _passing_validator(GroundingValidator, "validate_grounding", _grounding_result(False))
    mcq = _passing_validator(MCQValidator, "validate", _mcq_result(True))
    category = _passing_validator(CategoryValidator, "validate", _category_result(True))
    quality = _passing_validator(QualityValidator, "validate", _quality_result(True))
    textbook = _passing_validator(TextbookValidator, "validate", _textbook_result(TextbookCheckStatus.CONSISTENT))
    producer = _make_producer(
        grounding=grounding, mcq=mcq, category=category, quality=quality, textbook=textbook, max_attempts=1
    )
    with pytest.raises(QuestionAttemptsExhaustedError):
        producer.produce_question(category=CATEGORY, generation_mode=GenerationMode.INDEPENDENT, target=_target())
    assert grounding.validate_grounding.call_count == 1
    assert mcq.validate.call_count == 1
    assert category.validate.call_count == 1
    assert quality.validate.call_count == 1
    assert textbook.validate.call_count == 1


def test_validator_order_is_deterministic_grounding_mcq_category_quality_textbook():
    call_log: list[str] = []

    def _tracker(name, result):
        def _side_effect(candidate):
            call_log.append(name)
            return result

        return _side_effect

    grounding = _passing_validator(
        GroundingValidator, "validate_grounding", None, side_effect=_tracker("grounding", _grounding_result(True))
    )
    mcq = _passing_validator(MCQValidator, "validate", None, side_effect=_tracker("mcq", _mcq_result(True)))
    category = _passing_validator(
        CategoryValidator, "validate", None, side_effect=_tracker("category", _category_result(True))
    )
    quality = _passing_validator(
        QualityValidator, "validate", None, side_effect=_tracker("quality", _quality_result(True))
    )
    textbook = _passing_validator(
        TextbookValidator,
        "validate",
        None,
        side_effect=_tracker("textbook", _textbook_result(TextbookCheckStatus.CONSISTENT)),
    )
    producer = _make_producer(grounding=grounding, mcq=mcq, category=category, quality=quality, textbook=textbook)
    producer.produce_question(category=CATEGORY, generation_mode=GenerationMode.INDEPENDENT, target=_target())
    assert call_log == ["grounding", "mcq", "category", "quality", "textbook"]


def test_operational_generator_failure_propagates():
    generator = _passing_generator(side_effect=LLMProviderError("connection failed"))
    producer = _make_producer(generator=generator, max_attempts=3)
    with pytest.raises(LLMProviderError):
        producer.produce_question(category=CATEGORY, generation_mode=GenerationMode.INDEPENDENT, target=_target())


def test_operational_validator_failure_propagates():
    grounding = _passing_validator(
        GroundingValidator, "validate_grounding", None, side_effect=LLMProviderError("connection failed")
    )
    producer = _make_producer(grounding=grounding, max_attempts=3)
    with pytest.raises(LLMProviderError):
        producer.produce_question(category=CATEGORY, generation_mode=GenerationMode.INDEPENDENT, target=_target())


def test_operational_generator_failure_does_not_trigger_regeneration():
    generator = _passing_generator(side_effect=LLMProviderError("connection failed"))
    producer = _make_producer(generator=generator, max_attempts=3)
    with pytest.raises(LLMProviderError):
        producer.produce_question(category=CATEGORY, generation_mode=GenerationMode.INDEPENDENT, target=_target())
    assert generator.generate_candidate_question.call_count == 1


def test_operational_validator_failure_stops_remaining_validators_for_that_attempt():
    grounding = _passing_validator(GroundingValidator, "validate_grounding", _grounding_result(True))
    mcq = _passing_validator(
        MCQValidator, "validate", None, side_effect=LLMProviderError("connection failed")
    )
    textbook = _passing_validator(TextbookValidator, "validate", _textbook_result(TextbookCheckStatus.CONSISTENT))
    producer = _make_producer(grounding=grounding, mcq=mcq, textbook=textbook, max_attempts=3)
    with pytest.raises(LLMProviderError):
        producer.produce_question(category=CATEGORY, generation_mode=GenerationMode.INDEPENDENT, target=_target())
    assert grounding.validate_grounding.call_count == 1
    assert textbook.validate.call_count == 0


def test_category_and_generation_mode_remain_stable_across_attempts():
    generator = _passing_generator(side_effect=[_candidate(), _candidate()])
    grounding = _passing_validator(
        GroundingValidator, "validate_grounding", None, side_effect=[_grounding_result(False), _grounding_result(True)]
    )
    producer = _make_producer(generator=generator, grounding=grounding, max_attempts=3)
    producer.produce_question(category=CATEGORY, generation_mode=GenerationMode.STYLE_SIMILAR, target=_target())
    for call in generator.generate_candidate_question.call_args_list:
        assert call.kwargs["category"] == CATEGORY
        assert call.kwargs["generation_mode"] == GenerationMode.STYLE_SIMILAR


def test_target_remains_identical_object_across_wp013_bounded_retry_attempts():
    # WP-026 section 18: a rejected candidate may be reframed differently on
    # the next attempt, but it must still test the exact same assigned
    # QuestionTarget - never a re-planned or substituted one.
    target = _target()
    candidate1, candidate2 = _candidate(question="שאלה ראשונה"), _candidate(question="שאלה שנייה")
    generator = _passing_generator(side_effect=[candidate1, candidate2])
    grounding = _passing_validator(
        GroundingValidator, "validate_grounding", None, side_effect=[_grounding_result(False), _grounding_result(True)]
    )
    producer = _make_producer(generator=generator, grounding=grounding, max_attempts=3)
    producer.produce_question(category=CATEGORY, generation_mode=GenerationMode.INDEPENDENT, target=target)
    calls = generator.generate_candidate_question.call_args_list
    assert len(calls) == 2
    assert calls[0].kwargs["target"] is target
    assert calls[1].kwargs["target"] is target


def test_candidate_not_mutated_by_production_cycle():
    candidate = _candidate()
    before = candidate.model_dump()
    generator = _passing_generator(candidate=candidate)
    producer = _make_producer(generator=generator, max_attempts=1)
    producer.produce_question(category=CATEGORY, generation_mode=GenerationMode.INDEPENDENT, target=_target())
    assert candidate.model_dump() == before


def test_invalid_max_attempts_is_rejected():
    with pytest.raises(InvalidProductionConfigurationError):
        _make_producer(max_attempts=0)


def test_negative_max_attempts_is_rejected():
    with pytest.raises(InvalidProductionConfigurationError):
        _make_producer(max_attempts=-1)


def test_no_llm_provider_referenced_directly_in_producer_module():
    # Acceptance is plain Python policy; the control layer never talks to an
    # LLM provider itself - it only calls the already-independent generator
    # and validators.
    source = inspect.getsource(producer_module)
    assert "generate_structured" not in source
    assert "LLMProvider" not in source


def test_produce_question_signature_has_no_feedback_or_llm_parameter():
    parameters = inspect.signature(QuestionProducer.produce_question).parameters
    assert set(parameters) == {"self", "category", "generation_mode", "target"}
