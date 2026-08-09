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
from pydantic import BaseModel, ValidationError

from exam_generator.category_generation import CategoryQuestionSetService
from exam_generator.config.models import LLMConfig, LLMGenerationParams, LLMValidationParams
from exam_generator.generation import InvalidGeneratedOutputError, QuestionGenerator
from exam_generator.historical import HistoricalQuestionRepository
from exam_generator.llm import LLMMessage, LLMProfile, LLMProvider, LLMProviderError, MessageRole
from exam_generator.models import (
    CategoryValidationResult,
    DistractorArchetype,
    DistractorDesign,
    ExamGenerationStatus,
    ExamRequest,
    GeneratedQuestionResponse,
    GenerationMode,
    GroundingAnswerAssessment,
    GroundingValidationResponse,
    HistoricalStyleReference,
    MCQValidationResult,
    PlannedQuestionTargetResponse,
    QualityValidationResult,
    QuestionBlueprint,
    QuestionDifficulty,
    QuestionTargetPlanningResponse,
    SourceEvidenceChunk,
    SourceType,
    TextbookValidationResponse,
    TextbookCheckStatus,
)
from exam_generator.orchestration import ExamOrchestrator, QuestionProductionFailedError
from exam_generator.output import build_exam_output_bundle, serialize_audit_json
from exam_generator.planning import QuestionTargetPlanner
from exam_generator.production import QuestionAttemptsExhaustedError, QuestionProducer
from exam_generator.prompts import PromptRepository
from exam_generator.retrieval import CategoryResolver, FactualRetrievalIndex
from exam_generator.validation import (
    CategoryValidator,
    GroundingValidator,
    MCQValidator,
    QualityValidator,
    TextbookValidator,
)
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
        #: Every call's messages, in call order, parallel to ``call_log`` -
        #: purely additive observability for tests that need to inspect
        #: actual prompt content, never used to change fake behavior.
        self.messages_log: list[Sequence[LLMMessage]] = []

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
        self.messages_log.append(messages)
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


def _distractor() -> DistractorDesign:
    return DistractorDesign(
        archetype=DistractorArchetype.SIBLING_STRUCTURE,
        plausibility_reason="plausible",
        incorrectness_reason="incorrect for the exact relationship asked",
        evidence_checked=True,
    )


def _blueprint() -> QuestionBlueprint:
    return QuestionBlueprint(
        knowledge_target="knowledge target",
        tested_relationship="tested relationship",
        question_style="direct question",
        intended_difficulty=QuestionDifficulty.MEDIUM,
        correct_answer_role="supported by the evidence",
        distractors=[_distractor(), _distractor(), _distractor()],
    )


def _generated_response(question: str = "שאלה לדוגמה?", correct_answer: int = 1) -> GeneratedQuestionResponse:
    return GeneratedQuestionResponse(
        blueprint=_blueprint(),
        question=question,
        answers=["תשובה א", "תשובה ב", "תשובה ג", "תשובה ד"],
        correct_answer=correct_answer,
        evidence_refs=[],
        historical_reference_id=None,
    )


def _grounding(passed: bool = True) -> GroundingValidationResponse:
    # WP-027: per-option assessments. Every _grounding() call in this file
    # is paired with a _generated_response() using its default
    # correct_answer=1, so only index 1 is ever marked supported here.
    return GroundingValidationResponse(
        grounded=passed,
        answer_assessments=[
            GroundingAnswerAssessment(
                answer_index=i, supported_as_correct=(passed and i == 1), evidence_refs=[], reason="stub"
            )
            for i in (1, 2, 3, 4)
        ],
        reason="stub",
        confidence=0.9,
    )


def _mcq(valid: bool = True) -> MCQValidationResult:
    return MCQValidationResult(valid=valid, exactly_four_answers=True, single_best_answer=valid, reason="stub")


def _category(category: str, valid: bool = True) -> CategoryValidationResult:
    return CategoryValidationResult(valid=valid, requested_category=category, assessed_category=category, reason="stub")


def _quality(valid: bool = True) -> QualityValidationResult:
    return QualityValidationResult(valid=valid, reason="stub")


def _textbook(status: TextbookCheckStatus = TextbookCheckStatus.CONSISTENT) -> TextbookValidationResponse:
    return TextbookValidationResponse(status=status, reason="stub")


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
    target_planner = QuestionTargetPlanner(
        category_resolver=category_resolver,
        student_summary_index=student_summary_index,
        prompt_repository=prompt_repository,
        llm_provider=fake_provider,
    )
    category_question_set_service = CategoryQuestionSetService(
        category_resolver=category_resolver,
        target_planner=target_planner,
        producer=producer,
        max_duplicate_replacement_attempts=max_duplicate_replacement_attempts,
    )
    orchestrator = ExamOrchestrator(
        category_resolver=category_resolver,
        category_question_set_service=category_question_set_service,
    )
    return orchestrator, fake_provider


def _queue_target_plans(fake_provider: FakeLLMProvider, categories: dict) -> None:
    """Queue one WP-025 target-planning response per *planned question*
    (WP-032: ``CategoryGenerationService`` calls ``plan_targets(count=1)``
    once per question, not once per category with the full count), each
    citing no evidence (``evidence_refs=[]``) since these integration
    tests exercise generation/validation/orchestration behavior, not
    planning-provenance resolution itself (see ``test_planning.py`` for
    that)."""
    for category, count in categories.items():
        for i in range(1, count + 1):
            fake_provider.queue(
                QuestionTargetPlanningResponse,
                QuestionTargetPlanningResponse(
                    targets=[
                        PlannedQuestionTargetResponse(topic=f"topic {i}", factual_focus=f"focus {i}", evidence_refs=[])
                    ]
                ),
            )


def _queue_passing_attempt(
    fake_provider: FakeLLMProvider,
    *,
    category: str,
    question: str = "שאלה לדוגמה?",
    textbook_status: TextbookCheckStatus = TextbookCheckStatus.NOT_FOUND,
) -> None:
    fake_provider.queue(GeneratedQuestionResponse, _generated_response(question=question))
    fake_provider.queue(GroundingValidationResponse, _grounding(True))
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
    fake_provider.queue(TextbookValidationResponse, _textbook(textbook_status))


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

    _queue_target_plans(fake_provider, {CATEGORY_A: 1})
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
    fake_provider.queue(GroundingValidationResponse, _grounding(True))
    fake_provider.queue(MCQValidationResult, _mcq(False))
    fake_provider.queue(CategoryValidationResult, _category(CATEGORY_A, True))
    fake_provider.queue(QualityValidationResult, _quality(True))
    fake_provider.queue(TextbookValidationResponse, _textbook(TextbookCheckStatus.NOT_FOUND))
    # Attempt 2: accepted.
    _queue_passing_attempt(fake_provider, category=CATEGORY_A, question="שאלה שנייה")

    _queue_target_plans(fake_provider, {CATEGORY_A: 1})
    result = orchestrator.generate_exam(ExamRequest(categories={CATEGORY_A: 1}))

    attempts = result.productions[0].production.attempts
    assert len(attempts) == 2
    assert attempts[0].accepted is False
    assert attempts[1].accepted is True
    assert result.exam.questions[0].question == "שאלה שנייה"


# ---------------------------------------------------------------------------
# Scenario: attempts exhausted
# ---------------------------------------------------------------------------


def test_attempts_exhausted_is_question_local_and_yields_partial_result():
    # WP-023: WP-013's own attempt-budget exhaustion is question-local -
    # orchestration returns a PARTIAL result rather than raising.
    orchestrator, fake_provider = _build_pipeline(
        student_summary_corpus=_student_summary_corpus(),
        course_book_corpus=_course_book_corpus_no_overlap(),
        historical_repository=_historical_repository(),
        canonical_categories=[CATEGORY_A],
        max_generation_attempts=2,
    )
    for i in range(2):
        fake_provider.queue(GeneratedQuestionResponse, _generated_response(question=f"שאלה {i}"))
        fake_provider.queue(GroundingValidationResponse, _grounding(False))
        fake_provider.queue(MCQValidationResult, _mcq(True))
        fake_provider.queue(CategoryValidationResult, _category(CATEGORY_A, True))
        fake_provider.queue(QualityValidationResult, _quality(True))
        fake_provider.queue(TextbookValidationResponse, _textbook(TextbookCheckStatus.NOT_FOUND))

    _queue_target_plans(fake_provider, {CATEGORY_A: 1})
    result = orchestrator.generate_exam(ExamRequest(categories={CATEGORY_A: 1}))

    assert result.status == ExamGenerationStatus.PARTIAL
    assert result.exam is None
    assert len(result.failed_questions) == 1
    failed = result.failed_questions[0]
    assert failed.failure_type == "QuestionAttemptsExhaustedError"
    assert len(failed.attempts) == 2


def test_partial_exam_end_to_end_through_output_boundary():
    # WP-023 full pipeline: one planned question accepted, the next
    # exhausts locally - the run still reaches the end of its plan, the
    # clean exam contains only the accepted question renumbered to 1, and
    # the audit/output boundary represents both outcomes.
    orchestrator, fake_provider = _build_pipeline(
        student_summary_corpus=_student_summary_corpus(),
        course_book_corpus=_course_book_corpus_no_overlap(),
        historical_repository=_historical_repository(),
        canonical_categories=[CATEGORY_A],
        max_generation_attempts=1,
    )
    # Planned position 1: accepted on the first attempt.
    _queue_passing_attempt(fake_provider, category=CATEGORY_A, question="שאלה ראשונה")
    # Planned position 2: a single generation-contract failure exhausts the
    # (1-attempt) budget.
    invented_response = GeneratedQuestionResponse(
        blueprint=_blueprint(),
        question="שאלה שנייה?",
        answers=["תשובה א", "תשובה ב", "תשובה ג", "תשובה ד"],
        correct_answer=1,
        evidence_refs=[99],  # WP-024: out-of-range local reference, the new "invented" analog
        historical_reference_id=None,
    )
    fake_provider.queue(GeneratedQuestionResponse, invented_response)

    _queue_target_plans(fake_provider, {CATEGORY_A: 2})
    result = orchestrator.generate_exam(ExamRequest(categories={CATEGORY_A: 2}))

    assert result.status == ExamGenerationStatus.PARTIAL
    assert len(result.exam.questions) == 1
    assert result.exam.questions[0].number == 1
    assert result.exam.questions[0].question == "שאלה ראשונה"

    bundle = build_exam_output_bundle(
        result,
        exam_id="exam-partial-e2e",
        generated_at=datetime.now(timezone.utc),
        llm_config=LLMConfig(
            provider="openai",
            model="gpt-4o-mini",
            generation=LLMGenerationParams(temperature=0.7, max_tokens=800),
            validation=LLMValidationParams(temperature=0.2, max_tokens=500),
        ),
        diversity_target=0.7,
    )
    assert bundle.exam is not None
    assert len(bundle.exam.questions) == 1
    assert bundle.audit.status.value == "PARTIAL"
    assert bundle.audit.planned_question_count == 2
    assert bundle.audit.accepted_count == 1
    assert bundle.audit.failed_count == 1
    assert bundle.audit.questions[0].planned_position == 1
    assert bundle.audit.failed_questions[0].planned_position == 2

    serialized = serialize_audit_json(bundle.audit)
    assert "Evidence" not in serialized  # no local reference leaks into canonical output


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

    _queue_target_plans(fake_provider, {CATEGORY_A: 1})
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
    fake_provider.queue(GroundingValidationResponse, _grounding(True))
    fake_provider.queue(MCQValidationResult, _mcq(True))
    fake_provider.queue(CategoryValidationResult, _category(CATEGORY_A, True))
    fake_provider.queue(QualityValidationResult, _quality(True))
    fake_provider.queue(TextbookValidationResponse, _textbook(TextbookCheckStatus.POTENTIAL_CONFLICT))

    _queue_target_plans(fake_provider, {CATEGORY_A: 1})
    result = orchestrator.generate_exam(ExamRequest(categories={CATEGORY_A: 1}))

    assert result.status == ExamGenerationStatus.PARTIAL
    attempt = result.failed_questions[0].attempts[0]
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

    _queue_target_plans(fake_provider, {CATEGORY_A: 2})
    result = orchestrator.generate_exam(ExamRequest(categories={CATEGORY_A: 2}))

    questions = [q.question for q in result.exam.questions]
    assert questions == ["שאלה ייחודית", "שאלה שונה"]
    assert result.productions[1].duplicate_replacement_attempts == 1


# ---------------------------------------------------------------------------
# Scenario: operational failure propagation
# ---------------------------------------------------------------------------


def test_operational_failure_propagates_immediately():
    # WP-019: no retry occurs, and the exam-level failure is contextualized
    # (position/category/mode/completed count) rather than the raw
    # LLMProviderError propagating unwrapped - the original cause remains
    # inspectable via QuestionProductionFailedError.operational_cause and
    # standard exception chaining.
    orchestrator, fake_provider = _build_pipeline(
        student_summary_corpus=_student_summary_corpus(),
        course_book_corpus=_course_book_corpus_no_overlap(),
        historical_repository=_historical_repository(),
        canonical_categories=[CATEGORY_A],
    )
    fake_provider.queue(GeneratedQuestionResponse, LLMProviderError("connection failed"))

    with pytest.raises(QuestionProductionFailedError) as excinfo:
        _queue_target_plans(fake_provider, {CATEGORY_A: 1})
        orchestrator.generate_exam(ExamRequest(categories={CATEGORY_A: 1}))

    assert isinstance(excinfo.value.operational_cause, LLMProviderError)
    assert isinstance(excinfo.value.__cause__, LLMProviderError)
    assert excinfo.value.planned_question.position == 1
    assert excinfo.value.planned_question.category == CATEGORY_A
    assert excinfo.value.completed_productions == ()
    assert fake_provider.call_log.count((GeneratedQuestionResponse, LLMProfile.GENERATION)) == 1


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

    _queue_target_plans(fake_provider, {CATEGORY_A: 1, CATEGORY_B: 1})
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

    _queue_target_plans(fake_provider, {CATEGORY_A: 2})
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

    _queue_target_plans(fake_provider, {CATEGORY_A: 1, CATEGORY_B: 1})
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


# ---------------------------------------------------------------------------
# WP-018: reliability hardening scenarios - invalid structured output,
# provenance violations, and structural quality must each classify
# correctly as operational failure vs. normal candidate-quality rejection.
# ---------------------------------------------------------------------------


def test_invalid_structured_validator_output_is_an_operational_failure():
    # A pydantic ValidationError (e.g. the raw structured-output-model-level
    # empty-reason contract violation WP-018 investigates) must still
    # propagate as an operational failure, never be silently treated as a
    # rejection - WP-019 only makes GENERATION-contract failures
    # recoverable, never a validator's own structured-output failure.
    try:
        QualityValidationResult(valid=True, reason="")
    except ValidationError as exc:
        raw_validation_error = exc
    else:
        raise AssertionError("expected QualityValidationResult(reason='') to raise ValidationError")

    orchestrator, fake_provider = _build_pipeline(
        student_summary_corpus=_student_summary_corpus(),
        course_book_corpus=_course_book_corpus_no_overlap(),
        historical_repository=_historical_repository(),
        canonical_categories=[CATEGORY_A],
    )
    fake_provider.queue(GeneratedQuestionResponse, _generated_response())
    fake_provider.queue(GroundingValidationResponse, _grounding(True))
    fake_provider.queue(MCQValidationResult, _mcq(True))
    fake_provider.queue(CategoryValidationResult, _category(CATEGORY_A, True))
    fake_provider.queue(QualityValidationResult, raw_validation_error)

    with pytest.raises(QuestionProductionFailedError) as excinfo:
        _queue_target_plans(fake_provider, {CATEGORY_A: 1})
        orchestrator.generate_exam(ExamRequest(categories={CATEGORY_A: 1}))

    assert isinstance(excinfo.value.operational_cause, ValidationError)
    assert isinstance(excinfo.value.__cause__, ValidationError)


def test_generation_provenance_violation_is_recovered_within_the_attempt_budget():
    # WP-019: a single recoverable generation-contract failure (WP-024: an
    # out-of-range local evidence_refs value) is discarded and retried -
    # not an operational failure at all anymore. No validator is ever
    # called for the discarded attempt (nothing queued for it would be
    # consumed).
    orchestrator, fake_provider = _build_pipeline(
        student_summary_corpus=_student_summary_corpus(),
        course_book_corpus=_course_book_corpus_no_overlap(),
        historical_repository=_historical_repository(),
        canonical_categories=[CATEGORY_A],
        max_generation_attempts=3,
    )
    invented_response = GeneratedQuestionResponse(
        blueprint=_blueprint(),
        question="שאלה לדוגמה?",
        answers=["תשובה א", "תשובה ב", "תשובה ג", "תשובה ד"],
        correct_answer=1,
        evidence_refs=[99],  # WP-024: out-of-range local reference, the new "invented" analog
        historical_reference_id=None,
    )
    fake_provider.queue(GeneratedQuestionResponse, invented_response)
    _queue_passing_attempt(fake_provider, category=CATEGORY_A, question="שאלה תקינה")

    _queue_target_plans(fake_provider, {CATEGORY_A: 1})
    result = orchestrator.generate_exam(ExamRequest(categories={CATEGORY_A: 1}))

    attempts = result.productions[0].production.attempts
    assert len(attempts) == 2
    assert attempts[0].is_generation_contract_failure is True
    assert attempts[0].candidate is None
    assert attempts[0].validations is None
    assert attempts[0].accepted is False
    assert attempts[1].accepted is True
    assert result.exam.questions[0].question == "שאלה תקינה"
    # No MCQ/category/quality/textbook/grounding call was made for the
    # discarded attempt - only one full validation cycle occurred.
    assert fake_provider.call_log.count((MCQValidationResult, LLMProfile.VALIDATION)) == 1


def test_generation_provenance_violation_exhausts_when_every_attempt_is_invalid():
    # WP-023: WP-013's attempt-budget exhaustion is question-local -
    # orchestration returns a PARTIAL result rather than raising, even
    # when every discarded attempt was a generation-contract failure.
    orchestrator, fake_provider = _build_pipeline(
        student_summary_corpus=_student_summary_corpus(),
        course_book_corpus=_course_book_corpus_no_overlap(),
        historical_repository=_historical_repository(),
        canonical_categories=[CATEGORY_A],
        max_generation_attempts=3,
    )
    invented_response = GeneratedQuestionResponse(
        blueprint=_blueprint(),
        question="שאלה לדוגמה?",
        answers=["תשובה א", "תשובה ב", "תשובה ג", "תשובה ד"],
        correct_answer=1,
        evidence_refs=[99],  # WP-024: out-of-range local reference, the new "invented" analog
        historical_reference_id=None,
    )
    for _ in range(3):
        fake_provider.queue(GeneratedQuestionResponse, invented_response)

    _queue_target_plans(fake_provider, {CATEGORY_A: 1})
    result = orchestrator.generate_exam(ExamRequest(categories={CATEGORY_A: 1}))

    assert result.status == ExamGenerationStatus.PARTIAL
    assert result.exam is None
    failed = result.failed_questions[0]
    assert len(failed.attempts) == 3
    assert all(attempt.is_generation_contract_failure for attempt in failed.attempts)
    assert failed.planned.position == 1
    assert result.productions == ()
    # No MCQ/grounding/etc. call was ever made - every attempt was
    # discarded before validation.
    assert fake_provider.call_log.count((MCQValidationResult, LLMProfile.VALIDATION)) == 0


def test_generation_provenance_violation_then_quality_rejection_then_accepted():
    # WP-019: contract failures and candidate-quality rejections share one
    # bounded attempt budget.
    orchestrator, fake_provider = _build_pipeline(
        student_summary_corpus=_student_summary_corpus(),
        course_book_corpus=_course_book_corpus_no_overlap(),
        historical_repository=_historical_repository(),
        canonical_categories=[CATEGORY_A],
        max_generation_attempts=3,
    )
    invented_response = GeneratedQuestionResponse(
        blueprint=_blueprint(),
        question="שאלה לדוגמה?",
        answers=["תשובה א", "תשובה ב", "תשובה ג", "תשובה ד"],
        correct_answer=1,
        evidence_refs=[99],  # WP-024: out-of-range local reference, the new "invented" analog
        historical_reference_id=None,
    )
    fake_provider.queue(GeneratedQuestionResponse, invented_response)
    # Attempt 2: valid candidate but MCQ rejects.
    fake_provider.queue(GeneratedQuestionResponse, _generated_response(question="שאלה שנייה"))
    fake_provider.queue(GroundingValidationResponse, _grounding(True))
    fake_provider.queue(MCQValidationResult, _mcq(False))
    fake_provider.queue(CategoryValidationResult, _category(CATEGORY_A, True))
    fake_provider.queue(QualityValidationResult, _quality(True))
    fake_provider.queue(TextbookValidationResponse, _textbook(TextbookCheckStatus.NOT_FOUND))
    # Attempt 3: accepted.
    _queue_passing_attempt(fake_provider, category=CATEGORY_A, question="שאלה שלישית")

    _queue_target_plans(fake_provider, {CATEGORY_A: 1})
    result = orchestrator.generate_exam(ExamRequest(categories={CATEGORY_A: 1}))

    attempts = result.productions[0].production.attempts
    assert len(attempts) == 3
    assert attempts[0].is_generation_contract_failure is True
    assert attempts[1].is_generation_contract_failure is False
    assert attempts[1].accepted is False
    assert attempts[2].accepted is True
    assert result.exam.questions[0].question == "שאלה שלישית"


def test_grounding_provenance_violation_is_question_local_after_wp021_retry_exhausts():
    # WP-021: a single invented grounding evidence id is retried once (same
    # logical validation) before exhausting. WP-023: that exhaustion
    # (InvalidGroundingOutputError) is question-local - orchestration
    # returns a PARTIAL result rather than raising.
    orchestrator, fake_provider = _build_pipeline(
        student_summary_corpus=_student_summary_corpus(),
        course_book_corpus=_course_book_corpus_no_overlap(),
        historical_repository=_historical_repository(),
        canonical_categories=[CATEGORY_A],
    )
    fake_provider.queue(GeneratedQuestionResponse, _generated_response())
    invented_grounding = GroundingValidationResponse(
        grounded=True,
        answer_assessments=[
            GroundingAnswerAssessment(answer_index=1, supported_as_correct=True, evidence_refs=[99], reason="stub"),
            GroundingAnswerAssessment(answer_index=2, supported_as_correct=False, evidence_refs=[], reason="stub"),
            GroundingAnswerAssessment(answer_index=3, supported_as_correct=False, evidence_refs=[], reason="stub"),
            GroundingAnswerAssessment(answer_index=4, supported_as_correct=False, evidence_refs=[], reason="stub"),
        ],
        reason="stub",
        confidence=0.9,
    )
    fake_provider.queue(GroundingValidationResponse, invented_grounding, invented_grounding)

    _queue_target_plans(fake_provider, {CATEGORY_A: 1})
    result = orchestrator.generate_exam(ExamRequest(categories={CATEGORY_A: 1}))

    assert result.status == ExamGenerationStatus.PARTIAL
    assert result.failed_questions[0].failure_type == "InvalidGroundingOutputError"
    assert fake_provider.call_log.count((GroundingValidationResponse, LLMProfile.VALIDATION)) == 2


def test_textbook_provenance_violation_is_question_local_after_wp021_retry_exhausts():
    # WP-023: same retry-then-exhaust behavior for textbook provenance;
    # exhaustion is question-local, yielding a PARTIAL result.
    orchestrator, fake_provider = _build_pipeline(
        student_summary_corpus=_student_summary_corpus(),
        course_book_corpus=_course_book_corpus_with_overlap(),
        historical_repository=_historical_repository(),
        canonical_categories=[CATEGORY_A],
    )
    fake_provider.queue(GeneratedQuestionResponse, _generated_response())
    fake_provider.queue(GroundingValidationResponse, _grounding(True))
    fake_provider.queue(MCQValidationResult, _mcq(True))
    fake_provider.queue(CategoryValidationResult, _category(CATEGORY_A, True))
    fake_provider.queue(QualityValidationResult, _quality(True))
    invented_textbook = TextbookValidationResponse(
        status=TextbookCheckStatus.CONSISTENT,
        evidence_refs=[99],
        reason="stub",
    )
    fake_provider.queue(TextbookValidationResponse, invented_textbook, invented_textbook)

    _queue_target_plans(fake_provider, {CATEGORY_A: 1})
    result = orchestrator.generate_exam(ExamRequest(categories={CATEGORY_A: 1}))

    assert result.status == ExamGenerationStatus.PARTIAL
    assert result.failed_questions[0].failure_type == "InvalidTextbookOutputError"
    assert fake_provider.call_log.count((TextbookValidationResponse, LLMProfile.VALIDATION)) == 2


def test_multi_question_exam_recovers_a_later_planned_questions_contract_failure():
    # WP-019 section 22: one later planned question experiences a
    # recoverable generation-contract failure and then succeeds; earlier
    # completed questions and the final exam output remain correct.
    orchestrator, fake_provider = _build_pipeline(
        student_summary_corpus=_student_summary_corpus(),
        course_book_corpus=_course_book_corpus_no_overlap(),
        historical_repository=_historical_repository(),
        canonical_categories=[CATEGORY_A, CATEGORY_B],
        max_generation_attempts=3,
    )
    _queue_passing_attempt(fake_provider, category=CATEGORY_A, question="שאלה ראשונה")
    invented_response = GeneratedQuestionResponse(
        blueprint=_blueprint(),
        question="שאלה לדוגמה?",
        answers=["תשובה א", "תשובה ב", "תשובה ג", "תשובה ד"],
        correct_answer=1,
        evidence_refs=[99],  # WP-024: out-of-range local reference, the new "invented" analog
        historical_reference_id=None,
    )
    fake_provider.queue(GeneratedQuestionResponse, invented_response)
    _queue_passing_attempt(fake_provider, category=CATEGORY_B, question="שאלה שנייה")

    _queue_target_plans(fake_provider, {CATEGORY_A: 1, CATEGORY_B: 1})
    result = orchestrator.generate_exam(ExamRequest(categories={CATEGORY_A: 1, CATEGORY_B: 1}))

    assert [q.question for q in result.exam.questions] == ["שאלה ראשונה", "שאלה שנייה"]
    assert len(result.productions[0].production.attempts) == 1
    assert len(result.productions[1].production.attempts) == 2
    assert result.productions[1].production.attempts[0].is_generation_contract_failure is True


def test_duplicated_answer_numbering_is_a_normal_quality_rejection_not_a_failure():
    # The deterministic structural pre-check (WP-018) short-circuits before
    # any LLM validation call, so no QualityValidationResult is queued for
    # the defective attempt - if the pipeline tried to call the LLM anyway,
    # FakeLLMProvider would raise AssertionError for under-provisioning.
    orchestrator, fake_provider = _build_pipeline(
        student_summary_corpus=_student_summary_corpus(),
        course_book_corpus=_course_book_corpus_no_overlap(),
        historical_repository=_historical_repository(),
        canonical_categories=[CATEGORY_A],
        max_generation_attempts=2,
    )
    defective_response = GeneratedQuestionResponse(
        blueprint=_blueprint(),
        question="שאלה לדוגמה?",
        answers=[
            "1. לטרלית ל-Olfactory Tract",
            "2. מדיאלית ל-Olfactory Tract",
            "תשובה ג",
            "תשובה ד",
        ],
        correct_answer=1,
        evidence_refs=[],
        historical_reference_id=None,
    )
    fake_provider.queue(GeneratedQuestionResponse, defective_response)
    fake_provider.queue(GroundingValidationResponse, _grounding(True))
    fake_provider.queue(MCQValidationResult, _mcq(True))
    fake_provider.queue(CategoryValidationResult, _category(CATEGORY_A, True))
    # No QualityValidationResult queued - the structural pre-check must
    # reject before reaching the LLM call. Textbook is still queued as a
    # fallback (all five validators run regardless of quality's verdict),
    # per the same real-TF-IDF caveat _queue_passing_attempt documents.
    fake_provider.queue(TextbookValidationResponse, _textbook(TextbookCheckStatus.NOT_FOUND))
    _queue_passing_attempt(fake_provider, category=CATEGORY_A, question="שאלה תקינה")

    _queue_target_plans(fake_provider, {CATEGORY_A: 1})
    result = orchestrator.generate_exam(ExamRequest(categories={CATEGORY_A: 1}))

    attempts = result.productions[0].production.attempts
    assert attempts[0].accepted is False
    assert attempts[0].validations.quality.valid is False
    assert "numbering" in attempts[0].validations.quality.reason.lower()
    assert attempts[1].accepted is True
    assert result.exam.questions[0].question == "שאלה תקינה"


# ---------------------------------------------------------------------------
# WP-021: bounded validator provenance recovery
# ---------------------------------------------------------------------------


def test_grounding_provenance_retry_recovers_within_one_question_attempt():
    orchestrator, fake_provider = _build_pipeline(
        student_summary_corpus=_student_summary_corpus(),
        course_book_corpus=_course_book_corpus_no_overlap(),
        historical_repository=_historical_repository(),
        canonical_categories=[CATEGORY_A],
    )
    fake_provider.queue(GeneratedQuestionResponse, _generated_response())
    invented_grounding = GroundingValidationResponse(
        grounded=True,
        answer_assessments=[
            GroundingAnswerAssessment(answer_index=1, supported_as_correct=True, evidence_refs=[99], reason="stub"),
            GroundingAnswerAssessment(answer_index=2, supported_as_correct=False, evidence_refs=[], reason="stub"),
            GroundingAnswerAssessment(answer_index=3, supported_as_correct=False, evidence_refs=[], reason="stub"),
            GroundingAnswerAssessment(answer_index=4, supported_as_correct=False, evidence_refs=[], reason="stub"),
        ],
        reason="stub",
        confidence=0.9,
    )
    fake_provider.queue(GroundingValidationResponse, invented_grounding, _grounding(True))
    fake_provider.queue(MCQValidationResult, _mcq(True))
    fake_provider.queue(CategoryValidationResult, _category(CATEGORY_A, True))
    fake_provider.queue(QualityValidationResult, _quality(True))
    fake_provider.queue(TextbookValidationResponse, _textbook(TextbookCheckStatus.NOT_FOUND))

    _queue_target_plans(fake_provider, {CATEGORY_A: 1})
    result = orchestrator.generate_exam(ExamRequest(categories={CATEGORY_A: 1}))

    assert len(result.exam.questions) == 1
    # The WP-021 provenance retry is internal to one logical validation -
    # still exactly one QuestionAttempt, not two.
    assert len(result.productions[0].production.attempts) == 1
    assert fake_provider.call_log.count((GroundingValidationResponse, LLMProfile.VALIDATION)) == 2


# ---------------------------------------------------------------------------
# WP-022: local evidence references never leak into audit/output
# ---------------------------------------------------------------------------


def test_grounding_local_reference_never_leaks_into_serialized_audit():
    orchestrator, fake_provider = _build_pipeline(
        student_summary_corpus=_student_summary_corpus(),
        course_book_corpus=_course_book_corpus_no_overlap(),
        historical_repository=_historical_repository(),
        canonical_categories=[CATEGORY_A],
    )
    fake_provider.queue(GeneratedQuestionResponse, _generated_response())
    fake_provider.queue(
        GroundingValidationResponse,
        GroundingValidationResponse(
            grounded=True,
            answer_assessments=[
                GroundingAnswerAssessment(answer_index=1, supported_as_correct=True, evidence_refs=[1], reason="stub"),
                GroundingAnswerAssessment(answer_index=2, supported_as_correct=False, evidence_refs=[], reason="stub"),
                GroundingAnswerAssessment(answer_index=3, supported_as_correct=False, evidence_refs=[], reason="stub"),
                GroundingAnswerAssessment(answer_index=4, supported_as_correct=False, evidence_refs=[], reason="stub"),
            ],
            reason="stub",
            confidence=0.9,
        ),
    )
    fake_provider.queue(MCQValidationResult, _mcq(True))
    fake_provider.queue(CategoryValidationResult, _category(CATEGORY_A, True))
    fake_provider.queue(QualityValidationResult, _quality(True))
    fake_provider.queue(TextbookValidationResponse, _textbook(TextbookCheckStatus.NOT_FOUND))

    _queue_target_plans(fake_provider, {CATEGORY_A: 1})
    result = orchestrator.generate_exam(ExamRequest(categories={CATEGORY_A: 1}))
    bundle = build_exam_output_bundle(
        result,
        exam_id="wp022-leak-test",
        generated_at=datetime.now(timezone.utc),
        llm_config=LLMConfig(
            provider="fake", model="fake-model",
            generation=LLMGenerationParams(temperature=0.7, max_tokens=800),
            validation=LLMValidationParams(temperature=0.2, max_tokens=500),
        ),
        diversity_target=0.7,
    )

    audit_json = serialize_audit_json(bundle.audit)
    resolved_ids = bundle.audit.questions[0].attempts[-1].grounding.evidence_chunk_ids
    assert resolved_ids == ["STUDENT_SUMMARY:s1.pdf:0001:0001"]
    assert "STUDENT_SUMMARY:s1.pdf:0001:0001" in audit_json
    assert "Evidence 1" not in audit_json
    assert "[Evidence" not in audit_json
    assert "evidence_refs" not in audit_json


def test_generation_local_reference_never_leaks_downstream():
    # WP-024: generation cites a local evidence_refs value (never a
    # canonical chunk id); nothing downstream (CandidateQuestion, the
    # clean exam, or the serialized audit) may ever surface that raw
    # local reference or the field name it travels in.
    orchestrator, fake_provider = _build_pipeline(
        student_summary_corpus=_student_summary_corpus(),
        course_book_corpus=_course_book_corpus_no_overlap(),
        historical_repository=_historical_repository(),
        canonical_categories=[CATEGORY_A],
    )
    fake_provider.queue(
        GeneratedQuestionResponse,
        GeneratedQuestionResponse(
            blueprint=_blueprint(),
            question="שאלה לדוגמה עם הפניה מקומית",
            answers=["תשובה א", "תשובה ב", "תשובה ג", "תשובה ד"],
            correct_answer=1,
            evidence_refs=[1],
            historical_reference_id=None,
        ),
    )
    fake_provider.queue(GroundingValidationResponse, _grounding(True))
    fake_provider.queue(MCQValidationResult, _mcq(True))
    fake_provider.queue(CategoryValidationResult, _category(CATEGORY_A, True))
    fake_provider.queue(QualityValidationResult, _quality(True))
    fake_provider.queue(TextbookValidationResponse, _textbook(TextbookCheckStatus.NOT_FOUND))

    _queue_target_plans(fake_provider, {CATEGORY_A: 1})
    result = orchestrator.generate_exam(ExamRequest(categories={CATEGORY_A: 1}))
    bundle = build_exam_output_bundle(
        result,
        exam_id="wp024-leak-test",
        generated_at=datetime.now(timezone.utc),
        llm_config=LLMConfig(
            provider="fake", model="fake-model",
            generation=LLMGenerationParams(temperature=0.7, max_tokens=800),
            validation=LLMValidationParams(temperature=0.2, max_tokens=500),
        ),
        diversity_target=0.7,
    )

    assert "evidence_refs" not in type(result.productions[0].production.candidate).model_fields
    audit_json = serialize_audit_json(bundle.audit)
    assert "evidence_refs" not in audit_json


def test_two_distinct_planned_targets_reach_two_distinct_generation_prompts():
    # WP-025 end-to-end (WP-032: target planning now happens once per
    # question rather than once per category): real ExamOrchestrator,
    # real QuestionTargetPlanner, real QuestionGenerator - the two targets
    # planned, one per CategoryGenerationService call, must be the ones
    # actually assigned to the two generation calls, in plan order, each
    # producing genuinely different prompt content.
    orchestrator, fake_provider = _build_pipeline(
        student_summary_corpus=_student_summary_corpus(),
        course_book_corpus=_course_book_corpus_no_overlap(),
        historical_repository=_historical_repository(),
        canonical_categories=[CATEGORY_A],
    )
    fake_provider.queue(
        QuestionTargetPlanningResponse,
        QuestionTargetPlanningResponse(
            targets=[
                PlannedQuestionTargetResponse(
                    topic="target one distinct topic", factual_focus="target one distinct focus", evidence_refs=[]
                ),
            ]
        ),
    )
    fake_provider.queue(
        QuestionTargetPlanningResponse,
        QuestionTargetPlanningResponse(
            targets=[
                PlannedQuestionTargetResponse(
                    topic="target two distinct topic", factual_focus="target two distinct focus", evidence_refs=[]
                ),
            ]
        ),
    )
    _queue_passing_attempt(fake_provider, category=CATEGORY_A, question="שאלה ראשונה")
    _queue_passing_attempt(fake_provider, category=CATEGORY_A, question="שאלה שנייה")

    result = orchestrator.generate_exam(ExamRequest(categories={CATEGORY_A: 2}))

    assert result.status == ExamGenerationStatus.COMPLETE
    assert len(result.exam.questions) == 2

    generation_call_indices = [
        i for i, (response_model, _) in enumerate(fake_provider.call_log) if response_model is GeneratedQuestionResponse
    ]
    assert len(generation_call_indices) == 2
    first_user_content = next(
        m for m in fake_provider.messages_log[generation_call_indices[0]] if m.role == MessageRole.USER
    ).content
    second_user_content = next(
        m for m in fake_provider.messages_log[generation_call_indices[1]] if m.role == MessageRole.USER
    ).content
    assert "target one distinct topic" in first_user_content
    assert "target two distinct topic" not in first_user_content
    assert "target two distinct topic" in second_user_content
    assert "target one distinct topic" not in second_user_content
