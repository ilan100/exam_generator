"""Domain-specific exceptions for independent grounding validation.

Existing retrieval/prompt/LLM/pydantic errors are reused where they already
describe the failure; these are only for the grounding-layer concerns no
existing error hierarchy covers. A negative grounding verdict
(``GroundingValidationResult(passed=False, ...)``) is never one of these -
it is a successful validator execution, not a failure. Named
``GroundingValidationError`` rather than plain ``ValidationError`` to avoid
colliding with ``pydantic.ValidationError``, which is used throughout this
same layer.
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
