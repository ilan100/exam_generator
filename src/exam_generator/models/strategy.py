"""The generation-strategy-preference domain model (WP-054).

Separate from ``QuestionTarget`` (WHAT to test - WP-025) and separate from
``QuestionRelationship`` (the relationship being tested - WP-030):
``GenerationStrategyPreference`` is a narrow generation-policy preference -
HOW generation should approach constructing the question, for a small,
explicitly-approved set of (category, target) pairs - never an intrinsic
property of the target itself, and never stored on ``QuestionTarget``.

Always deterministically resolved by
``exam_generator.generation.strategy.resolve_strategy_preference()`` - never
produced, classified, or guessed by an LLM call, and never derived from a
general sparse-evidence signal, a chunk count, or a historical failure
count (WP-054 explicitly rejects generalizing beyond the two
experimentally-validated targets - see
``implementation/WP-053_COMPLETION_REPORT.md`` and
``implementation/WP-053_ARCHITECTURE_REVIEW.md``).
"""

from __future__ import annotations

from enum import Enum


class GenerationStrategyPreference(str, Enum):
    """How generation should approach the assigned target.

    ``DEFAULT`` is the ordinary case - no additional preference beyond the
    existing generation requirements. ``IDENTITY_FIRST`` is a preference,
    not an exclusive requirement (WP-054 section 15): generation should
    prefer a question whose correct answer is determined by the target's
    own identity/name, but may still fall back to its existing behavior if
    an identity-based question genuinely cannot be constructed from the
    supplied evidence.
    """

    DEFAULT = "DEFAULT"
    IDENTITY_FIRST = "IDENTITY_FIRST"
