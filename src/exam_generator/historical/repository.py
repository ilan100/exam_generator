"""Read-only access to ingested historical exam questions.

Historical questions are style/structure/terminology references only (see
docs/ARCHITECTURE.md and WP-002's ``HistoricalStyleReference``); this
repository never exposes them as, or converts them into, factual grounding
evidence (``SourceEvidenceChunk``).
"""

from __future__ import annotations

from pathlib import Path
from types import MappingProxyType
from typing import Mapping, Sequence

from exam_generator.historical.loader import default_workbook_path, load_historical_questions
from exam_generator.models import HistoricalStyleReference


class HistoricalQuestionRepository:
    """Read-only, in-memory view over the ingested historical workbook."""

    def __init__(
        self,
        questions: Sequence[HistoricalStyleReference],
        categories_in_order: Sequence[str],
    ) -> None:
        self._questions: tuple[HistoricalStyleReference, ...] = tuple(questions)
        self._categories: tuple[str, ...] = tuple(categories_in_order)

        by_category: dict[str, list[HistoricalStyleReference]] = {}
        for question in self._questions:
            by_category.setdefault(question.category, []).append(question)
        self._by_category: dict[str, tuple[HistoricalStyleReference, ...]] = {
            category: tuple(items) for category, items in by_category.items()
        }
        self._counts: Mapping[str, int] = MappingProxyType(
            {category: len(self._by_category.get(category, ())) for category in self._categories}
        )

    @classmethod
    def from_workbook(
        cls, path: Path | str, *, sheet_name: str | None = None
    ) -> "HistoricalQuestionRepository":
        """Load a repository from an explicit workbook path (used by tests
        against synthetic fixtures, and by callers with a non-default path)."""
        questions, categories = load_historical_questions(path, sheet_name=sheet_name)
        return cls(questions, categories)

    @classmethod
    def from_default_location(cls) -> "HistoricalQuestionRepository":
        """Load a repository from the configured default workbook location."""
        return cls.from_workbook(default_workbook_path())

    @property
    def all_questions(self) -> tuple[HistoricalStyleReference, ...]:
        """All successfully loaded historical questions, in workbook order."""
        return self._questions

    @property
    def canonical_categories(self) -> tuple[str, ...]:
        """Canonical categories, in first-seen workbook order."""
        return self._categories

    def questions_for_category(self, category: str) -> tuple[HistoricalStyleReference, ...]:
        """Questions for an exact canonical category, in workbook order.

        No fuzzy matching or alias resolution. An unknown category returns an
        empty tuple rather than raising, since callers may reasonably query
        category availability.
        """
        return self._by_category.get(category, ())

    @property
    def total_questions(self) -> int:
        return len(self._questions)

    @property
    def category_count(self) -> int:
        return len(self._categories)

    @property
    def counts_per_category(self) -> Mapping[str, int]:
        return self._counts
