"""Domain-specific exceptions for independent candidate-quality validation.

Existing retrieval/prompt/LLM/pydantic errors are reused where they already
describe the failure; these are only for validation-layer concerns no
existing error hierarchy covers. A negative validation verdict (e.g.
``GroundingValidationResult(passed=False, ...)``, ``TextbookCheckResult
(status=NOT_FOUND, ...)``) is never one of these - it is a successful
validator execution, not a failure. Named ``...ValidationError`` rather than
plain ``ValidationError`` to avoid colliding with ``pydantic.ValidationError``,
which is used throughout this same layer.
"""

from __future__ import annotations


class GroundingValidationError(Exception):
    """Base class for all grounding-validation-layer failures."""


class NoValidationEvidenceError(GroundingValidationError):
    """No usable student-summary evidence could be independently retrieved
    to validate a candidate; validation must fail before any LLM call."""


class InvalidGroundingOutputError(GroundingValidationError):
    """The LLM's structured grounding response claims supporting evidence
    chunk id(s) that were not actually supplied to the validator."""


class TextbookValidationError(Exception):
    """Base class for all textbook-validation-layer failures."""


class InvalidTextbookOutputError(TextbookValidationError):
    """The LLM's structured textbook-check response cites a source page or
    reference text that does not correspond to any course-book chunk
    actually supplied to the validator."""
