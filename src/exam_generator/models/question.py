"""Question-level domain models: generation mode, clean questions, and the
internal candidate representation produced before independent validation.
"""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, ConfigDict, Field

from exam_generator.models._common import CorrectAnswerId, NonBlankStr, PositiveIntStrict


class GenerationMode(str, Enum):
    """How a candidate question was produced.

    Both modes still require independent student-summary grounding; neither
    mode is itself evidence of factual validity.
    """

    STYLE_SIMILAR = "STYLE_SIMILAR"
    INDEPENDENT = "INDEPENDENT"


class ExamQuestion(BaseModel):
    """The authoritative, externally-facing exam question contract.

    Contains only clean question content - no source, grounding, validation,
    historical-reference, generation-mode, model, confidence, or other audit
    information. See ``exam_generator.models.audit.QuestionAudit`` for that.
    """

    model_config = ConfigDict(extra="forbid")

    number: PositiveIntStrict
    question: NonBlankStr
    answer1: NonBlankStr
    answer2: NonBlankStr
    answer3: NonBlankStr
    answer4: NonBlankStr
    correct_answer: CorrectAnswerId
    category: NonBlankStr


class CandidateQuestion(BaseModel):
    """An LLM-generated candidate question prior to independent acceptance.

    Deliberately carries no self-reported "grounded" claim: grounding is
    established only by a later, independent validator.
    """

    model_config = ConfigDict(extra="forbid")

    question: NonBlankStr
    answers: list[NonBlankStr] = Field(min_length=4, max_length=4)
    correct_answer: CorrectAnswerId
    category: NonBlankStr
    generation_mode: GenerationMode


class GeneratedQuestionResponse(BaseModel):
    """The LLM-facing structured-output contract for one generation call
    (WP-009), returned by ``LLMProvider.generate_structured(...,
    response_model=GeneratedQuestionResponse, profile=LLMProfile.GENERATION)``.

    Deliberately excludes ``category`` and ``generation_mode`` - those are
    supplied by the caller as part of the request, not invented by the
    model, and are assigned directly onto ``CandidateQuestion`` by
    application code rather than trusted from LLM output.

    ``evidence_chunk_ids``/``historical_reference_id`` are the model's
    *claimed* provenance only; they are not authoritative and must be
    validated against the actual supplied generation context (the chunks
    actually retrieved, and the historical reference actually supplied, if
    any) before a caller may rely on them. See
    ``exam_generator.generation.generator``.
    """

    model_config = ConfigDict(extra="forbid")

    question: NonBlankStr = Field(description="The generated Hebrew exam question text.")
    answers: list[NonBlankStr] = Field(
        min_length=4, max_length=4, description="Exactly four Hebrew answer choices, in order."
    )
    correct_answer: CorrectAnswerId = Field(
        description="The 1-based position (1-4) of the single correct answer choice."
    )
    evidence_chunk_ids: list[NonBlankStr] = Field(
        default_factory=list,
        description=(
            "Identifiers of the supplied factual-evidence chunks that support this "
            "question, using only identifiers that were actually supplied to you. "
            "Never invent an identifier that was not supplied."
        ),
    )
    historical_reference_id: PositiveIntStrict | None = Field(
        default=None,
        description=(
            "The identifier of the supplied historical style reference, only if one "
            "was supplied to you and used as a style guide. Null if no historical "
            "reference was supplied."
        ),
    )


def candidate_to_exam_question(candidate: CandidateQuestion, number: int) -> ExamQuestion:
    """Deterministically convert an already-accepted candidate to a clean ExamQuestion.

    Performs no LLM call, grounding decision, factual validation, translation,
    answer shuffling, rewriting, or category mapping. The caller is
    responsible for supplying only a candidate that has already been accepted.
    """
    return ExamQuestion(
        number=number,
        question=candidate.question,
        answer1=candidate.answers[0],
        answer2=candidate.answers[1],
        answer3=candidate.answers[2],
        answer4=candidate.answers[3],
        correct_answer=candidate.correct_answer,
        category=candidate.category,
    )
