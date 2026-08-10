"""Question-target planning contracts (WP-025): the intended factual focus
of one question, decided before generation begins, so multiple questions
requested from the same category can be planned to be genuinely distinct
rather than deduplicated after the fact.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from exam_generator.models._common import NonBlankStr, PositiveIntStrict, StrictBool


class QuestionTarget(BaseModel):
    """One planned question's intended factual/conceptual focus - a
    generation plan, never a generated question, a validator verdict, or
    an accepted exam question.

    ``supporting_evidence_chunk_ids`` are genuine canonical
    ``SourceEvidenceChunk.chunk_id`` values, already resolved from the
    planner's call-local ``evidence_refs`` (WP-022/WP-024's proven
    local-reference pattern) - never a raw LLM claim.

    ``named_entity_target`` (WP-040) is ``True`` only when ``topic`` is
    known, by construction, to be a specific named entity (an artery,
    tract, nucleus, or similar) rather than a free-text subtopic label -
    currently set only by the pilot-category deterministic planning path
    (``planning.planner._plan_targets_from_concept_inventory()``), where
    every ``topic`` is exactly a concept-inventory concept's own
    structurally-extracted text (WP-035/036's own "named entity" signal),
    never an LLM-authored description. Defaults to ``False`` - the
    LLM-based planning path (every non-pilot category) never sets this,
    since its own ``topic`` field is free-text and not reliably a named
    entity. This is internal-only information for the generation prompt
    (see ``prompts.formatting.format_target_answer_requirement()``) -
    never itself validated or scored, and never part of any public
    request/response contract.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    target_id: PositiveIntStrict
    category: NonBlankStr
    topic: NonBlankStr
    factual_focus: NonBlankStr
    supporting_evidence_chunk_ids: tuple[NonBlankStr, ...] = ()
    named_entity_target: StrictBool = False


class PlannedQuestionTargetResponse(BaseModel):
    """The LLM-facing structured-output contract for one target within a
    WP-025 planning call's response - never exposed beyond
    ``QuestionTargetPlanner``, which resolves it into the canonical,
    application-owned ``QuestionTarget``."""

    model_config = ConfigDict(extra="forbid")

    topic: NonBlankStr = Field(
        description="A short label for this target's subtopic/focus, e.g. 'spinothalamic tract - sensory modalities'."
    )
    factual_focus: NonBlankStr = Field(
        description=(
            "A concise statement of the single factual/conceptual point this target should test - "
            "specific enough that two targets testing this same statement would be duplicates."
        )
    )
    evidence_refs: list[int] = Field(
        default_factory=list,
        description=(
            "1-based local references to the supplied evidence items that support this target, "
            "matching the '[Evidence N]' labels shown in the factual evidence below - e.g. 1 refers "
            "to [Evidence 1]. Cite only evidence numbers that were actually supplied to you. Never "
            "invent a number outside the supplied range, and never report a chunk identifier, source "
            "file name, or any other text - only the plain number. If you are not confident which "
            "evidence number supports this target, leave this list empty rather than guessing - an "
            "empty list is always acceptable and preferred over an invented or approximate reference."
        ),
    )


class QuestionTargetPlanningResponse(BaseModel):
    """The LLM-facing structured-output contract for one WP-025 target-
    planning call, returned by ``LLMProvider.generate_structured(...,
    response_model=QuestionTargetPlanningResponse,
    profile=LLMProfile.GENERATION)``.

    ``targets`` may legitimately contain fewer than the requested count -
    the planner must never fabricate artificial diversity merely to reach
    a requested number."""

    model_config = ConfigDict(extra="forbid")

    targets: list[PlannedQuestionTargetResponse] = Field(
        default_factory=list,
        description=(
            "Up to the requested number of distinct, evidence-supported question targets. Return "
            "fewer than requested if the supplied evidence does not genuinely support that many "
            "distinct targets - never fabricate artificial diversity. An empty list is acceptable if "
            "no usable target exists at all."
        ),
    )
