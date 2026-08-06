"""Independent validation result contracts.

These models represent the *result* of future validation behavior (grounding,
MCQ structure, category, quality, textbook consistency). This module does not
implement any validation logic itself.
"""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, ConfigDict, Field

from exam_generator.models._common import NonBlankStr, PositiveIntStrict, StrictBool, UnitInterval


class GroundingValidationResult(BaseModel):
    """Result of independently checking a candidate against source evidence.

    A generator's own claim that its question is grounded is never trusted;
    this result is produced only by an independent validator.

    Since WP-022, this model is no longer sent directly to the LLM - the
    LLM-facing contract is ``GroundingValidationResponse`` (below), which
    reports provenance via call-local evidence references rather than
    canonical chunk identifiers. ``GroundingValidator`` deterministically
    resolves those references and constructs this result; ``evidence_chunk_ids``
    is always a genuine, verified canonical identifier from the evidence
    actually supplied, never invented or guessed - the invariant is
    unchanged, only how it is established.
    """

    model_config = ConfigDict(extra="forbid")

    grounded: StrictBool = Field(
        description="Whether the question's factual premise is supported by the supplied evidence."
    )
    correct_answer_supported: StrictBool = Field(
        description="Whether the candidate's stated correct answer is supported by the supplied evidence."
    )
    other_answers_not_equally_correct: StrictBool = Field(
        description="Whether no other answer choice is equally well supported by the supplied evidence."
    )
    evidence_chunk_ids: list[NonBlankStr] = Field(
        default_factory=list,
        description=(
            "Identifiers of only the supplied evidence chunks that actually support this "
            "determination. Resolved (WP-022) from the validator's own call-local "
            "evidence references - always a genuine identifier from the evidence "
            "actually supplied, never invented or guessed."
        ),
    )
    evidence_text: NonBlankStr | None = Field(
        default=None, description="The supporting evidence text, when evidence_chunk_ids is reported."
    )
    reason: NonBlankStr = Field(
        description=(
            "A concise explanation of this determination. Required. Must always contain a "
            "substantive, non-empty explanation, even when the determination is positive - "
            "never an empty string."
        )
    )
    confidence: UnitInterval = Field(
        description=(
            "Confidence in this determination, from 0.0 to 1.0. Does not by itself "
            "determine pass/fail."
        )
    )

    @property
    def passed(self) -> bool:
        """Centralized pass rule - callers must use this, not re-derive it.

        Confidence is bounded but intentionally does not affect pass/fail.
        """
        return self.grounded and self.correct_answer_supported and self.other_answers_not_equally_correct


class GroundingValidationResponse(BaseModel):
    """The LLM-facing structured-output contract for one grounding-validation
    call (WP-022), returned by ``LLMProvider.generate_structured(...,
    response_model=GroundingValidationResponse, profile=LLMProfile.VALIDATION)``.

    Deliberately mirrors ``GroundingValidationResult`` except for provenance:
    the model reports ``evidence_refs`` - small, 1-based, call-local
    integers matching the "[Evidence N]" labels already shown in the
    prompt's factual-evidence section - instead of reproducing canonical
    ``SourceEvidenceChunk.chunk_id`` strings character-for-character.

    Never exposed beyond ``GroundingValidator``: it is discarded immediately
    after strict reference validation, once resolved into the existing,
    unchanged ``GroundingValidationResult`` with genuine canonical
    ``evidence_chunk_ids``. See ``exam_generator.validation.grounding``.
    """

    model_config = ConfigDict(extra="forbid")

    grounded: StrictBool = Field(
        description="Whether the question's factual premise is supported by the supplied evidence."
    )
    correct_answer_supported: StrictBool = Field(
        description="Whether the candidate's stated correct answer is supported by the supplied evidence."
    )
    other_answers_not_equally_correct: StrictBool = Field(
        description="Whether no other answer choice is equally well supported by the supplied evidence."
    )
    evidence_refs: list[int] = Field(
        default_factory=list,
        description=(
            "1-based local references to the supplied evidence items that actually "
            "support this determination, matching the '[Evidence N]' labels shown in "
            "the factual evidence below - e.g. 1 refers to [Evidence 1]. Cite only "
            "evidence numbers that were actually supplied to you. Never invent a "
            "number outside the supplied range. If you are not confident which "
            "evidence number supports your determination, leave this list empty "
            "rather than guessing - an empty list is always acceptable and preferred "
            "over an invented or approximate reference."
        ),
    )
    evidence_text: NonBlankStr | None = Field(
        default=None, description="The supporting evidence text, when evidence_refs is reported."
    )
    reason: NonBlankStr = Field(
        description=(
            "A concise explanation of this determination. Required. Must always contain a "
            "substantive, non-empty explanation, even when the determination is positive - "
            "never an empty string."
        )
    )
    confidence: UnitInterval = Field(
        description=(
            "Confidence in this determination, from 0.0 to 1.0. Does not by itself "
            "determine pass/fail."
        )
    )


class MCQValidationResult(BaseModel):
    """Structural/semantic MCQ validation result."""

    model_config = ConfigDict(extra="forbid")

    valid: StrictBool = Field(description="Whether the candidate's multiple-choice structure is valid.")
    exactly_four_answers: StrictBool = Field(description="Whether the candidate has exactly four answer choices.")
    single_best_answer: StrictBool = Field(
        description="Whether exactly one answer choice is unambiguously the single best answer."
    )
    reason: NonBlankStr = Field(
        description=(
            "A concise explanation of this determination. Required. Must always contain a "
            "substantive, non-empty explanation, even when the determination is positive - "
            "never an empty string."
        )
    )


class CategoryValidationResult(BaseModel):
    """Category-appropriateness validation result."""

    model_config = ConfigDict(extra="forbid")

    valid: StrictBool = Field(
        description="Whether the candidate question genuinely belongs to the requested canonical category."
    )
    requested_category: NonBlankStr = Field(description="The canonical category name that was requested.")
    assessed_category: NonBlankStr | None = Field(
        default=None,
        description="The category the question's subject matter actually appears to fit, if different.",
    )
    reason: NonBlankStr = Field(
        description=(
            "A concise explanation of this determination. Required. Must always contain a "
            "substantive, non-empty explanation, even when the determination is positive - "
            "never an empty string."
        )
    )


class QualityValidationResult(BaseModel):
    """Minimal stylistic/quality validation result."""

    model_config = ConfigDict(extra="forbid")

    valid: StrictBool = Field(
        description="Whether the candidate question meets general exam-quality expectations."
    )
    reason: NonBlankStr = Field(
        description=(
            "A concise explanation of this determination. Required. Must always contain a "
            "substantive, non-empty explanation, even when the determination is positive - "
            "never an empty string."
        )
    )


class TextbookCheckStatus(str, Enum):
    """Secondary, non-authoritative textbook consistency status."""

    CONSISTENT = "CONSISTENT"
    NOT_FOUND = "NOT_FOUND"
    POTENTIAL_CONFLICT = "POTENTIAL_CONFLICT"


class TextbookCheckResult(BaseModel):
    """Secondary textbook validation result.

    A ``CONSISTENT`` result does not itself satisfy student-summary grounding,
    and a missing/absent textbook check does not invalidate an otherwise
    properly grounded question.

    ``evidence_chunk_ids`` (WP-018) is the primary, strictly-verified
    provenance signal. Since WP-022, this model is no longer sent directly
    to the LLM - the LLM-facing contract is ``TextbookValidationResponse``
    (below), which reports provenance via call-local evidence references;
    ``TextbookValidator`` deterministically resolves those into this
    result's canonical ``evidence_chunk_ids`` and, where available,
    ``source_page`` (derived from the first resolved chunk - never claimed
    by the LLM). ``reference_text`` (WP-022: no longer LLM-facing at all -
    there is no deterministic equivalent of a short human excerpt once
    verbatim reproduction is no longer required) is always ``None`` going
    forward; the field remains on the contract only for downstream/schema
    stability.
    """

    model_config = ConfigDict(extra="forbid")

    status: TextbookCheckStatus = Field(
        description=(
            "Exactly one of CONSISTENT, POTENTIAL_CONFLICT, or NOT_FOUND, describing how "
            "the supplied course-book evidence relates to the candidate question."
        )
    )
    evidence_chunk_ids: list[NonBlankStr] = Field(
        default_factory=list,
        description=(
            "Identifiers of only the supplied course-book evidence chunks that support "
            "this determination. Resolved (WP-022) from the validator's own call-local "
            "evidence references - always a genuine identifier from the evidence "
            "actually supplied, never invented or guessed. Empty if status is NOT_FOUND "
            "or if no supplied chunk is a good match."
        ),
    )
    source_page: PositiveIntStrict | None = Field(
        default=None,
        description=(
            "The page number of the supplied course-book evidence that supports this "
            "determination, if any was resolved. Deterministically derived (WP-022) from "
            "the first resolved evidence chunk - never claimed directly by the LLM."
        ),
    )
    reference_text: NonBlankStr | None = Field(
        default=None,
        description=(
            "No longer populated (WP-022) - retained on the contract for downstream/"
            "schema stability only. Always None; see the class docstring."
        ),
    )
    reason: NonBlankStr = Field(
        description=(
            "A concise explanation of this determination. Required. Must always contain a "
            "substantive, non-empty explanation - never an empty string."
        )
    )


class TextbookValidationResponse(BaseModel):
    """The LLM-facing structured-output contract for one textbook-consistency
    call (WP-022), returned by ``LLMProvider.generate_structured(...,
    response_model=TextbookValidationResponse, profile=LLMProfile.VALIDATION)``.

    Deliberately smaller than ``TextbookCheckResult``: the model reports
    only ``status``/``evidence_refs``/``reason`` - call-local evidence
    references (matching the prompt's "[Evidence N]" labels), never
    canonical chunk identifiers, and never ``source_page``/``reference_text``
    as provenance proof (both become deterministically derivable from the
    resolved canonical chunk instead - see
    ``exam_generator.validation.textbook``).

    Never exposed beyond ``TextbookValidator``: discarded immediately after
    strict reference validation, once resolved into the existing,
    unchanged ``TextbookCheckResult``.
    """

    model_config = ConfigDict(extra="forbid")

    status: TextbookCheckStatus = Field(
        description=(
            "Exactly one of CONSISTENT, POTENTIAL_CONFLICT, or NOT_FOUND, describing how "
            "the supplied course-book evidence relates to the candidate question."
        )
    )
    evidence_refs: list[int] = Field(
        default_factory=list,
        description=(
            "1-based local references to the supplied course-book evidence items that "
            "support this determination, matching the '[Evidence N]' labels shown in "
            "the course-book evidence below - e.g. 1 refers to [Evidence 1]. Cite only "
            "evidence numbers that were actually supplied to you. Never invent a number "
            "outside the supplied range. Leave empty if status is NOT_FOUND or no "
            "supplied evidence is a good match - an empty list is always acceptable and "
            "preferred over an invented or approximate reference."
        ),
    )
    reason: NonBlankStr = Field(
        description=(
            "A concise explanation of this determination. Required. Must always contain a "
            "substantive, non-empty explanation - never an empty string."
        )
    )
