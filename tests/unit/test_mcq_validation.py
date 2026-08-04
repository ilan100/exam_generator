from unittest.mock import MagicMock

from exam_generator.llm import LLMProfile, LLMProvider, LLMProviderError, MessageRole
from exam_generator.models import CandidateQuestion, GenerationMode, MCQValidationResult
from exam_generator.prompts import PromptId, PromptRepository
from exam_generator.validation import MCQValidator

import pytest

CATEGORY = "קליפת המוח"
QUESTION_TEXT = "מהו תפקידה העיקרי של קליפת המוח?"


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


def _mcq_result(**kwargs) -> MCQValidationResult:
    defaults = dict(
        valid=True,
        exactly_four_answers=True,
        single_best_answer=True,
        reason="one clearly best answer, plausible distractors",
    )
    defaults.update(kwargs)
    return MCQValidationResult(**defaults)


class _RecordingPromptRepository:
    """Wraps the real production PromptRepository, recording every
    requested PromptId so tests can assert only the MCQ prompt (and the
    shared system prompt) were used - never grounding/category/quality/
    textbook validation prompts."""

    def __init__(self, real_repository: PromptRepository) -> None:
        self._real = real_repository
        self.requested_ids: list[PromptId] = []

    def get(self, prompt_id: PromptId):
        self.requested_ids.append(prompt_id)
        return self._real.get(prompt_id)


def _provider(result: MCQValidationResult | None = None, *, side_effect=None) -> MagicMock:
    provider = MagicMock(spec=LLMProvider)
    if side_effect is not None:
        provider.generate_structured.side_effect = side_effect
    else:
        provider.generate_structured.return_value = result if result is not None else _mcq_result()
    return provider


PRODUCTION_PROMPT_REPOSITORY = PromptRepository.from_default_location()


def _make_validator(*, prompt_repository=None, provider=None) -> MCQValidator:
    return MCQValidator(
        prompt_repository=prompt_repository or _RecordingPromptRepository(PRODUCTION_PROMPT_REPOSITORY),
        llm_provider=provider or _provider(),
    )


# ---------------------------------------------------------------------------
# Pass / fail as normal results
# ---------------------------------------------------------------------------


def test_good_one_best_answer_question_passes():
    passing = _mcq_result(valid=True, exactly_four_answers=True, single_best_answer=True)
    validator = _make_validator(provider=_provider(passing))
    result = validator.validate(_candidate())
    assert result.valid is True
    assert isinstance(result, MCQValidationResult)


def test_ambiguous_multiple_defensible_answer_question_fails_as_normal_result():
    failing = _mcq_result(
        valid=False, single_best_answer=False, reason="two answers are equally defensible"
    )
    validator = _make_validator(provider=_provider(failing))
    result = validator.validate(_candidate())
    assert result.valid is False
    assert isinstance(result, MCQValidationResult)


def test_poor_distractors_fail():
    failing = _mcq_result(valid=False, reason="distractors are obviously wrong/nonsensical")
    validator = _make_validator(provider=_provider(failing))
    result = validator.validate(_candidate())
    assert result.valid is False


# ---------------------------------------------------------------------------
# Prompt / LLM call shape
# ---------------------------------------------------------------------------


def test_mcq_production_prompt_is_used():
    recording_repository = _RecordingPromptRepository(PRODUCTION_PROMPT_REPOSITORY)
    validator = _make_validator(prompt_repository=recording_repository)
    validator.validate(_candidate())
    assert set(recording_repository.requested_ids) == {PromptId.SYSTEM, PromptId.MCQ_VALIDATION}


def test_llm_called_through_validation_profile():
    provider = _provider()
    validator = _make_validator(provider=provider)
    validator.validate(_candidate())
    assert provider.generate_structured.call_args.kwargs["profile"] == LLMProfile.VALIDATION


def test_llm_called_with_mcq_validation_result_model():
    provider = _provider()
    validator = _make_validator(provider=provider)
    validator.validate(_candidate())
    assert provider.generate_structured.call_args.kwargs["response_model"] is MCQValidationResult


def test_messages_are_system_then_user():
    provider = _provider()
    validator = _make_validator(provider=provider)
    validator.validate(_candidate())
    messages = provider.generate_structured.call_args.kwargs["messages"]
    assert [m.role for m in messages] == [MessageRole.SYSTEM, MessageRole.USER]


def test_no_retry_exactly_one_llm_call():
    provider = _provider()
    validator = _make_validator(provider=provider)
    validator.validate(_candidate())
    assert provider.generate_structured.call_count == 1


def test_question_text_appears_in_rendered_user_message():
    provider = _provider()
    validator = _make_validator(provider=provider)
    validator.validate(_candidate())
    messages = provider.generate_structured.call_args.kwargs["messages"]
    assert QUESTION_TEXT in messages[1].content


# ---------------------------------------------------------------------------
# No retrieval / no other validation stages
# ---------------------------------------------------------------------------


def test_no_retrieval_dependency_exists():
    import inspect

    parameters = inspect.signature(MCQValidator.__init__).parameters
    assert "student_summary_index" not in parameters
    assert not any("retriev" in name for name in parameters)


def test_no_grounding_category_quality_textbook_validation_triggered():
    recording_repository = _RecordingPromptRepository(PRODUCTION_PROMPT_REPOSITORY)
    validator = _make_validator(prompt_repository=recording_repository)
    validator.validate(_candidate())
    forbidden = {
        PromptId.GROUNDING_VALIDATION,
        PromptId.CATEGORY_VALIDATION,
        PromptId.QUALITY_VALIDATION,
        PromptId.TEXTBOOK_VALIDATION,
    }
    assert not forbidden.intersection(recording_repository.requested_ids)


# ---------------------------------------------------------------------------
# Operational failure vs. negative verdict
# ---------------------------------------------------------------------------


def test_provider_failure_is_operational_error_not_a_failed_verdict():
    provider = _provider(side_effect=LLMProviderError("connection failed"))
    validator = _make_validator(provider=provider)
    with pytest.raises(LLMProviderError):
        validator.validate(_candidate())


# ---------------------------------------------------------------------------
# Candidate immutability
# ---------------------------------------------------------------------------


def test_candidate_not_mutated():
    candidate = _candidate()
    before = candidate.model_dump()
    validator = _make_validator()
    validator.validate(candidate)
    assert candidate.model_dump() == before
