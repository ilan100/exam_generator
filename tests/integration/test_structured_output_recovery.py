"""WP-020 integration tests: bounded structured-output retry exercised
through real application components (real retrieval/TF-IDF, real prompt
rendering, real provenance validation, real acceptance policy, real exam
planning) wired to a *real* ``OpenAIProvider`` whose raw SDK client is
faked at the ``client.responses.parse(...)`` boundary.

Deliberately different from ``test_end_to_end_pipeline.py``: that file
fakes the ``LLMProvider`` ABC itself (one layer above the provider), which
never exercises ``OpenAIProvider``'s own WP-020 retry logic. Here, only the
raw SDK client is faked, so the real provider's retry loop actually runs.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from exam_generator.config.models import LLMGenerationParams, LLMValidationParams
from exam_generator.generation import QuestionGenerator
from exam_generator.llm import LLMProfile, LLMStructuredOutputError, OpenAIProvider
from exam_generator.models import (
    CategoryValidationResult,
    ExamRequest,
    GeneratedQuestionResponse,
    GroundingValidationResponse,
    MCQValidationResult,
    QualityValidationResult,
    SourceType,
    TextbookValidationResponse,
    TextbookCheckStatus,
)
from exam_generator.orchestration import ExamOrchestrator, QuestionProductionFailedError
from exam_generator.production import QuestionProducer
from exam_generator.prompts import PromptRepository
from exam_generator.retrieval import CategoryResolver, FactualRetrievalIndex
from exam_generator.validation import CategoryValidator, GroundingValidator, MCQValidator, QualityValidator, TextbookValidator
from tests.integration.test_end_to_end_pipeline import (
    CATEGORY_A,
    _course_book_corpus_no_overlap,
    _historical_repository,
    _student_summary_corpus,
)

# ---------------------------------------------------------------------------
# Fakes mimicking the raw OpenAI SDK's client.responses.parse() surface
# ---------------------------------------------------------------------------


class _FakeTextContent:
    type = "output_text"

    def __init__(self, parsed):
        self.parsed = parsed


class _FakeOutputMessage:
    type = "message"

    def __init__(self, content):
        self.content = content


class _FakeParsedResponse:
    def __init__(self, output, parsed=None):
        self.output = output
        self._parsed = parsed

    @property
    def output_parsed(self):
        return self._parsed


def _successful_response(parsed) -> _FakeParsedResponse:
    return _FakeParsedResponse(output=[_FakeOutputMessage([_FakeTextContent(parsed)])], parsed=parsed)


class _QueuedSdkClient:
    """Queued per response_model, at the raw SDK client boundary - the
    layer directly beneath ``OpenAIProvider``, so its own physical-call
    retry loop actually executes."""

    def __init__(self) -> None:
        self._queues: dict[type, list[object]] = {}
        self.call_log: list[type] = []

    @property
    def responses(self) -> "_QueuedSdkClient":
        return self

    def queue(self, response_model: type, *items: object) -> None:
        self._queues.setdefault(response_model, []).extend(items)

    def parse(self, *, model, input, text_format, temperature, max_output_tokens):
        self.call_log.append(text_format)
        queue = self._queues.get(text_format)
        if not queue:
            raise AssertionError(
                f"Integration test scenario under-provisioned: no queued response for "
                f"{text_format.__name__} (call #{len(self.call_log)})"
            )
        item = queue.pop(0)
        if isinstance(item, BaseException):
            raise item
        return _successful_response(item)


def _malformed_json_error(response_model: type) -> ValidationError:
    try:
        response_model.model_validate_json('{"trunca')
    except ValidationError as exc:
        return exc
    raise AssertionError("expected truncated JSON to raise ValidationError")


# ---------------------------------------------------------------------------
# Fixture helpers
# ---------------------------------------------------------------------------


def _generated_response(**kwargs) -> GeneratedQuestionResponse:
    defaults = dict(
        question="שאלה לדוגמה?",
        answers=["תשובה א", "תשובה ב", "תשובה ג", "תשובה ד"],
        correct_answer=1,
        evidence_chunk_ids=[],
        historical_reference_id=None,
    )
    defaults.update(kwargs)
    return GeneratedQuestionResponse(**defaults)


def _grounding(passed: bool = True) -> GroundingValidationResponse:
    return GroundingValidationResponse(
        grounded=passed, correct_answer_supported=passed, other_answers_not_equally_correct=passed,
        evidence_refs=[], reason="stub", confidence=0.9,
    )


def _mcq(valid: bool = True) -> MCQValidationResult:
    return MCQValidationResult(valid=valid, exactly_four_answers=True, single_best_answer=valid, reason="stub")


def _category(category: str, valid: bool = True) -> CategoryValidationResult:
    return CategoryValidationResult(valid=valid, requested_category=category, assessed_category=category, reason="stub")


def _quality(valid: bool = True) -> QualityValidationResult:
    return QualityValidationResult(valid=valid, reason="stub")


def _textbook(status: TextbookCheckStatus = TextbookCheckStatus.NOT_FOUND) -> TextbookValidationResponse:
    return TextbookValidationResponse(status=status, reason="stub")


def _build_real_pipeline(*, sdk_client: _QueuedSdkClient, structured_output_retries: int = 1, max_generation_attempts: int = 3):
    prompt_repository = PromptRepository.from_default_location()
    category_resolver = CategoryResolver([CATEGORY_A], {})

    student_summary_index = FactualRetrievalIndex.from_corpus(
        _student_summary_corpus(), source_type=SourceType.STUDENT_SUMMARY, top_k=8, ngram_range=(3, 5)
    )
    course_book_index = FactualRetrievalIndex.from_corpus(
        _course_book_corpus_no_overlap(), source_type=SourceType.COURSE_BOOK, top_k=8, ngram_range=(3, 5)
    )

    provider = OpenAIProvider(
        model="gpt-4o-mini",
        api_key="test-api-key",
        generation_params=LLMGenerationParams(temperature=0.7, max_tokens=1024),
        validation_params=LLMValidationParams(temperature=0.0, max_tokens=1024),
        client=sdk_client,
        structured_output_retries=structured_output_retries,
    )

    generator = QuestionGenerator(
        category_resolver=category_resolver,
        student_summary_index=student_summary_index,
        historical_repository=_historical_repository(),
        prompt_repository=prompt_repository,
        llm_provider=provider,
    )
    producer = QuestionProducer(
        generator=generator,
        grounding_validator=GroundingValidator(
            student_summary_index=student_summary_index, prompt_repository=prompt_repository, llm_provider=provider
        ),
        mcq_validator=MCQValidator(prompt_repository=prompt_repository, llm_provider=provider),
        category_validator=CategoryValidator(prompt_repository=prompt_repository, llm_provider=provider),
        quality_validator=QualityValidator(prompt_repository=prompt_repository, llm_provider=provider),
        textbook_validator=TextbookValidator(
            course_book_index=course_book_index, prompt_repository=prompt_repository, llm_provider=provider
        ),
        max_attempts=max_generation_attempts,
    )
    orchestrator = ExamOrchestrator(
        category_resolver=category_resolver, producer=producer, max_duplicate_replacement_attempts=2
    )
    return orchestrator


def _queue_passing_validators(client: _QueuedSdkClient, *, category: str) -> None:
    client.queue(GroundingValidationResponse, _grounding(True))
    _queue_passing_validators_without_grounding(client, category=category)


def _queue_passing_validators_without_grounding(client: _QueuedSdkClient, *, category: str) -> None:
    client.queue(MCQValidationResult, _mcq(True))
    client.queue(CategoryValidationResult, _category(category, True))
    client.queue(QualityValidationResult, _quality(True))
    client.queue(TextbookValidationResponse, _textbook(TextbookCheckStatus.NOT_FOUND))


# ---------------------------------------------------------------------------
# Scenario: validator recovery
# ---------------------------------------------------------------------------


def test_validator_structured_output_recovers_and_question_is_accepted():
    client = _QueuedSdkClient()
    client.queue(GeneratedQuestionResponse, _generated_response())
    client.queue(GroundingValidationResponse, _malformed_json_error(GroundingValidationResponse), _grounding(True))
    client.queue(MCQValidationResult, _mcq(True))
    client.queue(CategoryValidationResult, _category(CATEGORY_A, True))
    client.queue(QualityValidationResult, _quality(True))
    client.queue(TextbookValidationResponse, _textbook(TextbookCheckStatus.NOT_FOUND))

    orchestrator = _build_real_pipeline(sdk_client=client)
    result = orchestrator.generate_exam(ExamRequest(categories={CATEGORY_A: 1}))

    assert len(result.exam.questions) == 1
    # The structured-output retry is internal to one logical operation -
    # still exactly one QuestionAttempt, not two.
    assert len(result.productions[0].production.attempts) == 1
    assert client.call_log.count(GroundingValidationResponse) == 2


# ---------------------------------------------------------------------------
# Scenario: generation structured recovery
# ---------------------------------------------------------------------------


def test_generation_structured_output_recovers_without_consuming_a_production_attempt():
    client = _QueuedSdkClient()
    client.queue(GeneratedQuestionResponse, _malformed_json_error(GeneratedQuestionResponse), _generated_response())
    _queue_passing_validators(client, category=CATEGORY_A)

    orchestrator = _build_real_pipeline(sdk_client=client)
    result = orchestrator.generate_exam(ExamRequest(categories={CATEGORY_A: 1}))

    assert len(result.exam.questions) == 1
    assert len(result.productions[0].production.attempts) == 1
    assert result.productions[0].production.attempts[0].is_generation_contract_failure is False
    assert client.call_log.count(GeneratedQuestionResponse) == 2


# ---------------------------------------------------------------------------
# Scenario: retry exhaustion propagates as a contextualized exam failure
# ---------------------------------------------------------------------------


def test_structured_output_retry_exhaustion_is_a_contextualized_exam_failure():
    client = _QueuedSdkClient()
    client.queue(GeneratedQuestionResponse, _generated_response())
    client.queue(
        GroundingValidationResponse,
        _malformed_json_error(GroundingValidationResponse),
        _malformed_json_error(GroundingValidationResponse),
    )

    orchestrator = _build_real_pipeline(sdk_client=client, structured_output_retries=1)
    with pytest.raises(QuestionProductionFailedError) as excinfo:
        orchestrator.generate_exam(ExamRequest(categories={CATEGORY_A: 1}))

    assert isinstance(excinfo.value.operational_cause, LLMStructuredOutputError)
    assert isinstance(excinfo.value.__cause__, LLMStructuredOutputError)
    assert excinfo.value.planned_question.position == 1
    assert excinfo.value.planned_question.category == CATEGORY_A
    assert excinfo.value.completed_productions == ()
    assert client.call_log.count(GroundingValidationResponse) == 2


# ---------------------------------------------------------------------------
# Scenario: interaction with WP-019 generation-contract recovery
# ---------------------------------------------------------------------------


def test_generation_structured_retry_then_wp019_provenance_recovery_then_accepted():
    client = _QueuedSdkClient()
    # Attempt 1's generation: physical call #1 malformed, physical call #2
    # parses successfully but claims invented provenance.
    invented = _generated_response(evidence_chunk_ids=["NOT_A_SUPPLIED_CHUNK_ID"])
    client.queue(GeneratedQuestionResponse, _malformed_json_error(GeneratedQuestionResponse), invented)
    # Attempt 2's generation: succeeds cleanly.
    client.queue(GeneratedQuestionResponse, _generated_response(question="שאלה תקינה"))
    _queue_passing_validators(client, category=CATEGORY_A)

    orchestrator = _build_real_pipeline(sdk_client=client)
    result = orchestrator.generate_exam(ExamRequest(categories={CATEGORY_A: 1}))

    assert result.exam.questions[0].question == "שאלה תקינה"
    attempts = result.productions[0].production.attempts
    assert len(attempts) == 2
    assert attempts[0].is_generation_contract_failure is True
    assert attempts[1].accepted is True
    assert client.call_log.count(GeneratedQuestionResponse) == 3


# ---------------------------------------------------------------------------
# Scenario: interaction with WP-021 validator provenance recovery
# ---------------------------------------------------------------------------


def test_structured_output_recovery_then_valid_provenance_succeeds():
    # WP-020 physical retry (malformed -> valid) within a grounding call
    # that has valid provenance on the very first successfully-parsed
    # response - WP-021's own retry loop never needs to engage.
    client = _QueuedSdkClient()
    client.queue(GeneratedQuestionResponse, _generated_response())
    client.queue(GroundingValidationResponse, _malformed_json_error(GroundingValidationResponse), _grounding(True))
    _queue_passing_validators_without_grounding(client, category=CATEGORY_A)

    orchestrator = _build_real_pipeline(sdk_client=client)
    result = orchestrator.generate_exam(ExamRequest(categories={CATEGORY_A: 1}))

    assert len(result.exam.questions) == 1
    assert len(result.productions[0].production.attempts) == 1
    assert client.call_log.count(GroundingValidationResponse) == 2


def test_structured_output_recovery_then_invalid_provenance_then_wp021_recovery_succeeds():
    # WP-020 physical retry (malformed -> valid JSON but invented
    # evidence id) completes the FIRST logical grounding call, which
    # WP-021 then discards and retries as a SECOND logical call (a fresh
    # physical call that succeeds immediately). Both retry budgets are
    # exercised independently and remain bounded.
    client = _QueuedSdkClient()
    client.queue(GeneratedQuestionResponse, _generated_response())
    invented = GroundingValidationResponse(
        grounded=True, correct_answer_supported=True, other_answers_not_equally_correct=True,
        evidence_refs=[99], reason="stub", confidence=0.9,
    )
    client.queue(
        GroundingValidationResponse,
        _malformed_json_error(GroundingValidationResponse),  # logical call 1, physical call 1: malformed
        invented,  # logical call 1, physical call 2 (WP-020 recovery): valid JSON, invented provenance
        _grounding(True),  # logical call 2 (WP-021 recovery): valid
    )
    _queue_passing_validators_without_grounding(client, category=CATEGORY_A)

    orchestrator = _build_real_pipeline(sdk_client=client)
    result = orchestrator.generate_exam(ExamRequest(categories={CATEGORY_A: 1}))

    assert len(result.exam.questions) == 1
    # Still exactly one QuestionAttempt - neither retry mechanism creates
    # a new candidate-production attempt.
    assert len(result.productions[0].production.attempts) == 1
    assert client.call_log.count(GroundingValidationResponse) == 3
