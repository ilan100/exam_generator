"""The tested-relationship domain model (WP-030).

Introduces the relationship being tested as a first-class application
concept, separate from ``QuestionTarget`` (WHAT to test - WP-025) and
separate from generation policy (HOW to construct the question - prompt
guidance only). ``QuestionRelationship`` is always deterministically
derived from an existing ``QuestionTarget`` by
``exam_generator.generation.relationship.extract_relationship()`` -
never produced, classified, or guessed by an LLM call.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from exam_generator.models._common import NonBlankStr


class QuestionRelationship(BaseModel):
    """The specific relationship a question tests.

    ``relationship_type`` is deliberately a plain string, not a closed
    enum: the vocabulary of relationship types (supplies, innervates,
    connects, contains, projects_to, located_in, develops_into,
    receives_input_from, drains_into, surrounds, and others) must remain
    extensible without a schema change, per WP-030 section 2's explicit
    "do not hard-code these values" instruction. ``UNSPECIFIED`` is the
    reserved fallback value when no known relationship keyword is found -
    never fabricated, never guessed.

    ``statement`` is the exact tested-relationship text this
    classification was derived from (identical to the source
    ``QuestionTarget.factual_focus`` - never rewritten or paraphrased),
    kept alongside the classification so a ``QuestionRelationship`` value
    is self-describing on its own.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    relationship_type: NonBlankStr
    statement: NonBlankStr
