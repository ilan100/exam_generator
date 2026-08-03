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
from exam_generator.models import CandidateQuestion, GroundingValidationResult, SourceEvidenceChunk
from exam_generator.prompts import GroundingPromptContext, PromptId, PromptRepository, build_prompt_messages
from exam_generator.retrieval import FactualRetrievalIndex, build_student_summary_retrieval_index
from exam_generator.validation.errors import InvalidGroundingOutputError, NoValidationEvidenceError


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


def _validate_supporting_evidence_ids(
    result: GroundingValidationResult, validation_evidence: tuple[SourceEvidenceChunk, ...]
) -> None:
    """Reject (rather than silently drop/repair) any supporting evidence id
    the LLM claims that was not actually supplied to the validator."""
    supplied_ids = {chunk.chunk_id for chunk in validation_evidence}
    invented_ids = [chunk_id for chunk_id in result.evidence_chunk_ids if chunk_id not in supplied_ids]
    if invented_ids:
        raise InvalidGroundingOutputError(
            f"Grounding result claims supporting evidence chunk id(s) that were not "
            f"supplied to the validator: {invented_ids}"
        )


class GroundingValidator:
    """Application-facing entry point for one independent
    grounding-validation call.

    Every dependency is injected explicitly - never hidden global state -
    so tests can supply fakes/mocks. Use
    ``GroundingValidator.from_default_configuration()`` for the normal
    application wiring against real project configuration/data.
    """

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

    def validate_grounding(self, candidate: CandidateQuestion) -> GroundingValidationResult:
        """Independently determine whether ``candidate`` is factually
        grounded in student-summary evidence.

        Makes exactly one ``LLMProfile.VALIDATION`` call - no retry. A
        negative verdict (``passed=False``) is a normal, successful
        result; a provider/LLM failure raises instead of ever silently
        becoming a fabricated ``passed=False``. Never mutates ``candidate``.
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

        result = self._llm_provider.generate_structured(
            messages=messages,
            response_model=GroundingValidationResult,
            profile=LLMProfile.VALIDATION,
        )

        _validate_supporting_evidence_ids(result, validation_evidence)

        return result
