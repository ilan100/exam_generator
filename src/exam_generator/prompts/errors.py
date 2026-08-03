"""Domain-specific exceptions for the external prompt infrastructure.

Callers should never need to interpret raw ``str.format``/filesystem
exceptions for expected prompt-boundary failures.
"""

from __future__ import annotations


class PromptError(Exception):
    """Base class for all prompt-layer failures."""


class PromptRepositoryError(PromptError):
    """Failure loading a prompt from the configured prompt directory: a
    required file is missing, or its content is empty/whitespace-only."""


class PromptNotFoundError(PromptRepositoryError):
    """The requested ``PromptId`` is not known to the repository."""


class PromptTemplateError(PromptRepositoryError):
    """A prompt file's placeholder syntax could not be parsed, or uses an
    unsupported placeholder form (positional/numbered fields,
    attribute/index access, conversion syntax, or a format spec)."""


class PromptRenderError(PromptError):
    """Rendering failed: a required variable was not supplied, an
    unexpected variable was supplied, or substitution itself failed."""


class PromptContextError(PromptError):
    """A prompt-context value object, or a formatting helper, was given an
    invalid combination of inputs (e.g. blank category, empty required
    evidence, a generation-mode/historical-reference mismatch, or evidence
    of the wrong source type)."""
