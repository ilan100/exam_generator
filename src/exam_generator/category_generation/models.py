"""Control-layer request/response contracts for the WP-032
``CategoryGenerationService`` - the project's primary generation API,
introduced to replace "generate a whole exam" with "generate the next
question for a category" as the project's top-level capability (see
``docs/ARCHITECTURE.md``).

These wrap the existing, unmodified ``CandidateQuestion``/``GenerationMode``
(WP-002/WP-009) and ``QuestionAttempt``/``QuestionProductionResult``
(WP-013) contracts; they do not replace or redesign any of them.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, model_validator

from exam_generator.models import CandidateQuestion, ExamQuestion, GenerationMode
from exam_generator.models._common import NonBlankStr, NonNegativeIntStrict, StrictBool
from exam_generator.production import QuestionAttempt, QuestionProductionResult


class CategoryGenerationOptions(BaseModel):
    """Forward-compatible generation options (WP-032 section 2) - reserved
    for future difficulty/style-aware generation. Deliberately unused by
    every current pipeline component; carrying only default values today
    is intentional, not an oversight (WP-032 section 13 explicitly
    excludes redesigning generation itself)."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    difficulty: NonBlankStr | None = None
    style: NonBlankStr | None = None


class CategoryGenerationRequest(BaseModel):
    """One request to produce the next accepted question for ``category``,
    given every question already accepted for that category so far in the
    calling session (WP-032 section 1/5) - passed through to the
    generation layer unchanged, never summarized, concept-extracted, or
    used for diversity scoring (those remain future work packages).

    ``generation_mode`` stays a required, caller-supplied field rather
    than something this service infers from ``existing_questions``: mode
    alternation is a plan-level policy already owned by
    ``exam_generator.orchestration.build_exam_plan`` (fixed per planned
    position, independent of any later question-local failure/retry), and
    inferring it here from ``len(existing_questions)`` would silently
    drift from that policy the moment any earlier position in the same
    category failed. Preserving the caller's existing policy exactly
    (WP-032 section 12: "identical retry behavior... unchanged") takes
    priority over section 2's illustrative (explicitly non-binding)
    example shape.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    category: NonBlankStr
    generation_mode: GenerationMode
    existing_questions: tuple[CandidateQuestion, ...] = ()
    generation_options: CategoryGenerationOptions = Field(default_factory=CategoryGenerationOptions)


class CategoryGenerationResponse(BaseModel):
    """The outcome of one ``CategoryGenerationService.generate_next()``
    call: either an accepted question (``production`` - WP-013's full,
    unmodified result: the accepted candidate plus every attempt that led
    to it) or an honest, question-local failure (``failure_type``/
    ``failure_message``, mirroring
    ``exam_generator.orchestration.FailedPlannedQuestion``'s existing
    shape). Exactly one of the two is ever populated.

    ``duplicate_replacement_attempts``/``duplicate_productions`` mirror
    the equivalent pre-WP-032 exam-level fields, now produced per-call
    instead of accumulated across an entire exam - see the WP-032
    completion report for the resulting, deliberately-disclosed narrowing
    of duplicate-detection scope from "every question already accepted
    anywhere in the exam" to "every question supplied in this request's
    own ``existing_questions``".
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    accepted: StrictBool
    production: QuestionProductionResult | None = None
    duplicate_replacement_attempts: NonNegativeIntStrict = 0
    duplicate_productions: tuple[QuestionProductionResult, ...] = ()
    failure_type: NonBlankStr | None = None
    failure_message: NonBlankStr | None = None
    failure_attempts: tuple[QuestionAttempt, ...] = ()

    @model_validator(mode="after")
    def _check_consistent(self) -> "CategoryGenerationResponse":
        if self.accepted:
            if self.production is None:
                raise ValueError("production must be set when accepted=True")
            if self.failure_type is not None or self.failure_message is not None:
                raise ValueError("failure_type/failure_message must be unset when accepted=True")
            if self.failure_attempts:
                raise ValueError("failure_attempts must be empty when accepted=True")
        else:
            if self.production is not None:
                raise ValueError("production must be unset when accepted=False")
            if self.failure_type is None or self.failure_message is None:
                raise ValueError("failure_type and failure_message must both be set when accepted=False")
        return self

    @property
    def question(self) -> CandidateQuestion | None:
        """Convenience accessor matching WP-032 section 3's illustrative
        response shape - never a distinct stored field, to avoid
        duplicating ``production.candidate``."""
        return self.production.candidate if self.production is not None else None

    @property
    def attempts(self) -> int:
        """Convenience accessor matching WP-032 section 3's illustrative
        response shape: the number of ``QuestionProducer`` attempts that
        led to this outcome - derived from ``production.attempts``/
        ``failure_attempts``, never a distinct stored field."""
        if self.production is not None:
            return len(self.production.attempts)
        return len(self.failure_attempts)


class CategoryQuestionSetRequest(BaseModel):
    """WP-033's permanent replacement for ``CategoryGenerationRequest`` -
    the same "one more question for this category" request, except every
    existing question uses exactly the production question schema
    (``ExamQuestion``, WP-002's already-established, already-schema-
    exported contract) rather than the internal, pre-acceptance
    ``CandidateQuestion``. Section 3's "reuse the production question
    model, do not create a duplicate model" is followed literally -
    ``ExamQuestion`` itself is reused, unmodified beyond WP-033's own
    ``number``-becomes-optional change (see ``models/question.py``).

    ``existing_questions`` may legitimately hold anywhere from 0 to any
    number of questions (section 2: "no assumptions may be made about the
    count") and is passed through unchanged (section 6) - never
    summarized, concept-extracted, or used for diversity/coverage
    computation; those remain explicitly deferred to later work packages.
    A supplied existing question's own ``number`` may be a real assigned
    number (e.g. from an already-built exam) or ``None`` (e.g. an earlier
    question generated in this same category-extension session, not yet
    renumbered) - both are valid, since this contract never reads
    ``number`` for anything (only ``question`` text, for the existing
    exact-duplicate check WP-014 already established).

    ``generation_mode`` remains a required, caller-supplied field for the
    exact reason documented on ``CategoryGenerationRequest`` above - that
    reasoning is unchanged by WP-033 and still applies verbatim.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    category: NonBlankStr
    generation_mode: GenerationMode
    existing_questions: tuple[ExamQuestion, ...] = ()
    generation_options: CategoryGenerationOptions = Field(default_factory=CategoryGenerationOptions)


class CategoryQuestionSetResponse(BaseModel):
    """WP-033's permanent replacement for ``CategoryGenerationResponse``.

    ``question`` (WP-033 section 4) is the newly-generated question using
    exactly the same schema as every supplied existing question
    (``ExamQuestion``, ``number=None`` - "generation is responsible only
    for the question content"; the orchestration layer assigns
    ``number``/other runtime identifiers "if they are not already
    available"). ``production`` is retained alongside it, reusing WP-013's
    full unmodified result unchanged - the orchestration layer still needs
    the underlying ``CandidateQuestion``/full attempt history to build its
    own audit trail (``QuestionProductionRecord``/``FailedPlannedQuestion``,
    WP-014/WP-023, both untouched by WP-033); ``question`` and
    ``production.candidate`` always describe the same accepted candidate,
    never two different representations of two different questions.

    All other fields mirror ``CategoryGenerationResponse`` exactly - same
    meaning, same derivation, same accepted/failed consistency rule.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    accepted: StrictBool
    question: ExamQuestion | None = None
    production: QuestionProductionResult | None = None
    duplicate_replacement_attempts: NonNegativeIntStrict = 0
    duplicate_productions: tuple[QuestionProductionResult, ...] = ()
    failure_type: NonBlankStr | None = None
    failure_message: NonBlankStr | None = None
    failure_attempts: tuple[QuestionAttempt, ...] = ()

    @model_validator(mode="after")
    def _check_consistent(self) -> "CategoryQuestionSetResponse":
        if self.accepted:
            if self.question is None or self.production is None:
                raise ValueError("question and production must both be set when accepted=True")
            if self.failure_type is not None or self.failure_message is not None:
                raise ValueError("failure_type/failure_message must be unset when accepted=True")
            if self.failure_attempts:
                raise ValueError("failure_attempts must be empty when accepted=True")
        else:
            if self.question is not None or self.production is not None:
                raise ValueError("question and production must both be unset when accepted=False")
            if self.failure_type is None or self.failure_message is None:
                raise ValueError("failure_type and failure_message must both be set when accepted=False")
        return self

    @property
    def attempts(self) -> int:
        """Convenience accessor: the number of ``QuestionProducer``
        attempts that led to this outcome - derived, never a distinct
        stored field, mirroring ``CategoryGenerationResponse.attempts``."""
        if self.production is not None:
            return len(self.production.attempts)
        return len(self.failure_attempts)
