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
from exam_generator.models import CandidateQuestion, SourceEvidenceChunk, TextbookCheckResult, TextbookCheckStatus
from exam_generator.prompts import (
    PromptId,
    PromptRepository,
    build_prompt_messages,
    format_candidate_question,
    format_course_book_evidence,
)
from exam_generator.retrieval import FactualRetrievalIndex, build_course_book_retrieval_index
from exam_generator.validation.errors import InvalidTextbookOutputError

_NO_EVIDENCE_REASON = "No course-book evidence could be independently retrieved for this candidate."


def _build_textbook_query(candidate: CandidateQuestion) -> str:
    """Deterministic V1 textbook-retrieval query policy - mirrors WP-010's
    grounding-retrieval query exactly (category + question + intended
    correct-answer text only, distractors excluded), applied here against
    the course-book index instead of the student-summary index."""
    correct_answer_text = candidate.answers[candidate.correct_answer - 1]
    return f"{candidate.category} {candidate.question} {correct_answer_text}"


def _validate_textbook_provenance(
    result: TextbookCheckResult, course_book_evidence: tuple[SourceEvidenceChunk, ...]
) -> None:
    """Reject (rather than silently drop/repair) a cited source page or
    reference text that does not correspond to any course-book chunk
    actually supplied to the validator."""
    if result.source_page is not None:
        supplied_pages = {chunk.page for chunk in course_book_evidence}
        if result.source_page not in supplied_pages:
            raise InvalidTextbookOutputError(
                f"Textbook check result cites source_page={result.source_page}, which does not "
                f"match any course-book page actually supplied to the validator: {sorted(supplied_pages)}"
            )

    if result.reference_text is not None:
        if not any(result.reference_text in chunk.text for chunk in course_book_evidence):
            raise InvalidTextbookOutputError(
                "Textbook check result cites reference_text that does not appear in any "
                "course-book chunk actually supplied to the validator"
            )


class TextbookValidator:
    """Application-facing entry point for one independent, secondary
    textbook-consistency check.

    Every dependency is injected explicitly - never hidden global state -
    so tests can supply fakes/mocks. Use
    ``TextbookValidator.from_default_configuration()`` for the normal
    application wiring against real project configuration/data.
    """

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

    def validate(self, candidate: CandidateQuestion) -> TextbookCheckResult:
        """Independently determine whether course-book evidence is
        consistent with, contradicts, or is insufficient/unclear regarding
        ``candidate``.

        Unlike primary grounding, course-book evidence is optional
        secondary material: when independent retrieval finds nothing at
        all, that is returned directly as ``TextbookCheckStatus.NOT_FOUND``
        without making an LLM call - there is nothing for a model to judge
        against. Otherwise makes exactly one ``LLMProfile.VALIDATION``
        call - so a single invocation makes *at most* one LLM call, never
        more, and never a retry. Never mutates ``candidate``.
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

        result = self._llm_provider.generate_structured(
            messages=messages,
            response_model=TextbookCheckResult,
            profile=LLMProfile.VALIDATION,
        )

        _validate_textbook_provenance(result, course_book_evidence)

        return result
