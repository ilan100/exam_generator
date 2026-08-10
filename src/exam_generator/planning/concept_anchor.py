"""Concept-anchored evidence (WP-037 pilot).

WP-036's live pilot found that deterministic *target selection* worked -
every round was correctly assigned a different, coverage-filtered
concept - but the actual tested content frequently did not follow the
assignment, because ``InventoryConcept.factual_focus`` (a fixed 120-
character window around the concept's occurrence) was often still
dominated by a more salient neighboring entity in the same source
passage. WP-037 addresses this with two additive, deterministic,
LLM-free refinements - both applied only to WP-036's three pilot
categories, never touching ``extract_concept_inventory()`` itself:

1. ``refine_concept_inventory()`` - a post-processing pass over the raw
   WP-036 inventory that detects and either safely repairs or excludes
   two specific extraction-artifact shapes observed in WP-036's live
   data (leading-character truncation, category self-restatement) -
   never guessing a repair when the evidence does not unambiguously
   support one (WP-037 section 10: "never invent a concept correction").
2. ``anchor_concept_evidence()`` - replaces the old fixed-width context
   window with a narrow, line-bounded walk that stops at the nearest
   sibling concept or paragraph boundary, so the evidence handed to
   generation is about the selected concept specifically, not "the
   selected concept plus everything nearby."

**Zero LLM calls, zero embeddings, zero semantic search** - every
decision here is either a fixed keyword/character check or a bounded
line walk over already-retrieved text.
"""

from __future__ import annotations

from typing import Sequence

from exam_generator.models import SourceEvidenceChunk
from exam_generator.planning.concept_inventory import (
    InventoryConcept,
    _is_candidate_concept_line,
    extract_concept_inventory,
)

#: Hebrew "also called / known as" cue phrases (WP-037 section 11) - a
#: small, explicit, extensible keyword table, the same shape and spirit
#: as ``generation/relationship.py``'s own ``_RELATIONSHIP_KEYWORDS``.
#: A concept found shortly after one of these phrases is very likely a
#: naming/synonym statement about the category itself (WP-036's real
#: example: "...הבסיס נקראים גם lia \nThe Basal Gang..." - "...also
#: called The Basal Ganglia...") rather than a genuine, independently
#: testable sub-concept - deliberately lexical/keyword-based, never
#: semantic similarity, matching this codebase's established philosophy
#: since WP-030.
_NAMING_CUE_PHRASES: tuple[str, ...] = (
    "נקרא גם",
    "נקראים גם",
    "נקראת גם",
    "הנקרא",
    "המכונה",
    "מכונה גם",
    "ידוע גם כ",
    "ידועה גם כ",
)

#: How many characters immediately before a concept's occurrence to scan
#: for a naming-cue phrase. Small and local by design - a naming
#: statement is a short, adjacent grammatical construction, not a
#: paragraph-scale association.
_NAMING_CUE_WINDOW_CHARS = 60

#: How many lines to walk backward/forward from a selected concept's own
#: line when building its anchored evidence (see
#: ``anchor_concept_evidence()``). Deliberately small - WP-037 section 4:
#: "prefer the smallest trustworthy evidence unit."
_MAX_ANCHOR_WALK_LINES = 3


def _is_likely_category_self_restatement(chunk_text: str, concept: str) -> bool:
    """WP-037 section 11: true if a naming-cue phrase (see
    ``_NAMING_CUE_PHRASES``) appears within ``_NAMING_CUE_WINDOW_CHARS``
    characters immediately before ``concept``'s first occurrence in
    ``chunk_text``. Deterministic text comparison only - never semantic
    similarity, per section 11's explicit instruction."""
    index = chunk_text.find(concept)
    if index == -1:
        return False
    window_start = max(0, index - _NAMING_CUE_WINDOW_CHARS)
    preceding_text = chunk_text[window_start:index]
    return any(phrase in preceding_text for phrase in _NAMING_CUE_PHRASES)


def _looks_leading_truncated(concept: str) -> bool:
    """WP-037 section 10: true if ``concept``'s first word starts with a
    lowercase letter while the concept as a whole still passed
    ``extract_concept_inventory()``'s own "contains an uppercase letter
    somewhere" filter - the exact shape observed in WP-036's live data
    ("edial Lemniscus Tract", missing a leading "M"). A purely structural
    check, never a dictionary/spellcheck lookup."""
    words = concept.split()
    if not words:
        return False
    first_word = words[0]
    return first_word[0].isalpha() and first_word[0].islower()


def _attempt_leading_reconstruction(chunk_text: str, concept: str) -> str | None:
    """WP-037 section 10, outcome A ("unambiguous local reconstruction"):
    if ``concept``'s own line in ``chunk_text`` has exactly one immediate
    neighbor line (the line directly before or directly after it) that
    consists of a single uppercase letter and nothing else, prepend that
    letter to reconstruct the truncated word - the exact adjacent-orphan-
    letter shape WP-036's own extraction already excludes as noise (see
    ``concept_inventory._MIN_ALPHA_CHARS``), now reused here as the
    completing fragment for the *specific* concept it was severed from.

    Returns ``None`` (outcome B, "reject/exclude") if the concept's line
    cannot be found, if neither neighbor qualifies, or if *both* neighbors
    qualify (genuinely ambiguous - never guess which one is correct).
    """
    lines = chunk_text.splitlines()
    for index, line in enumerate(lines):
        if line.strip() != concept:
            continue
        neighbors = []
        if index > 0:
            neighbors.append(lines[index - 1].strip())
        if index + 1 < len(lines):
            neighbors.append(lines[index + 1].strip())
        single_letter_neighbors = [n for n in neighbors if len(n) == 1 and n.isalpha() and n.isupper()]
        if len(single_letter_neighbors) == 1:
            return single_letter_neighbors[0] + concept
        return None
    return None


def refine_concept_inventory(source_evidence: Sequence[SourceEvidenceChunk]) -> tuple[InventoryConcept, ...]:
    """WP-037: apply the extraction-artifact policy (section 10) and the
    category-self-restatement policy (section 11) to WP-036's raw
    ``extract_concept_inventory()`` output. ``extract_concept_inventory()``
    itself is never modified - this is an additive, separate refinement
    layer, used only by the pilot-category planning path.

    For every raw concept, in order:
    1. If it looks like a category self-restatement (naming-cue-phrase
       proximity), exclude it.
    2. Else if it looks leading-truncated, attempt an unambiguous local
       reconstruction; use the repaired concept if found, otherwise
       exclude it (never guess).
    3. Otherwise, keep it unchanged.

    Deterministic, pure function of its input; never calls an LLM
    provider, embeddings, or any other I/O.
    """
    raw_inventory = extract_concept_inventory(source_evidence)
    chunk_text_by_id = {chunk.chunk_id: chunk.text for chunk in source_evidence}

    refined: list[InventoryConcept] = []
    for item in raw_inventory:
        chunk_text = chunk_text_by_id.get(item.evidence_chunk_id, "")

        if _is_likely_category_self_restatement(chunk_text, item.concept):
            continue

        if _looks_leading_truncated(item.concept):
            reconstructed = _attempt_leading_reconstruction(chunk_text, item.concept)
            if reconstructed is None:
                continue
            refined.append(
                item.model_copy(
                    update={
                        "concept": reconstructed,
                        "extraction_reason": (
                            f"{item.extraction_reason} (WP-037: leading character restored from an "
                            "adjacent single-letter orphan line - unambiguous local reconstruction)"
                        ),
                    }
                )
            )
            continue

        refined.append(item)

    return tuple(refined)


def anchor_concept_evidence(*, chunk_text: str, concept: str) -> str:
    """WP-037 section 4: build a narrow, deterministic factual-focus
    context around ``concept``'s own line in ``chunk_text``, instead of
    ``concept_inventory``'s wide fixed-character window.

    Locates ``concept``'s own line (or, if not found verbatim - e.g. a
    reconstructed concept whose reconstructed leading character is not
    literally present in the source text - the longest suffix of
    ``concept`` that *is* found, so anchoring still works for repaired
    concepts). Walks backward and forward from that line (see ``_walk()``),
    including each non-blank neighboring line, but **stopping before**
    including any line that is itself a candidate concept line (WP-037
    section 4: "avoid unnecessarily including neighboring facts" - a
    sibling list item's own name is exactly the kind of competing fact
    WP-036's live pilot showed causes generation to drift), a genuine
    paragraph boundary (two *consecutive* blank lines - a single blank
    line is treated as visual spacing within the same logical list item,
    not a boundary, since this corpus uses single blank lines liberally
    and stopping at the first one was found, during development, to
    frequently strip a concept of all context whatsoever), or
    ``_MAX_ANCHOR_WALK_LINES`` non-blank lines included in either
    direction, whichever comes first.

    Falls back to ``concept`` itself if no matching line can be found at
    all (should not happen in practice, but never raises - the same
    fail-honest-not-fail-loud convention ``concept_inventory``'s own
    fallback already uses).
    """
    lines = chunk_text.splitlines()
    concept_index, consumed_neighbor_index = _find_concept_line_index(lines, concept)
    if concept_index is None:
        return concept

    backward = _walk(
        lines, start=concept_index, step=-1, consumed_neighbor_index=consumed_neighbor_index
    )
    backward.reverse()
    forward = _walk(
        lines, start=concept_index, step=1, consumed_neighbor_index=consumed_neighbor_index
    )

    # Always display the caller-supplied concept text (already the
    # authoritative, possibly-reconstructed form) rather than the raw
    # source line - the two only ever differ by the reconstructed leading
    # character(s), which the "consumed_neighbor_index" skip above already
    # ensures is not also duplicated as separate context.
    anchored_lines = backward + [concept] + forward
    return "\n".join(anchored_lines).strip()


#: Safety bound on how many raw lines ``_walk()`` will ever inspect in one
#: direction, regardless of how many turn out to be blank - prevents an
#: unusual chunk (e.g. one with long runs of single blank lines) from
#: being scanned without limit while still allowing single blanks to be
#: skipped over rather than treated as an immediate stop.
_MAX_RAW_SCAN_LINES = 12


def _walk(lines: list[str], *, start: int, step: int, consumed_neighbor_index: int | None) -> list[str]:
    """Walk from ``lines[start]`` in direction ``step`` (``-1`` for
    backward, ``1`` for forward), collecting non-blank, non-candidate-
    concept lines in the order visited (backward results are reversed by
    the caller). Stops at two consecutive blank lines, at a candidate
    concept line, once ``_MAX_ANCHOR_WALK_LINES`` lines have been
    collected, or after ``_MAX_RAW_SCAN_LINES`` raw lines have been
    inspected - whichever comes first. Skips ``consumed_neighbor_index``
    (already absorbed into a reconstructed concept, see
    ``_find_concept_line_index()``) without counting it as blank."""
    collected: list[str] = []
    consecutive_blanks = 0
    index = start + step
    raw_scanned = 0

    while 0 <= index < len(lines) and raw_scanned < _MAX_RAW_SCAN_LINES and len(collected) < _MAX_ANCHOR_WALK_LINES:
        raw_scanned += 1
        if index == consumed_neighbor_index:
            index += step
            continue

        line = lines[index]
        if not line.strip():
            consecutive_blanks += 1
            if consecutive_blanks >= 2:
                break
            index += step
            continue
        consecutive_blanks = 0

        if _is_candidate_concept_line(line):
            break

        collected.append(line)
        index += step

    return collected


def _find_concept_line_index(lines: list[str], concept: str) -> tuple[int | None, int | None]:
    """Find ``concept``'s own line by exact match first; if not found (a
    reconstructed concept whose repaired leading character was never
    literally present in the source text), fall back to matching the
    suffix of ``concept`` obtained by dropping its leading 1-2 characters
    - covering exactly WP-037's own reconstruction shape (a single
    prepended letter), never an open-ended fuzzy search.

    Returns ``(line_index, consumed_neighbor_index)``: the second value
    is the index of the immediate neighbor line that was "absorbed" into
    the reconstruction (so the caller can skip re-including it as
    separate context), or ``None`` when an exact match was found and
    nothing was consumed.
    """
    for index, line in enumerate(lines):
        if line.strip() == concept:
            return index, None
    for drop in (1, 2):
        if drop >= len(concept):
            break
        suffix = concept[drop:]
        for index, line in enumerate(lines):
            if line.strip() != suffix:
                continue
            for neighbor_index in (index - 1, index + 1):
                if 0 <= neighbor_index < len(lines) and lines[neighbor_index].strip() == concept[:drop]:
                    return index, neighbor_index
            return index, None
    return None, None
