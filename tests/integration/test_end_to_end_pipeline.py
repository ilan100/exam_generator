"""WP-017 end-to-end integration tests: the complete architecture

    ExamRequest -> planning -> generation -> retrieval -> validation ->
    acceptance -> exam -> audit/output

wired together from real components (real retrieval/TF-IDF, real prompt
rendering, real provenance validation, real acceptance policy, real exam
planning, real duplicate detection, real audit construction) with only the
LLM call itself replaced by a small scripted fake - no real API key or
network access required. These tests verify cross-component contracts,
not each component's own internal correctness (already covered by the
unit suites).
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Sequence

import pytest
from pydantic import BaseModel

from exam_generator.config.models import LLMConfig, LLMGenerationParams, LLMValidationParams
from exam_generator.generation import QuestionGenerator
from exam_generator.historical import HistoricalQuestionRepository
from exam_generator.llm import LLMMessage, LLMProfile, LLMProvider, LLMProviderError
from exam_generator.models import (
    CategoryValidationResult,
    ExamRequest,
    GeneratedQuestionResponse,
    GenerationMode,
    GroundingValidationResult,
    HistoricalStyleReference,
    MCQValidationResult,
    QualityValidationResult,
    SourceEvidenceChunk,
    SourceType,
    TextbookCheckResult,
    TextbookCheckStatus,
)
from exam_generator.orchestration import ExamOrchestrator, QuestionProductionFailedError
from exam_generator.output import build_exam_output_bundle
from exam_generator.production import QuestionAttemptsExhaustedError, QuestionProducer
from exam_generator.prompts import PromptRepository
from exam_generator.retrieval import CategoryResolver, FactualRetrievalIndex
from exam_generator.validation import CategoryValidator, GroundingValidator, MCQValidator, QualityValidator, TextbookValidator
from exam_generator.chunking import FactualSourceCorpus

CATEGORY_A = "קליפת המוח"
CATEGORY_B = "גזע המוח"


# ---------------------------------------------------------------------------
# Fake LLM provider - the only faked component
# ---------------------------------------------------------------------------


class FakeLLMProvider(LLMProvider):
    """A scripted, provider-independent fake: for each ``response_model``
    type, returns queued responses in order (or raises a queued
    exception). Raises loudly (``AssertionError``) if a test scenario
    under-provisions responses, rather than silently returning something
    unexpected."""

    def __init__(self) -> None:
        self._queues: dict[type, list[object]] = {}
        self.call_log: list[tuple[type, LLMProfile]] = []

    def queue(self, response_model: type, *responses: object) -> None:
        self._queues.setdefault(response_model, []).extend(responses)

    @property
    def provider_name(self) -> str:
        return "fake"

    @property
    def model_name(self) -> str:
        return "fake-model"

    def generate_structured(self, *, messages: Sequence[LLMMessage], response_model: type, profile: LLMProfile):
        self.call_log.append((response_model, profile))
        queue = self._queues.get(response_model)
        if not queue:
            raise AssertionError(
                f"Integration test scenario under-provisioned: no queued fake response for "
                f"{response_model.__name__} (call #{len(self.call_log)})"
            )
        next_item = queue.pop(0)
        if isinstance(next_item, BaseException):
            raise next_item
        assert isinstance(next_item, response_model)
        return next_item


# ---------------------------------------------------------------------------
# Fixture helpers
# ---------------------------------------------------------------------------


def _chunk(text: str, *, chunk_id: str, source_file: str, page: int, source_type: SourceType) -> SourceEvidenceChunk:
    return SourceEvidenceChunk(chunk_id=chunk_id, source_file=source_file, page=page, text=text, source_type=source_type)


def _student_summary_corpus() -> FactualSourceCorpus:
    chunks = [
        _chunk(
            f"{CATEGORY_A} אחראית לתפקודים גבוהים כמו חשיבה ותכנון מורכב אצל בני אדם",
            chunk_id="STUDENT_SUMMARY:s1.pdf:0001:0001", source_file="s1.pdf", page=1, source_type=SourceType.STUDENT_SUMMARY,
        ),
        _chunk(
            f"{CATEGORY_B} מחבר בין המוח לחוט השדרה ומכיל גרעינים חיוניים לתפקוד הבסיסי",
            chunk_id="STUDENT_SUMMARY:s1.pdf:0002:0001", source_file="s1.pdf", page=2, source_type=SourceType.STUDENT_SUMMARY,
        ),
    ]
    return FactualSourceCorpus(chunks)


def _course_book_corpus_with_overlap() -> FactualSourceCorpus:
    chunks = [
        _chunk(
            f"{CATEGORY_A} is responsible for higher cognitive functions in the human brain",
            chunk_id="COURSE_BOOK:cb.pdf:0010:0001", source_file="cb.pdf", page=10, source_type=SourceType.COURSE_BOOK,
        ),
    ]
    return FactualSourceCorpus(chunks)


def _course_book_corpus_no_overlap() -> FactualSourceCorpus:
    chunks = [
        _chunk(
            "פרק נפרד לחלוטין על נושא שאינו קשור כלל לתוכן הנבדק כאן ולשאילתות המשמשות בבדיקה",
            chunk_id="COURSE_BOOK:cb.pdf:0099:0001", source_file="cb.pdf", page=99, source_type=SourceType.COURSE_BOOK,
        ),
    ]
    return FactualSourceCorpus(chunks)


def _historical_repository() -> HistoricalQuestionRepository:
    questions = [
        HistoricalStyleReference(
            historical_question_id=1, category=CATEGORY_A, question="שאלה היסטורית לדוגמה?",
            answers=["א", "ב", "ג", "ד"], correct_answer=1,
        ),
        HistoricalStyleReference(
            historical_question_id=2, category=CATEGORY_B, question="שאלה היסטורית נוספת?",
            answers=["א", "ב", "ג", "ד"], correct_answer=2,
        ),
    ]
    return HistoricalQuestionRepository(questions, [CATEGORY_A, CATEGORY_B])


def _generated_response(question: str = "שאלה לדוגמה?", correct_answer: int = 1) -> GeneratedQuestionResponse:
    return GeneratedQuestionResponse(
        question=question,
        answers=["תשובה א", "תשובה ב", "תשובה ג", "תשובה ד"],
        correct_answer=correct_answer,
        evidence_chunk_ids=[],
        historical_reference_id=None,
    )


def _grounding(passed: bool = True) -> GroundingValidationResult:
    return GroundingValidationResult(
        grounded=passed, correct_answer_supported=passed, other_answers_not_equally_correct=passed,
        evidence_chunk_ids=[], reason="stub", confidence=0.9,
    )


def _mcq(valid: bool = True) -> MCQValidationResult:
    return MCQValidationResult(valid=valid, exactly_four_answers=True, single_best_answer=valid, reason="stub")


def _category(category: str, valid: bool = True) -> CategoryValidationResult:
    return CategoryValidationResult(valid=valid, requested_category=category, assessed_category=category, reason="stub")


def _quality(valid: bool = True) -> QualityValidationResult:
    return QualityValidationResult(valid=valid, reason="stub")


def _textbook(status: TextbookCheckStatus = TextbookCheckStatus.CONSISTENT) -> TextbookCheckResult:
    return TextbookCheckResult(status=status, reason="stub")


def _build_pipeline(
    *,
    student_summary_corpus: FactualSourceCorpus,
    course_book_corpus: FactualSourceCorpus,
    historical_repository: HistoricalQuestionRepository,
    canonical_categories: list[str],
    max_generation_attempts: int = 3,
    max_duplicate_replacement_attempts: int = 2,
) -> tuple[ExamOrchestrator, FakeLLMProvider]:
    fake_provider = FakeLLMProvider()
    prompt_repository = PromptRepository.from_default_location()
    category_resolver = CategoryResolver(canonical_categories, {})

    student_summary_index = FactualRetrievalIndex.from_corpus(
        student_summary_corpus, source_type=SourceType.STUDENT_SUMMARY, top_k=8, ngram_range=(3, 5)
    )
    course_book_index = FactualRetrievalIndex.from_corpus(
        course_book_corpus, source_type=SourceType.COURSE_BOOK, top_k=8, ngram_range=(3, 5)
    )

    generator = QuestionGenerator(
        category_resolver=category_resolver,
        student_summary_index=student_summary_index,
        historical_repository=historical_repository,
        prompt_repository=prompt_repository,
        llm_provider=fake_provider,
    )
    grounding_validator = GroundingValidator(
        student_summary_index=student_summary_index, prompt_repository=prompt_repository, llm_provider=fake_provider
    )
    mcq_validator = MCQValidator(prompt_repository=prompt_repository, llm_provider=fake_provider)
    category_validator = CategoryValidator(prompt_repository=prompt_repository, llm_provider=fake_provider)
    quality_validator = QualityValidator(prompt_repository=prompt_repository, llm_provider=fake_provider)
    textbook_validator = TextbookValidator(
        course_book_index=course_book_index, prompt_repository=prompt_repository, llm_provider=fake_provider
    )

    producer = QuestionProducer(
        generator=generator,
        grounding_validator=grounding_validator,
        mcq_validator=mcq_validator,
        category_validator=category_validator,
        quality_validator=quality_validator,
        textbook_validator=textbook_validator,
        max_attempts=max_generation_attempts,
    )
    orchestrator = ExamOrchestrator(
        category_resolver=category_resolver,
        producer=producer,
        max_duplicate_replacement_attempts=max_duplicate_replacement_attempts,
    )
    return orchestrator, fake_provider


def _queue_passing_attempt(
    fake_provider: FakeLLMProvider,
    *,
    category: str,
    question: str = "שאלה לדוגמה?",
    textbook_status: TextbookCheckStatus = TextbookCheckStatus.NOT_FOUND,
) -> None:
    fake_provider.queue(GeneratedQuestionResponse, _generated_response(question=question))
    fake_provider.queue(GroundingValidationResult, _grounding(True))
    fake_provider.queue(MCQValidationResult, _mcq(True))
    fake_provider.queue(CategoryValidationResult, _category(category, True))
    fake_provider.queue(QualityValidationResult, _quality(True))
    # Queued as a fallback in case course-book retrieval (real TF-IDF, not
    # mocked) finds anything at all for this candidate - char-n-gram
    # cosine similarity is only ever exactly zero for genuinely disjoint
    # character content, so a real LLM call is possible even for
    # "unrelated" text. If retrieval finds nothing, TextbookValidator's
    # own empty-retrieval short-circuit means this queued response is
    # simply never consumed.
    fake_provider.queue(TextbookCheckResult, _textbook(textbook_status))


# ---------------------------------------------------------------------------
# Scenario: all candidates accepted first attempt (single category)
# ---------------------------------------------------------------------------


def test_all_accepted_first_attempt_produces_complete_exam_and_audit():
    orchestrator, fake_provider = _build_pipeline(
        student_summary_corpus=_student_summary_corpus(),
        course_book_corpus=_course_book_corpus_no_overlap(),
        historical_repository=_historical_repository(),
        canonical_categories=[CATEGORY_A],
    )
    _queue_passing_attempt(fake_provider, category=CATEGORY_A)

    result = orchestrator.generate_exam(ExamRequest(categories={CATEGORY_A: 1}))

    assert len(result.exam.questions) == 1
    assert result.productions[0].production.attempts[0].attempt_number == 1

    bundle = build_exam_output_bundle(
        result,
        exam_id="integration-test",
        generated_at=datetime.now(timezone.utc),
        llm_config=LLMConfig(
            provider="fake", model="fake-model",
            generation=LLMGenerationParams(temperature=0.7, max_tokens=800),
            validation=LLMValidationParams(temperature=0.2, max_tokens=500),
        ),
        diversity_target=0.7,
    )
    assert len(bundle.audit.questions) == 1
    assert bundle.audit.questions[0].attempts[0].accepted is True


# ---------------------------------------------------------------------------
# Scenario: candidate rejected then accepted
# ---------------------------------------------------------------------------


def test_candidate_rejected_then_accepted():
    orchestrator, fake_provider = _build_pipeline(
        student_summary_corpus=_student_summary_corpus(),
        course_book_corpus=_course_book_corpus_no_overlap(),
        historical_repository=_historical_repository(),
        canonical_categories=[CATEGORY_A],
    )
    # Attempt 1: rejected (MCQ fails).
    fake_provider.queue(GeneratedQuestionResponse, _generated_response(question="שאלה ראשונה"))
    fake_provider.queue(GroundingValidationResult, _grounding(True))
    fake_provider.queue(MCQValidationResult, _mcq(False))
    fake_provider.queue(CategoryValidationResult, _category(CATEGORY_A, True))
    fake_provider.queue(QualityValidationResult, _quality(True))
    fake_provider.queue(TextbookCheckResult, _textbook(TextbookCheckStatus.NOT_FOUND))
    # Attempt 2: accepted.
    _queue_passing_attempt(fake_provider, category=CATEGORY_A, question="שאלה שנייה")

    result = orchestrator.generate_exam(ExamRequest(categories={CATEGORY_A: 1}))

    attempts = result.productions[0].production.attempts
    assert len(attempts) == 2
    assert attempts[0].accepted is False
    assert attempts[1].accepted is True
    assert result.exam.questions[0].question == "שאלה שנייה"


# ---------------------------------------------------------------------------
# Scenario: attempts exhausted
# ---------------------------------------------------------------------------


def test_attempts_exhausted_propagates_as_question_production_failed():
    orchestrator, fake_provider = _build_pipeline(
        student_summary_corpus=_student_summary_corpus(),
        course_book_corpus=_course_book_corpus_no_overlap(),
        historical_repository=_historical_repository(),
        canonical_categories=[CATEGORY_A],
        max_generation_attempts=2,
    )
    for i in range(2):
        fake_provider.queue(GeneratedQuestionResponse, _generated_response(question=f"שאלה {i}"))
        fake_provider.queue(GroundingValidationResult, _grounding(False))
        fake_provider.queue(MCQValidationResult, _mcq(True))
        fake_provider.queue(CategoryValidationResult, _category(CATEGORY_A, True))
        fake_provider.queue(QualityValidationResult, _quality(True))
        fake_provider.queue(TextbookCheckResult, _textbook(TextbookCheckStatus.NOT_FOUND))

    with pytest.raises(QuestionProductionFailedError) as excinfo:
        orchestrator.generate_exam(ExamRequest(categories={CATEGORY_A: 1}))

    assert excinfo.value.attempts_exhausted is not None
    assert len(excinfo.value.attempts_exhausted) == 2


# ---------------------------------------------------------------------------
# Scenario: textbook NOT_FOUND (empty course-book retrieval) with otherwise
# accepted candidate
# ---------------------------------------------------------------------------


def test_textbook_not_found_does_not_block_acceptance():
    orchestrator, fake_provider = _build_pipeline(
        student_summary_corpus=_student_summary_corpus(),
        course_book_corpus=_course_book_corpus_no_overlap(),
        historical_repository=_historical_repository(),
        canonical_categories=[CATEGORY_A],
    )
    # Course-book content is deliberately unrelated to this category's
    # query; a NOT_FOUND fallback is queued in case retrieval still finds
    # a nonzero (but weak) match - either the empty-retrieval short-circuit
    # or a genuine LLM-judged NOT_FOUND both demonstrate the same WP-012
    # invariant under test here: NOT_FOUND never blocks acceptance.
    _queue_passing_attempt(fake_provider, category=CATEGORY_A, textbook_status=TextbookCheckStatus.NOT_FOUND)

    result = orchestrator.generate_exam(ExamRequest(categories={CATEGORY_A: 1}))

    validations = result.productions[0].production.attempts[0].validations
    assert validations.textbook.status == TextbookCheckStatus.NOT_FOUND
    assert validations.accepted is True


# ---------------------------------------------------------------------------
# Scenario: textbook POTENTIAL_CONFLICT blocks acceptance
# ---------------------------------------------------------------------------


def test_textbook_potential_conflict_blocks_acceptance_and_exhausts():
    orchestrator, fake_provider = _build_pipeline(
        student_summary_corpus=_student_summary_corpus(),
        course_book_corpus=_course_book_corpus_with_overlap(),
        historical_repository=_historical_repository(),
        canonical_categories=[CATEGORY_A],
        max_generation_attempts=1,
    )
    fake_provider.queue(GeneratedQuestionResponse, _generated_response())
    fake_provider.queue(GroundingValidationResult, _grounding(True))
    fake_provider.queue(MCQValidationResult, _mcq(True))
    fake_provider.queue(CategoryValidationResult, _category(CATEGORY_A, True))
    fake_provider.queue(QualityValidationResult, _quality(True))
    fake_provider.queue(TextbookCheckResult, _textbook(TextbookCheckStatus.POTENTIAL_CONFLICT))

    with pytest.raises(QuestionProductionFailedError) as excinfo:
        orchestrator.generate_exam(ExamRequest(categories={CATEGORY_A: 1}))

    attempt = excinfo.value.attempts_exhausted[0]
    assert attempt.accepted is False
    assert attempt.validations.textbook.status == TextbookCheckStatus.POTENTIAL_CONFLICT
    assert attempt.validations.grounding.passed is True  # primary validators all passed


# ---------------------------------------------------------------------------
# Scenario: duplicate candidate replacement
# ---------------------------------------------------------------------------


def test_duplicate_candidate_is_replaced():
    orchestrator, fake_provider = _build_pipeline(
        student_summary_corpus=_student_summary_corpus(),
        course_book_corpus=_course_book_corpus_no_overlap(),
        historical_repository=_historical_repository(),
        canonical_categories=[CATEGORY_A],
        max_duplicate_replacement_attempts=2,
    )
    # First planned question: unique.
    _queue_passing_attempt(fake_provider, category=CATEGORY_A, question="שאלה ייחודית")
    # Second planned question: duplicate of the first, then a unique replacement.
    _queue_passing_attempt(fake_provider, category=CATEGORY_A, question="שאלה ייחודית")
    _queue_passing_attempt(fake_provider, category=CATEGORY_A, question="שאלה שונה")

    result = orchestrator.generate_exam(ExamRequest(categories={CATEGORY_A: 2}))

    questions = [q.question for q in result.exam.questions]
    assert questions == ["שאלה ייחודית", "שאלה שונה"]
    assert result.productions[1].duplicate_replacement_attempts == 1


# ---------------------------------------------------------------------------
# Scenario: operational failure propagation
# ---------------------------------------------------------------------------


def test_operational_failure_propagates_immediately():
    orchestrator, fake_provider = _build_pipeline(
        student_summary_corpus=_student_summary_corpus(),
        course_book_corpus=_course_book_corpus_no_overlap(),
        historical_repository=_historical_repository(),
        canonical_categories=[CATEGORY_A],
    )
    fake_provider.queue(GeneratedQuestionResponse, LLMProviderError("connection failed"))

    with pytest.raises(LLMProviderError):
        orchestrator.generate_exam(ExamRequest(categories={CATEGORY_A: 1}))


# ---------------------------------------------------------------------------
# Scenario: multi-category request
# ---------------------------------------------------------------------------


def test_multi_category_request_produces_exact_requested_distribution():
    orchestrator, fake_provider = _build_pipeline(
        student_summary_corpus=_student_summary_corpus(),
        course_book_corpus=_course_book_corpus_no_overlap(),
        historical_repository=_historical_repository(),
        canonical_categories=[CATEGORY_A, CATEGORY_B],
    )
    _queue_passing_attempt(fake_provider, category=CATEGORY_A, question="שאלה קטגוריה א")
    _queue_passing_attempt(fake_provider, category=CATEGORY_B, question="שאלה קטגוריה ב")

    result = orchestrator.generate_exam(ExamRequest(categories={CATEGORY_A: 1, CATEGORY_B: 1}))

    categories = [q.category for q in result.exam.questions]
    assert categories == [CATEGORY_A, CATEGORY_B]


# ---------------------------------------------------------------------------
# Scenario: STYLE_SIMILAR and INDEPENDENT paths both exercised
# ---------------------------------------------------------------------------


def test_style_similar_and_independent_modes_both_produce_accepted_questions():
    orchestrator, fake_provider = _build_pipeline(
        student_summary_corpus=_student_summary_corpus(),
        course_book_corpus=_course_book_corpus_no_overlap(),
        historical_repository=_historical_repository(),
        canonical_categories=[CATEGORY_A],
    )
    _queue_passing_attempt(fake_provider, category=CATEGORY_A, question="שאלה 1")
    _queue_passing_attempt(fake_provider, category=CATEGORY_A, question="שאלה 2")

    result = orchestrator.generate_exam(ExamRequest(categories={CATEGORY_A: 2}))

    modes = [record.planned.generation_mode for record in result.productions]
    assert modes == [GenerationMode.STYLE_SIMILAR, GenerationMode.INDEPENDENT]


# ---------------------------------------------------------------------------
# Scenario: final clean/audit consistency
# ---------------------------------------------------------------------------


def test_final_clean_and_audit_outputs_are_consistent():
    orchestrator, fake_provider = _build_pipeline(
        student_summary_corpus=_student_summary_corpus(),
        course_book_corpus=_course_book_corpus_no_overlap(),
        historical_repository=_historical_repository(),
        canonical_categories=[CATEGORY_A, CATEGORY_B],
    )
    _queue_passing_attempt(fake_provider, category=CATEGORY_A, question="שאלה קטגוריה א")
    _queue_passing_attempt(fake_provider, category=CATEGORY_B, question="שאלה קטגוריה ב")

    result = orchestrator.generate_exam(ExamRequest(categories={CATEGORY_A: 1, CATEGORY_B: 1}))
    bundle = build_exam_output_bundle(
        result,
        exam_id="consistency-test",
        generated_at=datetime.now(timezone.utc),
        llm_config=LLMConfig(
            provider="fake", model="fake-model",
            generation=LLMGenerationParams(temperature=0.7, max_tokens=800),
            validation=LLMValidationParams(temperature=0.2, max_tokens=500),
        ),
        diversity_target=0.5,
    )

    assert len(bundle.exam.questions) == len(bundle.audit.questions) == 2
    for exam_question, audit_question in zip(bundle.exam.questions, bundle.audit.questions):
        assert exam_question.number == audit_question.number
        assert exam_question.category == audit_question.category
