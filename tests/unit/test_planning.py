from unittest.mock import MagicMock

import pytest
from pydantic import ValidationError

from exam_generator.generation import InvalidGeneratedOutputError, MissingEvidenceError
from exam_generator.llm import LLMProfile, LLMProvider, MessageRole
from exam_generator.models import (
    PlannedQuestionTargetResponse,
    QuestionTargetPlanningResponse,
    SourceEvidenceChunk,
    SourceType,
)
from exam_generator.planning import QuestionTargetPlanner
from exam_generator.planning.planner import _resolve_planned_targets
from exam_generator.prompts import PromptId, PromptRepository
from exam_generator.retrieval import CategoryResolver
from exam_generator.retrieval.models import RetrievalResult

CATEGORY = "גזע המוח"


# ---------------------------------------------------------------------------
# Fixture helpers
# ---------------------------------------------------------------------------


def _chunk(
    *,
    chunk_id="STUDENT_SUMMARY:s1.pdf:0001:0001",
    source_file="student_summary_1.pdf",
    page=1,
    text="טקסט ראיה לדוגמה",
) -> SourceEvidenceChunk:
    return SourceEvidenceChunk(
        chunk_id=chunk_id, source_file=source_file, page=page, text=text, source_type=SourceType.STUDENT_SUMMARY
    )


def _target_response(**kwargs) -> PlannedQuestionTargetResponse:
    defaults = dict(topic="topic", factual_focus="factual focus", evidence_refs=[])
    defaults.update(kwargs)
    return PlannedQuestionTargetResponse(**defaults)


def _planning_response(*targets: PlannedQuestionTargetResponse) -> QuestionTargetPlanningResponse:
    return QuestionTargetPlanningResponse(targets=list(targets))


class _StubIndex:
    """Minimal fake matching FactualRetrievalIndex.search()'s call shape,
    recording every query for assertions."""

    def __init__(self, results: tuple[RetrievalResult, ...] = ()) -> None:
        self.results = results
        self.calls: list[tuple[str, int | None]] = []

    def search(self, query: str, *, top_k: int | None = None) -> tuple[RetrievalResult, ...]:
        self.calls.append((query, top_k))
        return self.results


def _resolver(categories=(CATEGORY,), aliases=None) -> CategoryResolver:
    return CategoryResolver(categories, aliases or {})


def _provider(response: QuestionTargetPlanningResponse | None = None) -> MagicMock:
    provider = MagicMock(spec=LLMProvider)
    provider.generate_structured.return_value = response if response is not None else _planning_response(_target_response())
    return provider


PRODUCTION_PROMPT_REPOSITORY = PromptRepository.from_default_location()


def _make_planner(*, resolver=None, index=None, prompt_repository=None, provider=None) -> QuestionTargetPlanner:
    return QuestionTargetPlanner(
        category_resolver=resolver or _resolver(),
        student_summary_index=index
        if index is not None
        else _StubIndex((RetrievalResult(chunk=_chunk(), score=0.5, rank=1),)),
        prompt_repository=prompt_repository or PRODUCTION_PROMPT_REPOSITORY,
        llm_provider=provider or _provider(),
    )


# ---------------------------------------------------------------------------
# Basic planning
# ---------------------------------------------------------------------------


def test_count_1_returns_one_target():
    planner = _make_planner(provider=_provider(_planning_response(_target_response())))
    targets = planner.plan_targets(category=CATEGORY, count=1)
    assert len(targets) == 1


def test_count_2_returns_two_targets():
    response = _planning_response(_target_response(topic="t1"), _target_response(topic="t2"))
    planner = _make_planner(provider=_provider(response))
    targets = planner.plan_targets(category=CATEGORY, count=2)
    assert len(targets) == 2


def test_count_greater_than_two_supported_structurally():
    response = _planning_response(*[_target_response(topic=f"t{i}") for i in range(4)])
    planner = _make_planner(provider=_provider(response))
    targets = planner.plan_targets(category=CATEGORY, count=4)
    assert len(targets) == 4


def test_targets_preserve_canonical_category():
    planner = _make_planner()
    targets = planner.plan_targets(category=CATEGORY, count=1)
    assert targets[0].category == CATEGORY


def test_alias_resolves_to_canonical_category():
    resolver = _resolver(categories=(CATEGORY,), aliases={"alias": CATEGORY})
    planner = _make_planner(resolver=resolver)
    targets = planner.plan_targets(category="alias", count=1)
    assert targets[0].category == CATEGORY


def test_target_ids_are_1_based_sequential():
    response = _planning_response(_target_response(topic="t1"), _target_response(topic="t2"))
    planner = _make_planner(provider=_provider(response))
    targets = planner.plan_targets(category=CATEGORY, count=2)
    assert [t.target_id for t in targets] == [1, 2]


def test_planner_returns_exactly_requested_count_when_supported():
    response = _planning_response(
        _target_response(topic="t1"), _target_response(topic="t2"), _target_response(topic="t3")
    )
    planner = _make_planner(provider=_provider(response))
    # the model returned 3, but only 2 were requested - never more than requested.
    targets = planner.plan_targets(category=CATEGORY, count=2)
    assert len(targets) == 2


def test_model_returning_fewer_than_requested_is_an_honest_shortfall():
    response = _planning_response(_target_response(topic="t1"))
    planner = _make_planner(provider=_provider(response))
    targets = planner.plan_targets(category=CATEGORY, count=3)
    assert len(targets) == 1


def test_empty_targets_list_is_a_valid_response():
    planner = _make_planner(provider=_provider(_planning_response()))
    targets = planner.plan_targets(category=CATEGORY, count=2)
    assert targets == []


def test_missing_evidence_raises():
    planner = _make_planner(index=_StubIndex(()))
    with pytest.raises(MissingEvidenceError):
        planner.plan_targets(category=CATEGORY, count=1)


def test_missing_evidence_fails_before_any_llm_call():
    provider = _provider()
    planner = _make_planner(index=_StubIndex(()), provider=provider)
    with pytest.raises(MissingEvidenceError):
        planner.plan_targets(category=CATEGORY, count=1)
    provider.generate_structured.assert_not_called()


# ---------------------------------------------------------------------------
# LLM call shape
# ---------------------------------------------------------------------------


def test_llm_called_through_generation_profile():
    provider = _provider()
    planner = _make_planner(provider=provider)
    planner.plan_targets(category=CATEGORY, count=1)
    assert provider.generate_structured.call_args.kwargs["profile"] == LLMProfile.GENERATION


def test_llm_called_with_planning_response_model():
    provider = _provider()
    planner = _make_planner(provider=provider)
    planner.plan_targets(category=CATEGORY, count=1)
    assert provider.generate_structured.call_args.kwargs["response_model"] is QuestionTargetPlanningResponse


def test_no_retry_loop_exactly_one_llm_call():
    provider = _provider()
    planner = _make_planner(provider=provider)
    planner.plan_targets(category=CATEGORY, count=1)
    assert provider.generate_structured.call_count == 1


def test_evidence_and_count_rendered_in_prompt():
    distinctive_evidence = "טקסט ראיה ייחודי לבדיקה זו בלבד"
    chunk = _chunk(text=distinctive_evidence)
    index = _StubIndex((RetrievalResult(chunk=chunk, score=0.5, rank=1),))
    provider = _provider()
    planner = _make_planner(index=index, provider=provider)
    planner.plan_targets(category=CATEGORY, count=3)
    sent_messages = provider.generate_structured.call_args.kwargs["messages"]
    user_message = next(m for m in sent_messages if m.role == MessageRole.USER)
    assert distinctive_evidence in user_message.content
    assert "3" in user_message.content


# ---------------------------------------------------------------------------
# Local-reference resolution (WP-022/WP-024 pattern applied to planning)
# ---------------------------------------------------------------------------


def test_valid_evidence_ref_resolves_to_canonical_id():
    chunk = _chunk(chunk_id="STUDENT_SUMMARY:s1.pdf:0002:0001")
    index = _StubIndex((RetrievalResult(chunk=chunk, score=0.5, rank=1),))
    response = _planning_response(_target_response(evidence_refs=[1]))
    planner = _make_planner(index=index, provider=_provider(response))
    targets = planner.plan_targets(category=CATEGORY, count=1)
    assert targets[0].supporting_evidence_chunk_ids == ("STUDENT_SUMMARY:s1.pdf:0002:0001",)


def test_zero_evidence_ref_discards_the_whole_response():
    response = _planning_response(_target_response(evidence_refs=[0]))
    planner = _make_planner(provider=_provider(response))
    assert planner.plan_targets(category=CATEGORY, count=1) == []


def test_negative_evidence_ref_discards_the_whole_response():
    response = _planning_response(_target_response(evidence_refs=[-1]))
    planner = _make_planner(provider=_provider(response))
    assert planner.plan_targets(category=CATEGORY, count=1) == []


def test_out_of_range_evidence_ref_discards_the_whole_response():
    # the default fixture supplies exactly one chunk
    response = _planning_response(_target_response(evidence_refs=[2]))
    planner = _make_planner(provider=_provider(response))
    assert planner.plan_targets(category=CATEGORY, count=1) == []


def test_one_invalid_ref_discards_every_target_in_the_response():
    response = _planning_response(
        _target_response(topic="valid", evidence_refs=[1]),
        _target_response(topic="invalid", evidence_refs=[99]),
    )
    planner = _make_planner(provider=_provider(response))
    assert planner.plan_targets(category=CATEGORY, count=2) == []


def test_llm_cannot_inject_arbitrary_canonical_chunk_id():
    # the response model has no field capable of carrying a raw chunk-id
    # string at all - only an integer local reference.
    with pytest.raises(ValidationError):
        PlannedQuestionTargetResponse(
            topic="t", factual_focus="f", evidence_chunk_ids=["STUDENT_SUMMARY:fake.pdf:0000:0000"]
        )


# ---------------------------------------------------------------------------
# _resolve_planned_targets() - direct unit coverage
# ---------------------------------------------------------------------------


def test_resolve_planned_targets_preserves_supplied_ordering():
    chunks = (
        _chunk(chunk_id="STUDENT_SUMMARY:s1.pdf:0001:0001"),
        _chunk(chunk_id="STUDENT_SUMMARY:s1.pdf:0002:0001"),
    )
    resolved = _resolve_planned_targets([_target_response(evidence_refs=[2, 1])], category=CATEGORY, source_evidence=chunks)
    assert resolved[0].supporting_evidence_chunk_ids == (
        "STUDENT_SUMMARY:s1.pdf:0002:0001",
        "STUDENT_SUMMARY:s1.pdf:0001:0001",
    )


def test_resolve_planned_targets_deduplicates_preserving_first_occurrence():
    chunks = (_chunk(chunk_id="STUDENT_SUMMARY:s1.pdf:0001:0001"),)
    resolved = _resolve_planned_targets([_target_response(evidence_refs=[1, 1])], category=CATEGORY, source_evidence=chunks)
    assert resolved[0].supporting_evidence_chunk_ids == ("STUDENT_SUMMARY:s1.pdf:0001:0001",)


def test_resolve_planned_targets_rejects_invalid_ref():
    with pytest.raises(InvalidGeneratedOutputError):
        _resolve_planned_targets([_target_response(evidence_refs=[0])], category=CATEGORY, source_evidence=(_chunk(),))


def test_resolve_planned_targets_assigns_sequential_target_ids():
    chunks = (_chunk(),)
    resolved = _resolve_planned_targets(
        [_target_response(topic="a"), _target_response(topic="b")], category=CATEGORY, source_evidence=chunks
    )
    assert [t.target_id for t in resolved] == [1, 2]


# ---------------------------------------------------------------------------
# Observability
# ---------------------------------------------------------------------------


def test_plan_history_records_each_call():
    provider = _provider()
    planner = _make_planner(provider=provider)
    planner.plan_targets(category=CATEGORY, count=1)
    assert len(planner.plan_history) == 1
    recorded_category, recorded_targets = planner.plan_history[0]
    assert recorded_category == CATEGORY
    assert len(recorded_targets) == 1


def test_plan_history_empty_before_any_call():
    planner = _make_planner()
    assert planner.plan_history == ()


# ---------------------------------------------------------------------------
# Scope boundaries
# ---------------------------------------------------------------------------


def test_no_validation_prompts_requested():
    class _RecordingPromptRepository:
        def __init__(self, real_repository: PromptRepository) -> None:
            self._real = real_repository
            self.requested_ids: list[PromptId] = []

        def get(self, prompt_id: PromptId):
            self.requested_ids.append(prompt_id)
            return self._real.get(prompt_id)

    recording_repository = _RecordingPromptRepository(PRODUCTION_PROMPT_REPOSITORY)
    planner = _make_planner(prompt_repository=recording_repository)
    planner.plan_targets(category=CATEGORY, count=1)
    assert set(recording_repository.requested_ids) == {PromptId.SYSTEM, PromptId.QUESTION_TARGET_PLANNING}


def test_no_course_book_retrieval_dependency_exists():
    import inspect

    parameters = inspect.signature(QuestionTargetPlanner.__init__).parameters
    assert not any("course_book" in name for name in parameters)
