"""Domain-specific exceptions for the question-generation layer.

Existing category/retrieval/prompt/LLM/pydantic errors are reused where
they already describe the failure; these are only for the generation-layer
concerns that no existing error hierarchy covers.
"""

from __future__ import annotations


class GenerationError(Exception):
    """Base class for all generation-layer failures."""


class GenerationContextError(GenerationError):
    """The requested generation context itself is invalid (e.g. an
    unsupported ``generation_mode`` value)."""


class MissingEvidenceError(GenerationError):
    """No usable student-summary evidence was retrieved for the requested
    category; generation must fail before any LLM call is made."""


class MissingHistoricalReferenceError(GenerationError):
    """``STYLE_SIMILAR`` was requested but no historical style reference is
    available for the requested category. Never silently falls back to
    ``INDEPENDENT``."""


class InvalidGeneratedOutputError(GenerationError):
    """The LLM's structured response claims provenance that does not match
    the actual generation context (an evidence chunk id that was not
    supplied, or a historical-reference id inconsistent with what was
    actually supplied)."""
