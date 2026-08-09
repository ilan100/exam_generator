"""Evidence-grounded question-target planning (WP-025).

Diversity between multiple questions requested from the same category is
achieved primarily BY CONSTRUCTION: before any question is generated, this
module identifies up to the requested number of distinct, evidence-
supported factual targets for a category, so each later
``QuestionGenerator`` call can be pointed at a specific, already-distinct
focus rather than generating arbitrary questions and relying on rejection
to enforce diversity after the fact.

Connects existing infrastructure only - no competing retrieval, prompt, or
LLM abstraction is introduced here:

    canonical category
           v
    student-summary retrieval          (exam_generator.retrieval, WP-006)
           v
    prompt construction                (exam_generator.prompts, WP-008)
           v
    structured LLM call                (exam_generator.llm, WP-007)
           v
    local evidence_refs -> canonical chunk ids   (WP-022/WP-024 pattern)
           v
    QuestionTarget(s)                  (exam_generator.models, WP-025)

This is planning only: it never generates a final question, validates a
candidate, decides acceptance, or performs orchestration/output - that
remains ``QuestionGenerator``/``QuestionProducer``/``ExamOrchestrator``.
"""

from __future__ import annotations

from exam_generator.config import load_llm_config
from exam_generator.generation import InvalidGeneratedOutputError, MissingEvidenceError
from exam_generator.llm import LLMProfile, LLMProvider, build_llm_provider
from exam_generator.models import (
    CategoryCoverage,
    PlannedQuestionTargetResponse,
    QuestionTarget,
    QuestionTargetPlanningResponse,
    SourceEvidenceChunk,
)
from exam_generator.prompts import PromptId, PromptRepository, QuestionTargetPlanningPromptContext, build_prompt_messages
from exam_generator.retrieval import (
    CategoryResolver,
    FactualRetrievalIndex,
    build_category_resolver,
    build_student_summary_retrieval_index,
    retrieve_for_category,
)


def _resolve_planned_targets(
    raw_targets: list[PlannedQuestionTargetResponse],
    *,
    category: str,
    source_evidence: tuple[SourceEvidenceChunk, ...],
) -> list[QuestionTarget]:
    """Strictly validate every raw target's call-local ``evidence_refs``
    (WP-025, mirroring WP-022/WP-024's proven local-reference pattern)
    against the evidence actually supplied to this planning call, then
    deterministically resolve them to genuine canonical
    ``SourceEvidenceChunk.chunk_id`` values.

    Fails closed on the *whole* response - a single invalid reference on
    any one target discards every target from this attempt, never
    partially repaired, exactly as WP-022/WP-024 never repair a
    partially-invalid response.
    """
    resolved: list[QuestionTarget] = []
    for target_id, raw in enumerate(raw_targets, start=1):
        invalid_refs = [ref for ref in raw.evidence_refs if not (1 <= ref <= len(source_evidence))]
        if invalid_refs:
            raise InvalidGeneratedOutputError(
                f"Planning response's target {target_id} claims evidence reference(s) outside "
                f"the supplied range 1..{len(source_evidence)}: {invalid_refs}"
            )
        deduplicated_refs = list(dict.fromkeys(raw.evidence_refs))
        chunk_ids = tuple(source_evidence[ref - 1].chunk_id for ref in deduplicated_refs)
        resolved.append(
            QuestionTarget(
                target_id=target_id,
                category=category,
                topic=raw.topic,
                factual_focus=raw.factual_focus,
                supporting_evidence_chunk_ids=chunk_ids,
            )
        )
    return resolved


class QuestionTargetPlanner:
    """Application-facing entry point for one category's target-planning
    call.

    Every dependency is injected explicitly - never hidden global state -
    so tests can supply fakes/mocks. Use
    ``QuestionTargetPlanner.from_default_configuration()`` for the normal
    application wiring against real project configuration/data.
    """

    def __init__(
        self,
        *,
        category_resolver: CategoryResolver,
        student_summary_index: FactualRetrievalIndex,
        prompt_repository: PromptRepository,
        llm_provider: LLMProvider,
    ) -> None:
        self._category_resolver = category_resolver
        self._student_summary_index = student_summary_index
        self._prompt_repository = prompt_repository
        self._llm_provider = llm_provider
        self._plan_history: list[tuple[str, tuple[QuestionTarget, ...]]] = []

    @classmethod
    def from_default_configuration(cls) -> "QuestionTargetPlanner":
        """Construct the normal application wiring: the real category
        resolver, the real student-summary retrieval index, the real
        production prompt repository, and the configured OpenAI provider.

        Requires ``OPENAI_API_KEY`` to be set (resolved by
        ``build_llm_provider`` at this point, not earlier).
        """
        return cls(
            category_resolver=build_category_resolver(),
            student_summary_index=build_student_summary_retrieval_index(),
            prompt_repository=PromptRepository.from_default_location(),
            llm_provider=build_llm_provider(load_llm_config()),
        )

    @property
    def plan_history(self) -> tuple[tuple[str, tuple[QuestionTarget, ...]], ...]:
        """Observability only (WP-025): every ``plan_targets()`` call's
        canonical category and resulting targets, in call order. Never
        used to make any application decision - mirrors WP-020/WP-021's
        existing retry-event observability pattern."""
        return tuple(self._plan_history)

    def plan_targets(
        self, *, category: str, count: int, coverage: CategoryCoverage | None = None
    ) -> list[QuestionTarget]:
        """Identify up to ``count`` distinct, evidence-supported question
        targets for ``category``.

        Makes exactly one LLM call (``LLMProfile.GENERATION``) - no retry
        loop of any kind (WP-025 section 10: diversity planning must not
        become a hidden retry loop, and must not consume WP-013's
        candidate-production attempt budget). May return fewer than
        ``count`` targets - never more - if the supplied evidence does not
        genuinely support that many distinct targets, or if the response
        claimed a local evidence reference never actually supplied (a
        stochastic per-call reliability issue that degrades to "zero
        usable targets from this attempt" rather than aborting the whole
        exam or being silently repaired). Never fabricates a target.

        Since WP-034, ``coverage`` (a deterministic summary of what the
        category's already-generated questions have already tested - see
        ``exam_generator.planning.coverage.extract_category_coverage()``)
        is threaded into the planning prompt as information, never a
        rejection mechanism: it may influence which target the LLM
        chooses, but a target overlapping with already-tested knowledge is
        never itself rejected or retried here - that would reintroduce the
        hidden retry loop WP-025 section 10 already forbids. Defaults to
        an empty ``CategoryCoverage()`` ("nothing tested yet") when omitted,
        so every pre-WP-034 caller continues to behave identically.

        Raises ``MissingEvidenceError`` (reused from
        ``exam_generator.generation`` - the identical condition, at the
        identical retrieval step, generation itself already treats as
        system-level) if no student-summary evidence can be retrieved for
        ``category`` at all - a genuine data-completeness problem,
        distinct from "evidence exists but doesn't support N distinct
        targets".
        """
        canonical_category = self._category_resolver.resolve(category)

        retrieval_results = retrieve_for_category(
            canonical_category, self._category_resolver, self._student_summary_index
        )
        source_evidence = tuple(result.chunk for result in retrieval_results)
        if not source_evidence:
            raise MissingEvidenceError(
                f"No student-summary evidence retrieved for category {canonical_category!r}"
            )

        context = QuestionTargetPlanningPromptContext(
            category=canonical_category,
            count=count,
            source_evidence=source_evidence,
            coverage=coverage if coverage is not None else CategoryCoverage(),
        )
        messages = build_prompt_messages(
            system_template=self._prompt_repository.get(PromptId.SYSTEM),
            task_template=self._prompt_repository.get(PromptId.QUESTION_TARGET_PLANNING),
            variables=context.render_variables(),
        )

        response = self._llm_provider.generate_structured(
            messages=messages,
            response_model=QuestionTargetPlanningResponse,
            profile=LLMProfile.GENERATION,
        )

        try:
            targets = _resolve_planned_targets(
                response.targets, category=canonical_category, source_evidence=source_evidence
            )
        except InvalidGeneratedOutputError:
            targets = []

        targets = targets[:count]
        self._plan_history.append((canonical_category, tuple(targets)))
        return targets
