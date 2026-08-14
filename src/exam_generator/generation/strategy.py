"""Deterministic generation-strategy-preference resolution (WP-054, WP-057).

``resolve_strategy_preference()`` classifies which
``GenerationStrategyPreference`` applies to a (category, target-topic)
pair - purely from application logic, before any generation LLM call, so
generation can be told the preference explicitly rather than inferring it.

This is the permanent production use of the identity-first strategy
WP-052 (retrospective analysis) diagnosed and WP-053 (a fresh, controlled,
live-API experiment) confirmed for ``Caudate Nucleus``/``Nucleus
Accumbens`` - see ``implementation/WP-052_COMPLETION_REPORT.md``,
``implementation/WP-053_COMPLETION_REPORT.md``, and
``implementation/WP-053_ARCHITECTURE_REVIEW.md`` - and, since WP-057, also
for ``Globus Pallidus``, following the identical evidence -> experiment ->
architecture-review -> implementation sequence: WP-055 (diagnostic
investigation), WP-056 (a fresh, controlled, live-API experiment testing
specifically reverse-framed identity generation), and the WP-056
architecture review's explicit approval - see
``implementation/WP-055_COMPLETION_REPORT.md``,
``implementation/WP-056_COMPLETION_REPORT.md``, and
``implementation/WP-056_ARCHITECTURE_REVIEW.md``. The mapping below is a
narrow, explicit, reviewed product/architecture decision, not a
runtime-computed signal: it is intentionally NOT derived from
distinct-chunk-mention counts (investigated and rejected as a general
mechanism by WP-051), historical failure counts, an LLM judgment, or any
other automatic classifier. Extending this mapping to any other
target/category requires its own dedicated evidence/experiment, per
WP-054's/WP-057's explicit non-generalization rule - do not broaden
``_IDENTITY_FIRST_TARGETS_BY_CATEGORY`` without one.
"""

from __future__ import annotations

from exam_generator.models import GenerationStrategyPreference

#: The only approved (category -> {target topics}) pairs for
#: IDENTITY_FIRST. Deliberately a small in-code table (mirroring
#: ``generation.relationship._RELATIONSHIP_KEYWORDS``'s own precedent for
#: a narrow, explicit, hand-reviewed mapping) - not read from the
#: historical Excel workbook or any other runtime data source at request
#: time; the decision itself was derived from historical evidence during
#: the WP-052/WP-053 investigation (``Caudate Nucleus``/``Nucleus
#: Accumbens``) and the WP-055/WP-056 investigation (``Globus Pallidus``),
#: but is now a fixed, reviewed policy.
_IDENTITY_FIRST_TARGETS_BY_CATEGORY: dict[str, frozenset[str]] = {
    "גרעיני הבסיס": frozenset({"Caudate Nucleus", "Nucleus Accumbens", "Globus Pallidus"}),
}


def resolve_strategy_preference(*, category: str, topic: str) -> GenerationStrategyPreference:
    """Deterministically resolve the generation-strategy preference for
    ``category``/``topic`` (a ``QuestionTarget.category``/``.topic`` pair).

    Returns ``GenerationStrategyPreference.IDENTITY_FIRST`` only for the
    three experimentally-approved (category, topic) pairs (``Caudate
    Nucleus``/``Nucleus Accumbens`` since WP-054; ``Globus Pallidus``
    since WP-057); ``DEFAULT`` for every other combination, including all
    three approved topics under any other category, and any other target
    within ``גרעיני הבסיס`` (e.g. ``Putamen``). Exact string matching
    only - no fuzzy/alias/case-insensitive/substring matching, consistent
    with ``QuestionTarget.topic`` always being the concept inventory's own
    structurally-extracted, verbatim text (WP-035/036).

    Pure function of its two string inputs; never calls an LLM provider,
    retrieval, or any other I/O.
    """
    approved_topics = _IDENTITY_FIRST_TARGETS_BY_CATEGORY.get(category, frozenset())
    if topic in approved_topics:
        return GenerationStrategyPreference.IDENTITY_FIRST
    return GenerationStrategyPreference.DEFAULT
