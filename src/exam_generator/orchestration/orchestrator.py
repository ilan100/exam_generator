"""The WP-014 control layer, refactored by WP-032/WP-033 into a thin
client of ``CategoryQuestionSetService``: turns an ``ExamRequest`` into a
complete ``ExamOutput`` by planning, then sequentially invoking the
project's primary category-question-set generation API once per planned
question.

    ExamRequest
         v
    resolve categories (WP-006 CategoryResolver, counts combined)
         v
    build deterministic plan (category, generation_mode, position)
         v
    for each category:
        for each planned question in that category:
            CategoryQuestionSetService.generate_next(...)   (WP-033: target
                                                               planning,
                                                               production,
                                                               and duplicate
                                                               replacement -
                                                               all reused
                                                               unchanged)
         v
    candidate_to_exam_question() (WP-002/WP-009 deterministic conversion,
                                   assigning the real runtime number)
         v
    ExamOutput

Since WP-032, this module owns planning and sequencing only - no
generation, validation, target-planning, or duplicate-replacement logic
remains here; all of it lives in ``exam_generator.category_generation``.
It never mutates a candidate, plan entry, or validator/production result.
See ``docs/ARCHITECTURE.md`` ("V1 vs. V2 Generation Architecture" and its
WP-033 "Category Question Set" extension) for why the abstraction changed.
"""

from __future__ import annotations

from exam_generator.category_generation import (
    SYSTEM_LEVEL_ERROR_TYPES,
    CategoryQuestionSetRequest,
    CategoryQuestionSetService,
)
from exam_generator.models import (
    ExamGenerationStatus,
    ExamOutput,
    ExamRequest,
    GenerationMode,
    candidate_to_exam_question,
)
from exam_generator.orchestration.errors import QuestionProductionFailedError
from exam_generator.orchestration.models import (
    ExamGenerationResult,
    FailedPlannedQuestion,
    PlannedQuestion,
    QuestionProductionRecord,
)
from exam_generator.retrieval import CategoryResolver, build_category_resolver, resolve_exam_request_categories


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

    Since WP-032 (contract updated to WP-033's permanent
    ``CategoryQuestionSetService``), ``ExamOrchestrator`` is nothing more
    than: for each category, while that category still has planned
    questions remaining, call ``CategoryQuestionSetService.generate_next()``.
    Every dependency is injected explicitly - never hidden global state -
    so tests can supply fakes/mocks for the category resolver and the
    service. Use ``ExamOrchestrator.from_default_configuration()`` for the
    normal application wiring against real project configuration/data.

    WP-032's own ``CategoryGenerationService``/``CategoryGenerationRequest``/
    ``CategoryGenerationResponse`` remain fully present and functional
    elsewhere in ``exam_generator.category_generation`` (WP-033 section 7:
    "the previous request model should remain temporarily supported
    internally") - they are simply no longer what this class calls.
    """

    def __init__(
        self,
        *,
        category_resolver: CategoryResolver,
        category_question_set_service: CategoryQuestionSetService,
    ) -> None:
        self._category_resolver = category_resolver
        self._category_question_set_service = category_question_set_service

    @classmethod
    def from_default_configuration(cls) -> "ExamOrchestrator":
        """Construct the normal application wiring: the real category
        resolver and a real ``CategoryQuestionSetService`` (WP-033),
        itself wired against a real ``QuestionTargetPlanner`` (WP-025), a
        real ``QuestionProducer`` (WP-013), and
        ``config/app.yaml``'s ``generation.max_duplicate_replacement_attempts``.

        Requires ``OPENAI_API_KEY`` to be set (resolved deeper inside
        ``CategoryQuestionSetService.from_default_configuration()``).
        """
        return cls(
            category_resolver=build_category_resolver(),
            category_question_set_service=CategoryQuestionSetService.from_default_configuration(),
        )

    def generate_exam(self, request: ExamRequest) -> ExamGenerationResult:
        """Generate an exam for ``request``.

        Resolves aliases to canonical categories and combines their
        requested counts (WP-006, never reimplemented here), builds a
        deterministic plan, then - grouped by category, in plan order -
        calls ``CategoryQuestionSetService.generate_next()`` once per
        planned question in that category, passing every question already
        accepted for that category so far (as ``ExamQuestion``s,
        ``number=None`` until this method assigns the real exam-wide
        number below) as ``existing_questions``. Never reimplements
        generation/validation/target-planning/acceptance/duplicate-
        replacement - all of that lives in
        ``exam_generator.category_generation``. Only an accepted,
        non-duplicate candidate enters the exam.

        Since WP-023, a question-local failure (see
        ``exam_generator.category_generation.QUESTION_LOCAL_ERROR_TYPES``)
        no longer aborts the run: the service reports it as
        ``accepted=False`` rather than raising, it is recorded here as a
        ``FailedPlannedQuestion``, and the plan continues, yielding a
        ``PARTIAL`` result if the plan otherwise completes. A
        system-level failure (``SYSTEM_LEVEL_ERROR_TYPES``) still
        propagates immediately, wrapped here as
        ``QuestionProductionFailedError`` with this planned question's
        position/category/mode and how many questions were already
        completed - no result is returned at all in that case, and the
        original failure is preserved via exception chaining. A genuinely
        unexpected exception is left uncaught, propagating with its full
        traceback.

        Accepted questions are renumbered contiguously 1..N in plan order
        (never gap-preserving, since a failed planned position leaves no
        clean-exam slot to preserve); each accepted question's original
        planned position remains available via its
        ``QuestionProductionRecord.planned.position``, separate from its
        final exam number - this method remains the sole place a real
        ``number`` is ever assigned (WP-033 section 4: generation itself
        never assigns one). Never mutates ``request`` or any production/
        validation result.
        """
        resolved_request = resolve_exam_request_categories(request, self._category_resolver)
        plan = build_exam_plan(resolved_request)

        positions_by_category: dict[str, list[PlannedQuestion]] = {}
        for planned in plan:
            positions_by_category.setdefault(planned.category, []).append(planned)

        productions: list[QuestionProductionRecord] = []
        failed_questions: list[FailedPlannedQuestion] = []

        for category, planned_positions in positions_by_category.items():
            existing_questions_in_category: list = []
            for planned in planned_positions:
                service_request = CategoryQuestionSetRequest(
                    category=category,
                    generation_mode=planned.generation_mode,
                    existing_questions=tuple(existing_questions_in_category),
                )
                try:
                    response = self._category_question_set_service.generate_next(service_request)
                except SYSTEM_LEVEL_ERROR_TYPES as exc:
                    raise QuestionProductionFailedError(
                        f"Exam generation failed at question {planned.position}/{len(plan)} "
                        f"(category={planned.category!r}, generation_mode={planned.generation_mode.value}). "
                        f"Completed questions: {len(productions)}. "
                        f"Cause: {type(exc).__name__}: {exc}",
                        planned_question=planned,
                        completed_productions=tuple(productions),
                        operational_cause=exc,
                    ) from exc

                if not response.accepted:
                    failed_questions.append(
                        FailedPlannedQuestion(
                            planned=planned,
                            failure_type=response.failure_type,
                            failure_message=response.failure_message,
                            attempts=response.failure_attempts,
                            duplicate_productions=response.duplicate_productions,
                        )
                    )
                    continue

                productions.append(
                    QuestionProductionRecord(
                        planned=planned,
                        production=response.production,
                        duplicate_replacement_attempts=response.duplicate_replacement_attempts,
                    )
                )
                existing_questions_in_category.append(response.question)

        exam_questions = [
            candidate_to_exam_question(record.production.candidate, number)
            for number, record in enumerate(productions, start=1)
        ]
        exam = ExamOutput(questions=exam_questions) if exam_questions else None
        status = ExamGenerationStatus.PARTIAL if failed_questions else ExamGenerationStatus.COMPLETE

        return ExamGenerationResult(
            status=status,
            exam=exam,
            plan=plan,
            productions=tuple(productions),
            failed_questions=tuple(failed_questions),
        )
