"""Domain-specific exceptions for the single-question production/control layer.

Existing generation/validation error hierarchies are reused where they
already describe the failure (an operational LLM/provider/prompt/retrieval
failure raised by ``QuestionGenerator`` or any of the five validators simply
propagates unchanged - it is never caught and reinterpreted here). These
are only for control-layer concerns no existing error hierarchy covers.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from exam_generator.production.models import QuestionAttempt


class ProductionError(Exception):
    """Base class for all control-layer production failures."""


class InvalidProductionConfigurationError(ProductionError):
    """The configured/supplied ``max_attempts`` is invalid (must be >= 1)."""


class QuestionAttemptsExhaustedError(ProductionError):
    """Every configured generation attempt completed (each a normal,
    operationally successful generate-then-validate cycle), but no
    candidate was accepted.

    This is a normal, expected outcome of the acceptance policy rejecting
    every attempt - not an operational failure. Carries every completed
    ``QuestionAttempt`` (in 1-based attempt order) so callers retain full
    diagnostic history rather than only the final rejection.
    """

    def __init__(self, message: str, *, attempts: tuple["QuestionAttempt", ...]) -> None:
        super().__init__(message)
        self.attempts = attempts
