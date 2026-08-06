"""The WP-013 control layer: turns generation (WP-009) and the five
independent validators (WP-010/WP-011/WP-012) into a reliable
single-question production cycle.

    generate candidate
           v
    run all five validators (deterministic order, always to completion)
           v
    deterministic Python acceptance policy (CandidateValidationResults.accepted)
           v
    accepted -> return
    rejected -> regenerate, if attempts remain
           v
    attempts exhausted -> QuestionAttemptsExhaustedError

No LLM is ever asked whether a candidate should be accepted - acceptance is
plain, inspectable Python policy over the five independent results. This
module owns coordination only: it introduces no new generation or
validation logic, and never mutates a candidate or a validator's result.
"""

from __future__ import annotations

from exam_generator.config import load_app_config
from exam_generator.generation import InvalidGeneratedOutputError, QuestionGenerator
from exam_generator.models import CandidateQuestion, GenerationMode, QuestionTarget
from exam_generator.production.errors import InvalidProductionConfigurationError, QuestionAttemptsExhaustedError
from exam_generator.production.models import CandidateValidationResults, QuestionAttempt, QuestionProductionResult
from exam_generator.validation import (
    CategoryValidator,
    GroundingValidator,
    MCQValidator,
    QualityValidator,
    TextbookValidator,
)


def _validate_max_attempts(value: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise InvalidProductionConfigurationError(f"max_attempts must be an integer >= 1, got {value!r}")
    return value


class QuestionProducer:
    """Application-facing entry point for one single-question production
    cycle.

    Every dependency is injected explicitly - never hidden global state -
    so tests can supply fakes/mocks for the generator and each of the five
    validators independently. Use
    ``QuestionProducer.from_default_configuration()`` for the normal
    application wiring against real project configuration/data.
    """

    def __init__(
        self,
        *,
        generator: QuestionGenerator,
        grounding_validator: GroundingValidator,
        mcq_validator: MCQValidator,
        category_validator: CategoryValidator,
        quality_validator: QualityValidator,
        textbook_validator: TextbookValidator,
        max_attempts: int,
    ) -> None:
        self._generator = generator
        self._grounding_validator = grounding_validator
        self._mcq_validator = mcq_validator
        self._category_validator = category_validator
        self._quality_validator = quality_validator
        self._textbook_validator = textbook_validator
        self._max_attempts = _validate_max_attempts(max_attempts)

    @classmethod
    def from_default_configuration(cls) -> "QuestionProducer":
        """Construct the normal application wiring: the real generator, all
        five real validators, and ``config/app.yaml``'s existing
        ``generation.max_generation_attempts`` (WP-001) as the attempt
        bound - no new configuration value was needed.

        Requires ``OPENAI_API_KEY`` to be set (resolved by each
        component's own ``from_default_configuration()``).
        """
        return cls(
            generator=QuestionGenerator.from_default_configuration(),
            grounding_validator=GroundingValidator.from_default_configuration(),
            mcq_validator=MCQValidator.from_default_configuration(),
            category_validator=CategoryValidator.from_default_configuration(),
            quality_validator=QualityValidator.from_default_configuration(),
            textbook_validator=TextbookValidator.from_default_configuration(),
            max_attempts=load_app_config().generation.max_generation_attempts,
        )

    def _validate_candidate(self, candidate: CandidateQuestion) -> CandidateValidationResults:
        """Run all five validators, in a fixed deterministic order, to
        completion - never short-circuited after the first negative
        verdict. A negative verdict from any validator is a normal result;
        an operational failure from any validator propagates immediately
        and is never caught here."""
        return CandidateValidationResults(
            grounding=self._grounding_validator.validate_grounding(candidate),
            mcq=self._mcq_validator.validate(candidate),
            category=self._category_validator.validate(candidate),
            quality=self._quality_validator.validate(candidate),
            textbook=self._textbook_validator.validate(candidate),
        )

    def produce_question(
        self, *, category: str, generation_mode: GenerationMode, target: QuestionTarget
    ) -> QuestionProductionResult:
        """Produce exactly one accepted candidate for ``category``/
        ``generation_mode``, testing ``target`` (WP-025 - planned before
        generation begins), generating and validating up to
        ``max_attempts`` candidates.

        ``category``/``generation_mode``/``target`` are held fixed across
        every attempt - never silently altered, and never replaced with a
        newly-planned target merely because an earlier attempt was
        rejected (target planning owns diversity; this bounded budget
        owns candidate-production reliability - the two remain separate
        concerns). Stops at the first accepted candidate. Raises
        ``QuestionAttemptsExhaustedError`` (carrying every completed
        attempt) if all attempts are rejected.

        WP-019: a recoverable generation-contract failure
        (``InvalidGeneratedOutputError`` - the model's structured response
        could not safely become a ``CandidateQuestion``, e.g. it claimed
        evidence provenance that was never supplied) is caught here,
        recorded as a failed attempt consuming this same bounded attempt
        budget, and never reaches any validator - the fabricated response
        is discarded completely, never repaired, normalized, or guessed
        at. Every other operational failure (from generation or any
        validator - provider/auth/rate-limit/retrieval/prompt/config
        errors) still propagates immediately, consuming no further
        attempts and never retried here. Never mutates a candidate or a
        validator's result.
        """
        attempts: list[QuestionAttempt] = []

        for attempt_number in range(1, self._max_attempts + 1):
            try:
                candidate = self._generator.generate_candidate_question(
                    category=category, generation_mode=generation_mode, target=target
                )
            except InvalidGeneratedOutputError as exc:
                attempts.append(
                    QuestionAttempt(
                        attempt_number=attempt_number,
                        generation_failure_type=type(exc).__name__,
                        generation_failure_message=str(exc),
                    )
                )
                continue

            validations = self._validate_candidate(candidate)
            attempt = QuestionAttempt(
                attempt_number=attempt_number, candidate=candidate, validations=validations
            )
            attempts.append(attempt)

            if attempt.accepted:
                return QuestionProductionResult(candidate=candidate, attempts=tuple(attempts))

        raise QuestionAttemptsExhaustedError(
            f"Exhausted {self._max_attempts} generation attempt(s) for category {category!r} "
            f"({generation_mode.value}) without an accepted candidate",
            attempts=tuple(attempts),
        )
