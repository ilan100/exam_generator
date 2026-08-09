"""Deterministic relationship extraction (WP-030).

``extract_relationship()`` classifies the relationship a ``QuestionTarget``
tests, purely from application logic - no LLM call, no prompt asking a
model to identify anything. This runs before the generation LLM call, so
generation can be told the classified relationship type explicitly rather
than inferring it implicitly from free-text alone.

This is a coarse, keyword-based heuristic, not a real natural-language
relation-extraction system - deliberately: the project's own architecture
review (WP-028) and the WP-029 proposal both favor small, honest,
deterministic application logic over anything resembling free-form model
judgment. A target whose ``factual_focus`` does not contain a recognized
keyword classifies as ``UNSPECIFIED`` rather than guessing - the same
fail-honest philosophy the rest of this codebase already applies to
uncertain LLM-facing claims, applied here to uncertain deterministic
classification instead.
"""

from __future__ import annotations

from exam_generator.models import QuestionRelationship, QuestionTarget

UNSPECIFIED_RELATIONSHIP_TYPE = "UNSPECIFIED"

#: Ordered (relationship_type, keywords) table - first match wins. Keywords
#: are matched case-insensitively as substrings of `factual_focus`. Hebrew
#: verb forms are listed alongside their common English equivalents, since
#: `factual_focus` values may mix both. Extending the vocabulary is a pure
#: data change (add a tuple) - never a schema/model change, per the
#: `QuestionRelationship.relationship_type` docstring's own "do not
#: hard-code" instruction.
_RELATIONSHIP_KEYWORDS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("SUPPLIES", ("מספק", "מספקת", "מספקים", "אספקת דם", "supplies", "supplying")),
    ("INNERVATES", ("מעצבב", "מעצבבת", "עצבוב", "innervates", "innervating")),
    ("CONNECTS", ("מחבר", "מחברת", "מחברים", "מקשר", "connects", "connect ", "connecting", "connection between")),
    ("CONTAINS", ("כולל", "כוללת", "כוללים", "מכיל", "מכילה", "מורכב מ", "מורכבת מ", "contains", "consists of", "composed of")),
    ("PROJECTS_TO", ("מקרין", "מקרינה", "פרויקציה", "projects to", "projecting to")),
    ("LOCATED_IN", ("ממוקם", "ממוקמת", "נמצא ב", "נמצאת ב", "located in", "found in")),
    ("DEVELOPS_INTO", ("מתפתח מ", "מתפתחת מ", "מתפתח ל", "מתפתחת ל", "develops from", "develops into", "developing from")),
    ("RECEIVES_INPUT_FROM", ("מקבל קלט מ", "מקבלת קלט מ", "מקבל מידע מ", "מקבלת מידע מ", "receives input from")),
    ("DRAINS_INTO", ("מתנקז", "מתנקזת", "מנקז", "מנקזת", "drains into", "draining into")),
    ("SURROUNDS", ("מקיף", "מקיפה", "עוטף", "עוטפת", "surrounds", "surrounding")),
)


def keywords_for(relationship_type: str) -> tuple[str, ...]:
    """The keyword variants used to classify ``relationship_type`` (WP-031:
    reused by competitor discovery to scan other evidence chunks for the
    same relationship). Returns an empty tuple for
    ``UNSPECIFIED_RELATIONSHIP_TYPE`` or any unrecognized value - there is
    nothing to search for when no classification was made.
    """
    for known_type, keywords in _RELATIONSHIP_KEYWORDS:
        if known_type == relationship_type:
            return keywords
    return ()


def classify_relationship_type(haystack: str) -> str:
    """Deterministically classify which relationship type (if any) is
    expressed in already-lowercased free text ``haystack`` - the shared
    keyword-matching primitive behind ``extract_relationship()`` (below,
    operating on a ``QuestionTarget.factual_focus``) and WP-034's
    ``exam_generator.planning.coverage.extract_category_coverage()``
    (operating on already-generated question/answer text), so both
    callers reuse exactly the same classification rules rather than each
    maintaining their own copy.

    Scans for the first matching keyword in ``_RELATIONSHIP_KEYWORDS``
    (case-insensitive substring match, table order = priority order);
    returns ``UNSPECIFIED_RELATIONSHIP_TYPE`` if none match. Pure function
    of its input; never calls an LLM provider, retrieval, or any other I/O.
    """
    for relationship_type, keywords in _RELATIONSHIP_KEYWORDS:
        if any(keyword.lower() in haystack for keyword in keywords):
            return relationship_type
    return UNSPECIFIED_RELATIONSHIP_TYPE


def extract_relationship(target: QuestionTarget) -> QuestionRelationship:
    """Deterministically classify the relationship ``target`` tests.

    Scans ``target.factual_focus`` for the first matching keyword (see
    ``classify_relationship_type()``); returns
    ``UNSPECIFIED_RELATIONSHIP_TYPE`` if none match. Pure function of its
    input - the same target always classifies identically. Never mutates
    ``target``; never calls an LLM provider, retrieval, or any other I/O.
    """
    relationship_type = classify_relationship_type(target.factual_focus.lower())
    return QuestionRelationship(relationship_type=relationship_type, statement=target.factual_focus)
