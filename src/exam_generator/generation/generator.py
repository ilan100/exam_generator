"""The first real question-generation path.

Connects existing infrastructure only - no competing retrieval, prompt, or
LLM abstraction is introduced here:

    canonical category
           v
    student-summary retrieval          (exam_generator.retrieval, WP-006)
           v
    historical style reference         (exam_generator.historical, WP-003; STYLE_SIMILAR only)
           v
    prompt construction                (exam_generator.prompts, WP-008)
           v
    structured LLM call                (exam_generator.llm, WP-007)
           v
    CandidateQuestion                  (exam_generator.models, WP-002)

This is generation only: the returned ``CandidateQuestion`` has not been
independently grounding/MCQ/category/quality/textbook validated - that is
WP-010 and later.
"""

from __future__ import annotations

from exam_generator.config import load_llm_config
from exam_generator.generation.errors import (
    GenerationContextError,
    InvalidGeneratedOutputError,
    MissingEvidenceError,
    MissingHistoricalReferenceError,
)
from exam_generator.historical import HistoricalQuestionRepository
from exam_generator.llm import LLMProfile, LLMProvider, build_llm_provider
from exam_generator.models import (
    CandidateQuestion,
    GeneratedQuestionResponse,
    GenerationMode,
    HistoricalStyleReference,
    SourceEvidenceChunk,
)
from exam_generator.prompts import GenerationPromptContext, PromptId, PromptRepository, build_prompt_messages
from exam_generator.retrieval import (
    CategoryResolver,
    FactualRetrievalIndex,
    build_category_resolver,
    build_student_summary_retrieval_index,
    retrieve_for_category,
)


def _select_historical_reference(
    historical_repository: HistoricalQuestionRepository, canonical_category: str
) -> HistoricalStyleReference:
    """Deterministic ``STYLE_SIMILAR`` historical-reference selection policy
    for WP-009: the first historical question for the canonical category,
    in workbook order (``HistoricalQuestionRepository.questions_for_category()``
    already preserves that order). No randomness, no diversity/retry
    awareness - see WP-013 for that.
    """
    candidates = historical_repository.questions_for_category(canonical_category)
    if not candidates:
        raise MissingHistoricalReferenceError(
            f"No historical style reference available for category {canonical_category!r}"
        )
    return candidates[0]


def _validate_generated_provenance(
    response: GeneratedQuestionResponse,
    *,
    source_evidence: tuple[SourceEvidenceChunk, ...],
    generation_mode: GenerationMode,
    historical_reference: HistoricalStyleReference | None,
) -> None:
    """Reject any provenance claim the LLM makes that does not correspond to
    what was actually supplied - a generated response is never trusted
    merely because it parsed as structured output."""
    supplied_chunk_ids = {chunk.chunk_id for chunk in source_evidence}
    invented_ids = [
        chunk_id for chunk_id in response.evidence_chunk_ids if chunk_id not in supplied_chunk_ids
    ]
    if invented_ids:
        raise InvalidGeneratedOutputError(
            f"Generated response claims evidence chunk id(s) that were not supplied: {invented_ids}"
        )

    if generation_mode == GenerationMode.INDEPENDENT:
        if response.historical_reference_id is not None:
            raise InvalidGeneratedOutputError(
                "INDEPENDENT generation must not claim a historical_reference_id, "
                f"got {response.historical_reference_id!r}"
            )
        return

    # STYLE_SIMILAR: a claimed historical_reference_id must match the one
    # actually supplied. Reporting none is tolerated (the claim is optional -
    # see GeneratedQuestionResponse); reporting a different id is not.
    if response.historical_reference_id is not None:
        supplied_id = historical_reference.historical_question_id if historical_reference else None
        if response.historical_reference_id != supplied_id:
            raise InvalidGeneratedOutputError(
                f"Generated response claims historical_reference_id "
                f"{response.historical_reference_id!r}, but the historical reference "
                f"actually supplied was {supplied_id!r}"
            )


class QuestionGenerator:
    """Application-facing entry point for one candidate-generation call.

    Every dependency is injected explicitly - never hidden global state -
    so tests can supply fakes/mocks. Use
    ``QuestionGenerator.from_default_configuration()`` for the normal
    application wiring against real project configuration/data.
    """

    def __init__(
        self,
        *,
        category_resolver: CategoryResolver,
        student_summary_index: FactualRetrievalIndex,
        historical_repository: HistoricalQuestionRepository,
        prompt_repository: PromptRepository,
        llm_provider: LLMProvider,
    ) -> None:
        self._category_resolver = category_resolver
        self._student_summary_index = student_summary_index
        self._historical_repository = historical_repository
        self._prompt_repository = prompt_repository
        self._llm_provider = llm_provider

    @classmethod
    def from_default_configuration(cls) -> "QuestionGenerator":
        """Construct the normal application wiring: the real category
        resolver, the real student-summary retrieval index (configured
        ``top_k``), the real historical repository, the real production
        prompt repository, and the configured OpenAI provider.

        Requires ``OPENAI_API_KEY`` to be set (resolved by
        ``build_llm_provider`` at this point, not earlier).
        """
        return cls(
            category_resolver=build_category_resolver(),
            student_summary_index=build_student_summary_retrieval_index(),
            historical_repository=HistoricalQuestionRepository.from_default_location(),
            prompt_repository=PromptRepository.from_default_location(),
            llm_provider=build_llm_provider(load_llm_config()),
        )

    def generate_candidate_question(
        self, *, category: str, generation_mode: GenerationMode
    ) -> CandidateQuestion:
        """Generate exactly one candidate question for ``category`` using
        ``generation_mode``.

        Makes exactly one LLM call (``LLMProfile.GENERATION``) - no semantic
        retry loop. Performs no grounding/MCQ/category/quality/textbook
        validation; the returned candidate is not yet exam-ready.
        """
        if not isinstance(generation_mode, GenerationMode):
            raise GenerationContextError(f"Unsupported generation mode: {generation_mode!r}")

        canonical_category = self._category_resolver.resolve(category)

        retrieval_results = retrieve_for_category(
            canonical_category, self._category_resolver, self._student_summary_index
        )
        source_evidence = tuple(result.chunk for result in retrieval_results)
        if not source_evidence:
            raise MissingEvidenceError(
                f"No student-summary evidence retrieved for category {canonical_category!r}"
            )

        historical_reference: HistoricalStyleReference | None = None
        if generation_mode == GenerationMode.STYLE_SIMILAR:
            historical_reference = _select_historical_reference(
                self._historical_repository, canonical_category
            )

        context = GenerationPromptContext(
            category=canonical_category,
            generation_mode=generation_mode,
            source_evidence=source_evidence,
            historical_reference=historical_reference,
        )

        messages = build_prompt_messages(
            system_template=self._prompt_repository.get(PromptId.SYSTEM),
            task_template=self._prompt_repository.get(PromptId.QUESTION_GENERATION),
            variables=context.render_variables(),
        )

        response = self._llm_provider.generate_structured(
            messages=messages,
            response_model=GeneratedQuestionResponse,
            profile=LLMProfile.GENERATION,
        )

        _validate_generated_provenance(
            response,
            source_evidence=source_evidence,
            generation_mode=generation_mode,
            historical_reference=historical_reference,
        )

        return CandidateQuestion(
            question=response.question,
            answers=response.answers,
            correct_answer=response.correct_answer,
            category=canonical_category,
            generation_mode=generation_mode,
        )
