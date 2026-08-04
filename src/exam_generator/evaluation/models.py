"""Evaluation-layer result contracts (WP-017).

Deliberately separate from the WP-002/WP-015 audit/output contracts -
evaluation reporting must never modify or extend those (WP-017 section 21).
These models exist purely to hold *observed* data from running the
existing, unmodified production pipeline; they introduce no new domain
policy of their own.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from exam_generator.models import GenerationMode, TextbookCheckStatus
from exam_generator.models._common import CorrectAnswerId, NonBlankStr, NonNegativeIntStrict, PositiveIntStrict, StrictBool


class CandidateAttemptRecord(BaseModel):
    """One complete generate-then-validate attempt observed during
    evaluation, whether or not it was accepted.

    ``question_position`` identifies which planned evaluation question
    this attempt belongs to (multiple attempts share the same position
    until one is accepted or the unit is exhausted) - needed because a
    category may be evaluated with more than one question in the same
    generation mode, which category+mode alone cannot disambiguate.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    question_position: PositiveIntStrict
    category: NonBlankStr
    generation_mode: GenerationMode
    attempt_number: PositiveIntStrict
    accepted: StrictBool
    grounding_passed: StrictBool
    mcq_valid: StrictBool
    category_valid: StrictBool
    quality_valid: StrictBool
    textbook_status: TextbookCheckStatus
    # Populated only for accepted attempts, so a human reviewer (WP-017
    # section 19) has the actual content to judge - rejected attempts
    # never need their content inspected for this purpose. Never used by
    # any metric in metrics.py; purely for human review/reporting.
    question_text: NonBlankStr | None = None
    answers: tuple[NonBlankStr, ...] | None = None
    correct_answer: CorrectAnswerId | None = None


class OperationalFailureRecord(BaseModel):
    """One operational failure observed during evaluation for one planned
    (category, generation_mode) unit - distinct from a validator
    rejection, and from WP-013's own quality-attempt exhaustion."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    question_position: PositiveIntStrict
    category: NonBlankStr
    generation_mode: GenerationMode
    failure_type: NonBlankStr
    message: NonBlankStr


class CategoryEvaluationResult(BaseModel):
    """Per-category rollup for one evaluation run."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    category: NonBlankStr
    requested_questions: PositiveIntStrict
    produced_questions: NonNegativeIntStrict
    candidate_attempts: NonNegativeIntStrict
    accepted_candidates: NonNegativeIntStrict
    rejected_candidates: NonNegativeIntStrict
    exhausted_units: NonNegativeIntStrict
    operational_failures: NonNegativeIntStrict


class RetrievalEvalQuery(BaseModel):
    """One corpus-grounded retrieval-evaluation query (WP-017 section 12).

    ``expected_literal_term`` is checked for literal substring containment
    against the corpus *at evaluation time* - never a pre-computed/hardcoded
    chunk-id list - so the fixture can never silently go stale or claim
    relevance the corpus doesn't actually contain.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    query: NonBlankStr
    expected_literal_term: NonBlankStr
    category: NonBlankStr | None = None
    note: NonBlankStr | None = None


class RetrievalEvalResult(BaseModel):
    """Outcome of running one ``RetrievalEvalQuery`` against a retrieval
    index."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    query: NonBlankStr
    expected_literal_term: NonBlankStr
    category: NonBlankStr | None = None
    expected_chunk_ids: tuple[str, ...]
    retrieved_chunk_ids: tuple[str, ...]
    hit_at_3: StrictBool
    hit_at_5: StrictBool
    hit_at_8: StrictBool


class EvaluationConfig(BaseModel):
    """Reproducibility metadata for one evaluation run (WP-017 section 22).
    No secrets - provider/model identity only, never a key."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    provider: NonBlankStr
    model: NonBlankStr
    generation_temperature: float
    generation_max_tokens: PositiveIntStrict
    validation_temperature: float
    validation_max_tokens: PositiveIntStrict
    chunk_size: PositiveIntStrict
    chunk_overlap: NonNegativeIntStrict
    retrieval_top_k: PositiveIntStrict
    retrieval_ngram_min: PositiveIntStrict
    retrieval_ngram_max: PositiveIntStrict
    max_generation_attempts: PositiveIntStrict
    max_duplicate_replacement_attempts: PositiveIntStrict
    canonical_categories: tuple[str, ...]
    evaluated_categories: tuple[str, ...]
    questions_per_category_requested: PositiveIntStrict
    baseline_type: NonBlankStr
    prompt_versions: dict[str, str] = Field(default_factory=dict)


class EvaluationReport(BaseModel):
    """The complete structured output of one WP-017 evaluation run."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    config: EvaluationConfig
    generated_at: datetime
    candidate_attempts: tuple[CandidateAttemptRecord, ...] = Field(default_factory=tuple)
    operational_failures: tuple[OperationalFailureRecord, ...] = Field(default_factory=tuple)
    category_results: tuple[CategoryEvaluationResult, ...] = Field(default_factory=tuple)
    retrieval_results: tuple[RetrievalEvalResult, ...] = Field(default_factory=tuple)
