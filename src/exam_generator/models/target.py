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

    ``is_source_role`` (WP-043 Part B) is ``True`` only when the target's
    own evidence positions it as the **source** of another, more salient
    described entity (e.g. a labeled "source:" value for a different
    artery) rather than as the subject of its own descriptive sentence -
    detected deterministically by
    ``planning.target_role.detect_source_evidence_role()``. Defaults to
    ``False`` (the ordinary case for the overwhelming majority of
    targets). Internal-only, same precedent as ``named_entity_target``.

    ``source_relationship_entity`` (WP-044 Part B) - only ever non-``None``
    when ``is_source_role`` is ``True`` - is the deterministically-
    identified name of the *other*, downstream entity the target's
    evidence positions it as the source/origin of (e.g. ``"Superior
    cerebellar artery"`` for the target ``"Basillar artery"``), extracted
    by ``planning.target_role.extract_source_relationship_entity()``. This
    is the concrete "tested relationship" WP-044 section 6 asks the
    existing blueprint to represent, reusing ``is_source_role`` rather than
    introducing a new relationship abstraction: a structured fact
    (deterministically read from the evidence itself, never LLM-inferred)
    that both strengthens the generation prompt's evidence-role note (see
    ``prompts.formatting.format_target_evidence_role()``) and backs a
    deterministic post-generation consistency check (see
    ``generation.generator._validate_target_role_consistency()``) that
    rejects a candidate whose correct answer names this downstream entity
    instead of the target itself. ``None`` when ``is_source_role`` is
    ``False``, or when it is ``True`` but no downstream entity could be
    identified within the bounded backward scan (never guessed).

    ``is_enumeration_member`` (WP-044 Part A) is ``True`` only when the
    target's own anchored ``factual_focus`` has enumeration shape - an
    enumeration-introduction cue phrase (e.g. "contains several sub-
    structures") appears immediately before the target's own occurrence -
    detected deterministically by
    ``planning.concept_anchor.detect_enumeration_member_shape()``. A
    target reaching this field as ``True`` has already been confirmed
    (``planning.concept_anchor.is_enumeration_evidence_insufficient()``)
    to carry genuine member-specific distinguishing content beyond the
    shared enumeration intro - a target whose enumeration evidence carries
    no such content is skipped entirely during planning and never becomes
    a ``QuestionTarget`` at all. Used only to add an explicit, target-
    specific reinforcement of the existing general "testing enumeration or
    classification targets" prompt guidance (see
    ``prompts.formatting.format_target_enumeration_requirement()``).
    Defaults to ``False`` (the ordinary, non-enumeration case). Internal-
    only, same precedent as ``named_entity_target``/``is_source_role``.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    target_id: PositiveIntStrict
    category: NonBlankStr
    topic: NonBlankStr
    factual_focus: NonBlankStr
    supporting_evidence_chunk_ids: tuple[NonBlankStr, ...] = ()
    named_entity_target: StrictBool = False
    is_source_role: StrictBool = False
    source_relationship_entity: NonBlankStr | None = None
    is_enumeration_member: StrictBool = False


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
