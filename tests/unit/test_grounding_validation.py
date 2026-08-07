import inspect
from unittest.mock import MagicMock

import pytest

from exam_generator.llm import LLMAuthenticationError, LLMProfile, LLMProvider, LLMProviderError, LLMRateLimitError, MessageRole
from exam_generator.models import (
    CandidateQuestion,
    GenerationMode,
    GroundingAnswerAssessment,
    GroundingValidationResponse,
    GroundingValidationResult,
    SourceEvidenceChunk,
    SourceType,
)
from exam_generator.prompts import GroundingPromptContext, PromptContextError, PromptId, PromptRenderError, PromptRepository
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


def _assessment(index: int, *, supported: bool, refs: list[int] = (), reason: str = "stub") -> GroundingAnswerAssessment:
    return GroundingAnswerAssessment(
        answer_index=index, supported_as_correct=supported, evidence_refs=list(refs), reason=reason
    )


def _grounding_response(
    *,
    grounded: bool = True,
    supported: frozenset[int] = frozenset({2}),
    evidence_refs: list[int] | None = None,
    reason: str = "supported by the evidence",
    confidence: float = 0.8,
    evidence_text: str | None = None,
) -> GroundingValidationResponse:
    """Builds the LLM-facing response (WP-022/WP-027): one independent
    per-option assessment for each of the four answer choices, provenance
    via call-local ``evidence_refs`` on the relevant assessment(s), never
    canonical chunk identifiers.

    ``supported`` names which 1-based answer indices are judged
    ``supported_as_correct`` - by default only index 2 (this file's
    ``_candidate()`` default ``correct_answer``), modeling a clean single-
    answer pass. Passing more than one index models WP-027's false-
    acceptance shape (more than one answer choice genuinely supported);
    passing an empty set models "designated answer unsupported."
    ``evidence_refs``, when given, is attached to every supported index's
    own assessment (there is normally at most one in these fixtures).
    """
    refs = evidence_refs or []
    assessments = [_assessment(i, supported=i in supported, refs=refs if i in supported else []) for i in (1, 2, 3, 4)]
    return GroundingValidationResponse(
        grounded=grounded,
        answer_assessments=assessments,
        evidence_text=evidence_text,
        reason=reason,
        confidence=confidence,
    )


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


def _provider(response: GroundingValidationResponse | None = None, *, side_effect=None) -> MagicMock:
    provider = MagicMock(spec=LLMProvider)
    if side_effect is not None:
        provider.generate_structured.side_effect = side_effect
    else:
        provider.generate_structured.return_value = response if response is not None else _grounding_response()
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
    passing = _grounding_response(grounded=True, supported=frozenset({2}))
    validator = _make_validator(provider=_provider(passing))
    result = validator.validate_grounding(_candidate())
    assert result.passed is True


def test_unsupported_candidate_fails_as_normal_result_not_exception():
    failing = _grounding_response(grounded=False, supported=frozenset(), reason="no supporting evidence found")
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


def test_llm_called_with_grounding_validation_response_model():
    provider = _provider()
    validator = _make_validator(provider=provider)
    validator.validate_grounding(_candidate())
    assert provider.generate_structured.call_args.kwargs["response_model"] is GroundingValidationResponse


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
# WP-022: evidence-reference provenance (call-local -> canonical mapping)
# ---------------------------------------------------------------------------


def test_valid_evidence_ref_resolves_to_canonical_chunk_id():
    chunk = _chunk(chunk_id="STUDENT_SUMMARY:s1.pdf:0002:0001")
    index = _StubIndex((RetrievalResult(chunk=chunk, score=0.5, rank=1),))
    response = _grounding_response(evidence_refs=[1])
    validator = _make_validator(index=index, provider=_provider(response))
    returned = validator.validate_grounding(_candidate())
    assert returned.evidence_chunk_ids == ["STUDENT_SUMMARY:s1.pdf:0002:0001"]


def test_multiple_evidence_refs_resolve_in_order():
    chunk_a = _chunk(chunk_id="STUDENT_SUMMARY:s1.pdf:0001:0001")
    chunk_b = _chunk(chunk_id="STUDENT_SUMMARY:s1.pdf:0002:0001")
    chunk_c = _chunk(chunk_id="STUDENT_SUMMARY:s1.pdf:0003:0001")
    index = _StubIndex(
        (
            RetrievalResult(chunk=chunk_a, score=0.9, rank=1),
            RetrievalResult(chunk=chunk_b, score=0.8, rank=2),
            RetrievalResult(chunk=chunk_c, score=0.7, rank=3),
        )
    )
    response = _grounding_response(evidence_refs=[1, 3])
    validator = _make_validator(index=index, provider=_provider(response))
    returned = validator.validate_grounding(_candidate())
    assert returned.evidence_chunk_ids == [
        "STUDENT_SUMMARY:s1.pdf:0001:0001",
        "STUDENT_SUMMARY:s1.pdf:0003:0001",
    ]


def test_evidence_ref_beyond_supplied_range_is_rejected():
    # Only 1 chunk supplied - ref 4 does not exist.
    response = _grounding_response(evidence_refs=[4])
    provider = _provider(response)
    validator = _make_validator(provider=provider)
    with pytest.raises(InvalidGroundingOutputError):
        validator.validate_grounding(_candidate())
    assert provider.generate_structured.call_count == 2  # WP-021 retries once, same bad response


def test_evidence_ref_zero_is_rejected():
    response = _grounding_response(evidence_refs=[0])
    validator = _make_validator(provider=_provider(response))
    with pytest.raises(InvalidGroundingOutputError):
        validator.validate_grounding(_candidate())


def test_evidence_ref_negative_is_rejected():
    response = _grounding_response(evidence_refs=[-1])
    validator = _make_validator(provider=_provider(response))
    with pytest.raises(InvalidGroundingOutputError):
        validator.validate_grounding(_candidate())


def test_canonical_chunk_id_string_instead_of_local_ref_is_rejected():
    # The LLM-facing schema only accepts integers - a canonical ID string
    # cannot even be constructed as a valid GroundingAnswerAssessment.
    with pytest.raises(Exception):
        GroundingAnswerAssessment(
            answer_index=1,
            supported_as_correct=True,
            evidence_refs=["STUDENT_SUMMARY:s1.pdf:0002:0001"],
            reason="stub",
        )


def test_no_local_reference_leaks_into_final_result():
    chunk = _chunk(chunk_id="STUDENT_SUMMARY:s1.pdf:0002:0001")
    index = _StubIndex((RetrievalResult(chunk=chunk, score=0.5, rank=1),))
    response = _grounding_response(evidence_refs=[1])
    validator = _make_validator(index=index, provider=_provider(response))
    returned = validator.validate_grounding(_candidate())
    assert "evidence_refs" not in type(returned).model_fields
    assert all(cid.startswith("STUDENT_SUMMARY:") for cid in returned.evidence_chunk_ids)
    assert "1" not in returned.evidence_chunk_ids


# ---------------------------------------------------------------------------
# WP-021: bounded provenance retry
# ---------------------------------------------------------------------------


def test_normal_success_makes_exactly_one_logical_call():
    passing = _grounding_response(evidence_refs=[])
    provider = _provider(passing)
    validator = _make_validator(provider=provider)
    validator.validate_grounding(_candidate())
    assert provider.generate_structured.call_count == 1
    assert validator.provenance_retry_events == ()


def test_invented_evidence_ref_then_valid_recovers():
    chunk = _chunk(chunk_id="STUDENT_SUMMARY:s1.pdf:0002:0001")
    index = _StubIndex((RetrievalResult(chunk=chunk, score=0.5, rank=1),))
    invalid = _grounding_response(evidence_refs=[9])
    valid = _grounding_response(evidence_refs=[1])
    provider = _provider(side_effect=[invalid, valid])
    validator = _make_validator(index=index, provider=provider)

    result = validator.validate_grounding(_candidate())

    assert result.evidence_chunk_ids == ["STUDENT_SUMMARY:s1.pdf:0002:0001"]
    assert provider.generate_structured.call_count == 2
    # Same request resubmitted unchanged (retrieval happened only once) -
    # the identical Evidence-N mapping is reused across the retry.
    assert len(index.calls) == 1
    first_call, second_call = provider.generate_structured.call_args_list
    assert first_call.kwargs["messages"] == second_call.kwargs["messages"]
    assert first_call.kwargs["response_model"] == second_call.kwargs["response_model"]
    assert first_call.kwargs["profile"] == second_call.kwargs["profile"]
    assert len(validator.provenance_retry_events) == 1
    event = validator.provenance_retry_events[0]
    assert event.validator == "grounding"
    assert event.attempts_made == 2
    assert event.recovered is True


def test_invented_evidence_ref_twice_exhausts():
    invalid = _grounding_response(evidence_refs=[9])
    provider = _provider(side_effect=[invalid, invalid])
    validator = _make_validator(provider=provider)
    with pytest.raises(InvalidGroundingOutputError):
        validator.validate_grounding(_candidate())
    assert provider.generate_structured.call_count == 2
    assert len(validator.provenance_retry_events) == 1
    assert validator.provenance_retry_events[0].recovered is False


def test_normal_passed_false_verdict_is_not_retried():
    failing = _grounding_response(grounded=False, supported=frozenset(), reason="not supported")
    provider = _provider(failing)
    validator = _make_validator(provider=provider)
    result = validator.validate_grounding(_candidate())
    assert result.passed is False
    assert provider.generate_structured.call_count == 1
    assert validator.provenance_retry_events == ()


@pytest.mark.parametrize(
    "exc",
    [
        LLMAuthenticationError("bad key"),
        LLMRateLimitError("rate limited"),
        LLMProviderError("connection failed"),
        PromptRenderError("bad prompt"),
    ],
)
def test_operational_errors_are_never_provenance_retried(exc):
    provider = _provider(side_effect=exc)
    validator = _make_validator(provider=provider)
    with pytest.raises(type(exc)):
        validator.validate_grounding(_candidate())
    assert provider.generate_structured.call_count == 1
    assert validator.provenance_retry_events == ()


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


# ---------------------------------------------------------------------------
# WP-027: per-option factual grounding and distractor correctness
#
# Root cause (evaluation/wp026_false_acceptance_diagnostic.md): a single
# holistic "no other answer is equally correct" LLM boolean could be wrong
# even when the LLM had, and cited, the evidence that contradicted it.
# WP-027 requires an explicit independent assessment of all four answer
# choices, with correct_answer_supported/other_answers_not_equally_correct
# now deterministically DERIVED in Python from those four assessments -
# never trusted as a separate LLM-reported summary.
# ---------------------------------------------------------------------------


def test_second_correct_answer_forces_rejection_pns_shape():
    # WP-027 section 16 core regression case, reproducing WP-026 question
    # #23's exact factual structure: evidence states a classification
    # divides into two named members, both of which appear among the four
    # answer choices, but only one was designated correct. Both must be
    # assessed as supported, and that must force rejection - this candidate
    # must never be accepted.
    response = _grounding_response(grounded=True, supported=frozenset({1, 3}), evidence_refs=[1])
    validator = _make_validator(provider=_provider(response))
    result = validator.validate_grounding(_candidate(correct_answer=1))
    assert result.correct_answer_supported is True
    assert result.other_answers_not_equally_correct is False
    assert result.passed is False


def test_second_correct_answer_ct_shape_distractor_directly_evidenced():
    # WP-027 section 17 "CT case" (#8): a distractor directly, verbatim
    # supported by the same evidence shown to the validator must be caught
    # even though a different option was designated correct.
    response = _grounding_response(grounded=True, supported=frozenset({2, 3}), evidence_refs=[1])
    validator = _make_validator(provider=_provider(response))
    result = validator.validate_grounding(_candidate(correct_answer=2))
    assert result.other_answers_not_equally_correct is False
    assert result.passed is False


def test_second_correct_answer_blood_supply_shape_broad_relationship_distractor():
    # WP-027 section 17 "blood-supply case" (#14): a distractor satisfying a
    # broader/less direct anatomical relationship than the designated
    # answer must still be represented as supported when it genuinely is -
    # never silently ignored merely because its support is less obvious.
    response = _grounding_response(grounded=True, supported=frozenset({3, 4}), evidence_refs=[1])
    validator = _make_validator(provider=_provider(response))
    result = validator.validate_grounding(_candidate(correct_answer=3))
    assert result.other_answers_not_equally_correct is False
    assert result.passed is False


def test_second_correct_answer_microglia_shape_multiple_real_functions():
    # WP-027 section 17 "microglia case" (#32): when evidence states more
    # than one real function/property and the question asks broadly for
    # "the central" one, grounding must not arbitrarily declare one false
    # without addressing it - if both are genuinely supported, both must be
    # marked supported, forcing rejection rather than a silent single pick.
    response = _grounding_response(grounded=True, supported=frozenset({1, 2}), evidence_refs=[1])
    validator = _make_validator(provider=_provider(response))
    result = validator.validate_grounding(_candidate(correct_answer=2))
    assert result.other_answers_not_equally_correct is False
    assert result.passed is False


def test_unsupported_designated_answer_shape():
    # WP-027 section 17 "#30 case": a different defect shape entirely - the
    # designated answer's own specific claim is not established by the
    # supplied evidence, and no other answer is supported either. WP-027's
    # distractor-correctness focus must not weaken this ordinary check.
    response = _grounding_response(grounded=True, supported=frozenset(), reason="no answer choice is supported")
    validator = _make_validator(provider=_provider(response))
    result = validator.validate_grounding(_candidate(correct_answer=2))
    assert result.correct_answer_supported is False
    assert result.other_answers_not_equally_correct is True  # vacuously true - no OTHER answer is supported either
    assert result.passed is False


def test_positive_case_distractors_true_elsewhere_but_do_not_satisfy_exact_question():
    # WP-027 section 18 ("do not overcorrect"): distractors may be real
    # entities with true properties described elsewhere in the evidence,
    # but if they do not satisfy the EXACT question asked they remain
    # unsupported and the candidate must still pass.
    response = _grounding_response(grounded=True, supported=frozenset({2}), evidence_refs=[1])
    validator = _make_validator(provider=_provider(response))
    result = validator.validate_grounding(_candidate(correct_answer=2))
    assert result.correct_answer_supported is True
    assert result.other_answers_not_equally_correct is True
    assert result.passed is True


def test_deterministic_derivation_ignores_reason_text_and_uses_only_booleans():
    # WP-027 section 19: application-side derivation must never trust a
    # free-text reason's claim over the actual structured per-option
    # booleans - even if `reason` asserts the candidate is fine, two
    # supported indices still force rejection.
    response = _grounding_response(
        grounded=True,
        supported=frozenset({1, 2}),
        evidence_refs=[1],
        reason="the correct answer is the only one supported by the evidence",
    )
    validator = _make_validator(provider=_provider(response))
    result = validator.validate_grounding(_candidate(correct_answer=2))
    assert result.other_answers_not_equally_correct is False
    assert result.passed is False


def test_grounding_response_no_longer_exposes_llm_facing_summary_booleans():
    # WP-027: correct_answer_supported/other_answers_not_equally_correct
    # are no longer LLM-facing fields at all - there is nothing for the
    # model to inconsistently self-summarize; they exist only on the
    # unchanged public GroundingValidationResult, always derived.
    assert "correct_answer_supported" not in GroundingValidationResponse.model_fields
    assert "other_answers_not_equally_correct" not in GroundingValidationResponse.model_fields
    assert "answer_assessments" in GroundingValidationResponse.model_fields
    assert "correct_answer_supported" in GroundingValidationResult.model_fields
    assert "other_answers_not_equally_correct" in GroundingValidationResult.model_fields


# ---------------------------------------------------------------------------
# WP-027 section 5: exactly-four-assessments structural validation
# ---------------------------------------------------------------------------


def test_missing_answer_index_is_rejected():
    response = GroundingValidationResponse(
        grounded=True,
        answer_assessments=[_assessment(1, supported=True), _assessment(2, supported=False), _assessment(3, supported=False)],
        reason="stub",
        confidence=0.8,
    )
    provider = _provider(response)
    validator = _make_validator(provider=provider)
    with pytest.raises(InvalidGroundingOutputError):
        validator.validate_grounding(_candidate(correct_answer=1))
    assert provider.generate_structured.call_count == 2  # WP-021 retries once, same malformed response


def test_duplicate_answer_index_is_rejected():
    response = GroundingValidationResponse(
        grounded=True,
        answer_assessments=[
            _assessment(1, supported=True),
            _assessment(1, supported=False),
            _assessment(3, supported=False),
            _assessment(4, supported=False),
        ],
        reason="stub",
        confidence=0.8,
    )
    validator = _make_validator(provider=_provider(response))
    with pytest.raises(InvalidGroundingOutputError):
        validator.validate_grounding(_candidate())


def test_answer_index_zero_is_rejected():
    response = GroundingValidationResponse(
        grounded=True,
        answer_assessments=[
            _assessment(0, supported=True),
            _assessment(2, supported=False),
            _assessment(3, supported=False),
            _assessment(4, supported=False),
        ],
        reason="stub",
        confidence=0.8,
    )
    validator = _make_validator(provider=_provider(response))
    with pytest.raises(InvalidGroundingOutputError):
        validator.validate_grounding(_candidate())


def test_answer_index_negative_is_rejected():
    response = GroundingValidationResponse(
        grounded=True,
        answer_assessments=[
            _assessment(-1, supported=True),
            _assessment(2, supported=False),
            _assessment(3, supported=False),
            _assessment(4, supported=False),
        ],
        reason="stub",
        confidence=0.8,
    )
    validator = _make_validator(provider=_provider(response))
    with pytest.raises(InvalidGroundingOutputError):
        validator.validate_grounding(_candidate())


def test_answer_index_above_four_is_rejected():
    response = GroundingValidationResponse(
        grounded=True,
        answer_assessments=[
            _assessment(1, supported=True),
            _assessment(2, supported=False),
            _assessment(3, supported=False),
            _assessment(5, supported=False),
        ],
        reason="stub",
        confidence=0.8,
    )
    validator = _make_validator(provider=_provider(response))
    with pytest.raises(InvalidGroundingOutputError):
        validator.validate_grounding(_candidate())


def test_invalid_ref_on_non_designated_assessment_is_also_rejected():
    # Bounds-checking must cover every assessment's evidence_refs, not only
    # the designated answer's - an invalid ref anywhere in the response is
    # fail-closed, mirroring WP-022's whole-response-discard philosophy,
    # generalized from "per-response" to "per-option."
    assessments = [
        _assessment(1, supported=False),
        _assessment(2, supported=True, refs=[1]),
        _assessment(3, supported=False, refs=[99]),  # invalid - out of the supplied range
        _assessment(4, supported=False),
    ]
    response = GroundingValidationResponse(grounded=True, answer_assessments=assessments, reason="stub", confidence=0.8)
    validator = _make_validator(provider=_provider(response))
    with pytest.raises(InvalidGroundingOutputError):
        validator.validate_grounding(_candidate())
