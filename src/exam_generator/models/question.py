"""Question-level domain models: generation mode, clean questions, and the
internal candidate representation produced before independent validation.
"""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, ConfigDict, Field

from exam_generator.models._common import CorrectAnswerId, NonBlankStr, PositiveIntStrict, StrictBool


class GenerationMode(str, Enum):
    """How a candidate question was produced.

    Both modes still require independent student-summary grounding; neither
    mode is itself evidence of factual validity.
    """

    STYLE_SIMILAR = "STYLE_SIMILAR"
    INDEPENDENT = "INDEPENDENT"


class ExamQuestion(BaseModel):
    """The authoritative, externally-facing exam question contract - also
    the WP-033 "production question" contract reused (never duplicated)
    by ``exam_generator.category_generation``'s ``CategoryQuestionSet``
    API for both ``existing_questions`` and the freshly-generated question.

    Contains only clean question content - no source, grounding, validation,
    historical-reference, generation-mode, model, confidence, or other audit
    information. See ``exam_generator.models.audit.QuestionAudit`` for that.

    ``number`` is optional (WP-033) - a freshly-generated question does not
    yet have a runtime identifier assigned (``CategoryQuestionSetService``
    is "responsible only for the question content" per WP-033 section 4);
    the orchestration layer assigns ``number`` when it is not already
    available. A question actually inserted into ``ExamOutput.questions``
    must always carry a real, contiguous number - ``ExamOutput``'s own
    validator enforces this unconditionally and was not relaxed.
    """

    model_config = ConfigDict(extra="forbid")

    number: PositiveIntStrict | None = None
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


class DistractorArchetype(str, Enum):
    """Named wrong-answer design strategies (WP-028) - generation must
    intentionally choose one of these for each distractor rather than
    inventing plausible-sounding wrong answers ad hoc. Not exhaustive of
    every possible wrong-answer shape in principle, but names the shapes
    observed in practice across WP-025 through WP-027's live evaluation."""

    SIBLING_STRUCTURE = "SIBLING_STRUCTURE"
    PARENT_CATEGORY = "PARENT_CATEGORY"
    CHILD_CATEGORY = "CHILD_CATEGORY"
    NEIGHBORING_ANATOMY = "NEIGHBORING_ANATOMY"
    FUNCTIONAL_CONFUSION = "FUNCTIONAL_CONFUSION"
    LOCATION_CONFUSION = "LOCATION_CONFUSION"
    DEVELOPMENTAL_STAGE_CONFUSION = "DEVELOPMENTAL_STAGE_CONFUSION"
    TERMINOLOGY_CONFUSION = "TERMINOLOGY_CONFUSION"


class QuestionDifficulty(str, Enum):
    """Intended difficulty (WP-028) - a blueprint-only design signal, never
    validated or scored; exists so generation makes the choice explicitly
    rather than leaving it implicit."""

    EASY = "EASY"
    MEDIUM = "MEDIUM"
    HARD = "HARD"


class DistractorDesign(BaseModel):
    """One intentionally-designed wrong answer (WP-028), part of the
    internal question blueprint - never exposed beyond the generation call
    that produced it, and never persisted onto ``CandidateQuestion`` or any
    audit output. Deliberately does not carry the distractor's own answer
    text - it would duplicate the final ``answers`` list; the blueprint
    exists to justify design choices, not to restate the MCQ (see
    ``QuestionBlueprint``).
    """

    model_config = ConfigDict(extra="forbid")

    archetype: DistractorArchetype = Field(
        description="The intentional wrong-answer strategy used for this distractor - never chosen at random."
    )
    plausibility_reason: NonBlankStr = Field(
        description="Why a student might plausibly consider this distractor, absent full knowledge."
    )
    incorrectness_reason: NonBlankStr = Field(
        description=(
            "The single, exact reason this distractor is false for the specific relationship the "
            "question asks about - not merely a different or less complete fact. Must be a single "
            "clear reason, not several unrelated ones."
        )
    )
    evidence_checked: StrictBool = Field(
        description=(
            "Whether this distractor was explicitly checked against the supplied factual evidence "
            "and confirmed not to also correctly answer the exact question as worded. Must be true "
            "for every distractor - a distractor that fails this check must not be used; choose a "
            "different one instead."
        )
    )


class QuestionBlueprint(BaseModel):
    """The internal question design (WP-028), constructed before the final
    MCQ, inside the same generation call - never a second LLM call, never
    persisted, never exposed beyond ``QuestionGenerator``. Discarded
    immediately once the final ``CandidateQuestion`` is constructed,
    mirroring the established pattern of LLM-facing-only reasoning
    artifacts (e.g. WP-027's ``GroundingAnswerAssessment``).

    Generation is required to reason in terms of the tested relationship,
    not merely "the correct answer" - see ``tested_relationship`` - and to
    intentionally design each distractor - see ``distractors``. This
    structurally forces the reasoning already requested in prose
    (``prompts/generation/question.txt``) rather than leaving it optional.
    """

    model_config = ConfigDict(extra="forbid")

    knowledge_target: NonBlankStr = Field(
        description="The specific knowledge being tested - may narrow the assigned QuestionTarget to one relationship within it."
    )
    tested_relationship: NonBlankStr = Field(
        description=(
            "The precise factual relationship or property the question tests, stated as a "
            "relationship rather than as 'the correct answer' - for example 'fibers connecting "
            "cortical regions within the same hemisphere', not just 'association fibers'."
        )
    )
    question_style: NonBlankStr = Field(description="A short description of the question's phrasing style.")
    intended_difficulty: QuestionDifficulty = Field(description="The intended difficulty level for this question.")
    correct_answer_role: NonBlankStr = Field(
        description="Why the intended correct answer specifically satisfies the tested relationship, according to the supplied evidence."
    )
    distractors: list[DistractorDesign] = Field(
        min_length=3,
        max_length=3,
        description="Exactly three intentionally-designed distractors, one for each incorrect answer choice.",
    )


class GeneratedQuestionResponse(BaseModel):
    """The LLM-facing structured-output contract for one generation call
    (WP-009), returned by ``LLMProvider.generate_structured(...,
    response_model=GeneratedQuestionResponse, profile=LLMProfile.GENERATION)``.

    Deliberately excludes ``category`` and ``generation_mode`` - those are
    supplied by the caller as part of the request, not invented by the
    model, and are assigned directly onto ``CandidateQuestion`` by
    application code rather than trusted from LLM output.

    ``evidence_refs``/``historical_reference_id`` are the model's *claimed*
    provenance only; they are not authoritative and must be validated
    against the actual supplied generation context (the chunks actually
    retrieved, and the historical reference actually supplied, if any)
    before a caller may rely on them. Since WP-024, ``evidence_refs`` are
    small, 1-based, call-local integers matching the "[Evidence N]" labels
    already shown in the prompt's factual-evidence section - not canonical
    ``SourceEvidenceChunk.chunk_id`` strings - deterministically resolved
    into genuine canonical identifiers by
    ``exam_generator.generation.generator``, mirroring the pattern WP-022
    already established for grounding/textbook validation.

    ``blueprint`` (WP-028) is required internal design reasoning,
    constructed inside this same call - never a second LLM call. It is
    discarded immediately after this response is validated; the existing
    ``CandidateQuestion`` it converts into carries no blueprint field of
    its own, unchanged since WP-009.
    """

    model_config = ConfigDict(extra="forbid")

    blueprint: QuestionBlueprint = Field(
        description=(
            "The internal question design, constructed before the final question and answers: the "
            "tested relationship, intended difficulty, why the correct answer satisfies that "
            "relationship, and an intentional design (with an explicit evidence check) for each of "
            "the three distractors. Required for every generated question."
        )
    )
    question: NonBlankStr = Field(description="The generated Hebrew exam question text.")
    answers: list[NonBlankStr] = Field(
        min_length=4, max_length=4, description="Exactly four Hebrew answer choices, in order."
    )
    correct_answer: CorrectAnswerId = Field(
        description="The 1-based position (1-4) of the single correct answer choice."
    )
    evidence_refs: list[int] = Field(
        default_factory=list,
        description=(
            "1-based local references to the supplied factual-evidence items that "
            "support this question, matching the '[Evidence N]' labels shown in the "
            "factual evidence below - e.g. 1 refers to [Evidence 1]. Cite only "
            "evidence numbers that were actually supplied to you. Never invent a "
            "number outside the supplied range, and never report a chunk identifier, "
            "source file name, or any other text - only the plain number. If you are "
            "not confident which evidence number supports your question, leave this "
            "list empty rather than guessing - an empty list is always acceptable and "
            "preferred over an invented or approximate reference."
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


def candidate_to_exam_question(candidate: CandidateQuestion, number: int | None = None) -> ExamQuestion:
    """Deterministically convert an already-accepted candidate to a clean ExamQuestion.

    Performs no LLM call, grounding decision, factual validation, translation,
    answer shuffling, rewriting, or category mapping. The caller is
    responsible for supplying only a candidate that has already been accepted.

    ``number`` defaults to ``None`` (WP-033) - generation itself never
    assigns a runtime identifier; a caller that owns exam-wide numbering
    (``ExamOrchestrator``) still always supplies a real number explicitly.
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
