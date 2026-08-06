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
    GenerationMode,
    HistoricalStyleReference,
    QuestionTarget,
    SourceEvidenceChunk,
)
from exam_generator.prompts.errors import PromptContextError
from exam_generator.prompts.formatting import (
    format_candidate_question,
    format_historical_reference,
    format_question_target,
    format_student_summary_evidence,
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
    """

    category: str
    generation_mode: GenerationMode
    source_evidence: tuple[SourceEvidenceChunk, ...]
    target: QuestionTarget
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

    def render_variables(self) -> dict[str, str]:
        """The exact variable set the production generation prompt
        (``PromptId.QUESTION_GENERATION``) requires."""
        return {
            "category": self.category,
            "generation_mode": self.generation_mode.value,
            "source_evidence": format_student_summary_evidence(self.source_evidence),
            "historical_reference": format_historical_reference(self.historical_reference),
            "question_target": format_question_target(self.target),
        }


@dataclass(frozen=True)
class QuestionTargetPlanningPromptContext:
    """Validated inputs for one WP-025 target-planning prompt render."""

    category: str
    count: int
    source_evidence: tuple[SourceEvidenceChunk, ...]

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
