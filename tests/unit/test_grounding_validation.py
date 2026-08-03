import inspect
from unittest.mock import MagicMock

import pytest

from exam_generator.llm import LLMProfile, LLMProvider, LLMProviderError, MessageRole
from exam_generator.models import (
    CandidateQuestion,
    GenerationMode,
    GroundingValidationResult,
    SourceEvidenceChunk,
    SourceType,
)
from exam_generator.prompts import GroundingPromptContext, PromptContextError, PromptId, PromptRepository
from exam_generator.retrieval.models import RetrievalResult
from exam_generator.validation import (
    GroundingValidator,
    InvalidGroundingOutputError,
    NoValidationEvidenceError,
)

CATEGORY = "קליפת המוח"
QUESTION_TEXT = "מהו תפקידה העיקרי של קליפת המוח?"
EVIDENCE_TEXT = "קליפת המוח (cerebral cortex) אחראית לתפקודים גבוהים כמו חשיבה ותכנון."


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


def _chunk(
    *,
    chunk_id="STUDENT_SUMMARY:s1.pdf:0001:0001",
    source_file="student_summary_1.pdf",
    page=1,
    text=EVIDENCE_TEXT,
    source_type=SourceType.STUDENT_SUMMARY,
) -> SourceEvidenceChunk:
    return SourceEvidenceChunk(
        chunk_id=chunk_id, source_file=source_file, page=page, text=text, source_type=source_type
    )


def _grounding_result(**kwargs) -> GroundingValidationResult:
    defaults = dict(
        grounded=True,
        correct_answer_supported=True,
        other_answers_not_equally_correct=True,
        evidence_chunk_ids=[],
        reason="supported by the evidence",
        confidence=0.8,
    )
    defaults.update(kwargs)
    return GroundingValidationResult(**defaults)


class _StubIndex:
    """Minimal fake matching FactualRetrievalIndex.search()'s call shape,
    recording every query for assertions."""

    def __init__(self, results: tuple[RetrievalResult, ...] = ()) -> None:
        self.results = results
        self.calls: list[str] = []

    def search(self, query: str, *, top_k=None) -> tuple[RetrievalResult, ...]:
        self.calls.append(query)
        return self.results


class _RecordingPromptRepository:
    """Wraps the real production PromptRepository, recording every
    requested PromptId so tests can assert only the grounding prompt (and
    the shared system prompt) were used - never an MCQ/category/quality/
    textbook validation prompt."""

    def __init__(self, real_repository: PromptRepository) -> None:
        self._real = real_repository
        self.requested_ids: list[PromptId] = []

    def get(self, prompt_id: PromptId):
        self.requested_ids.append(prompt_id)
        return self._real.get(prompt_id)


def _provider(result: GroundingValidationResult | None = None, *, side_effect=None) -> MagicMock:
    provider = MagicMock(spec=LLMProvider)
    if side_effect is not None:
        provider.generate_structured.side_effect = side_effect
    else:
        provider.generate_structured.return_value = result if result is not None else _grounding_result()
    return provider


PRODUCTION_PROMPT_REPOSITORY = PromptRepository.from_default_location()


def _make_validator(*, index=None, prompt_repository=None, provider=None):
    return GroundingValidator(
        student_summary_index=index
        if index is not None
        else _StubIndex((RetrievalResult(chunk=_chunk(), score=0.5, rank=1),)),
        prompt_repository=prompt_repository or _RecordingPromptRepository(PRODUCTION_PROMPT_REPOSITORY),
        llm_provider=provider or _provider(),
    )


# ---------------------------------------------------------------------------
# Grounding pass / fail as normal results
# ---------------------------------------------------------------------------


def test_clearly_supported_candidate_passes():
    passing = _grounding_result(
        grounded=True, correct_answer_supported=True, other_answers_not_equally_correct=True
    )
    validator = _make_validator(provider=_provider(passing))
    result = validator.validate_grounding(_candidate())
    assert result.passed is True


def test_unsupported_candidate_fails_as_normal_result_not_exception():
    failing = _grounding_result(
        grounded=False, correct_answer_supported=False, reason="no supporting evidence found"
    )
    validator = _make_validator(provider=_provider(failing))
    result = validator.validate_grounding(_candidate())
    assert result.passed is False
    assert isinstance(result, GroundingValidationResult)


# ---------------------------------------------------------------------------
# Independent evidence retrieval
# ---------------------------------------------------------------------------


def test_validator_independently_retrieves_evidence():
    index = _StubIndex((RetrievalResult(chunk=_chunk(), score=0.5, rank=1),))
    validator = _make_validator(index=index)
    validator.validate_grounding(_candidate())
    assert len(index.calls) == 1
    assert QUESTION_TEXT in index.calls[0]


def test_retrieval_query_includes_category_question_and_correct_answer():
    index = _StubIndex((RetrievalResult(chunk=_chunk(), score=0.5, rank=1),))
    candidate = _candidate(
        category=CATEGORY,
        question=QUESTION_TEXT,
        answers=["distractor 1", "distractor 2", "correct answer text", "distractor 3"],
        correct_answer=3,
    )
    validator = _make_validator(index=index)
    validator.validate_grounding(candidate)
    query = index.calls[0]
    assert CATEGORY in query
    assert QUESTION_TEXT in query
    assert "correct answer text" in query
    assert "distractor 1" not in query
    assert "distractor 2" not in query
    assert "distractor 3" not in query


def test_candidate_has_no_generation_time_evidence_ids_field_to_blindly_trust():
    # CandidateQuestion (WP-002/WP-009) deliberately carries no
    # evidence_chunk_ids of its own - there is structurally nothing for the
    # validator to blindly reuse from the generator's claims.
    assert "evidence_chunk_ids" not in CandidateQuestion.model_fields
    assert "historical_reference_id" not in CandidateQuestion.model_fields


def test_validate_grounding_signature_has_no_historical_reference_parameter():
    params = inspect.signature(GroundingValidator.validate_grounding).parameters
    assert not any("historical" in name for name in params)


def test_grounding_prompt_context_has_no_historical_reference_field():
    import dataclasses

    field_names = {f.name for f in dataclasses.fields(GroundingPromptContext)}
    assert not any("historical" in name for name in field_names)


# ---------------------------------------------------------------------------
# Source-type boundaries
# ---------------------------------------------------------------------------


def test_validation_evidence_must_be_student_summary_only():
    course_book_chunk = _chunk(
        chunk_id="COURSE_BOOK:course_book.pdf:0001:0001",
        source_file="course_book.pdf",
        source_type=SourceType.COURSE_BOOK,
    )
    index = _StubIndex((RetrievalResult(chunk=course_book_chunk, score=0.5, rank=1),))
    validator = _make_validator(index=index)
    with pytest.raises(PromptContextError):
        validator.validate_grounding(_candidate())


def test_no_course_book_retrieval_dependency_exists():
    parameters = inspect.signature(GroundingValidator.__init__).parameters
    assert not any("course_book" in name for name in parameters)


# ---------------------------------------------------------------------------
# Prompt / LLM call shape
# ---------------------------------------------------------------------------


def test_grounding_production_prompt_is_used():
    recording_repository = _RecordingPromptRepository(PRODUCTION_PROMPT_REPOSITORY)
    validator = _make_validator(prompt_repository=recording_repository)
    validator.validate_grounding(_candidate())
    assert set(recording_repository.requested_ids) == {PromptId.SYSTEM, PromptId.GROUNDING_VALIDATION}


def test_llm_called_through_validation_profile():
    provider = _provider()
    validator = _make_validator(provider=provider)
    validator.validate_grounding(_candidate())
    assert provider.generate_structured.call_args.kwargs["profile"] == LLMProfile.VALIDATION


def test_llm_called_with_grounding_validation_result_model():
    provider = _provider()
    validator = _make_validator(provider=provider)
    validator.validate_grounding(_candidate())
    assert provider.generate_structured.call_args.kwargs["response_model"] is GroundingValidationResult


def test_messages_are_system_then_user():
    provider = _provider()
    validator = _make_validator(provider=provider)
    validator.validate_grounding(_candidate())
    messages = provider.generate_structured.call_args.kwargs["messages"]
    assert [m.role for m in messages] == [MessageRole.SYSTEM, MessageRole.USER]


def test_no_retry_exactly_one_llm_call():
    provider = _provider()
    validator = _make_validator(provider=provider)
    validator.validate_grounding(_candidate())
    assert provider.generate_structured.call_count == 1


# ---------------------------------------------------------------------------
# Supporting-evidence-id provenance
# ---------------------------------------------------------------------------


def test_returned_supporting_evidence_ids_must_belong_to_supplied_evidence():
    chunk = _chunk(chunk_id="STUDENT_SUMMARY:s1.pdf:0002:0001")
    index = _StubIndex((RetrievalResult(chunk=chunk, score=0.5, rank=1),))
    result = _grounding_result(evidence_chunk_ids=["STUDENT_SUMMARY:s1.pdf:0002:0001"])
    validator = _make_validator(index=index, provider=_provider(result))
    returned = validator.validate_grounding(_candidate())
    assert returned.evidence_chunk_ids == ["STUDENT_SUMMARY:s1.pdf:0002:0001"]


def test_invented_supporting_evidence_id_is_rejected():
    result = _grounding_result(evidence_chunk_ids=["NOT_A_SUPPLIED_CHUNK_ID"])
    validator = _make_validator(provider=_provider(result))
    with pytest.raises(InvalidGroundingOutputError):
        validator.validate_grounding(_candidate())


# ---------------------------------------------------------------------------
# Fail-before-LLM-call / operational-vs-verdict distinction
# ---------------------------------------------------------------------------


def test_empty_retrieval_fails_before_llm_call():
    empty_index = _StubIndex(())
    provider = _provider()
    validator = _make_validator(index=empty_index, provider=provider)
    with pytest.raises(NoValidationEvidenceError):
        validator.validate_grounding(_candidate())
    provider.generate_structured.assert_not_called()


def test_provider_failure_is_operational_error_not_a_failed_verdict():
    provider = _provider(side_effect=LLMProviderError("connection failed"))
    validator = _make_validator(provider=provider)
    with pytest.raises(LLMProviderError):
        validator.validate_grounding(_candidate())


# ---------------------------------------------------------------------------
# Candidate immutability
# ---------------------------------------------------------------------------


def test_candidate_not_mutated():
    candidate = _candidate()
    before = candidate.model_dump()
    validator = _make_validator()
    validator.validate_grounding(candidate)
    assert candidate.model_dump() == before


# ---------------------------------------------------------------------------
# Scope boundaries: no other validation stages triggered
# ---------------------------------------------------------------------------


def test_no_mcq_category_quality_textbook_validation_triggered():
    recording_repository = _RecordingPromptRepository(PRODUCTION_PROMPT_REPOSITORY)
    validator = _make_validator(prompt_repository=recording_repository)
    validator.validate_grounding(_candidate())
    forbidden = {
        PromptId.MCQ_VALIDATION,
        PromptId.CATEGORY_VALIDATION,
        PromptId.QUALITY_VALIDATION,
        PromptId.TEXTBOOK_VALIDATION,
    }
    assert not forbidden.intersection(recording_repository.requested_ids)


# ---------------------------------------------------------------------------
# Generation mode does not change factual authority
# ---------------------------------------------------------------------------


def test_style_similar_candidate_uses_same_grounding_standard():
    style_similar_candidate = _candidate(generation_mode=GenerationMode.STYLE_SIMILAR)
    validator = _make_validator()
    result = validator.validate_grounding(style_similar_candidate)
    assert isinstance(result, GroundingValidationResult)


def test_style_similar_and_independent_candidates_use_identical_prompt_shape():
    recording_repository_a = _RecordingPromptRepository(PRODUCTION_PROMPT_REPOSITORY)
    recording_repository_b = _RecordingPromptRepository(PRODUCTION_PROMPT_REPOSITORY)
    _make_validator(prompt_repository=recording_repository_a).validate_grounding(
        _candidate(generation_mode=GenerationMode.STYLE_SIMILAR)
    )
    _make_validator(prompt_repository=recording_repository_b).validate_grounding(
        _candidate(generation_mode=GenerationMode.INDEPENDENT)
    )
    assert recording_repository_a.requested_ids == recording_repository_b.requested_ids
