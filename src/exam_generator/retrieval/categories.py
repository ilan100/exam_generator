"""Canonical category resolution, alias handling, and category-based
student-summary retrieval.

Canonical categories always originate from the WP-003 historical repository
- never duplicated here as constants/YAML lists. Category text itself is
used as the V1 baseline retrieval query; no fuzzy matching, translation, or
LLM-based expansion is performed.
"""

from __future__ import annotations

from types import MappingProxyType
from typing import Mapping, Sequence

from exam_generator.config.loader import load_category_mapping
from exam_generator.historical import HistoricalQuestionRepository
from exam_generator.models import ExamRequest
from exam_generator.retrieval.errors import InvalidCategoryMappingError, UnknownCategoryError
from exam_generator.retrieval.index import FactualRetrievalIndex
from exam_generator.retrieval.models import RetrievalResult


class CategoryResolver:
    """Resolves a requested category name to an exact canonical category.

    Exact canonical category names always resolve to themselves. An explicit
    alias resolves to its configured canonical target. Anything else is an
    unknown category and fails clearly - no fuzzy matching, no guessing.
    """

    def __init__(self, canonical_categories: Sequence[str], aliases: Mapping[str, str]) -> None:
        self._canonical: tuple[str, ...] = tuple(canonical_categories)
        canonical_set = set(self._canonical)

        validated_aliases: dict[str, str] = {}
        for alias, target in aliases.items():
            if not alias or not alias.strip():
                raise InvalidCategoryMappingError("Category alias key must not be empty or whitespace-only")
            if not target or not target.strip():
                raise InvalidCategoryMappingError(f"Category alias '{alias}' has an empty target")
            if target not in canonical_set:
                raise InvalidCategoryMappingError(
                    f"Category alias '{alias}' targets unknown canonical category '{target}'"
                )
            if alias in canonical_set:
                raise InvalidCategoryMappingError(
                    f"Category alias '{alias}' collides with an existing canonical category name "
                    "and must not redirect it"
                )
            validated_aliases[alias] = target

        self._canonical_set = canonical_set
        self._aliases: Mapping[str, str] = MappingProxyType(validated_aliases)

    @property
    def canonical_categories(self) -> tuple[str, ...]:
        return self._canonical

    def resolve(self, category: str) -> str:
        """Resolve ``category`` to its canonical name, or raise ``UnknownCategoryError``."""
        if category in self._canonical_set:
            return category
        if category in self._aliases:
            return self._aliases[category]
        raise UnknownCategoryError(f"Unknown category: {category!r}")


def build_category_resolver() -> CategoryResolver:
    """Build a resolver from the real historical repository and the
    configured ``config/category_mapping.yaml`` aliases."""
    repository = HistoricalQuestionRepository.from_default_location()
    mapping_config = load_category_mapping()
    return CategoryResolver(repository.canonical_categories, mapping_config.mapping)


def resolve_exam_request_categories(request: ExamRequest, resolver: CategoryResolver) -> ExamRequest:
    """Resolve every requested category to its canonical name.

    Fails via ``UnknownCategoryError`` if any requested category is unknown.
    Aliases that collapse onto the same canonical category have their
    requested counts combined; the total requested question count is
    preserved. Does not mutate ``request``; returns a new ``ExamRequest``.
    """
    combined: dict[str, int] = {}
    order: list[str] = []
    for category, count in request.categories.items():
        canonical = resolver.resolve(category)
        if canonical not in combined:
            combined[canonical] = 0
            order.append(canonical)
        combined[canonical] += count
    return ExamRequest(categories={name: combined[name] for name in order})


def retrieve_for_category(
    category: str,
    resolver: CategoryResolver,
    index: FactualRetrievalIndex,
    *,
    top_k: int | None = None,
) -> tuple[RetrievalResult, ...]:
    """Resolve ``category`` and query ``index`` (normally the student-summary
    index) using the canonical category text as the retrieval query.

    This is candidate-evidence retrieval only; it does not decide whether the
    returned chunks are sufficient to ground a generated question.
    """
    canonical = resolver.resolve(category)
    return index.search(canonical, top_k=top_k)
