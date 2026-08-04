"""Domain-specific exceptions for the WP-017 evaluation layer."""

from __future__ import annotations


class EvaluationError(Exception):
    """Base class for all evaluation-layer failures."""


class UngroundedRetrievalQueryError(EvaluationError):
    """A retrieval-evaluation fixture entry's ``expected_literal_term``
    does not actually appear in the corpus being evaluated - the fixture
    itself is broken (or the corpus changed), not a retrieval miss."""
