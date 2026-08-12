"""Deterministic target evidence-role detection (WP-043 Part B).

WP-042's diagnostic investigation found that ``Basillar artery`` repeatedly
failed grounding validation under WP-040's target-answer-identity
requirement, for a reason unrelated to WP-041's English-first policy: the
evidence positions ``Basillar artery`` as the **source** feeding into
another, more salient artery (``Superior Cerebellar Artery``, which
actually supplies the named area) - not as the supplied entity a "which
artery supplies X" question naturally expects as its answer. Generation
kept constructing exactly that question shape, and grounding correctly
kept rejecting it, because the evidence does not support ``Basillar
artery`` as the answer to that specific question shape.

``detect_source_evidence_role()`` recognizes this one, narrow, real corpus
shape deterministically: the evidence's own structured list format labels
a value with a Hebrew "source" cue (e.g. "מקור :" -
"source:") immediately before it - exactly the label already observed,
verbatim, in the real corpus, immediately preceding ``Basillar artery``'s
own occurrence, and absent immediately before the *other* artery in the
same passage (``Superior cerebellar artery``, which is the subject of its
own sentence, not a labeled source value).

**Zero LLM calls, zero embeddings, zero semantic search, zero general
relationship/knowledge-graph inference** - a single, narrow, keyword-
proximity check, in the same spirit and using the same technique as
WP-037's own ``_is_likely_category_self_restatement()`` (a different cue
phrase, the same "look for an explicit label within a short window
immediately before the concept's occurrence" mechanism). This is
deliberately not a general "who supplies whom" relationship extractor -
WP-043 section 14 explicitly forbids building a medical knowledge graph in
this WP; it recognizes exactly the one structural pattern this corpus is
already observed to use for this specific case.
"""

from __future__ import annotations

from exam_generator.planning.concept_inventory import _is_candidate_concept_line

#: The Hebrew "source" label this corpus's own structured evidence lists
#: use, verbatim - confirmed directly against real evidence during this
#: WP's own investigation (WP-042's diagnostic capture, re-verified here):
#: "Basillar artery"'s own occurrence is immediately preceded by this
#: exact label; "Superior cerebellar artery" (the sibling entity in the
#: same passage that is *not* a labeled source value) is not.
_SOURCE_ROLE_CUE_PHRASES: tuple[str, ...] = ("מקור",)

#: How many characters immediately before a concept's occurrence to scan
#: for the source-role cue. Small and local by design, matching WP-037's
#: own naming-cue-phrase precedent: a structured "label: value" pairing
#: is a short, adjacent construction, not a paragraph-scale association.
#: Verified against the real corpus: the cue phrase and its value are
#: separated by only a handful of characters ("מקור
#: :\n" immediately before the value).
_SOURCE_ROLE_CUE_WINDOW_CHARS = 25


def detect_source_evidence_role(chunk_text: str, concept: str) -> bool:
    """WP-043 Part B: true if a source-role cue phrase (see
    ``_SOURCE_ROLE_CUE_PHRASES``) appears within
    ``_SOURCE_ROLE_CUE_WINDOW_CHARS`` characters immediately before
    ``concept``'s first occurrence in ``chunk_text``. Deterministic text
    comparison only - never semantic similarity, never a general
    relationship inference. Returns ``False`` (never guesses) when
    ``concept`` cannot be found in ``chunk_text`` verbatim (e.g. a
    leading-truncation-reconstructed concept whose repaired text differs
    in case from the raw source) - the safe, conservative default that
    matches this project's fail-closed convention: an undetected role is
    treated as the ordinary default (the target is the subject of its own
    evidence), never assumed to be a source role without positive
    evidence.
    """
    index = chunk_text.find(concept)
    if index == -1:
        return False
    window_start = max(0, index - _SOURCE_ROLE_CUE_WINDOW_CHARS)
    preceding_text = chunk_text[window_start:index]
    return any(phrase in preceding_text for phrase in _SOURCE_ROLE_CUE_PHRASES)


#: WP-044 Part B: how many raw lines ``extract_source_relationship_entity()``
#: will scan backward from the source-role concept's own line before
#: giving up - bounded, matching every other walk in ``planning/``. The
#: real corpus distance is exactly 3 lines (the concept's own line, the
#: "מקור :" cue line, and one bullet-marker "o" line) before reaching the
#: downstream entity's own heading line; this stays generously larger
#: while remaining a small, fixed bound rather than an unbounded search.
_SOURCE_RELATIONSHIP_MAX_BACKWARD_SCAN_LINES = 6


def extract_source_relationship_entity(chunk_text: str, concept: str) -> str | None:
    """WP-044 Part B: when ``concept``'s evidence positions it as a source
    value (see ``detect_source_evidence_role()``), deterministically
    identify the name of the other, downstream entity this source value
    belongs to - the real corpus structure this corresponds to is a
    labeled list-item pairing:

        <downstream entity - a candidate-concept heading line>
        o
        מקור :
        <source entity - concept's own line>
        o
        אזור אספקת דם :<supply-area description>

    so the downstream entity is the nearest candidate-concept line (see
    ``concept_inventory._is_candidate_concept_line()`` - the same
    structural "standalone capitalized ASCII line" signal used everywhere
    else in this codebase to recognize a named entity) found by scanning
    backward from ``concept``'s own line, skipping the non-candidate cue/
    bullet-marker lines between them, within
    ``_SOURCE_RELATIONSHIP_MAX_BACKWARD_SCAN_LINES`` lines.

    Returns ``None`` (never guesses) when ``concept`` cannot be found as
    its own standalone line, or when no candidate-concept line is found
    within the bounded backward scan - the same fail-honest-not-fail-loud
    convention this module's own ``detect_source_evidence_role()`` already
    uses. Deterministic text/structure matching only - never semantic
    similarity, never a general relationship extractor, never an LLM call.
    """
    lines = chunk_text.splitlines()
    concept_index = next((index for index, line in enumerate(lines) if line.strip() == concept), None)
    if concept_index is None:
        return None

    scanned = 0
    index = concept_index - 1
    while index >= 0 and scanned < _SOURCE_RELATIONSHIP_MAX_BACKWARD_SCAN_LINES:
        scanned += 1
        candidate_line = lines[index].strip()
        if _is_candidate_concept_line(candidate_line):
            return candidate_line
        index -= 1
    return None
