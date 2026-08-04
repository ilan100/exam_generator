"""Cross-validator architectural checks for WP-011 (MCQ/category/quality).

These do not duplicate each individual validator's own test module - they
verify the WP-011 invariant that the three validators are independent of
each other and of WP-010's grounding validator: no validator's verdict
depends on, or is required by, another's, and none invoke another
validator's prompt.
"""

from unittest.mock import MagicMock

from exam_generator.llm import LLMProfile, LLMProvider
from exam_generator.models import (
    CandidateQuestion,
    CategoryValidationResult,
    GenerationMode,
    MCQValidationResult,
    QualityValidationResult,
)
from exam_generator.prompts import PromptId, PromptRepository
from exam_generator.validation import CategoryValidator, MCQValidator, QualityValidator

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


PRODUCTION_PROMPT_REPOSITORY = PromptRepository.from_default_location()


def _mcq_provider(*, valid: bool) -> MagicMock:
    provider = MagicMock(spec=LLMProvider)
    provider.generate_structured.return_value = MCQValidationResult(
        valid=valid, exactly_four_answers=True, single_best_answer=valid, reason="stub"
    )
    return provider


def _category_provider(*, valid: bool) -> MagicMock:
    provider = MagicMock(spec=LLMProvider)
    provider.generate_structured.return_value = CategoryValidationResult(
        valid=valid, requested_category=CATEGORY, assessed_category=CATEGORY, reason="stub"
    )
    return provider


def _quality_provider(*, valid: bool) -> MagicMock:
    provider = MagicMock(spec=LLMProvider)
    provider.generate_structured.return_value = QualityValidationResult(valid=valid, reason="stub")
    return provider


# ---------------------------------------------------------------------------
# No validator requires another to have passed first
# ---------------------------------------------------------------------------


def test_mcq_validator_does_not_require_grounding_first():
    # No grounding-related parameter/dependency exists on MCQValidator at all.
    import inspect

    parameters = inspect.signature(MCQValidator.__init__).parameters
    assert not any("ground" in name for name in parameters)


def test_quality_validator_does_not_require_category_to_have_passed():
    # QualityValidator.validate() succeeds independently of any category verdict -
    # it never receives one and never calls the category prompt.
    provider = _quality_provider(valid=False)
    validator = QualityValidator(prompt_repository=PRODUCTION_PROMPT_REPOSITORY, llm_provider=provider)
    result = validator.validate(_candidate())
    assert isinstance(result, QualityValidationResult)
    assert provider.generate_structured.call_args.kwargs["response_model"] is QualityValidationResult


def test_category_validator_does_not_require_mcq_to_have_passed():
    provider = _category_provider(valid=False)
    validator = CategoryValidator(prompt_repository=PRODUCTION_PROMPT_REPOSITORY, llm_provider=provider)
    result = validator.validate(_candidate())
    assert isinstance(result, CategoryValidationResult)


# ---------------------------------------------------------------------------
# Each validator calls exactly its own prompt, never another's
# ---------------------------------------------------------------------------


def test_all_three_validators_use_distinct_prompts_and_validation_profile():
    mcq_provider = _mcq_provider(valid=True)
    category_provider = _category_provider(valid=True)
    quality_provider = _quality_provider(valid=True)

    candidate = _candidate()

    MCQValidator(prompt_repository=PRODUCTION_PROMPT_REPOSITORY, llm_provider=mcq_provider).validate(
        candidate
    )
    CategoryValidator(
        prompt_repository=PRODUCTION_PROMPT_REPOSITORY, llm_provider=category_provider
    ).validate(candidate)
    QualityValidator(
        prompt_repository=PRODUCTION_PROMPT_REPOSITORY, llm_provider=quality_provider
    ).validate(candidate)

    for provider in (mcq_provider, category_provider, quality_provider):
        assert provider.generate_structured.call_count == 1
        assert provider.generate_structured.call_args.kwargs["profile"] == LLMProfile.VALIDATION

    mcq_prompt = mcq_provider.generate_structured.call_args.kwargs["messages"][1].content
    category_prompt = category_provider.generate_structured.call_args.kwargs["messages"][1].content
    quality_prompt = quality_provider.generate_structured.call_args.kwargs["messages"][1].content
    assert mcq_prompt != category_prompt != quality_prompt


# ---------------------------------------------------------------------------
# Diagnostics: independent pass/fail combinations are all representable
# ---------------------------------------------------------------------------


def test_independent_pass_fail_combinations_are_all_representable():
    candidate = _candidate()

    mcq_result = MCQValidator(
        prompt_repository=PRODUCTION_PROMPT_REPOSITORY, llm_provider=_mcq_provider(valid=False)
    ).validate(candidate)
    category_result = CategoryValidator(
        prompt_repository=PRODUCTION_PROMPT_REPOSITORY, llm_provider=_category_provider(valid=True)
    ).validate(candidate)
    quality_result = QualityValidator(
        prompt_repository=PRODUCTION_PROMPT_REPOSITORY, llm_provider=_quality_provider(valid=False)
    ).validate(candidate)

    # MCQ FAIL, Category PASS, Quality FAIL - simultaneously representable,
    # exactly the diagnostic granularity WP-011 requires over a single
    # collapsed valid=false.
    assert mcq_result.valid is False
    assert category_result.valid is True
    assert quality_result.valid is False
