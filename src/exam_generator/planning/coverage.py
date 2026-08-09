"""Deterministic coverage extraction (WP-034).

``extract_category_coverage()`` summarizes what a category's already-
generated questions have already tested, purely from application logic -
no LLM call, no summarization prompt, no embeddings, no semantic
similarity. This runs before target planning's own LLM call, so planning
can be told what has already been tested explicitly, the same pattern
WP-030 (relationship) and WP-031 (competitors) already established for
generation.

``CategoryCoverage`` itself (``exam_generator.models.coverage``) is a
deliberately internal-only model (WP-034 section 3): it is never part of
``CategoryQuestionSetRequest``/``CategoryGenerationRequest`` or any other
public contract - WP-033 established that contract as stable, and WP-034
section 7 explicitly forbids adding new fields to it. Coverage is instead
re-derived, on every call, from the same ``existing_questions`` the
public contract already carries.

Honest limitation (WP-034 section 4: "if existing fields are
insufficient, document exactly why"): the production question schema
(``ExamQuestion``/``CandidateQuestion``) carries only plain question/
answer text - it does not preserve the original ``QuestionTarget``
(WP-025) or ``QuestionRelationship`` (WP-030) that produced a given
question, since neither is part of the production schema and WP-033
deliberately did not add them (that would have meant redesigning the
now-stable contract). Coverage extraction can therefore only
*approximately* recover a question's tested concept/relationship by
re-applying the same deterministic heuristics used elsewhere in the
codebase to its plain text after the fact - never the ground truth the
original planning/generation call actually used.
"""

from __future__ import annotations

from typing import Sequence

from exam_generator.generation import UNSPECIFIED_RELATIONSHIP_TYPE, classify_relationship_type
from exam_generator.models import CategoryCoverage


def extract_category_coverage(existing_questions: Sequence[tuple[str, str]]) -> CategoryCoverage:
    """Deterministically extract ``CategoryCoverage`` from
    ``existing_questions`` - a sequence of ``(question_text,
    correct_answer_text)`` pairs, one per already-generated question for
    the category, in any order (planning consumes the resulting sets
    without depending on input order).

    Callers supply plain text pairs rather than a model instance directly
    because the two request contracts that call this
    (``CategoryGenerationRequest.existing_questions: tuple[CandidateQuestion, ...]``
    and ``CategoryQuestionSetRequest.existing_questions: tuple[ExamQuestion, ...]``)
    represent an answer choice differently (a ``list[str]`` indexed by
    ``correct_answer - 1`` vs. four discrete ``answer1``..``answer4``
    fields) - each caller resolves its own shape's correct-answer text
    before calling this shared, contract-agnostic function, rather than
    this function depending on either model directly.

    Pure function of its input; never calls an LLM provider, retrieval,
    embeddings, or any other I/O. An empty ``existing_questions`` yields
    an empty ``CategoryCoverage`` - never fabricates coverage that was
    not actually observed.
    """
    concepts: list[str] = []
    relationship_types: list[str] = []

    for question_text, correct_answer_text in existing_questions:
        concept = correct_answer_text.strip()
        if concept and concept not in concepts:
            concepts.append(concept)

        relationship_type = classify_relationship_type(f"{question_text} {correct_answer_text}".lower())
        if relationship_type != UNSPECIFIED_RELATIONSHIP_TYPE and relationship_type not in relationship_types:
            relationship_types.append(relationship_type)

    return CategoryCoverage(tested_concepts=tuple(concepts), tested_relationship_types=tuple(relationship_types))
