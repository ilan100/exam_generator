"""Deterministic concept inventory extraction (WP-036 pilot).

Implements the "ConceptInventoryExtractor" responsibility WP-036 section 3
names: receive already-retrieved evidence, extract candidate concepts,
produce a deterministic concept inventory - as a plain function
(``extract_concept_inventory()``), matching this codebase's established
pattern for every other deterministic extraction step (``extract_relationship()``,
``discover_competitors()``, ``extract_category_coverage()`` are all plain
functions, never classes).

**Zero LLM calls, zero embeddings, zero semantic search** (WP-035's own
recommended hybrid strategy, section 8 of that investigation): structure-
first, marker-based, honest fallback. A line is extracted as a concept
candidate only when it exhibits a clear structural signal (see
``_is_candidate_concept_line()``) - never a best-effort guess over
ordinary prose. WP-035's real-corpus study found this signal reliable
specifically for capitalized, English, list-formatted named entities
(the dominant shape of "concepts" observed in this corpus - artery/tract/
nucleus names embedded in Hebrew prose); it is not expected to, and does
not attempt to, extract concepts from Hebrew-only prose.

This is a limited pilot (WP-036 section 2): only three categories, chosen
because WP-035's real-evidence study found them structurally suitable.
Every other category continues to use the existing WP-025 LLM-based
target planning entirely unchanged - see ``PILOT_CATEGORIES`` and its use
in ``exam_generator.planning.planner``.
"""

from __future__ import annotations

import re
from typing import Sequence

from pydantic import BaseModel, ConfigDict

from exam_generator.models import SourceEvidenceChunk
from exam_generator.models._common import NonBlankStr

#: The exact three categories WP-036 pilots concept-inventory-constrained
#: planning for - chosen from WP-035's real-evidence study
#: (`implementation/WP-035_ARCHITECTURE_INVESTIGATION.md` sections 2.1/2.3
#: plus a follow-up check of `גרעיני הבסיס`, whose top-scoring chunk is an
#: equally clean bulleted list of named sub-structures). Deliberately not
#: "all categories with English-list-shaped evidence" - WP-036 section 2
#: explicitly limits the pilot to three, to keep the blast radius small
#: and measurable.
PILOT_CATEGORIES: frozenset[str] = frozenset(
    {
        "אספקת דם",
        "מסילות עצביות",
        "גרעיני הבסיס",
    }
)

#: A candidate concept line must consist entirely of these characters
#: (after stripping whitespace) - deliberately ASCII-only. WP-035's study
#: found that lines mixing Hebrew and English are exactly the lines most
#: often corrupted by the source PDFs' bidi text extraction (WP-004,
#: pre-existing, unrelated to this WP); requiring a pure-ASCII line is a
#: simple, effective filter against extracting corrupted text, not merely
#: a language preference.
_CANDIDATE_LINE_PATTERN = re.compile(r"^[A-Za-z0-9()/,\-.\s]+$")

#: A candidate concept line must not exceed this many alphabetic words -
#: long ASCII runs are far more likely to be stray sentence fragments
#: (e.g. an equation or a citation) than a named concept. Chosen from
#: WP-035's real examples, the longest of which ("Anterior Inferior
#: Cerebellar Artery (AICA)") is 5 words.
_MAX_CONCEPT_WORDS = 6

#: A candidate concept line must contain at least this many alphabetic
#: characters in total. A direct, evidence-driven refinement: an early
#: extraction pass against this pilot's real corpus (see the WP-036
#: completion report) found that single uppercase letters ("A", "M", "P",
#: "V", "L", "N") were the single largest source of extraction noise -
#: not real concepts, but PDF line-wrapping artifacts where a word like
#: "Anterior" or "Medial" was split across two lines by the source PDF's
#: own layout, leaving one stray letter on its own line. 2 was chosen
#: (not 3) specifically to keep genuine short abbreviations observed in
#: this corpus - "VL", "LD", "LP", "GP" - which would otherwise also be
#: discarded.
_MIN_ALPHA_CHARS = 2

#: How many characters of context to keep on each side of a matched
#: concept when building its deterministic ``factual_focus`` snippet.
#: Deliberately a small, independent local implementation - not imported
#: from ``exam_generator.generation.competitors`` - since WP-036 section
#: 13 explicitly excludes touching competitor discovery; the two modules
#: happen to share the same simple technique (a fixed-width text window
#: around a keyword match) by coincidence of both needing one, not by
#: reuse.
_CONTEXT_WINDOW_CHARS = 120


class InventoryConcept(BaseModel):
    """One deterministically-extracted candidate concept (WP-036) - an
    internal-only model, never part of any public request/response
    contract (mirrors ``CategoryCoverage``'s WP-034 precedent).

    ``concept`` is the exact, verbatim extracted text (never rewritten or
    normalized) - honesty over convenience. ``evidence_chunk_id`` is a
    genuine canonical ``SourceEvidenceChunk.chunk_id``, never invented -
    the chunk this concept was actually found in. ``factual_focus`` is a
    deterministic context window around the concept's first occurrence in
    that chunk, used to build a ``QuestionTarget.factual_focus`` rich
    enough for WP-030's relationship classification to have something to
    key on (a bare entity name alone usually contains no relationship
    keyword). ``extraction_reason`` documents, in plain text, which
    structural signal caused this line to be extracted - never a numeric
    confidence score, since every extraction here is a clean structural
    match or it does not happen at all (WP-035's "never guess" principle
    admits no partial-confidence middle ground).

    ``source_line_indices`` (WP-043) - empty by default - is populated
    only when WP-039's trailing-truncation repair reconstructed
    ``concept`` from more than one raw source line (e.g. "Corpos Str" +
    "ia" + "tum"). It records every raw line index that contributed to
    the reconstructed text, in ascending order, so
    ``planning.concept_anchor.anchor_concept_evidence()`` can locate the
    concept's true origin span directly, instead of searching for a
    single raw line whose text exactly equals ``concept`` - a search that
    always fails for a reconstructed concept, since no single raw line
    ever contains its full reconstructed text verbatim (WP-043's own
    root-cause finding for why anchoring silently produced a bare,
    context-free ``factual_focus`` for such concepts).
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    concept: NonBlankStr
    evidence_chunk_id: NonBlankStr
    factual_focus: NonBlankStr
    extraction_reason: NonBlankStr
    source_line_indices: tuple[int, ...] = ()


def normalize_concept_text(text: str) -> str:
    """Deterministic concept-identity normalization for deduplication and
    coverage matching - collapse whitespace, case-fold. The same
    normalization shape already established for exact-duplicate question
    text (WP-014) and reused for coverage (WP-034), applied here to
    concept names instead."""
    return " ".join(text.split()).casefold()


def _is_candidate_concept_line(line: str) -> bool:
    """A line is a concept candidate only if it is a short, pure-ASCII,
    letter-containing, capitalized run - see the module docstring and the
    pattern/constant definitions above for the evidence-grounded reasoning
    behind each condition. Never a semantic judgment - purely structural."""
    stripped = line.strip()
    if not stripped:
        return False
    if not _CANDIDATE_LINE_PATTERN.match(stripped):
        return False
    alpha_char_count = sum(1 for character in stripped if character.isalpha())
    if alpha_char_count < _MIN_ALPHA_CHARS:
        return False
    if not any(character.isupper() for character in stripped):
        return False
    word_count = len(re.findall(r"[A-Za-z]+", stripped))
    if word_count == 0 or word_count > _MAX_CONCEPT_WORDS:
        return False
    return True


def _extract_context_window(text: str, concept: str) -> str:
    """A short, deterministic text window around the first occurrence of
    ``concept`` in ``text`` - the exact source substring, never rewritten
    or paraphrased. Falls back to ``concept`` itself if, unexpectedly, the
    already-matched concept text cannot be re-found (should not happen in
    practice, since ``concept`` was extracted from this exact ``text``,
    but never raises - matching this project's fail-honest-not-fail-loud
    convention for a purely cosmetic fallback)."""
    index = text.find(concept)
    if index == -1:
        return concept
    start = max(0, index - _CONTEXT_WINDOW_CHARS)
    end = min(len(text), index + len(concept) + _CONTEXT_WINDOW_CHARS)
    return text[start:end].strip()


def extract_concept_inventory(source_evidence: Sequence[SourceEvidenceChunk]) -> tuple[InventoryConcept, ...]:
    """Deterministically extract a concept inventory from already-
    retrieved evidence (WP-036 section 3). Pure function of its input;
    never calls an LLM provider, embeddings, or any other I/O.

    Scans each chunk's text line by line, in supplied (retrieval-rank)
    order, extracting a candidate for every line matching
    ``_is_candidate_concept_line()``. Concepts are deduplicated by
    ``normalize_concept_text()`` - the same concept appearing in a later
    chunk (a common corpus pattern - the same fact is often repeated
    across multiple source PDFs) is not extracted twice; the first
    (highest-retrieval-rank) occurrence is kept, matching this project's
    established "caller-supplied order is preserved, first occurrence
    wins" convention (WP-025's target ordering, WP-031's competitor
    ranking).

    Never fabricates a concept: a chunk contributing no matching lines
    (e.g. pure Hebrew prose, or off-topic/near-empty page-header
    fragments - both observed in WP-035's real-corpus study) simply
    contributes nothing, and an evidence set with no matching lines
    anywhere yields an empty inventory - not an error, and not a guess.
    """
    seen_normalized: set[str] = set()
    inventory: list[InventoryConcept] = []

    for chunk in source_evidence:
        for line in chunk.text.splitlines():
            if not _is_candidate_concept_line(line):
                continue
            concept_text = line.strip()
            normalized = normalize_concept_text(concept_text)
            if normalized in seen_normalized:
                continue
            seen_normalized.add(normalized)
            inventory.append(
                InventoryConcept(
                    concept=concept_text,
                    evidence_chunk_id=chunk.chunk_id,
                    factual_focus=_extract_context_window(chunk.text, concept_text),
                    extraction_reason=(
                        "standalone capitalized ASCII line "
                        f"({word_count_description(concept_text)}) - structural list-item signal"
                    ),
                )
            )

    return tuple(inventory)


def word_count_description(concept_text: str) -> str:
    """A tiny, honest, human-readable description of the matched line's
    shape, used only inside ``extraction_reason`` - not a scoring
    mechanism of any kind."""
    word_count = len(re.findall(r"[A-Za-z]+", concept_text))
    return f"{word_count} word{'s' if word_count != 1 else ''}"
