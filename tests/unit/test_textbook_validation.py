import inspect
from unittest.mock import MagicMock

import pytest

from exam_generator.llm import LLMAuthenticationError, LLMProfile, LLMProvider, LLMProviderError, LLMRateLimitError, MessageRole
from exam_generator.models import (
    CandidateQuestion,
    GenerationMode,
    SourceEvidenceChunk,
    SourceType,
    TextbookCheckResult,
    TextbookCheckStatus,
    TextbookValidationResponse,
)
from exam_generator.prompts import PromptId, PromptRepository
from exam_generator.retrieval.models import RetrievalResult
from exam_generator.validation import InvalidTextbookOutputError, TextbookValidator

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
    chunk_id="COURSE_BOOK:course_book.pdf:0010:0001",
    source_file="course_book.pdf",
    page=10,
    text=EVIDENCE_TEXT,
    source_type=SourceType.COURSE_BOOK,
) -> SourceEvidenceChunk:
    return SourceEvidenceChunk(
        chunk_id=chunk_id, source_file=source_file, page=page, text=text, source_type=source_type
    )


def _textbook_response(**kwargs) -> TextbookValidationResponse:
    """Builds the LLM-facing response (WP-022): provenance via call-local
    ``evidence_refs`` only - no source_page/reference_text, both now
    deterministically derived by the validator instead."""
    defaults = dict(
        status=TextbookCheckStatus.CONSISTENT,
        evidence_refs=[],
        reason="supported by course-book material",
    )
    defaults.update(kwargs)
    return TextbookValidationResponse(**defaults)


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
    requested PromptId so tests can assert only the textbook prompt (and
    the shared system prompt) were used - never grounding/MCQ/category/
    quality validation prompts."""

    def __init__(self, real_repository: PromptRepository) -> None:
        self._real = real_repository
        self.requested_ids: list[PromptId] = []

    def get(self, prompt_id: PromptId):
        self.requested_ids.append(prompt_id)
        return self._real.get(prompt_id)


def _provider(response: TextbookValidationResponse | None = None, *, side_effect=None) -> MagicMock:
    provider = MagicMock(spec=LLMProvider)
    if side_effect is not None:
        provider.generate_structured.side_effect = side_effect
    else:
        provider.generate_structured.return_value = response if response is not None else _textbook_response()
    return provider


PRODUCTION_PROMPT_REPOSITORY = PromptRepository.from_default_location()


def _make_validator(*, index=None, prompt_repository=None, provider=None) -> TextbookValidator:
    return TextbookValidator(
        course_book_index=index
        if index is not None
        else _StubIndex((RetrievalResult(chunk=_chunk(), score=0.5, rank=1),)),
        prompt_repository=prompt_repository or _RecordingPromptRepository(PRODUCTION_PROMPT_REPOSITORY),
        llm_provider=provider or _provider(),
    )


# ---------------------------------------------------------------------------
# Independent course-book retrieval
# ---------------------------------------------------------------------------


def test_course_book_evidence_is_independently_retrieved():
    index = _StubIndex((RetrievalResult(chunk=_chunk(), score=0.5, rank=1),))
    validator = _make_validator(index=index)
    validator.validate(_candidate())
    assert len(index.calls) == 1


def test_retrieval_query_includes_category_question_and_correct_answer():
    index = _StubIndex((RetrievalResult(chunk=_chunk(), score=0.5, rank=1),))
    candidate = _candidate(
        category=CATEGORY,
        question=QUESTION_TEXT,
        answers=["distractor 1", "distractor 2", "correct answer text", "distractor 3"],
        correct_answer=3,
    )
    validator = _make_validator(index=index)
    validator.validate(candidate)
    query = index.calls[0]
    assert CATEGORY in query
    assert QUESTION_TEXT in query
    assert "correct answer text" in query
    assert "distractor 1" not in query
    assert "distractor 2" not in query
    assert "distractor 3" not in query


def test_only_course_book_index_dependency_exists():
    parameters = inspect.signature(TextbookValidator.__init__).parameters
    assert "course_book_index" in parameters
    assert not any("student_summary" in name for name in parameters)


def test_candidate_generation_evidence_ids_are_not_used_as_provenance():
    # CandidateQuestion (WP-002/WP-009) carries no evidence_chunk_ids field at
    # all - structurally nothing exists for textbook retrieval to reuse.
    assert "evidence_chunk_ids" not in CandidateQuestion.model_fields


def test_historical_references_are_not_used():
    parameters = inspect.signature(TextbookValidator.__init__).parameters
    assert not any("historical" in name for name in parameters)
    validate_parameters = inspect.signature(TextbookValidator.validate).parameters
    assert not any("historical" in name for name in validate_parameters)


# ---------------------------------------------------------------------------
# Prompt / LLM call shape
# ---------------------------------------------------------------------------


def test_textbook_production_prompt_is_used():
    recording_repository = _RecordingPromptRepository(PRODUCTION_PROMPT_REPOSITORY)
    validator = _make_validator(prompt_repository=recording_repository)
    validator.validate(_candidate())
    assert set(recording_repository.requested_ids) == {PromptId.SYSTEM, PromptId.TEXTBOOK_VALIDATION}


def test_llm_called_through_validation_profile():
    provider = _provider()
    validator = _make_validator(provider=provider)
    validator.validate(_candidate())
    assert provider.generate_structured.call_args.kwargs["profile"] == LLMProfile.VALIDATION


def test_llm_called_with_textbook_validation_response_model():
    provider = _provider()
    validator = _make_validator(provider=provider)
    validator.validate(_candidate())
    assert provider.generate_structured.call_args.kwargs["response_model"] is TextbookValidationResponse


def test_messages_are_system_then_user():
    provider = _provider()
    validator = _make_validator(provider=provider)
    validator.validate(_candidate())
    messages = provider.generate_structured.call_args.kwargs["messages"]
    assert [m.role for m in messages] == [MessageRole.SYSTEM, MessageRole.USER]


def test_course_book_evidence_is_formatted_via_wp008():
    provider = _provider()
    validator = _make_validator(provider=provider)
    validator.validate(_candidate())
    messages = provider.generate_structured.call_args.kwargs["messages"]
    assert "BEGIN COURSE-BOOK EVIDENCE" in messages[1].content
    assert EVIDENCE_TEXT in messages[1].content


def test_no_retry_at_most_one_llm_call():
    provider = _provider()
    validator = _make_validator(provider=provider)
    validator.validate(_candidate())
    assert provider.generate_structured.call_count == 1


def test_no_grounding_mcq_category_quality_validation_triggered():
    recording_repository = _RecordingPromptRepository(PRODUCTION_PROMPT_REPOSITORY)
    validator = _make_validator(prompt_repository=recording_repository)
    validator.validate(_candidate())
    forbidden = {
        PromptId.GROUNDING_VALIDATION,
        PromptId.MCQ_VALIDATION,
        PromptId.CATEGORY_VALIDATION,
        PromptId.QUALITY_VALIDATION,
    }
    assert not forbidden.intersection(recording_repository.requested_ids)


# ---------------------------------------------------------------------------
# Verdict semantics
# ---------------------------------------------------------------------------


def test_support_verdict_returned_normally():
    supporting = _textbook_response(status=TextbookCheckStatus.CONSISTENT)
    validator = _make_validator(provider=_provider(supporting))
    result = validator.validate(_candidate())
    assert result.status == TextbookCheckStatus.CONSISTENT
    assert isinstance(result, TextbookCheckResult)


def test_contradiction_verdict_returned_normally():
    contradicting = _textbook_response(status=TextbookCheckStatus.POTENTIAL_CONFLICT, reason="conflicts with evidence")
    validator = _make_validator(provider=_provider(contradicting))
    result = validator.validate(_candidate())
    assert result.status == TextbookCheckStatus.POTENTIAL_CONFLICT


def test_insufficient_evidence_represented_as_not_found_status_from_llm():
    unclear = _textbook_response(status=TextbookCheckStatus.NOT_FOUND, reason="evidence is unclear")
    validator = _make_validator(provider=_provider(unclear))
    result = validator.validate(_candidate())
    assert result.status == TextbookCheckStatus.NOT_FOUND


def test_absence_of_retrieved_evidence_is_not_found_not_contradiction():
    empty_index = _StubIndex(())
    provider = _provider()
    validator = _make_validator(index=empty_index, provider=provider)
    result = validator.validate(_candidate())
    assert result.status == TextbookCheckStatus.NOT_FOUND
    assert result.status != TextbookCheckStatus.POTENTIAL_CONFLICT


def test_absence_of_retrieved_evidence_skips_llm_call_entirely():
    empty_index = _StubIndex(())
    provider = _provider()
    validator = _make_validator(index=empty_index, provider=provider)
    validator.validate(_candidate())
    provider.generate_structured.assert_not_called()


# ---------------------------------------------------------------------------
# WP-022: evidence-reference provenance (call-local -> canonical mapping)
# ---------------------------------------------------------------------------


def test_valid_evidence_ref_resolves_to_canonical_chunk_id_and_page():
    chunk = _chunk(chunk_id="COURSE_BOOK:course_book.pdf:0010:0001", page=10)
    index = _StubIndex((RetrievalResult(chunk=chunk, score=0.5, rank=1),))
    response = _textbook_response(evidence_refs=[1])
    validator = _make_validator(index=index, provider=_provider(response))
    returned = validator.validate(_candidate())
    assert returned.evidence_chunk_ids == ["COURSE_BOOK:course_book.pdf:0010:0001"]
    # source_page is deterministically derived from the resolved chunk -
    # never claimed directly by the LLM (WP-022).
    assert returned.source_page == 10


def test_reference_text_is_always_none_now():
    # WP-022: reference_text is no longer LLM-facing at all; the field
    # remains on the contract for downstream stability, always None.
    chunk = _chunk(text=EVIDENCE_TEXT)
    index = _StubIndex((RetrievalResult(chunk=chunk, score=0.5, rank=1),))
    response = _textbook_response(evidence_refs=[1])
    validator = _make_validator(index=index, provider=_provider(response))
    returned = validator.validate(_candidate())
    assert returned.reference_text is None


def test_no_evidence_refs_means_no_source_page():
    response = _textbook_response(evidence_refs=[])
    validator = _make_validator(provider=_provider(response))
    returned = validator.validate(_candidate())
    assert returned.source_page is None
    assert returned.evidence_chunk_ids == []


def test_evidence_ref_beyond_supplied_range_is_rejected():
    response = _textbook_response(evidence_refs=[4])
    provider = _provider(response)
    validator = _make_validator(provider=provider)
    with pytest.raises(InvalidTextbookOutputError):
        validator.validate(_candidate())
    assert provider.generate_structured.call_count == 2  # WP-021 retries once


def test_evidence_ref_zero_is_rejected():
    response = _textbook_response(evidence_refs=[0])
    validator = _make_validator(provider=_provider(response))
    with pytest.raises(InvalidTextbookOutputError):
        validator.validate(_candidate())


def test_evidence_ref_negative_is_rejected():
    response = _textbook_response(evidence_refs=[-1])
    validator = _make_validator(provider=_provider(response))
    with pytest.raises(InvalidTextbookOutputError):
        validator.validate(_candidate())


def test_no_local_reference_leaks_into_final_result():
    chunk = _chunk(chunk_id="COURSE_BOOK:course_book.pdf:0010:0001")
    index = _StubIndex((RetrievalResult(chunk=chunk, score=0.5, rank=1),))
    response = _textbook_response(evidence_refs=[1])
    validator = _make_validator(index=index, provider=_provider(response))
    returned = validator.validate(_candidate())
    assert "evidence_refs" not in type(returned).model_fields
    assert all(cid.startswith("COURSE_BOOK:") for cid in returned.evidence_chunk_ids)


# ---------------------------------------------------------------------------
# WP-021: bounded provenance retry
# ---------------------------------------------------------------------------


def test_normal_success_makes_exactly_one_logical_call():
    chunk = _chunk(chunk_id="COURSE_BOOK:course_book.pdf:0010:0001")
    index = _StubIndex((RetrievalResult(chunk=chunk, score=0.5, rank=1),))
    passing = _textbook_response(evidence_refs=[])
    provider = _provider(passing)
    validator = _make_validator(index=index, provider=provider)
    validator.validate(_candidate())
    assert provider.generate_structured.call_count == 1
    assert validator.provenance_retry_events == ()


def test_invented_evidence_ref_then_valid_recovers():
    chunk = _chunk(chunk_id="COURSE_BOOK:course_book.pdf:0010:0001")
    index = _StubIndex((RetrievalResult(chunk=chunk, score=0.5, rank=1),))
    invalid = _textbook_response(evidence_refs=[9])
    valid = _textbook_response(evidence_refs=[1])
    provider = _provider(side_effect=[invalid, valid])
    validator = _make_validator(index=index, provider=provider)

    result = validator.validate(_candidate())

    assert result.evidence_chunk_ids == ["COURSE_BOOK:course_book.pdf:0010:0001"]
    assert provider.generate_structured.call_count == 2
    assert len(index.calls) == 1
    first_call, second_call = provider.generate_structured.call_args_list
    assert first_call.kwargs["messages"] == second_call.kwargs["messages"]
    assert len(validator.provenance_retry_events) == 1
    event = validator.provenance_retry_events[0]
    assert event.validator == "textbook"
    assert event.attempts_made == 2
    assert event.recovered is True


def test_invented_evidence_ref_twice_exhausts():
    invalid = _textbook_response(evidence_refs=[9])
    provider = _provider(side_effect=[invalid, invalid])
    validator = _make_validator(provider=provider)
    with pytest.raises(InvalidTextbookOutputError):
        validator.validate(_candidate())
    assert provider.generate_structured.call_count == 2
    assert len(validator.provenance_retry_events) == 1
    assert validator.provenance_retry_events[0].recovered is False


def test_not_found_verdict_is_not_retried():
    response = _textbook_response(status=TextbookCheckStatus.NOT_FOUND, evidence_refs=[])
    provider = _provider(response)
    validator = _make_validator(provider=provider)
    returned = validator.validate(_candidate())
    assert returned.status == TextbookCheckStatus.NOT_FOUND
    assert provider.generate_structured.call_count == 1
    assert validator.provenance_retry_events == ()


def test_potential_conflict_verdict_is_not_retried():
    response = _textbook_response(status=TextbookCheckStatus.POTENTIAL_CONFLICT, evidence_refs=[])
    provider = _provider(response)
    validator = _make_validator(provider=provider)
    returned = validator.validate(_candidate())
    assert returned.status == TextbookCheckStatus.POTENTIAL_CONFLICT
    assert provider.generate_structured.call_count == 1
    assert validator.provenance_retry_events == ()


@pytest.mark.parametrize(
    "exc",
    [
        LLMAuthenticationError("bad key"),
        LLMRateLimitError("rate limited"),
        LLMProviderError("connection failed"),
    ],
)
def test_operational_errors_are_never_provenance_retried(exc):
    chunk = _chunk()
    index = _StubIndex((RetrievalResult(chunk=chunk, score=0.5, rank=1),))
    provider = _provider(side_effect=exc)
    validator = _make_validator(index=index, provider=provider)
    with pytest.raises(type(exc)):
        validator.validate(_candidate())
    assert provider.generate_structured.call_count == 1
    assert validator.provenance_retry_events == ()


# ---------------------------------------------------------------------------
# Source-type boundaries
# ---------------------------------------------------------------------------


def test_evidence_must_be_course_book_only():
    from exam_generator.prompts import PromptContextError

    student_summary_chunk = _chunk(
        chunk_id="STUDENT_SUMMARY:student_summary_1.pdf:0001:0001",
        source_file="student_summary_1.pdf",
        source_type=SourceType.STUDENT_SUMMARY,
    )
    index = _StubIndex((RetrievalResult(chunk=student_summary_chunk, score=0.5, rank=1),))
    validator = _make_validator(index=index)
    with pytest.raises(PromptContextError):
        validator.validate(_candidate())


# ---------------------------------------------------------------------------
# Fail-before-LLM-call / operational-vs-verdict distinction
# ---------------------------------------------------------------------------


def test_provider_failure_is_operational_error_not_a_textbook_verdict():
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


# ---------------------------------------------------------------------------
# Independence from other validators
# ---------------------------------------------------------------------------


def test_textbook_validator_does_not_invoke_other_validators():
    import exam_generator.validation.textbook as textbook_module

    source = inspect.getsource(textbook_module)
    for forbidden in ("GroundingValidator", "MCQValidator", "CategoryValidator", "QualityValidator"):
        assert forbidden not in source
