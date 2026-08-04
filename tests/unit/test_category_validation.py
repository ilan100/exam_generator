from unittest.mock import MagicMock

from exam_generator.llm import LLMProfile, LLMProvider, LLMProviderError, MessageRole
from exam_generator.models import CandidateQuestion, CategoryValidationResult, GenerationMode
from exam_generator.prompts import PromptId, PromptRepository
from exam_generator.validation import CategoryValidator

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


def _category_result(**kwargs) -> CategoryValidationResult:
    defaults = dict(
        valid=True,
        requested_category=CATEGORY,
        assessed_category=CATEGORY,
        reason="question content matches the requested category",
    )
    defaults.update(kwargs)
    return CategoryValidationResult(**defaults)


class _RecordingPromptRepository:
    """Wraps the real production PromptRepository, recording every
    requested PromptId so tests can assert only the category prompt (and
    the shared system prompt) were used - never grounding/MCQ/quality/
    textbook validation prompts."""

    def __init__(self, real_repository: PromptRepository) -> None:
        self._real = real_repository
        self.requested_ids: list[PromptId] = []

    def get(self, prompt_id: PromptId):
        self.requested_ids.append(prompt_id)
        return self._real.get(prompt_id)


def _provider(result: CategoryValidationResult | None = None, *, side_effect=None) -> MagicMock:
    provider = MagicMock(spec=LLMProvider)
    if side_effect is not None:
        provider.generate_structured.side_effect = side_effect
    else:
        provider.generate_structured.return_value = result if result is not None else _category_result()
    return provider


PRODUCTION_PROMPT_REPOSITORY = PromptRepository.from_default_location()


def _make_validator(*, prompt_repository=None, provider=None) -> CategoryValidator:
    return CategoryValidator(
        prompt_repository=prompt_repository or _RecordingPromptRepository(PRODUCTION_PROMPT_REPOSITORY),
        llm_provider=provider or _provider(),
    )


# ---------------------------------------------------------------------------
# Pass / fail as normal results
# ---------------------------------------------------------------------------


def test_correctly_categorized_question_passes():
    passing = _category_result(valid=True, assessed_category=CATEGORY)
    validator = _make_validator(provider=_provider(passing))
    result = validator.validate(_candidate())
    assert result.valid is True
    assert isinstance(result, CategoryValidationResult)


def test_semantically_mismatched_category_fails_as_normal_result():
    failing = _category_result(
        valid=False,
        assessed_category="עצבים קרניאליים",
        reason="question content is actually about cranial nerves, not the requested category",
    )
    validator = _make_validator(provider=_provider(failing))
    result = validator.validate(_candidate())
    assert result.valid is False
    assert isinstance(result, CategoryValidationResult)


# ---------------------------------------------------------------------------
# Canonical category / no alias resolution
# ---------------------------------------------------------------------------


def test_candidates_own_canonical_category_is_supplied_to_the_prompt():
    provider = _provider()
    candidate = _candidate(category=CATEGORY)
    validator = _make_validator(provider=provider)
    validator.validate(candidate)
    messages = provider.generate_structured.call_args.kwargs["messages"]
    assert CATEGORY in messages[1].content


def test_no_alias_resolution_dependency_exists():
    import inspect

    parameters = inspect.signature(CategoryValidator.__init__).parameters
    assert not any("resolver" in name or "alias" in name for name in parameters)


# ---------------------------------------------------------------------------
# Prompt / LLM call shape
# ---------------------------------------------------------------------------


def test_category_production_prompt_is_used():
    recording_repository = _RecordingPromptRepository(PRODUCTION_PROMPT_REPOSITORY)
    validator = _make_validator(prompt_repository=recording_repository)
    validator.validate(_candidate())
    assert set(recording_repository.requested_ids) == {PromptId.SYSTEM, PromptId.CATEGORY_VALIDATION}


def test_llm_called_through_validation_profile():
    provider = _provider()
    validator = _make_validator(provider=provider)
    validator.validate(_candidate())
    assert provider.generate_structured.call_args.kwargs["profile"] == LLMProfile.VALIDATION


def test_llm_called_with_category_validation_result_model():
    provider = _provider()
    validator = _make_validator(provider=provider)
    validator.validate(_candidate())
    assert provider.generate_structured.call_args.kwargs["response_model"] is CategoryValidationResult


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


# ---------------------------------------------------------------------------
# No retrieval / no other validation stages
# ---------------------------------------------------------------------------


def test_no_retrieval_dependency_exists():
    import inspect

    parameters = inspect.signature(CategoryValidator.__init__).parameters
    assert not any("retriev" in name for name in parameters)


def test_no_grounding_mcq_quality_textbook_validation_triggered():
    recording_repository = _RecordingPromptRepository(PRODUCTION_PROMPT_REPOSITORY)
    validator = _make_validator(prompt_repository=recording_repository)
    validator.validate(_candidate())
    forbidden = {
        PromptId.GROUNDING_VALIDATION,
        PromptId.MCQ_VALIDATION,
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
