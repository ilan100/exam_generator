"""Deterministic category-coverage summary (WP-034).

``CategoryCoverage`` is deliberately internal-only: it is never part of
``CategoryQuestionSetRequest``/``CategoryGenerationResponse`` or any other
public request/response contract (WP-033 established that contract as
stable; WP-034 section 3 explicitly keeps coverage out of the public
API). It lives in ``exam_generator.models`` - not
``exam_generator.planning``, where it is actually produced and consumed -
purely to avoid a circular import: ``exam_generator.prompts`` needs this
type (to render it into the target-planning prompt) and
``exam_generator.planning`` already imports ``exam_generator.prompts``,
so this model follows the same precedent already set by
``QuestionRelationship``/``CompetitorCandidate`` (both generation-internal
concepts that nonetheless live in ``models/`` for the same reason).
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class CategoryCoverage(BaseModel):
    """A deterministic summary of one category's already-tested
    knowledge, derived from its already-generated questions - see
    ``exam_generator.planning.coverage.extract_category_coverage()`` for
    how it is computed, and that module's docstring for the honest
    limitation of what can be recovered from the production question
    schema alone.

    ``tested_concepts``: each already-generated question's own correct
    answer text, verbatim. ``tested_relationship_types``: the WP-030
    relationship-type vocabulary inferred from each question's text.
    Both are deduplicated, first-occurrence order preserved. Empty tuples
    (the default) mean "nothing tested yet" - never fabricated.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    tested_concepts: tuple[str, ...] = ()
    tested_relationship_types: tuple[str, ...] = ()
