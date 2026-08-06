from unittest.mock import MagicMock

import pytest
from pydantic import ValidationError

from exam_generator.generation import (
    GenerationContextError,
    InvalidGeneratedOutputError,
    MissingEvidenceError,
    MissingHistoricalReferenceError,
    QuestionGenerator,
)
from exam_generator.historical import HistoricalQuestionRepository
from exam_generator.llm import LLMProfile, LLMProvider, MessageRole
from exam_generator.models import (
    CandidateQuestion,
    GeneratedQuestionResponse,
    GenerationMode,
    HistoricalStyleReference,
    SourceEvidenceChunk,
    SourceType,
)
from exam_generator.prompts import PromptId, PromptRepository
from exam_generator.retrieval import CategoryResolver
from exam_generator.retrieval.models import RetrievalResult

HEBREW_EVIDENCE_TEXT = "קליפת המוח (cerebral cortex) אחראית לתפקודים גבוהים כמו חשיבה ותכנון."
HEBREW_QUESTION_TEXT = "מהו תפקידה העיקרי של קליפת המוח?"
HEBREW_HISTORICAL_QUESTION = "מהי הפונקציה של גזע המוח?"

CATEGORY = "גזע המוח"


# ---------------------------------------------------------------------------
# Fixture helpers
# ---------------------------------------------------------------------------


def _chunk(
    *,
    chunk_id="STUDENT_SUMMARY:s1.pdf:0001:0001",
    source_file="student_summary_1.pdf",
    page=1,
    text=HEBREW_EVIDENCE_TEXT,
) -> SourceEvidenceChunk:
    return SourceEvidenceChunk(
        chunk_id=chunk_id, source_file=source_file, page=page, text=text, source_type=SourceType.STUDENT_SUMMARY
    )


def _historical_reference(
    *,
    historical_question_id=1,
    category=CATEGORY,
    question=HEBREW_HISTORICAL_QUESTION,
    answers=("א", "ב", "ג", "ד"),
    correct_answer=1,
) -> HistoricalStyleReference:
    return HistoricalStyleReference(
        historical_question_id=historical_question_id,
        category=category,
        question=question,
        answers=list(answers),
        correct_answer=correct_answer,
    )


def _generated_response(**kwargs) -> GeneratedQuestionResponse:
    defaults = dict(
        question=HEBREW_QUESTION_TEXT,
        answers=["תשובה א", "תשובה ב", "תשובה ג", "תשובה ד"],
        correct_answer=2,
        evidence_chunk_ids=[],
        historical_reference_id=None,
    )
    defaults.update(kwargs)
    return GeneratedQuestionResponse(**defaults)


class _StubIndex:
    """Minimal fake matching FactualRetrievalIndex.search()'s call shape,
    recording every query for assertions."""

    def __init__(self, results: tuple[RetrievalResult, ...] = ()) -> None:
        self.results = results
        self.calls: list[tuple[str, int | None]] = []

    def search(self, query: str, *, top_k: int | None = None) -> tuple[RetrievalResult, ...]:
        self.calls.append((query, top_k))
        return self.results


class _RecordingPromptRepository:
    """Wraps the real production PromptRepository, recording every
    requested PromptId so tests can assert only the expected prompts were
    used (no validation-prompt access from the generation layer)."""

    def __init__(self, real_repository: PromptRepository) -> None:
        self._real = real_repository
        self.requested_ids: list[PromptId] = []

    def get(self, prompt_id: PromptId):
        self.requested_ids.append(prompt_id)
        return self._real.get(prompt_id)


def _resolver(categories=(CATEGORY,), aliases=None) -> CategoryResolver:
    return CategoryResolver(categories, aliases or {})


def _historical_repository(references=(), categories=(CATEGORY,)) -> HistoricalQuestionRepository:
    return HistoricalQuestionRepository(list(references), list(categories))


def _provider(response: GeneratedQuestionResponse | None = None) -> MagicMock:
    provider = MagicMock(spec=LLMProvider)
    provider.generate_structured.return_value = response if response is not None else _generated_response()
    return provider


PRODUCTION_PROMPT_REPOSITORY = PromptRepository.from_default_location()


def _make_generator(
    *,
    resolver=None,
    index=None,
    historical_repository=None,
    prompt_repository=None,
    provider=None,
):
    return QuestionGenerator(
        category_resolver=resolver or _resolver(),
        student_summary_index=index if index is not None else _StubIndex((RetrievalResult(chunk=_chunk(), score=0.5, rank=1),)),
        historical_repository=historical_repository
        if historical_repository is not None
        else _historical_repository((_historical_reference(),)),
        prompt_repository=prompt_repository or _RecordingPromptRepository(PRODUCTION_PROMPT_REPOSITORY),
        llm_provider=provider or _provider(),
    )


# ---------------------------------------------------------------------------
# Successful generation
# ---------------------------------------------------------------------------


def test_successful_independent_generation():
    generator = _make_generator()
    candidate = generator.generate_candidate_question(category=CATEGORY, generation_mode=GenerationMode.INDEPENDENT)
    assert isinstance(candidate, CandidateQuestion)
    assert candidate.generation_mode == GenerationMode.INDEPENDENT
    assert candidate.category == CATEGORY


def test_successful_style_similar_generation():
    generator = _make_generator()
    candidate = generator.generate_candidate_question(category=CATEGORY, generation_mode=GenerationMode.STYLE_SIMILAR)
    assert isinstance(candidate, CandidateQuestion)
    assert candidate.generation_mode == GenerationMode.STYLE_SIMILAR
    assert candidate.category == CATEGORY


# ---------------------------------------------------------------------------
# Canonical category / retrieval integration
# ---------------------------------------------------------------------------


def test_canonical_category_used_for_retrieval_query():
    index = _StubIndex((RetrievalResult(chunk=_chunk(), score=0.5, rank=1),))
    resolver = _resolver(categories=(CATEGORY,), aliases={"alias name": CATEGORY})
    generator = _make_generator(resolver=resolver, index=index)
    candidate = generator.generate_candidate_question(category="alias name", generation_mode=GenerationMode.INDEPENDENT)
    assert index.calls[0][0] == CATEGORY
    assert candidate.category == CATEGORY


def test_unknown_category_fails_before_llm_call():
    from exam_generator.retrieval import UnknownCategoryError

    provider = _provider()
    generator = _make_generator(provider=provider)
    with pytest.raises(UnknownCategoryError):
        generator.generate_candidate_question(category="not a real category", generation_mode=GenerationMode.INDEPENDENT)
    provider.generate_structured.assert_not_called()


def test_factual_evidence_passed_to_prompt_comes_from_retrieval():
    distinctive_text = "טקסט ראיה ייחודי לבדיקה זו בלבד"
    chunk = _chunk(text=distinctive_text)
    index = _StubIndex((RetrievalResult(chunk=chunk, score=0.5, rank=1),))
    provider = _provider()
    generator = _make_generator(index=index, provider=provider)
    generator.generate_candidate_question(category=CATEGORY, generation_mode=GenerationMode.INDEPENDENT)
    sent_messages = provider.generate_structured.call_args.kwargs["messages"]
    user_message = next(m for m in sent_messages if m.role == MessageRole.USER)
    assert distinctive_text in user_message.content


# ---------------------------------------------------------------------------
# Generation modes / historical reference
# ---------------------------------------------------------------------------


def test_style_similar_supplies_real_historical_reference():
    reference = _historical_reference(historical_question_id=7, question=HEBREW_HISTORICAL_QUESTION)
    hist_repo = _historical_repository((reference,))
    provider = _provider()
    generator = _make_generator(historical_repository=hist_repo, provider=provider)
    generator.generate_candidate_question(category=CATEGORY, generation_mode=GenerationMode.STYLE_SIMILAR)
    sent_messages = provider.generate_structured.call_args.kwargs["messages"]
    user_message = next(m for m in sent_messages if m.role == MessageRole.USER)
    assert HEBREW_HISTORICAL_QUESTION in user_message.content


def test_independent_supplies_no_historical_reference():
    provider = _provider()
    generator = _make_generator(provider=provider)
    generator.generate_candidate_question(category=CATEGORY, generation_mode=GenerationMode.INDEPENDENT)
    sent_messages = provider.generate_structured.call_args.kwargs["messages"]
    user_message = next(m for m in sent_messages if m.role == MessageRole.USER)
    assert "No historical style reference is supplied" in user_message.content
    assert HEBREW_HISTORICAL_QUESTION not in user_message.content


def test_historical_reference_never_treated_as_factual_evidence():
    reference = _historical_reference(question=HEBREW_HISTORICAL_QUESTION)
    hist_repo = _historical_repository((reference,))
    chunk = _chunk(text=HEBREW_EVIDENCE_TEXT)
    index = _StubIndex((RetrievalResult(chunk=chunk, score=0.5, rank=1),))
    provider = _provider()
    generator = _make_generator(historical_repository=hist_repo, index=index, provider=provider)
    generator.generate_candidate_question(category=CATEGORY, generation_mode=GenerationMode.STYLE_SIMILAR)
    sent_messages = provider.generate_structured.call_args.kwargs["messages"]
    content = next(m for m in sent_messages if m.role == MessageRole.USER).content

    evidence_start = content.index("BEGIN FACTUAL EVIDENCE")
    evidence_end = content.index("END FACTUAL EVIDENCE")
    historical_start = content.index("BEGIN HISTORICAL STYLE REFERENCE")

    assert evidence_start < evidence_end < historical_start
    assert HEBREW_HISTORICAL_QUESTION not in content[evidence_start:evidence_end]
    assert HEBREW_EVIDENCE_TEXT in content[evidence_start:evidence_end]


def test_missing_style_reference_fails_clearly():
    empty_hist_repo = _historical_repository(())
    provider = _provider()
    generator = _make_generator(historical_repository=empty_hist_repo, provider=provider)
    with pytest.raises(MissingHistoricalReferenceError):
        generator.generate_candidate_question(category=CATEGORY, generation_mode=GenerationMode.STYLE_SIMILAR)
    provider.generate_structured.assert_not_called()


def test_unsupported_generation_mode_rejected():
    generator = _make_generator()
    with pytest.raises(GenerationContextError):
        generator.generate_candidate_question(category=CATEGORY, generation_mode="NOT_A_REAL_MODE")


# ---------------------------------------------------------------------------
# LLM call shape
# ---------------------------------------------------------------------------


def test_llm_called_through_generation_profile():
    provider = _provider()
    generator = _make_generator(provider=provider)
    generator.generate_candidate_question(category=CATEGORY, generation_mode=GenerationMode.INDEPENDENT)
    assert provider.generate_structured.call_args.kwargs["profile"] == LLMProfile.GENERATION


def test_llm_called_with_generated_question_response_model():
    provider = _provider()
    generator = _make_generator(provider=provider)
    generator.generate_candidate_question(category=CATEGORY, generation_mode=GenerationMode.INDEPENDENT)
    assert provider.generate_structured.call_args.kwargs["response_model"] is GeneratedQuestionResponse


def test_no_retry_loop_exactly_one_llm_call():
    provider = _provider()
    generator = _make_generator(provider=provider)
    generator.generate_candidate_question(category=CATEGORY, generation_mode=GenerationMode.INDEPENDENT)
    assert provider.generate_structured.call_count == 1


def test_structured_output_becomes_valid_candidate_question():
    response = _generated_response(
        question=HEBREW_QUESTION_TEXT, answers=["א", "ב", "ג", "ד"], correct_answer=3
    )
    generator = _make_generator(provider=_provider(response))
    candidate = generator.generate_candidate_question(category=CATEGORY, generation_mode=GenerationMode.INDEPENDENT)
    assert candidate.question == HEBREW_QUESTION_TEXT
    assert candidate.answers == ["א", "ב", "ג", "ד"]
    assert candidate.correct_answer == 3


# ---------------------------------------------------------------------------
# Provenance cannot be falsified
# ---------------------------------------------------------------------------


def test_generated_response_schema_forbids_category_field():
    with pytest.raises(ValidationError):
        GeneratedQuestionResponse(
            question="q", answers=["א", "ב", "ג", "ד"], correct_answer=1, category="invented"
        )


def test_generated_response_schema_forbids_generation_mode_field():
    with pytest.raises(ValidationError):
        GeneratedQuestionResponse(
            question="q", answers=["א", "ב", "ג", "ד"], correct_answer=1, generation_mode="INDEPENDENT"
        )


def test_candidate_category_always_matches_requested_canonical_category():
    resolver = _resolver(categories=(CATEGORY,), aliases={"alias": CATEGORY})
    generator = _make_generator(resolver=resolver)
    candidate = generator.generate_candidate_question(category="alias", generation_mode=GenerationMode.INDEPENDENT)
    assert candidate.category == CATEGORY


def test_candidate_generation_mode_always_matches_requested_mode():
    generator = _make_generator()
    candidate = generator.generate_candidate_question(category=CATEGORY, generation_mode=GenerationMode.STYLE_SIMILAR)
    assert candidate.generation_mode == GenerationMode.STYLE_SIMILAR


def test_invented_evidence_chunk_id_rejected():
    response = _generated_response(evidence_chunk_ids=["NOT_A_SUPPLIED_CHUNK_ID"])
    generator = _make_generator(provider=_provider(response))
    with pytest.raises(InvalidGeneratedOutputError):
        generator.generate_candidate_question(category=CATEGORY, generation_mode=GenerationMode.INDEPENDENT)


def test_valid_evidence_chunk_id_accepted():
    chunk = _chunk(chunk_id="STUDENT_SUMMARY:s1.pdf:0002:0001")
    index = _StubIndex((RetrievalResult(chunk=chunk, score=0.5, rank=1),))
    response = _generated_response(evidence_chunk_ids=["STUDENT_SUMMARY:s1.pdf:0002:0001"])
    generator = _make_generator(index=index, provider=_provider(response))
    candidate = generator.generate_candidate_question(category=CATEGORY, generation_mode=GenerationMode.INDEPENDENT)
    assert isinstance(candidate, CandidateQuestion)


def test_evidence_chunk_id_missing_prefix_rejected():
    chunk = _chunk(chunk_id="STUDENT_SUMMARY:s1.pdf:0002:0001")
    index = _StubIndex((RetrievalResult(chunk=chunk, score=0.5, rank=1),))
    response = _generated_response(evidence_chunk_ids=["s1.pdf:0002:0001"])
    generator = _make_generator(index=index, provider=_provider(response))
    with pytest.raises(InvalidGeneratedOutputError):
        generator.generate_candidate_question(category=CATEGORY, generation_mode=GenerationMode.INDEPENDENT)


def test_shortened_evidence_chunk_id_rejected():
    chunk = _chunk(chunk_id="STUDENT_SUMMARY:s1.pdf:0002:0001")
    index = _StubIndex((RetrievalResult(chunk=chunk, score=0.5, rank=1),))
    response = _generated_response(evidence_chunk_ids=["STUDENT_SUMMARY:s1.pdf:0002"])
    generator = _make_generator(index=index, provider=_provider(response))
    with pytest.raises(InvalidGeneratedOutputError):
        generator.generate_candidate_question(category=CATEGORY, generation_mode=GenerationMode.INDEPENDENT)


def test_wrong_historical_reference_id_rejected():
    reference = _historical_reference(historical_question_id=5)
    hist_repo = _historical_repository((reference,))
    response = _generated_response(historical_reference_id=999)
    generator = _make_generator(historical_repository=hist_repo, provider=_provider(response))
    with pytest.raises(InvalidGeneratedOutputError):
        generator.generate_candidate_question(category=CATEGORY, generation_mode=GenerationMode.STYLE_SIMILAR)


def test_correct_historical_reference_id_accepted():
    reference = _historical_reference(historical_question_id=5)
    hist_repo = _historical_repository((reference,))
    response = _generated_response(historical_reference_id=5)
    generator = _make_generator(historical_repository=hist_repo, provider=_provider(response))
    candidate = generator.generate_candidate_question(category=CATEGORY, generation_mode=GenerationMode.STYLE_SIMILAR)
    assert isinstance(candidate, CandidateQuestion)


def test_independent_response_claiming_historical_reference_id_rejected():
    response = _generated_response(historical_reference_id=1)
    generator = _make_generator(provider=_provider(response))
    with pytest.raises(InvalidGeneratedOutputError):
        generator.generate_candidate_question(category=CATEGORY, generation_mode=GenerationMode.INDEPENDENT)


# ---------------------------------------------------------------------------
# Fail-before-LLM-call behavior
# ---------------------------------------------------------------------------


def test_no_factual_evidence_fails_before_llm_call():
    empty_index = _StubIndex(())
    provider = _provider()
    generator = _make_generator(index=empty_index, provider=provider)
    with pytest.raises(MissingEvidenceError):
        generator.generate_candidate_question(category=CATEGORY, generation_mode=GenerationMode.INDEPENDENT)
    provider.generate_structured.assert_not_called()


# ---------------------------------------------------------------------------
# Scope boundaries
# ---------------------------------------------------------------------------


def test_no_course_book_retrieval_dependency_exists():
    import inspect

    parameters = inspect.signature(QuestionGenerator.__init__).parameters
    assert not any("course_book" in name for name in parameters)


def test_no_validation_prompts_requested():
    recording_repository = _RecordingPromptRepository(PRODUCTION_PROMPT_REPOSITORY)
    generator = _make_generator(prompt_repository=recording_repository)
    generator.generate_candidate_question(category=CATEGORY, generation_mode=GenerationMode.STYLE_SIMILAR)
    assert set(recording_repository.requested_ids) == {PromptId.SYSTEM, PromptId.QUESTION_GENERATION}


def test_returned_candidate_has_no_validation_or_audit_fields():
    generator = _make_generator()
    candidate = generator.generate_candidate_question(category=CATEGORY, generation_mode=GenerationMode.INDEPENDENT)
    assert set(type(candidate).model_fields.keys()) == {
        "question",
        "answers",
        "correct_answer",
        "category",
        "generation_mode",
    }


# ---------------------------------------------------------------------------
# Hebrew / mixed terminology preservation
# ---------------------------------------------------------------------------


def test_hebrew_and_mixed_terminology_survive_unchanged():
    mixed_text = "קליפת המוח (cerebral cortex) ותפקידה ב-Medulla Oblongata"
    response = _generated_response(question=mixed_text, answers=[mixed_text, "ב", "ג", "ד"], correct_answer=1)
    generator = _make_generator(provider=_provider(response))
    candidate = generator.generate_candidate_question(category=CATEGORY, generation_mode=GenerationMode.INDEPENDENT)
    assert candidate.question == mixed_text
    assert candidate.answers[0] == mixed_text
