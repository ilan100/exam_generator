"""Independent factual grounding validation for a WP-009 ``CandidateQuestion``.

Generation and grounding validation are separate operations. This module
never trusts:

* the generator, merely because it produced the candidate;
* the candidate's generation-time claimed evidence ids as proof;
* the historical style reference (a ``STYLE_SIMILAR`` candidate's style
  anchor is never factual evidence);
* course-book evidence (secondary, not used for primary grounding at all).

Instead it independently retrieves student-summary evidence for the
candidate and asks a validator LLM call - never the generator - whether
that evidence actually supports it.
"""

from __future__ import annotations

from exam_generator.config import load_llm_config
from exam_generator.llm import LLMProfile, LLMProvider, build_llm_provider
from exam_generator.models import (
    CandidateQuestion,
    GroundingValidationResponse,
    GroundingValidationResult,
    SourceEvidenceChunk,
)
from exam_generator.prompts import GroundingPromptContext, PromptId, PromptRepository, build_prompt_messages
from exam_generator.retrieval import FactualRetrievalIndex, build_student_summary_retrieval_index
from exam_generator.validation.errors import InvalidGroundingOutputError, NoValidationEvidenceError
from exam_generator.validation.models import ProvenanceRetryEvent


def _build_validation_query(candidate: CandidateQuestion) -> str:
    """Deterministic V1 validation-retrieval query policy.

    Combines the candidate's canonical category (category-aware retrieval,
    per WP-010 section 7), its question text, and the text of its
    *intended* correct answer only - not the three distractors, which would
    only dilute the query with text that is not the factual claim actually
    being validated.
    """
    correct_answer_text = candidate.answers[candidate.correct_answer - 1]
    return f"{candidate.category} {candidate.question} {correct_answer_text}"


def _resolve_grounding_response(
    response: GroundingValidationResponse, validation_evidence: tuple[SourceEvidenceChunk, ...]
) -> GroundingValidationResult:
    """Strictly validate the LLM's call-local ``evidence_refs`` (WP-022)
    against the evidence actually supplied to this call, then
    deterministically construct the existing, unchanged
    ``GroundingValidationResult`` with genuine canonical
    ``evidence_chunk_ids``.

    Fails closed (raises, rather than drops/repairs/clamps/fuzzy-matches)
    on any reference outside ``1..len(validation_evidence)`` - including
    zero, negative, and out-of-range values, all treated identically so
    every case benefits equally from WP-021's retry.
    """
    invalid_refs = [
        ref for ref in response.evidence_refs if not (1 <= ref <= len(validation_evidence))
    ]
    if invalid_refs:
        raise InvalidGroundingOutputError(
            f"Grounding result claims evidence reference(s) outside the supplied range "
            f"1..{len(validation_evidence)}: {invalid_refs}"
        )
    resolved_chunk_ids = [validation_evidence[ref - 1].chunk_id for ref in response.evidence_refs]
    return GroundingValidationResult(
        grounded=response.grounded,
        correct_answer_supported=response.correct_answer_supported,
        other_answers_not_equally_correct=response.other_answers_not_equally_correct,
        evidence_chunk_ids=resolved_chunk_ids,
        evidence_text=response.evidence_text,
        reason=response.reason,
        confidence=response.confidence,
    )


class GroundingValidator:
    """Application-facing entry point for one independent
    grounding-validation call.

    Every dependency is injected explicitly - never hidden global state -
    so tests can supply fakes/mocks. Use
    ``GroundingValidator.from_default_configuration()`` for the normal
    application wiring against real project configuration/data.
    """

    #: Number of retries AFTER the initial logical validation call, for the
    #: narrowly-scoped case where the LLM returns a syntactically valid
    #: ``GroundingValidationResult`` that claims evidence provenance never
    #: actually supplied (WP-021) - never for a normal ``passed=False``
    #: verdict, and never for an operational failure. A documented
    #: validator-level constant, not new configuration, per WP-021 section
    #: 8's explicit allowance (this is internal recovery policy for one
    #: validator, not an application-wide or LLM-transport-level setting).
    _MAX_PROVENANCE_RETRIES = 1

    def __init__(
        self,
        *,
        student_summary_index: FactualRetrievalIndex,
        prompt_repository: PromptRepository,
        llm_provider: LLMProvider,
    ) -> None:
        self._student_summary_index = student_summary_index
        self._prompt_repository = prompt_repository
        self._llm_provider = llm_provider
        self._provenance_retry_events: list[ProvenanceRetryEvent] = []

    @classmethod
    def from_default_configuration(cls) -> "GroundingValidator":
        """Construct the normal application wiring: the real
        student-summary retrieval index, the real production prompt
        repository, and the configured OpenAI provider.

        Requires ``OPENAI_API_KEY`` to be set (resolved by
        ``build_llm_provider`` at this point, not earlier).
        """
        return cls(
            student_summary_index=build_student_summary_retrieval_index(),
            prompt_repository=PromptRepository.from_default_location(),
            llm_provider=build_llm_provider(load_llm_config()),
        )

    @property
    def provenance_retry_events(self) -> tuple[ProvenanceRetryEvent, ...]:
        """Observability only (WP-021): every completed logical
        ``validate_grounding()`` operation that needed at least one
        provenance retry, in call order. Never used to make any
        application decision."""
        return tuple(self._provenance_retry_events)

    def validate_grounding(self, candidate: CandidateQuestion) -> GroundingValidationResult:
        """Independently determine whether ``candidate`` is factually
        grounded in student-summary evidence.

        Retrieval happens exactly once per call. The LLM is asked for a
        ``GroundingValidationResponse`` (WP-022) - provenance reported as
        small, call-local ``evidence_refs`` matching the "[Evidence N]"
        labels already shown in the prompt, never canonical chunk
        identifiers. The logical validation itself may involve up to
        ``1 + _MAX_PROVENANCE_RETRIES`` physical ``LLMProfile.VALIDATION``
        calls (WP-021) - but only when a syntactically valid response
        claims an evidence reference never actually supplied; that
        response is discarded completely (never repaired/normalized/
        guessed at) and the *same* candidate, evidence, evidence
        ordering, prompt, and response model are resubmitted unchanged.
        A normal negative verdict (``passed=False``) is never retried -
        it is a valid, successful result and is returned immediately. A
        provider/LLM failure raises instead of ever silently becoming a
        fabricated verdict. This retry is independent of, and composes
        with, WP-020's own provider-level structured-output retry (each
        physical call here may itself involve up to WP-020's own bounded
        recovery). Returns the existing, unchanged
        ``GroundingValidationResult`` with genuine canonical
        ``evidence_chunk_ids`` - the local references never leak beyond
        this method. Never mutates ``candidate``, and never creates a new
        candidate-production attempt - that remains entirely
        `QuestionProducer`'s concern.
        """
        query = _build_validation_query(candidate)
        retrieval_results = self._student_summary_index.search(query)
        validation_evidence = tuple(result.chunk for result in retrieval_results)
        if not validation_evidence:
            raise NoValidationEvidenceError(
                f"No student-summary evidence could be independently retrieved to "
                f"validate category {candidate.category!r}"
            )

        context = GroundingPromptContext(candidate=candidate, source_evidence=validation_evidence)

        messages = build_prompt_messages(
            system_template=self._prompt_repository.get(PromptId.SYSTEM),
            task_template=self._prompt_repository.get(PromptId.GROUNDING_VALIDATION),
            variables=context.render_variables(),
        )

        max_calls = 1 + self._MAX_PROVENANCE_RETRIES
        for attempt in range(1, max_calls + 1):
            response = self._llm_provider.generate_structured(
                messages=messages,
                response_model=GroundingValidationResponse,
                profile=LLMProfile.VALIDATION,
            )
            try:
                result = _resolve_grounding_response(response, validation_evidence)
            except InvalidGroundingOutputError:
                if attempt < max_calls:
                    continue
                if attempt > 1:
                    self._provenance_retry_events.append(
                        ProvenanceRetryEvent(validator="grounding", attempts_made=attempt, recovered=False)
                    )
                raise
            else:
                if attempt > 1:
                    self._provenance_retry_events.append(
                        ProvenanceRetryEvent(validator="grounding", attempts_made=attempt, recovered=True)
                    )
                return result

        raise AssertionError("unreachable: the attempt loop always returns or raises")
