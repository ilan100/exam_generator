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
