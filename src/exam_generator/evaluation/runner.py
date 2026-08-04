"""WP-017 evaluation runners: exercise the existing, unmodified production
pipeline programmatically and record structured observations.

Introduces no new generation, validation, retrieval, or acceptance logic -
every runner here only *observes* outcomes already produced by
``QuestionProducer``/``FactualRetrievalIndex``. Operational failures are
caught and recorded (never silently rerun), so one failing planned item
never aborts the rest of the evaluation.
"""

from __future__ import annotations

from typing import Sequence

from pydantic import ValidationError

from exam_generator.chunking import FactualSourceCorpus
from exam_generator.evaluation.errors import UngroundedRetrievalQueryError
from exam_generator.evaluation.models import (
    CandidateAttemptRecord,
    OperationalFailureRecord,
    RetrievalEvalQuery,
    RetrievalEvalResult,
)
from exam_generator.generation import GenerationError
from exam_generator.llm import LLMError
from exam_generator.models import GenerationMode
from exam_generator.production import QuestionAttempt, QuestionAttemptsExhaustedError, QuestionProducer
from exam_generator.prompts import PromptError
from exam_generator.retrieval import FactualRetrievalIndex, RetrievalError
from exam_generator.validation import GroundingValidationError, TextbookValidationError

#: Every operational-failure type an evaluation run is expected to
#: encounter (WP-017 section 16). Anything not in this tuple is a
#: genuinely unexpected exception and is allowed to propagate rather than
#: being silently absorbed into an evaluation record.
#:
#: ``pydantic.ValidationError`` is included deliberately: a live baseline
#: run (2026-08-04) hit it directly - the OpenAI SDK's own structured-output
#: parser raises it when a model response fails schema validation before
#: any project-specific ``LLMError`` wrapping ever sees it (observed here:
#: an empty-string ``reason`` field, the same already-documented occasional
#: reliability quirk noted in WP-014's "Known Issues"). Without this, one
#: such response would silently abort the entire evaluation run instead of
#: being recorded as the operational failure it is - a narrow
#: instrumentation fix, not a production-code change (WP-017 section 3).
KNOWN_OPERATIONAL_ERROR_TYPES: tuple[type[Exception], ...] = (
    LLMError,
    GenerationError,
    GroundingValidationError,
    TextbookValidationError,
    RetrievalError,
    PromptError,
    ValidationError,
)

EvaluationPlanItem = tuple[str, GenerationMode, int]


def build_evaluation_plan(categories: Sequence[str], questions_per_category: int) -> tuple[EvaluationPlanItem, ...]:
    """(category, generation_mode, question_position) triples, alternating
    modes within each category starting at ``STYLE_SIMILAR`` - mirrors
    ``exam_generator.orchestration.build_exam_plan()``'s established policy
    (WP-014) exactly, reimplemented locally rather than imported so the
    evaluation layer stays a read-only observer with no dependency on
    production orchestration internals.
    """
    plan: list[EvaluationPlanItem] = []
    position = 1
    for category in categories:
        for index_in_category in range(questions_per_category):
            mode = GenerationMode.STYLE_SIMILAR if index_in_category % 2 == 0 else GenerationMode.INDEPENDENT
            plan.append((category, mode, position))
            position += 1
    return tuple(plan)


def _records_from_attempts(
    attempts: Sequence[QuestionAttempt], *, category: str, mode: GenerationMode, position: int
) -> list[CandidateAttemptRecord]:
    records = []
    for attempt in attempts:
        validations = attempt.validations
        records.append(
            CandidateAttemptRecord(
                question_position=position,
                category=category,
                generation_mode=mode,
                attempt_number=attempt.attempt_number,
                accepted=attempt.accepted,
                grounding_passed=validations.grounding.passed,
                mcq_valid=validations.mcq.valid,
                category_valid=validations.category.valid,
                quality_valid=validations.quality.valid,
                textbook_status=validations.textbook.status,
                question_text=attempt.candidate.question if attempt.accepted else None,
                answers=tuple(attempt.candidate.answers) if attempt.accepted else None,
                correct_answer=attempt.candidate.correct_answer if attempt.accepted else None,
            )
        )
    return records


class CandidateEvaluationRunner:
    """Runs an evaluation plan through an existing ``QuestionProducer``,
    recording every attempt (accepted or rejected) and every operational
    failure encountered. Never retries an operational failure."""

    def __init__(self, *, producer: QuestionProducer) -> None:
        self._producer = producer

    def run(
        self, plan: Sequence[EvaluationPlanItem]
    ) -> tuple[list[CandidateAttemptRecord], list[OperationalFailureRecord]]:
        attempt_records: list[CandidateAttemptRecord] = []
        operational_failures: list[OperationalFailureRecord] = []

        for category, mode, position in plan:
            try:
                result = self._producer.produce_question(category=category, generation_mode=mode)
            except QuestionAttemptsExhaustedError as exc:
                attempt_records.extend(
                    _records_from_attempts(exc.attempts, category=category, mode=mode, position=position)
                )
            except KNOWN_OPERATIONAL_ERROR_TYPES as exc:
                operational_failures.append(
                    OperationalFailureRecord(
                        question_position=position,
                        category=category,
                        generation_mode=mode,
                        failure_type=type(exc).__name__,
                        message=str(exc),
                    )
                )
            else:
                attempt_records.extend(
                    _records_from_attempts(result.attempts, category=category, mode=mode, position=position)
                )

        return attempt_records, operational_failures


class RetrievalEvaluationRunner:
    """Runs a corpus-grounded retrieval-evaluation fixture against an
    existing ``FactualRetrievalIndex``. Makes no LLM calls and modifies
    neither the index nor the corpus."""

    def __init__(self, *, index: FactualRetrievalIndex, corpus: FactualSourceCorpus) -> None:
        self._index = index
        self._corpus = corpus

    def run(self, queries: Sequence[RetrievalEvalQuery], *, top_k: int = 8) -> list[RetrievalEvalResult]:
        results = []
        for query in queries:
            expected_chunk_ids = tuple(
                chunk.chunk_id for chunk in self._corpus.all_chunks if query.expected_literal_term in chunk.text
            )
            if not expected_chunk_ids:
                raise UngroundedRetrievalQueryError(
                    f"Fixture query {query.query!r} expects the literal term "
                    f"{query.expected_literal_term!r}, which does not appear in any corpus chunk"
                )

            retrieved = self._index.search(query.query, top_k=top_k)
            retrieved_chunk_ids = tuple(result.chunk.chunk_id for result in retrieved)
            expected_set = set(expected_chunk_ids)

            results.append(
                RetrievalEvalResult(
                    query=query.query,
                    expected_literal_term=query.expected_literal_term,
                    category=query.category,
                    expected_chunk_ids=expected_chunk_ids,
                    retrieved_chunk_ids=retrieved_chunk_ids,
                    hit_at_3=bool(expected_set.intersection(retrieved_chunk_ids[:3])),
                    hit_at_5=bool(expected_set.intersection(retrieved_chunk_ids[:5])),
                    hit_at_8=bool(expected_set.intersection(retrieved_chunk_ids[:8])),
                )
            )
        return results
