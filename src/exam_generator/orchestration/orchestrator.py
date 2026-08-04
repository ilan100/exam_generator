"""The WP-014 control layer: turns an ``ExamRequest`` into a complete
``ExamOutput`` by planning, then sequentially invoking, WP-013's existing
``QuestionProducer`` once per requested question.

    ExamRequest
         v
    resolve categories (WP-006 CategoryResolver, counts combined)
         v
    build deterministic plan (category, generation_mode, position)
         v
    for each planned question:
        QuestionProducer.produce_question(...)   (WP-013: generation + all
                                                    five validators + bounded
                                                    quality regeneration)
             v
        exact-duplicate check (bounded replacement if a duplicate)
         v
    candidate_to_exam_question() (WP-002/WP-009 deterministic conversion)
         v
    ExamOutput

This module owns planning, sequencing, and exam-level duplicate protection
only - it introduces no new generation, validation, or acceptance logic,
and never mutates a candidate, plan entry, or validator/production result.
"""

from __future__ import annotations

from exam_generator.config import load_app_config
from exam_generator.models import ExamOutput, ExamRequest, GenerationMode, candidate_to_exam_question
from exam_generator.orchestration.errors import InvalidOrchestrationConfigurationError, QuestionProductionFailedError
from exam_generator.orchestration.models import ExamGenerationResult, PlannedQuestion, QuestionProductionRecord
from exam_generator.production import QuestionAttemptsExhaustedError, QuestionProducer, QuestionProductionResult
from exam_generator.retrieval import CategoryResolver, build_category_resolver, resolve_exam_request_categories


def _validate_max_duplicate_replacement_attempts(value: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise InvalidOrchestrationConfigurationError(
            f"max_duplicate_replacement_attempts must be an integer >= 1, got {value!r}"
        )
    return value


def _normalize_question_text(text: str) -> str:
    """Deterministic exact-duplicate normalization (WP-014 section 12):
    collapse all whitespace runs (which also trims leading/trailing
    whitespace) and case-fold, so two questions differing only in
    whitespace or English/Latin letter case are still treated as the same
    question. Not semantic similarity - a genuinely different question
    that merely shares this normalized form is out of scope for WP-014."""
    return " ".join(text.split()).casefold()


def build_exam_plan(resolved_request: ExamRequest) -> tuple[PlannedQuestion, ...]:
    """Deterministically build the question-production plan for an
    already-canonicalized ``ExamRequest`` (see
    ``resolve_exam_request_categories`` - this function does not itself
    resolve aliases).

    Generation modes alternate *within each category*, starting at
    ``STYLE_SIMILAR`` for each category's first question - the master
    brief's established policy ("Questions alternate between two modes
    within each category"), applied independently per category rather
    than carried over globally. Position numbers are global, 1-based, and
    contiguous across the whole plan in request-dict iteration order,
    directly reusable as final ``ExamQuestion.number`` values. Identical
    input always produces an identical plan.
    """
    planned: list[PlannedQuestion] = []
    position = 1
    for category, count in resolved_request.categories.items():
        for index_in_category in range(count):
            mode = GenerationMode.STYLE_SIMILAR if index_in_category % 2 == 0 else GenerationMode.INDEPENDENT
            planned.append(PlannedQuestion(position=position, category=category, generation_mode=mode))
            position += 1
    return tuple(planned)


class ExamOrchestrator:
    """Application-facing entry point for one complete exam-generation run.

    Every dependency is injected explicitly - never hidden global state -
    so tests can supply fakes/mocks for the category resolver and the
    producer. Use ``ExamOrchestrator.from_default_configuration()`` for
    the normal application wiring against real project configuration/data.
    """

    def __init__(
        self,
        *,
        category_resolver: CategoryResolver,
        producer: QuestionProducer,
        max_duplicate_replacement_attempts: int,
    ) -> None:
        self._category_resolver = category_resolver
        self._producer = producer
        self._max_duplicate_replacement_attempts = _validate_max_duplicate_replacement_attempts(
            max_duplicate_replacement_attempts
        )

    @classmethod
    def from_default_configuration(cls) -> "ExamOrchestrator":
        """Construct the normal application wiring: the real category
        resolver, a real ``QuestionProducer`` (all five real validators),
        and ``config/app.yaml``'s ``generation.max_duplicate_replacement_attempts``
        as the duplicate-replacement bound - a new, small configuration
        value distinct from WP-013's own ``max_generation_attempts``.

        Requires ``OPENAI_API_KEY`` to be set (resolved by
        ``QuestionProducer.from_default_configuration()``).
        """
        return cls(
            category_resolver=build_category_resolver(),
            producer=QuestionProducer.from_default_configuration(),
            max_duplicate_replacement_attempts=load_app_config().generation.max_duplicate_replacement_attempts,
        )

    def _produce_unique_question(
        self,
        planned: PlannedQuestion,
        *,
        completed_productions: tuple[QuestionProductionRecord, ...],
        seen_normalized_questions: set[str],
    ) -> QuestionProductionRecord:
        """Produce one planned question, replacing (bounded) any result
        that exactly duplicates a question already accepted into this
        exam. Raises ``QuestionProductionFailedError`` - never silently
        continues with a partial exam - if WP-013 itself exhausts its
        attempts, or if every duplicate-replacement attempt is also a
        duplicate."""
        duplicate_productions: list[QuestionProductionResult] = []

        for _ in range(self._max_duplicate_replacement_attempts + 1):
            try:
                production = self._producer.produce_question(
                    category=planned.category, generation_mode=planned.generation_mode
                )
            except QuestionAttemptsExhaustedError as exc:
                raise QuestionProductionFailedError(
                    f"WP-013 exhausted its generation attempts for planned question at position "
                    f"{planned.position} (category={planned.category!r}, mode={planned.generation_mode.value})",
                    planned_question=planned,
                    completed_productions=completed_productions,
                    attempts_exhausted=exc.attempts,
                ) from exc

            normalized = _normalize_question_text(production.candidate.question)
            if normalized not in seen_normalized_questions:
                return QuestionProductionRecord(
                    planned=planned,
                    production=production,
                    duplicate_replacement_attempts=len(duplicate_productions),
                )

            duplicate_productions.append(production)

        raise QuestionProductionFailedError(
            f"Exhausted {self._max_duplicate_replacement_attempts} duplicate-replacement attempt(s) for "
            f"planned question at position {planned.position} (category={planned.category!r}, "
            f"mode={planned.generation_mode.value}) - every produced candidate duplicated a question "
            "already accepted into this exam",
            planned_question=planned,
            completed_productions=completed_productions,
            duplicate_productions=tuple(duplicate_productions),
        )

    def generate_exam(self, request: ExamRequest) -> ExamGenerationResult:
        """Generate a complete exam for ``request``.

        Resolves aliases to canonical categories and combines their
        requested counts (WP-006, never reimplemented here), builds a
        deterministic plan, then sequentially calls WP-013's
        ``QuestionProducer`` once per planned question - never
        reimplementing generation/validation/acceptance/regeneration.
        Only an accepted, non-duplicate candidate enters the exam. Any
        operational failure (from the producer, any validator, or the
        generator) propagates immediately; the entire exam is never
        silently returned incomplete. Never mutates ``request`` or any
        production/validation result.
        """
        resolved_request = resolve_exam_request_categories(request, self._category_resolver)
        plan = build_exam_plan(resolved_request)

        productions: list[QuestionProductionRecord] = []
        seen_normalized_questions: set[str] = set()

        for planned in plan:
            record = self._produce_unique_question(
                planned,
                completed_productions=tuple(productions),
                seen_normalized_questions=seen_normalized_questions,
            )
            productions.append(record)
            seen_normalized_questions.add(_normalize_question_text(record.production.candidate.question))

        exam_questions = [
            candidate_to_exam_question(record.production.candidate, record.planned.position)
            for record in productions
        ]
        exam = ExamOutput(questions=exam_questions)

        return ExamGenerationResult(exam=exam, plan=plan, productions=tuple(productions))
