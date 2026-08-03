"""Domain-specific exceptions for local retrieval and category resolution."""

from __future__ import annotations


class RetrievalError(Exception):
    """Base class for retrieval-layer failures."""


class RetrievalIndexError(RetrievalError):
    """Failure constructing a ``FactualRetrievalIndex`` (empty corpus, empty
    vocabulary/feature set, invalid index parameters)."""


class RetrievalQueryError(RetrievalError):
    """An invalid retrieval query (empty/whitespace-only query, invalid
    ``top_k``)."""


class SourceTypeMismatchError(RetrievalIndexError):
    """The supplied corpus contains a chunk whose ``source_type`` does not
    match the index's declared single source type."""


class CategoryResolutionError(Exception):
    """Base class for category-resolution failures."""


class UnknownCategoryError(CategoryResolutionError):
    """The supplied category is neither a canonical category nor a
    configured alias."""


class InvalidCategoryMappingError(CategoryResolutionError):
    """The configured category alias mapping is structurally invalid (empty
    key/target, unknown target, or an alias colliding with an existing
    canonical category name)."""
