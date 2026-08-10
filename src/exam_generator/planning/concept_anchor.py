"""Concept-anchored evidence (WP-037 pilot) and trailing-truncation
recovery (WP-039).

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
   extraction-artifact shapes observed in live pilot data (leading-
   character truncation and category self-restatement in WP-037;
   trailing-fragment truncation in WP-039) - never guessing a repair
   when the evidence does not unambiguously support one (WP-037 section
   10 / WP-039 section 8: "never invent a concept correction").
2. ``anchor_concept_evidence()`` - replaces the old fixed-width context
   window with a narrow, line-bounded walk that stops at the nearest
   sibling concept or paragraph boundary, so the evidence handed to
   generation is about the selected concept specifically, not "the
   selected concept plus everything nearby."

WP-038's live pilot surfaced a second-order consequence of *trailing*
truncation (disclosed but unaddressed by WP-037): a concept like
"Anterior Corticospinal T" (missing "ract") is correctly and completely
answered by generation, but coverage cannot recognize the complete
answer as covering the incomplete stored concept, causing repeated
reselection. WP-039 investigated the real evidence behind every observed
trailing-truncation shape (see ``docs/ARCHITECTURE.md``'s WP-039 section
and ``implementation/WP-039_COMPLETION_REPORT.md`` for the full,
evidence-grounded derivation) and found the root cause is the same PDF
bidi-text-extraction phenomenon WP-037's leading-truncation repair
already targets: a word wrapped across multiple physical PDF lines is
extracted with some of its fragments appearing on an adjacent line
(before or after, and occasionally spanning more than one adjacent
line) rather than joined into the same line as the rest of the word.
``_attempt_trailing_reconstruction()`` implements a conservative,
evidence-derived repair for this shape - see its own docstring.

**Zero LLM calls, zero embeddings, zero semantic search** - every
decision here is either a fixed keyword/character check or a bounded
line walk over already-retrieved text.
"""

from __future__ import annotations

from typing import Sequence

from exam_generator.models import SourceEvidenceChunk
from exam_generator.planning.concept_inventory import (
    _CANDIDATE_LINE_PATTERN,
    InventoryConcept,
    _is_candidate_concept_line,
    extract_concept_inventory,
    normalize_concept_text,
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


#: How many continuation-fragment lines ``_collect_trailing_fragments()``
#: will collect in one direction before giving up (WP-039 section 4:
#: real cases required up to two - "Corpos Str" needs "ia"+"tum" - but
#: this stays small and bounded, matching every other walk in this
#: module).
_MAX_TRAILING_FRAGMENTS = 5

#: Safety bound on how many raw lines ``_collect_trailing_fragments()``
#: will ever inspect in one direction - mirrors ``_MAX_RAW_SCAN_LINES``'s
#: purpose for ``_walk()``.
_MAX_TRAILING_RAW_SCAN_LINES = 12


def _looks_like_trailing_continuation_fragment(line: str) -> bool:
    """WP-039 section 6: a line is trusted as a trailing-truncation
    continuation fragment only if it is pure ASCII (the exact charset
    ``extract_concept_inventory()`` itself already requires,
    ``_CANDIDATE_LINE_PATTERN``) **and** its first word starts with a
    lowercase letter (reusing ``_looks_leading_truncated()``'s own,
    already-validated signal, applied here to a neighboring line rather
    than to the concept's own text).

    This combined check is derived directly from real corpus evidence
    (WP-039 section 4 investigation, not invented for the two originally-
    reported examples): every genuine standalone concept observed in this
    corpus starts with an uppercase letter (a structural property
    ``_looks_leading_truncated()`` already relies on elsewhere), so a
    lowercase-starting line is never a genuine sibling concept - only
    ever "more of a truncated word." The pure-ASCII requirement is what
    correctly rejects lines where a continuation-shaped fragment is fused
    with Hebrew text on the same physical line (e.g. the real corpus case
    ``' נקראים גםlia'`` - the same self-restatement-adjacent line WP-037
    already excludes for an unrelated reason) - such a line cannot be
    safely concatenated without also pulling in unrelated Hebrew prose,
    so it is never trusted as a fragment, matching WP-039 section 11's
    "no general text correction" boundary.
    """
    stripped = line.strip()
    if not stripped:
        return False
    if not _CANDIDATE_LINE_PATTERN.match(stripped):
        return False
    return _looks_leading_truncated(stripped)


def _collect_trailing_fragments(
    lines: list[str], *, start: int, step: int, consumed: set[int]
) -> list[tuple[int, str]]:
    """Walk from ``lines[start]`` in direction ``step`` (``-1`` backward,
    ``1`` forward), collecting consecutive continuation-fragment lines
    (see ``_looks_like_trailing_continuation_fragment()``), each paired
    with its own line index. Stops at the first line that does not
    qualify, at an already-``consumed`` index (already claimed by another
    concept's own successful reconstruction - see
    ``_repair_trailing_truncations()``), once
    ``_MAX_TRAILING_FRAGMENTS`` lines have been collected, or after
    ``_MAX_TRAILING_RAW_SCAN_LINES`` raw lines have been inspected -
    whichever comes first.
    """
    collected: list[tuple[int, str]] = []
    index = start + step
    scanned = 0

    while (
        0 <= index < len(lines)
        and scanned < _MAX_TRAILING_RAW_SCAN_LINES
        and len(collected) < _MAX_TRAILING_FRAGMENTS
    ):
        scanned += 1
        if index in consumed:
            break
        line = lines[index]
        if not _looks_like_trailing_continuation_fragment(line):
            break
        collected.append((index, line.strip()))
        index += step

    return collected


def _is_balanced_parens(text: str) -> bool:
    """A simple, deterministic well-formedness check - never a semantic
    judgment - used only to reject a trailing reconstruction that
    accidentally stopped mid-parenthetical (WP-039's own live example:
    "Substantia Nigra P" + "a" + "rs Reticulata (" stops one line short of
    its closing paren; per section 10's ambiguity rule, an unbalanced
    result is untrustworthy and must be excluded, never used partially)."""
    return text.count("(") == text.count(")")


def _attempt_trailing_reconstruction(
    lines: list[str], *, concept_index: int, consumed: set[int]
) -> tuple[str | None, list[int]]:
    """WP-039 sections 7-10: attempt to deterministically reconstruct a
    trailing-truncated concept from continuation-fragment lines
    immediately adjacent to its own line - in **either** direction,
    mirroring WP-037's own leading-truncation reconstruction, which
    already checks both neighbors because bidi text extraction can place
    a word's missing piece on either side (WP-039's own investigation
    found real examples of both: "Corpos Str"'s completing fragments
    appear *before* its own line; "Interna"'s completing fragment appears
    *after*).

    Collects continuation fragments independently in each direction (see
    ``_collect_trailing_fragments()``), then requires **exactly one**
    direction to have yielded any fragments at all - if neither direction
    has any, there is no evidence this concept is truncated, so it is
    correctly left alone (returns ``None`` - "unchanged," not "excluded";
    most concepts reach this function already complete, and the absence
    of adjacent continuation evidence is not itself evidence of
    incompleteness). If **both** directions independently yield
    fragments, the reconstruction is genuinely ambiguous (WP-039 section
    10: "if more than one plausible reconstruction exists, DO NOT
    REPAIR... EXCLUDE") - also returns ``None``, but the caller (which
    does distinguish "no evidence" from "ambiguous evidence" by re-
    checking whether the concept was already known-suspicious) excludes
    in this case; see ``_repair_trailing_truncations()``.

    When exactly one direction succeeds, the fragments are concatenated,
    in visitation order, onto the concept's own text; a single trailing
    period (ordinary sentence punctuation bleeding in from the source
    line, never part of an entity name in this corpus) is stripped; and
    the result is rejected (``None``) if its parentheses are unbalanced
    (``_is_balanced_parens()`` - a sign the walk stopped mid-fragment).

    Returns ``(reconstructed_text, consumed_line_indices)`` on success -
    the caller marks ``consumed_line_indices`` as claimed so a later
    concept's own walk cannot also claim the same physical line (the real
    corpus contains chains of 2-3 concepts sharing single-letter boundary
    lines, e.g. "Globus Pallidu"/"Putame"/"Lentifor", each claiming
    exactly the one fragment line between it and its neighbor).

    On failure (no evidence, or evidence found but unusable), returns
    ``(None, discovered_line_indices)`` instead of a bare ``None`` -
    ``discovered_line_indices`` is every fragment line inspected while
    deciding, empty when neither direction found anything. The caller
    (``_repair_trailing_truncations()``) still marks these as consumed
    even on failure: without this, a *different* concept could later
    walk into the same fragment lines and build an equally invalid,
    differently-ordered "reconstruction" - the real corpus case this
    fixes: "Substantia Nigra P"'s own (correctly rejected, unbalanced-
    parens) attempt discovers fragments "a" and "rs Reticulata (" one
    line away from an unrelated concept, "NSp.)"; without marking those
    two lines consumed here, "NSp.)" would separately and wrongly absorb
    them into "NSp.)rs Reticulata (a" - found and fixed during this WP's
    own development, exactly the kind of bug the ambiguity rule exists
    to prevent.
    """
    backward = _collect_trailing_fragments(lines, start=concept_index, step=-1, consumed=consumed)
    forward = _collect_trailing_fragments(lines, start=concept_index, step=1, consumed=consumed)
    discovered_indices = [index for index, _ in backward] + [index for index, _ in forward]

    candidates: list[tuple[str, list[int]]] = []
    if backward:
        text = lines[concept_index].strip() + "".join(fragment for _, fragment in backward)
        candidates.append((text, [index for index, _ in backward]))
    if forward:
        text = lines[concept_index].strip() + "".join(fragment for _, fragment in forward)
        candidates.append((text, [index for index, _ in forward]))

    if len(candidates) != 1:
        return None, discovered_indices

    text, consumed_indices = candidates[0]
    text = text.rstrip(".").strip()
    if not text or not _is_balanced_parens(text):
        return None, discovered_indices
    return text, consumed_indices


def _repair_trailing_truncations(
    refined: list[InventoryConcept], *, chunk_text_by_id: dict[str, str]
) -> list[InventoryConcept]:
    """WP-039: apply ``_attempt_trailing_reconstruction()`` to every
    concept in ``refined`` (the inventory after self-restatement exclusion
    and leading-truncation repair), grouped by ``evidence_chunk_id`` and
    processed in the inventory's own (first-occurrence) order, so a
    ``consumed`` line-index set can be shared across concepts from the
    same chunk (see ``_attempt_trailing_reconstruction()``'s own
    docstring for why this matters).

    A concept whose reconstruction attempt finds no adjacent continuation
    evidence in either direction is kept completely unchanged - the
    absence of evidence is not itself evidence of truncation (most
    concepts reach this function already complete). A concept whose
    attempt finds evidence but cannot safely resolve it (ambiguous - both
    directions yielded fragments - or malformed - unbalanced parentheses)
    is excluded entirely, never left in its truncated form and never
    guessed at (WP-039 section 10/25 Outcome D: "a false concept repair
    is more serious than leaving the concept unavailable").

    Finally, deduplicates by ``normalize_concept_text()`` (first
    occurrence wins - the same convention ``extract_concept_inventory()``
    already establishes), since a reconstruction can legitimately produce
    the same complete concept a different chunk already extracted intact
    (the real corpus case: "Neurom" reconstructs to "Neuromuscular
    Junction," already separately present, complete, from another chunk).
    """
    consumed_by_chunk: dict[str, set[int]] = {}
    lines_by_chunk: dict[str, list[str]] = {
        chunk_id: text.splitlines() for chunk_id, text in chunk_text_by_id.items()
    }

    repaired: list[InventoryConcept] = []
    for item in refined:
        chunk_id = item.evidence_chunk_id
        lines = lines_by_chunk.get(chunk_id, [])
        consumed = consumed_by_chunk.setdefault(chunk_id, set())

        concept_index = next((i for i, line in enumerate(lines) if line.strip() == item.concept), None)
        if concept_index is None:
            repaired.append(item)
            continue

        reconstructed_text, discovered_indices = _attempt_trailing_reconstruction(
            lines, concept_index=concept_index, consumed=consumed
        )
        if reconstructed_text is None:
            consumed.update(discovered_indices)
            if discovered_indices:
                continue  # ambiguous or malformed - exclude, never guess
            repaired.append(item)  # no adjacent evidence - already complete
            continue

        consumed.update(discovered_indices)
        repaired.append(
            item.model_copy(
                update={
                    "concept": reconstructed_text,
                    "extraction_reason": (
                        f"{item.extraction_reason} (WP-039: trailing fragment(s) restored from "
                        "adjacent continuation line(s) - unambiguous local reconstruction)"
                    ),
                }
            )
        )

    seen_normalized: set[str] = set()
    deduplicated: list[InventoryConcept] = []
    for item in repaired:
        normalized = normalize_concept_text(item.concept)
        if normalized in seen_normalized:
            continue
        seen_normalized.add(normalized)
        deduplicated.append(item)

    return deduplicated


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

    Finally (WP-039), every surviving concept is checked for *trailing*
    fragment truncation (``_repair_trailing_truncations()``) - a
    distinct, independently-discovered extraction-artifact shape from
    step 2's leading truncation, requiring its own detection/repair logic
    since (unlike leading truncation) there is no reliable signal in a
    concept's own text alone that it is incomplete; see that function's
    docstring for the full evidence-derived algorithm.

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

    repaired = _repair_trailing_truncations(refined, chunk_text_by_id=chunk_text_by_id)
    return tuple(repaired)


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
