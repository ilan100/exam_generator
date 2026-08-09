"""The competitor-candidate domain model (WP-031).

Introduces deterministic awareness of *other* concepts in the already-
retrieved evidence that share the tested relationship - the missing
architectural layer WP-030's own live evidence and its architecture
review identified: the generator knew the correct concept and the tested
relationship, but nothing about what else in the evidence might also
satisfy that relationship. ``CompetitorCandidate`` values are always
deterministically derived by
``exam_generator.generation.competitors.discover_competitors()`` - never
produced, ranked, or invented by an LLM call.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from exam_generator.models._common import NonBlankStr


class CompetitorCandidate(BaseModel):
    """One other concept, found deterministically in already-retrieved
    evidence, that plausibly shares the tested relationship with the
    assigned target - information, not a decision.

    Contains only information genuinely known before generation runs:
    ``concept`` is a short, deterministically-extracted text window from
    the source evidence (never a parsed/invented entity name, never
    distractor text, never a generation decision) - the exact passage a
    reader would need to judge relevance for themselves.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    concept: NonBlankStr
    source_evidence_chunk_id: NonBlankStr
    relationship_relevance: NonBlankStr
    similarity_reason: NonBlankStr
