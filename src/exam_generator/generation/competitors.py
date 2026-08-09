"""Deterministic competitor discovery (WP-031).

``discover_competitors()`` identifies other passages in the *already-
retrieved* evidence (no new retrieval call) that plausibly share the
tested relationship with the assigned target - the missing layer WP-030's
own architecture review identified: the generator knew the correct
concept and the tested relationship, but nothing about what else in the
evidence might satisfy the same relationship. This runs entirely in
Python before the generation LLM call - no LLM call, no embeddings, no
vector database, no ontology, using only ``QuestionTarget``,
``QuestionRelationship``, and the ``SourceEvidenceChunk``\\ s generation
already received.

The application discovers and ranks candidates only; it never decides
which (if any) become a distractor, and never authors distractor text -
that remains entirely generation's responsibility (WP-031 section 2's
explicit separation).
"""

from __future__ import annotations

from exam_generator.generation.relationship import UNSPECIFIED_RELATIONSHIP_TYPE, keywords_for
from exam_generator.models import CompetitorCandidate, QuestionRelationship, QuestionTarget, SourceEvidenceChunk

#: How many characters of context to keep on each side of a matched
#: keyword when extracting `concept` - a fixed-width window, not sentence
#: parsing (the corpus's OCR'd text does not reliably use clean sentence
#: punctuation), so this remains a simple, deterministic, honest heuristic
#: rather than an attempt at real natural-language processing.
_CONTEXT_WINDOW_CHARS = 80


def _extract_snippet(text: str, keyword: str) -> str | None:
    """Return a short, deterministic text window around the first
    case-insensitive occurrence of ``keyword`` in ``text``, or ``None`` if
    not found. Never rewrites or paraphrases - the exact source substring,
    trimmed."""
    lowered_text = text.lower()
    lowered_keyword = keyword.lower()
    index = lowered_text.find(lowered_keyword)
    if index == -1:
        return None
    start = max(0, index - _CONTEXT_WINDOW_CHARS)
    end = min(len(text), index + len(keyword) + _CONTEXT_WINDOW_CHARS)
    return text[start:end].strip()


def discover_competitors(
    *,
    target: QuestionTarget,
    relationship: QuestionRelationship,
    source_evidence: tuple[SourceEvidenceChunk, ...],
) -> tuple[CompetitorCandidate, ...]:
    """Deterministically discover other evidence-supported concepts
    sharing ``relationship``'s classification, from ``source_evidence``
    alone.

    Excludes only the chunks already cited as the target's own supporting
    evidence (``target.supporting_evidence_chunk_ids``) - every other
    supplied chunk is eligible, since a competitor is by definition
    evidence for something *other* than the assigned target. Returns an
    empty tuple when ``relationship`` is ``UNSPECIFIED`` (nothing to
    search for) or when no other chunk contains a matching keyword -
    never a guess.

    Ranking policy (WP-031 section 5, documented here rather than tuned
    empirically): candidates are returned in ``source_evidence``'s own
    existing order, which is already the retrieval index's relevance rank
    (WP-006, TF-IDF cosine score, highest first) - an already-computed
    deterministic signal, not a new one invented for this purpose.

    Pure function of its inputs; never mutates any argument; never calls
    an LLM provider, retrieval, or any other I/O.
    """
    if relationship.relationship_type == UNSPECIFIED_RELATIONSHIP_TYPE:
        return ()

    keywords = keywords_for(relationship.relationship_type)
    if not keywords:
        return ()

    excluded_chunk_ids = set(target.supporting_evidence_chunk_ids)
    competitors: list[CompetitorCandidate] = []
    for chunk in source_evidence:
        if chunk.chunk_id in excluded_chunk_ids:
            continue
        for keyword in keywords:
            snippet = _extract_snippet(chunk.text, keyword)
            if snippet is not None:
                competitors.append(
                    CompetitorCandidate(
                        concept=snippet,
                        source_evidence_chunk_id=chunk.chunk_id,
                        relationship_relevance=relationship.relationship_type,
                        similarity_reason=(
                            f"This passage, from evidence other than the assigned target's own, also "
                            f"contains a '{relationship.relationship_type}'-type relationship."
                        ),
                    )
                )
                break  # one candidate per chunk - the first matching keyword is sufficient

    return tuple(competitors)
