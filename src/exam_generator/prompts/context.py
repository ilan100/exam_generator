"""Small immutable prompt-context value objects.

These exist only where they materially prevent an invalid prompt from being
constructed (a generation-mode/historical-reference mismatch, missing
mandatory evidence). They deliberately do not duplicate the WP-002 domain
model layer, and they never call an LLM or perform retrieval/selection -
callers must already have chosen category/evidence/reference before
constructing one of these.
"""

from __future__ import annotations

from dataclasses import dataclass

from exam_generator.models import (
    CandidateQuestion,
    CategoryCoverage,
    CompetitorCandidate,
    GenerationMode,
    HistoricalStyleReference,
    QuestionRelationship,
    QuestionTarget,
    SourceEvidenceChunk,
)
from exam_generator.prompts.errors import PromptContextError
from exam_generator.prompts.formatting import (
    format_candidate_question,
    format_category_coverage,
    format_competitors,
    format_historical_reference,
    format_question_target,
    format_student_summary_evidence,
    format_target_answer_requirement,
)


@dataclass(frozen=True)
class GenerationPromptContext:
    """Validated inputs for one question-generation prompt render.

    Enforces the mode/historical-reference invariant (WP-008 section 44):
    ``STYLE_SIMILAR`` requires a historical reference; ``INDEPENDENT`` must
    not be supplied one (no fabricated reference is ever synthesized here).

    Since WP-025, every generation call is assigned a ``target`` planned
    before generation begins - enforced here to belong to the same
    category, never silently substituted or broadened.

    Since WP-030, every generation call also carries the ``target``'s
    deterministically-classified ``relationship`` (never produced by an
    LLM - see ``exam_generator.generation.relationship.extract_relationship()``),
    so generation can be told explicitly what relationship type it is
    testing rather than inferring it implicitly from free text alone.

    Since WP-031, every generation call also carries ``competitors`` -
    other evidence-supported concepts deterministically discovered to
    share the same relationship (see
    ``exam_generator.generation.competitors.discover_competitors()``) -
    information, never a generation decision; may legitimately be empty.

    Since WP-040, ``render_variables()`` also renders
    ``target.named_entity_target`` into an explicit answer-identity
    requirement (see
    ``exam_generator.prompts.formatting.format_target_answer_requirement()``) -
    derived purely from information the target already carries, never a
    new field on this context itself.
    """

    category: str
    generation_mode: GenerationMode
    source_evidence: tuple[SourceEvidenceChunk, ...]
    target: QuestionTarget
    relationship: QuestionRelationship
    competitors: tuple[CompetitorCandidate, ...]
    historical_reference: HistoricalStyleReference | None = None

    def __post_init__(self) -> None:
        if not self.category or not self.category.strip():
            raise PromptContextError("category must not be blank")
        if not self.source_evidence:
            raise PromptContextError("source_evidence must not be empty for question generation")
        if self.generation_mode == GenerationMode.STYLE_SIMILAR and self.historical_reference is None:
            raise PromptContextError(
                "STYLE_SIMILAR generation mode requires a historical_reference"
            )
        if self.generation_mode == GenerationMode.INDEPENDENT and self.historical_reference is not None:
            raise PromptContextError(
                "INDEPENDENT generation mode must not be supplied a historical_reference"
            )
        if self.target.category != self.category:
            raise PromptContextError(
                f"target.category {self.target.category!r} does not match the requested "
                f"category {self.category!r}"
            )
        if self.relationship.statement != self.target.factual_focus:
            raise PromptContextError(
                "relationship.statement does not match target.factual_focus - relationship "
                "must be extracted from this exact target, never substituted or reused across targets"
            )

    def render_variables(self) -> dict[str, str]:
        """The exact variable set the production generation prompt
        (``PromptId.QUESTION_GENERATION``) requires."""
        return {
            "category": self.category,
            "generation_mode": self.generation_mode.value,
            "source_evidence": format_student_summary_evidence(self.source_evidence),
            "historical_reference": format_historical_reference(self.historical_reference),
            "question_target": format_question_target(self.target),
            "target_answer_requirement": format_target_answer_requirement(self.target),
            "relationship_type": self.relationship.relationship_type,
            "competitor_concepts": format_competitors(self.competitors),
        }


@dataclass(frozen=True)
class QuestionTargetPlanningPromptContext:
    """Validated inputs for one WP-025 target-planning prompt render.

    Since WP-034, every planning call also carries ``coverage`` - a
    deterministic summary of what the category's already-generated
    questions have already tested (see
    ``exam_generator.planning.coverage.extract_category_coverage()``) -
    information only, never a rejection mechanism (WP-034 section 6:
    "coverage does NOT become another validator"). Defaults to an empty
    ``CategoryCoverage()`` ("nothing tested yet"), so every pre-WP-034
    caller/test continues to work unchanged.
    """

    category: str
    count: int
    source_evidence: tuple[SourceEvidenceChunk, ...]
    coverage: CategoryCoverage = CategoryCoverage()

    def __post_init__(self) -> None:
        if not self.category or not self.category.strip():
            raise PromptContextError("category must not be blank")
        if not self.source_evidence:
            raise PromptContextError("source_evidence must not be empty for target planning")
        if isinstance(self.count, bool) or not isinstance(self.count, int) or self.count < 1:
            raise PromptContextError(f"count must be a positive integer, got {self.count!r}")

    def render_variables(self) -> dict[str, str]:
        """The exact variable set the production target-planning prompt
        (``PromptId.QUESTION_TARGET_PLANNING``) requires."""
        return {
            "category": self.category,
            "count": str(self.count),
            "source_evidence": format_student_summary_evidence(self.source_evidence),
            "already_tested_summary": format_category_coverage(self.coverage),
        }


@dataclass(frozen=True)
class GroundingPromptContext:
    """Validated inputs for one grounding-validation prompt render."""

    candidate: CandidateQuestion
    source_evidence: tuple[SourceEvidenceChunk, ...]

    def __post_init__(self) -> None:
        if not self.source_evidence:
            raise PromptContextError("source_evidence must not be empty for grounding validation")

    def render_variables(self) -> dict[str, str]:
        """The exact variable set the production grounding prompt
        (``PromptId.GROUNDING_VALIDATION``) requires."""
        return {
            "candidate_question": format_candidate_question(self.candidate),
            "source_evidence": format_student_summary_evidence(self.source_evidence),
        }
