"""Deterministic concept identity and coverage matching (WP-038 pilot).

WP-037's live pilot found that concept-anchored evidence substantially
improved target-to-question alignment, but exposed a new problem: coverage
exclusion (``exam_generator.planning.coverage.extract_category_coverage()``,
WP-034) compares the *assigned concept's own text* against the *generated
answer's text* with plain exact matching. When generation answers in a
different language/script than the assigned concept (observed live:
concept ``"Superior cerebellar artery"`` -> generated answer ``"עורק
סופריור צרבלרי"``), the exact-text comparison never recognizes the concept
as tested, so the same concept is repeatedly reselected.

This module introduces ``ConceptIdentity`` - a small, internal-only
representation of "this concept, plus every form safely known to refer to
the same concept" - and ``concept_identity_matches_text()``, which coverage
exclusion (``planning/planner.py``'s ``_select_remaining_concepts()``) uses
instead of comparing raw concept text.

**Investigation finding (WP-038 section 4/7/8), before any code was
written**: the live corpus behind all three pilot categories was inspected
directly (not guessed at) for explicit bilingual (English/Hebrew) pairings
near each of WP-037's live-pilot concepts. None was found - not for
"Superior cerebellar artery" (אספקת דם, 8 retrieved chunks, zero Hebrew
rendering anywhere), not for "Spinothalamic Tract" (מסילות עצביות - a
Hebrew rendering exists, but only in a *different* retrieved chunk, in
ordinary prose, not adjacent to the concept), and not for "Corpos
Str"/"Corpus Striatum" (גרעיני הבסיס - "קורפוס סטריאטום" appears later in
the *same* chunk, but only as ordinary independent prose reuse, never as an
explicit paired/parenthetical statement next to the English concept).
Section 8's preferred "evidence-derived identity" mechanism below is
therefore genuinely implemented and genuinely tested (it works whenever the
evidence contains an explicit paired form), but it does not fire for any of
WP-037's three live-pilot concepts, because their evidence does not contain
that structural pattern. This is reported honestly, not worked around -
see the WP-038 completion report's cross-language findings section.

**Explicitly not implemented, and why (WP-038 section 24)**: general
Hebrew/English phonetic transliteration matching. The live WP-037 data
itself shows the LLM's own transliteration is not even self-consistent -
the same concept ("Spinothalamic Tract") produced two different Hebrew
spellings ("ספינותלמית" vs "ספינתלמית") across two consecutive rounds, and
neither spelling was found anywhere in the retrieved evidence at all.
Building a general transliteration algorithm to bridge this would require
an approximate phonetic mapping - fundamentally a fuzzy-matching mechanism,
which section 24 explicitly prohibits ("Do NOT use edit distance as a
general equivalence mechanism", "Do NOT implement broad fuzzy matching").

**Zero LLM calls, zero embeddings, zero semantic search, zero fuzzy/edit-
distance matching** - every decision here is either a fixed structural
check or a deterministic text transform.
"""

from __future__ import annotations

import re
import unicodedata
from typing import Sequence

from pydantic import BaseModel, ConfigDict

from exam_generator.models._common import NonBlankStr
from exam_generator.planning.concept_inventory import InventoryConcept, normalize_concept_text

#: Characters stripped for the punctuation-normalized form (WP-038 section
#: 6) - deliberately a small, fixed set of characters already observed in
#: this corpus's concept text (parenthetical abbreviations, hyphenated
#: compounds), never a general "strip everything non-alphanumeric" rule,
#: to avoid silently merging genuinely distinct concepts that happen to
#: share the same letters (e.g. "GPe" vs "GPi" must never collapse).
_STRIPPABLE_PUNCTUATION_PATTERN = re.compile(r"[().,]")

#: The narrow, structural pattern an evidence-derived alternate-language
#: form must match to be trusted (WP-038 section 8): the concept's own
#: text immediately followed by a parenthetical run of Hebrew characters,
#: or a parenthetical run of Hebrew characters immediately followed by the
#: concept's own text - the same explicit-pairing convention this corpus
#: already uses for English abbreviations (e.g. "Anterior Inferior
#: Cerebellar Artery (AICA)"), just checked for a Hebrew payload instead.
#: Deliberately does NOT match Hebrew prose appearing anywhere else in the
#: chunk (WP-038 section 10: "false positive coverage is more dangerous
#: than false negative coverage") - see the module docstring for the real
#: corpus cases this correctly does NOT match.
_HEBREW_RUN_PATTERN = re.compile(r"[֐-׿][֐-׿\s]*[֐-׿]|[֐-׿]")


class ConceptIdentity(BaseModel):
    """An internal-only, deterministic representation of one concept's
    known identity - never part of any public request/response contract
    (mirrors ``InventoryConcept``/``CategoryCoverage``'s existing
    precedent).

    ``canonical_form`` is the concept's own extracted text, verbatim -
    never rewritten. ``normalized_forms`` are deterministic, always-safe
    text transforms of ``canonical_form`` (whitespace collapse, case
    folding, Unicode NFKC normalization, punctuation stripping) - every
    one of these is a lossless-intent transform of the *same* text, never
    a guess at a different form. ``explicitly_supported_language_forms``
    are alternate-language/script forms found via genuine, narrow,
    structural evidence adjacency (see ``_extract_paired_language_form()``)
    - empty by default, since most concepts have no such supporting
    evidence, and an empty tuple here is never treated as a failure, only
    as an honest "no safe alternate form is known" - see the module
    docstring's investigation finding for how often this is actually the
    case in the current pilot corpus.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    canonical_form: NonBlankStr
    normalized_forms: tuple[NonBlankStr, ...]
    explicitly_supported_language_forms: tuple[NonBlankStr, ...] = ()


def _punctuation_stripped(text: str) -> str:
    """Remove a small, fixed set of punctuation characters and collapse
    the resulting whitespace - see ``_STRIPPABLE_PUNCTUATION_PATTERN``."""
    return " ".join(_STRIPPABLE_PUNCTUATION_PATTERN.sub(" ", text).split())


def _unicode_normalized(text: str) -> str:
    """Unicode NFKC normalization (WP-038 section 6: "harmless Unicode
    normalization") - collapses compatibility-equivalent character
    sequences (e.g. presentation-form variants) that are the same text by
    definition, never a semantic judgment."""
    return unicodedata.normalize("NFKC", text)


def _deterministic_normalized_forms(canonical_form: str) -> tuple[str, ...]:
    """Every always-safe deterministic normalization of ``canonical_form``
    (WP-038 section 6), deduplicated, in a fixed order. Every one of these
    is independently derivable from ``canonical_form`` alone - none require
    external evidence or lookup."""
    candidates = [
        normalize_concept_text(canonical_form),
        normalize_concept_text(_unicode_normalized(canonical_form)),
        normalize_concept_text(_punctuation_stripped(canonical_form)),
    ]
    seen: list[str] = []
    for candidate in candidates:
        if candidate and candidate not in seen:
            seen.append(candidate)
    return tuple(seen)


def _extract_paired_language_form(chunk_text: str, concept: str) -> str | None:
    """WP-038 section 8 ("Preferred Principle: Evidence-Derived
    Identity"): if ``concept``'s own line in ``chunk_text`` is immediately
    preceded or followed (on the very same line, or the single adjacent
    non-blank line) by a parenthetical run of Hebrew text, return that
    Hebrew text as a safely evidence-supported alternate form.

    Deliberately narrow and structural - never a proximity/co-occurrence
    heuristic over the whole chunk (WP-038 section 10's conservative
    safety requirement: a Hebrew word appearing anywhere near a concept in
    ordinary prose is not evidence that it names the same concept - only
    an explicit, adjacent parenthetical pairing is trusted). Returns
    ``None`` (never guesses) when no such adjacent pairing exists - the
    common case for this pilot corpus, see the module docstring.
    """
    lines = chunk_text.splitlines()
    for index, line in enumerate(lines):
        stripped = line.strip()
        if concept not in stripped:
            continue
        candidates = [stripped]
        if index > 0:
            candidates.append(lines[index - 1].strip())
        if index + 1 < len(lines):
            candidates.append(lines[index + 1].strip())
        for candidate_line in candidates:
            match = re.search(rf"\(([^()]*)\)", candidate_line)
            if not match:
                continue
            parenthetical = match.group(1).strip()
            if parenthetical and _HEBREW_RUN_PATTERN.fullmatch(parenthetical):
                return parenthetical
    return None


def build_concept_identity(concept: InventoryConcept, *, chunk_text: str) -> ConceptIdentity:
    """Construct ``concept``'s deterministic ``ConceptIdentity`` from its
    own text plus (if genuinely present) an evidence-derived alternate
    form found in ``chunk_text`` - the same source chunk the concept was
    extracted from, never a different or aggregated evidence set (WP-038
    section 8: prefer evidence-derived identity over externally inferred
    identity - "evidence-derived" specifically means *this concept's own*
    evidence, not the whole category's retrieved set).
    """
    paired_form = _extract_paired_language_form(chunk_text, concept.concept)
    return ConceptIdentity(
        canonical_form=concept.concept,
        normalized_forms=_deterministic_normalized_forms(concept.concept),
        explicitly_supported_language_forms=(paired_form,) if paired_form else (),
    )


def _all_normalized_identity_forms(identity: ConceptIdentity) -> frozenset[str]:
    """Every form ``identity`` is willing to recognize as itself, each put
    through the same ``normalize_concept_text()`` used for coverage
    comparison elsewhere (WP-034/036's established normalization for this
    exact purpose)."""
    forms = {normalize_concept_text(identity.canonical_form)}
    forms.update(normalize_concept_text(form) for form in identity.normalized_forms)
    forms.update(normalize_concept_text(form) for form in identity.explicitly_supported_language_forms)
    return frozenset(forms)


def concept_identity_matches_text(identity: ConceptIdentity, candidate_text: str) -> bool:
    """True if ``candidate_text`` (an already-generated answer's text)
    matches any form ``identity`` recognizes as itself, after the same
    deterministic normalization applied to every stored form.

    Exact match only, after normalization - never a substring or fuzzy
    match (WP-038 section 10: conservative, false-negative-over-false-
    positive). A generated answer that merely *mentions* the concept
    within a longer sentence, or that uses an unsupported alternate
    representation (e.g. an unlisted transliteration spelling), correctly
    does not match - see the module docstring's honest reporting of this
    exact live scenario.
    """
    return normalize_concept_text(candidate_text) in _all_normalized_identity_forms(identity)


def concept_identities_for_inventory(
    inventory: Sequence[InventoryConcept], *, chunk_text_by_id: dict[str, str]
) -> dict[str, ConceptIdentity]:
    """Build a ``ConceptIdentity`` for every concept in ``inventory``,
    keyed by the concept's own ``concept`` text - a small convenience
    helper so callers (``planning/planner.py``) build every identity in
    one pass rather than repeating ``build_concept_identity()`` calls
    inline."""
    return {
        concept.concept: build_concept_identity(
            concept, chunk_text=chunk_text_by_id.get(concept.evidence_chunk_id, "")
        )
        for concept in inventory
    }
