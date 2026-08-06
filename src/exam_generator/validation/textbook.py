"""Independent, secondary course-book consistency check for a WP-009
``CandidateQuestion``.

Student summaries remain the sole primary factual grounding authority (see
``exam_generator.validation.grounding``); this module never establishes or
replaces that. It independently retrieves course-book evidence for the
candidate and asks a validator LLM call whether that evidence is
consistent with, contradicts, or is insufficient/unclear regarding the
candidate - for audit/corroboration purposes only.
"""

from __future__ import annotations

from exam_generator.config import load_llm_config
from exam_generator.llm import LLMProfile, LLMProvider, build_llm_provider
from exam_generator.models import (
    CandidateQuestion,
    SourceEvidenceChunk,
    TextbookCheckResult,
    TextbookCheckStatus,
    TextbookValidationResponse,
)
from exam_generator.prompts import (
    PromptId,
    PromptRepository,
    build_prompt_messages,
    format_candidate_question,
    format_course_book_evidence,
)
from exam_generator.retrieval import FactualRetrievalIndex, build_course_book_retrieval_index
from exam_generator.validation.errors import InvalidTextbookOutputError
from exam_generator.validation.models import ProvenanceRetryEvent

_NO_EVIDENCE_REASON = "No course-book evidence could be independently retrieved for this candidate."


def _build_textbook_query(candidate: CandidateQuestion) -> str:
    """Deterministic V1 textbook-retrieval query policy - mirrors WP-010's
    grounding-retrieval query exactly (category + question + intended
    correct-answer text only, distractors excluded), applied here against
    the course-book index instead of the student-summary index."""
    correct_answer_text = candidate.answers[candidate.correct_answer - 1]
    return f"{candidate.category} {candidate.question} {correct_answer_text}"


def _resolve_textbook_response(
    response: TextbookValidationResponse, course_book_evidence: tuple[SourceEvidenceChunk, ...]
) -> TextbookCheckResult:
    """Strictly validate the LLM's call-local ``evidence_refs`` (WP-022)
    against the evidence actually supplied to this call, then
    deterministically construct the existing, unchanged
    ``TextbookCheckResult``.

    ``evidence_chunk_ids`` and ``source_page`` are both derived entirely
    from the resolved canonical chunk(s) - never claimed by the LLM.
    ``reference_text`` is no longer populated at all (WP-022): there is no
    deterministic equivalent of a short human excerpt once verbatim
    reproduction is no longer required, so it is always ``None`` going
    forward - an honest absence, not a fabricated value.

    Fails closed on any reference outside ``1..len(course_book_evidence)``
    - including zero, negative, and out-of-range values, all treated
    identically so every case benefits equally from WP-021's retry.
    """
    invalid_refs = [
        ref for ref in response.evidence_refs if not (1 <= ref <= len(course_book_evidence))
    ]
    if invalid_refs:
        raise InvalidTextbookOutputError(
            f"Textbook check result claims evidence reference(s) outside the supplied range "
            f"1..{len(course_book_evidence)}: {invalid_refs}"
        )
    resolved_chunks = [course_book_evidence[ref - 1] for ref in response.evidence_refs]
    return TextbookCheckResult(
        status=response.status,
        evidence_chunk_ids=[chunk.chunk_id for chunk in resolved_chunks],
        source_page=resolved_chunks[0].page if resolved_chunks else None,
        reference_text=None,
        reason=response.reason,
    )


class TextbookValidator:
    """Application-facing entry point for one independent, secondary
    textbook-consistency check.

    Every dependency is injected explicitly - never hidden global state -
    so tests can supply fakes/mocks. Use
    ``TextbookValidator.from_default_configuration()`` for the normal
    application wiring against real project configuration/data.
    """

    #: Same bounded-recovery policy as the grounding validator (WP-021):
    #: retried failure class is any ``InvalidTextbookOutputError`` raised
    #: by ``_resolve_textbook_response()`` - an evidence reference (WP-022)
    #: outside the supplied range - since it represents the same
    #: stochastic "the model claimed provenance it was never actually
    #: supplied" mistake, not a systematic defect. Never retried: a normal
    #: CONSISTENT/POTENTIAL_CONFLICT/NOT_FOUND verdict with valid
    #: provenance, or any operational failure.
    _MAX_PROVENANCE_RETRIES = 1

    def __init__(
        self,
        *,
        course_book_index: FactualRetrievalIndex,
        prompt_repository: PromptRepository,
        llm_provider: LLMProvider,
    ) -> None:
        self._course_book_index = course_book_index
        self._prompt_repository = prompt_repository
        self._llm_provider = llm_provider
        self._provenance_retry_events: list[ProvenanceRetryEvent] = []

    @classmethod
    def from_default_configuration(cls) -> "TextbookValidator":
        """Construct the normal application wiring: the real course-book
        retrieval index, the real production prompt repository, and the
        configured OpenAI provider.

        Requires ``OPENAI_API_KEY`` to be set (resolved by
        ``build_llm_provider`` at this point, not earlier).
        """
        return cls(
            course_book_index=build_course_book_retrieval_index(),
            prompt_repository=PromptRepository.from_default_location(),
            llm_provider=build_llm_provider(load_llm_config()),
        )

    @property
    def provenance_retry_events(self) -> tuple[ProvenanceRetryEvent, ...]:
        """Observability only (WP-021): every completed logical
        ``validate()`` operation that needed at least one provenance
        retry, in call order. Never used to make any application
        decision."""
        return tuple(self._provenance_retry_events)

    def validate(self, candidate: CandidateQuestion) -> TextbookCheckResult:
        """Independently determine whether course-book evidence is
        consistent with, contradicts, or is insufficient/unclear regarding
        ``candidate``.

        Unlike primary grounding, course-book evidence is optional
        secondary material: when independent retrieval finds nothing at
        all, that is returned directly as ``TextbookCheckStatus.NOT_FOUND``
        without making an LLM call - there is nothing for a model to judge
        against. Retrieval happens exactly once per call. Otherwise the
        LLM is asked for a ``TextbookValidationResponse`` (WP-022) -
        provenance reported as small, call-local ``evidence_refs``
        matching the "[Evidence N]" labels already shown in the prompt,
        never canonical chunk identifiers, and never ``source_page``/
        ``reference_text`` as claimed provenance proof. The logical
        validation itself may involve up to ``1 + _MAX_PROVENANCE_RETRIES``
        physical ``LLMProfile.VALIDATION`` calls (WP-021) - only when a
        syntactically valid response claims an evidence reference never
        actually supplied; that response is discarded completely and the
        same candidate/evidence/prompt/response model are resubmitted
        unchanged. A normal verdict with valid provenance is never
        retried. Independent of, and composes with, WP-020's own
        provider-level structured-output retry. Returns the existing,
        unchanged ``TextbookCheckResult`` with genuine canonical
        ``evidence_chunk_ids``/``source_page`` - local references never
        leak beyond this method. Never mutates ``candidate``, and never
        creates a new candidate-production attempt.
        """
        query = _build_textbook_query(candidate)
        retrieval_results = self._course_book_index.search(query)
        course_book_evidence = tuple(result.chunk for result in retrieval_results)

        if not course_book_evidence:
            return TextbookCheckResult(status=TextbookCheckStatus.NOT_FOUND, reason=_NO_EVIDENCE_REASON)

        messages = build_prompt_messages(
            system_template=self._prompt_repository.get(PromptId.SYSTEM),
            task_template=self._prompt_repository.get(PromptId.TEXTBOOK_VALIDATION),
            variables={
                "candidate_question": format_candidate_question(candidate),
                "course_book_evidence": format_course_book_evidence(course_book_evidence),
            },
        )

        max_calls = 1 + self._MAX_PROVENANCE_RETRIES
        for attempt in range(1, max_calls + 1):
            response = self._llm_provider.generate_structured(
                messages=messages,
                response_model=TextbookValidationResponse,
                profile=LLMProfile.VALIDATION,
            )
            try:
                result = _resolve_textbook_response(response, course_book_evidence)
            except InvalidTextbookOutputError:
                if attempt < max_calls:
                    continue
                if attempt > 1:
                    self._provenance_retry_events.append(
                        ProvenanceRetryEvent(validator="textbook", attempts_made=attempt, recovered=False)
                    )
                raise
            else:
                if attempt > 1:
                    self._provenance_retry_events.append(
                        ProvenanceRetryEvent(validator="textbook", attempts_made=attempt, recovered=True)
                    )
                return result

        raise AssertionError("unreachable: the attempt loop always returns or raises")
