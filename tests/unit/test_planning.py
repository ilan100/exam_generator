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


def _make_planner(
    *, resolver=None, index=None, prompt_repository=None, provider=None, pilot_categories=None
) -> QuestionTargetPlanner:
    kwargs = dict(
        category_resolver=resolver or _resolver(),
        student_summary_index=index
        if index is not None
        else _StubIndex((RetrievalResult(chunk=_chunk(), score=0.5, rank=1),)),
        prompt_repository=prompt_repository or PRODUCTION_PROMPT_REPOSITORY,
        llm_provider=provider or _provider(),
    )
    if pilot_categories is not None:
        kwargs["pilot_categories"] = pilot_categories
    return QuestionTargetPlanner(**kwargs)


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


# ---------------------------------------------------------------------------
# WP-034: coverage-aware planning
# ---------------------------------------------------------------------------


def test_plan_targets_without_coverage_still_works_unchanged():
    # Every pre-WP-034 caller (omitting coverage entirely) must behave
    # identically - default is an empty CategoryCoverage.
    planner = _make_planner()
    targets = planner.plan_targets(category=CATEGORY, count=1)
    assert len(targets) == 1


def test_coverage_is_rendered_into_the_planning_prompt():
    from exam_generator.models import CategoryCoverage

    distinctive_concept = "עורק בזילרי ייחודי לבדיקה"
    provider = _provider()
    planner = _make_planner(provider=provider)
    planner.plan_targets(
        category=CATEGORY, count=1, coverage=CategoryCoverage(tested_concepts=(distinctive_concept,))
    )
    sent_messages = provider.generate_structured.call_args.kwargs["messages"]
    user_message = next(m for m in sent_messages if m.role == MessageRole.USER)
    assert distinctive_concept in user_message.content


def test_no_coverage_renders_an_honest_nothing_tested_sentinel():
    provider = _provider()
    planner = _make_planner(provider=provider)
    planner.plan_targets(category=CATEGORY, count=1)
    sent_messages = provider.generate_structured.call_args.kwargs["messages"]
    user_message = next(m for m in sent_messages if m.role == MessageRole.USER)
    assert "No questions have been generated for this category yet" in user_message.content


def test_coverage_never_triggers_a_retry_or_second_llm_call():
    # WP-034 section 6: coverage does NOT become another validator - it
    # must never cause planning to retry or make more than one LLM call.
    from exam_generator.models import CategoryCoverage

    provider = _provider()
    planner = _make_planner(provider=provider)
    planner.plan_targets(
        category=CATEGORY, count=1, coverage=CategoryCoverage(tested_concepts=("כל דבר",))
    )
    assert provider.generate_structured.call_count == 1


# ---------------------------------------------------------------------------
# WP-036: concept-inventory-constrained planning for pilot categories only
# ---------------------------------------------------------------------------

PILOT_CATEGORY = "אספקת דם"


def _pilot_planner(*, provider=None, index=None, pilot_categories=None):
    resolver = _resolver(categories=(PILOT_CATEGORY,))
    chunk = _chunk(
        chunk_id="STUDENT_SUMMARY:s1.pdf:0128:0001",
        text="אספקת הדם:\nSuperior Cerebellar Artery\nמקור:\nBasilar Artery",
    )
    return _make_planner(
        resolver=resolver,
        index=index if index is not None else _StubIndex((RetrievalResult(chunk=chunk, score=0.5, rank=1),)),
        provider=provider,
        pilot_categories=pilot_categories,
    )


def test_pilot_category_makes_zero_llm_calls():
    provider = _provider()
    planner = _pilot_planner(provider=provider)
    planner.plan_targets(category=PILOT_CATEGORY, count=1)
    assert provider.generate_structured.call_count == 0


def test_pilot_category_returns_a_target_built_from_the_concept_inventory():
    planner = _pilot_planner()
    targets = planner.plan_targets(category=PILOT_CATEGORY, count=1)
    assert len(targets) == 1
    assert targets[0].topic == "Superior Cerebellar Artery"
    assert targets[0].category == PILOT_CATEGORY


def test_pilot_category_target_carries_genuine_evidence_chunk_id():
    planner = _pilot_planner()
    targets = planner.plan_targets(category=PILOT_CATEGORY, count=1)
    assert targets[0].supporting_evidence_chunk_ids == ("STUDENT_SUMMARY:s1.pdf:0128:0001",)


def test_pilot_category_respects_coverage_exclusion():
    from exam_generator.models import CategoryCoverage

    planner = _pilot_planner()
    coverage = CategoryCoverage(tested_concepts=("Superior Cerebellar Artery",))
    targets = planner.plan_targets(category=PILOT_CATEGORY, count=1, coverage=coverage)
    assert len(targets) == 1
    assert targets[0].topic == "Basilar Artery"


def test_pilot_category_exhaustion_yields_empty_list_not_llm_fallback():
    from exam_generator.models import CategoryCoverage

    provider = _provider()
    planner = _pilot_planner(provider=provider)
    coverage = CategoryCoverage(tested_concepts=("Superior Cerebellar Artery", "Basilar Artery"))
    targets = planner.plan_targets(category=PILOT_CATEGORY, count=1, coverage=coverage)
    assert targets == []
    # Exhaustion must never silently fall back to the LLM-based path -
    # WP-036 section 11: "report it honestly, do not invent concepts."
    assert provider.generate_structured.call_count == 0


def test_pilot_category_with_no_extractable_concepts_yields_empty_list():
    chunk = _chunk(text="זהו טקסט עברי בלבד ללא שום מבנה הניתן לחילוץ באנגלית.")
    planner = _pilot_planner(index=_StubIndex((RetrievalResult(chunk=chunk, score=0.5, rank=1),)))
    targets = planner.plan_targets(category=PILOT_CATEGORY, count=1)
    assert targets == []


def test_non_pilot_category_behavior_is_completely_unchanged():
    # CATEGORY ("גזע המוח") is deliberately not in the pilot set - every
    # pre-existing test in this file already exercises it through the
    # unchanged LLM path; this test makes that guarantee explicit.
    provider = _provider()
    planner = _make_planner(provider=provider)
    targets = planner.plan_targets(category=CATEGORY, count=1)
    assert provider.generate_structured.call_count == 1
    assert len(targets) == 1


def test_pilot_categories_constructor_default_is_the_real_wp036_set():
    from exam_generator.planning.concept_inventory import PILOT_CATEGORIES

    planner = _make_planner()
    assert planner._pilot_categories == PILOT_CATEGORIES


def test_injected_empty_pilot_set_disables_the_deterministic_path_entirely():
    # Confirms the pilot set is genuinely configurable, not hard-coded
    # deep inside plan_targets() - a category that IS one of the real
    # pilot categories still takes the LLM path if the injected pilot set
    # does not include it.
    provider = _provider()
    planner = _pilot_planner(provider=provider, pilot_categories=frozenset())
    planner.plan_targets(category=PILOT_CATEGORY, count=1)
    assert provider.generate_structured.call_count == 1


# ---------------------------------------------------------------------------
# WP-037: concept-anchored evidence for pilot-category targets
# ---------------------------------------------------------------------------


def test_pilot_category_target_uses_narrow_anchored_evidence_not_the_wide_window():
    # The exact WP-036 live-pilot failure this WP addresses: a competing,
    # more salient neighboring entity must not appear in the assigned
    # target's own factual_focus.
    chunk = _chunk(
        chunk_id="STUDENT_SUMMARY:s1.pdf:0128:0001",
        text="Superior Cerebellar Artery\nמקור:\nBasilar Artery\nאזור:\nהמשטח העליון",
    )
    planner = _pilot_planner(index=_StubIndex((RetrievalResult(chunk=chunk, score=0.5, rank=1),)))
    from exam_generator.models import CategoryCoverage

    coverage = CategoryCoverage(tested_concepts=("Superior Cerebellar Artery",))
    targets = planner.plan_targets(category=PILOT_CATEGORY, count=1, coverage=coverage)
    assert targets[0].topic == "Basilar Artery"
    assert "Superior Cerebellar Artery" not in targets[0].factual_focus


def test_pilot_category_excludes_a_category_self_restatement_concept():
    # WP-044 note: a distinguishing forward line is appended after
    # "Caudate Nucleus" (unrelated to what this WP-037 test itself
    # verifies - self-restatement exclusion) so this fixture's incidental
    # enumeration-intro shape ("...מכילים מספר תתי מבנים") does not also
    # trip WP-044 Part A's separate insufficient-enumeration-evidence
    # skip; without it, "Caudate Nucleus" would have no forward context
    # at all here (end of chunk), which is a real WP-044 concern
    # orthogonal to this test's own purpose.
    chunk = _chunk(
        chunk_id="STUDENT_SUMMARY:s1.pdf:0036:0001",
        text=(
            "גרעיני הבסיס נקראים גם\nThe Basal Ganglia\n"
            "אך מושג זה שגוי משום שגנגליה מתאר צבר גופי תאים במערכת העצבים ההיקפית\n"
            "גרעיני הבסיס מכילים מספר תתי מבנים\n\nCaudate Nucleus\n"
            "אחראי על תפקוד ייחודי ומובחן מבין תתי המבנים"
        ),
    )
    planner = _pilot_planner(index=_StubIndex((RetrievalResult(chunk=chunk, score=0.5, rank=1),)))
    targets = planner.plan_targets(category=PILOT_CATEGORY, count=1)
    assert targets[0].topic == "Caudate Nucleus"


# ---------------------------------------------------------------------------
# WP-038: deterministic concept identity for pilot-category coverage exclusion
# ---------------------------------------------------------------------------


def test_pilot_category_excludes_a_concept_via_its_evidence_derived_hebrew_form():
    # Evidence explicitly pairs the concept with a Hebrew form via an
    # adjacent parenthetical - WP-038's "evidence-derived identity"
    # mechanism must recognize the concept as tested when coverage's
    # tested_concepts carries that exact Hebrew form, even though it never
    # matches the concept's own (English) text.
    from exam_generator.models import CategoryCoverage

    chunk = _chunk(
        chunk_id="STUDENT_SUMMARY:s1.pdf:0128:0001",
        text=(
            "Superior Cerebellar Artery (עורק צרבלרי עליון)\n"
            "מקור:\nBasilar Artery"
        ),
    )
    planner = _pilot_planner(index=_StubIndex((RetrievalResult(chunk=chunk, score=0.5, rank=1),)))
    coverage = CategoryCoverage(tested_concepts=("עורק צרבלרי עליון",))
    targets = planner.plan_targets(category=PILOT_CATEGORY, count=1, coverage=coverage)
    assert targets[0].topic == "Basilar Artery"


def test_pilot_category_does_not_exclude_on_an_unsupported_alternate_representation():
    # The real, live-observed WP-037 regression, reproduced deterministically:
    # no evidence-derived pairing exists in this chunk (the exact real
    # corpus shape - see concept_identity's module docstring), so a
    # differently-scripted answer must honestly NOT be recognized as
    # covering the concept - WP-038 never guesses a match it cannot prove
    # from evidence.
    from exam_generator.models import CategoryCoverage

    chunk = _chunk(
        chunk_id="STUDENT_SUMMARY:s1.pdf:0128:0001",
        text="Superior Cerebellar Artery\nמקור:\nBasilar Artery",
    )
    planner = _pilot_planner(index=_StubIndex((RetrievalResult(chunk=chunk, score=0.5, rank=1),)))
    coverage = CategoryCoverage(tested_concepts=("עורק סופריור צרבלרי",))
    targets = planner.plan_targets(category=PILOT_CATEGORY, count=1, coverage=coverage)
    assert targets[0].topic == "Superior Cerebellar Artery"


def test_pilot_category_coverage_exclusion_is_still_case_and_whitespace_tolerant():
    from exam_generator.models import CategoryCoverage

    planner = _pilot_planner()
    coverage = CategoryCoverage(tested_concepts=("  superior   cerebellar ARTERY  ",))
    targets = planner.plan_targets(category=PILOT_CATEGORY, count=1, coverage=coverage)
    assert targets[0].topic == "Basilar Artery"


# ---------------------------------------------------------------------------
# WP-040: pilot-category targets are marked as named-entity targets
# ---------------------------------------------------------------------------


def test_pilot_category_target_is_marked_a_named_entity_target():
    planner = _pilot_planner()
    targets = planner.plan_targets(category=PILOT_CATEGORY, count=1)
    assert targets[0].named_entity_target is True


def test_non_pilot_category_target_is_not_marked_a_named_entity_target():
    planner = _make_planner()
    targets = planner.plan_targets(category=CATEGORY, count=1)
    assert targets[0].named_entity_target is False


# ---------------------------------------------------------------------------
# WP-043: evidence sufficiency fallback and target evidence-role detection
# ---------------------------------------------------------------------------


def test_pilot_category_target_marked_source_role_when_evidence_labels_it_so():
    # The default _pilot_planner() fixture chunk already contains the
    # real corpus's own "מקור:" (source:) label immediately before
    # "Basilar Artery" - the exact real shape WP-042 diagnosed.
    planner = _pilot_planner()
    targets = planner.plan_targets(category=PILOT_CATEGORY, count=2)
    by_topic = {t.topic: t for t in targets}
    assert by_topic["Basilar Artery"].is_source_role is True
    assert by_topic["Superior Cerebellar Artery"].is_source_role is False


def test_pilot_category_concept_with_insufficient_evidence_is_skipped_not_forced():
    # A concept whose only possible anchor is its own bare name (no
    # source_line_indices, no neighboring context in either direction,
    # immediately bounded by blank lines) must never become a target -
    # the planner should silently move to the next remaining concept.
    chunk = _chunk(
        chunk_id="STUDENT_SUMMARY:s1.pdf:0200:0001",
        text="Header Text\n\n\nIsolated Concept\n\n\nSuperior Cerebellar Artery\nמקור:\nBasilar Artery",
    )
    planner = _pilot_planner(index=_StubIndex((RetrievalResult(chunk=chunk, score=0.5, rank=1),)))
    targets = planner.plan_targets(category=PILOT_CATEGORY, count=10)
    topics = [t.topic for t in targets]
    assert "Isolated Concept" not in topics
    assert "Superior Cerebellar Artery" in topics
    assert all(t.factual_focus.strip() != t.topic.strip() for t in targets)


def test_pilot_category_all_concepts_insufficient_yields_empty_list_not_forced():
    chunk = _chunk(
        chunk_id="STUDENT_SUMMARY:s1.pdf:0201:0001",
        text="\n\nOnly Isolated Concept\n\n",
    )
    planner = _pilot_planner(index=_StubIndex((RetrievalResult(chunk=chunk, score=0.5, rank=1),)))
    targets = planner.plan_targets(category=PILOT_CATEGORY, count=1)
    assert targets == []


# ---------------------------------------------------------------------------
# WP-044: enumeration-shape skip and structural source-role entity
# ---------------------------------------------------------------------------


def test_pilot_category_target_carries_deterministic_downstream_entity():
    # The default _pilot_planner() fixture chunk already contains the
    # real corpus's own "מקור:" (source:) label immediately before
    # "Basilar Artery", preceded by "Superior Cerebellar Artery" - the
    # exact real shape WP-044 Part B extracts.
    planner = _pilot_planner()
    targets = planner.plan_targets(category=PILOT_CATEGORY, count=2)
    by_topic = {t.topic: t for t in targets}
    assert by_topic["Basilar Artery"].source_relationship_entity == "Superior Cerebellar Artery"
    assert by_topic["Superior Cerebellar Artery"].source_relationship_entity is None


def test_pilot_category_real_corpos_striatum_enumeration_shape_is_skipped():
    # WP-044 Part A: the exact real corpus shape (WP-043's own live pilot
    # finding) - the only anchorable evidence for "Corpos Striatum" is the
    # shared enumeration-intro sentence plus a bare bullet-marker fragment,
    # never anything member-specific. This must now be skipped entirely
    # rather than built into a target that could only produce a known-
    # ambiguous generic membership question.
    chunk = _chunk(
        chunk_id="STUDENT_SUMMARY:s1.pdf:0036:0001",
        text=(
            ", אך מושג זה שגוי משום שגנגליה מתאר צבר גופי תאים במערכת\n"
            ".העצבים ההיקפית, בעוד גרעיני הבסיס הם חלק ממערכת העצבים המרכזית \n"
            " גרעיני הבסיס:מכילים מספר תתי מבנים \n\ntum\nia\nCorpos Str\n \no\n\n"
            "Caudate Nucleus"
        ),
    )
    planner = _pilot_planner(index=_StubIndex((RetrievalResult(chunk=chunk, score=0.5, rank=1),)))
    targets = planner.plan_targets(category=PILOT_CATEGORY, count=10)
    topics = [t.topic for t in targets]
    assert "Corpos Striatum" not in topics
    assert "Caudate Nucleus" in topics


def test_pilot_category_enumeration_member_with_distinguishing_content_is_marked_and_kept():
    chunk = _chunk(
        chunk_id="STUDENT_SUMMARY:s1.pdf:0037:0001",
        text=(
            " גרעיני הבסיס:מכילים מספר תתי מבנים \n\n"
            "Caudate Nucleus\n"
            "אחראי על תפקוד ייחודי ומובחן מבין תתי המבנים"
        ),
    )
    planner = _pilot_planner(index=_StubIndex((RetrievalResult(chunk=chunk, score=0.5, rank=1),)))
    targets = planner.plan_targets(category=PILOT_CATEGORY, count=1)
    assert len(targets) == 1
    assert targets[0].topic == "Caudate Nucleus"
    assert targets[0].is_enumeration_member is True


def test_pilot_category_non_enumeration_target_is_not_marked_enumeration_member():
    planner = _pilot_planner()
    targets = planner.plan_targets(category=PILOT_CATEGORY, count=2)
    assert all(t.is_enumeration_member is False for t in targets)


# ---------------------------------------------------------------------------
# WP-063: first single-category post-WP-060 deterministic-planning pilot
# (המערכת הלימבית added to PILOT_CATEGORIES)
# ---------------------------------------------------------------------------

LIMBIC_CATEGORY = "המערכת הלימבית"


def _limbic_planner(*, provider=None, index=None, pilot_categories=None):
    # Fixture text mirrors the real corpus shape WP-063's own category
    # selection directly verified: a Hebrew descriptive sentence followed
    # by standalone-line English named entities.
    resolver = _resolver(categories=(LIMBIC_CATEGORY,))
    chunk = _chunk(
        chunk_id="STUDENT_SUMMARY:s1.pdf:0210:0001",
        text="המערכת הלימבית כוללת מבנים הקשורים לזיכרון:\nHippocampus\nמבנה הקשור לרגש:\nAmygdala\nמסילת חומר לבן:\nFornix",
    )
    return _make_planner(
        resolver=resolver,
        index=index if index is not None else _StubIndex((RetrievalResult(chunk=chunk, score=0.5, rank=1),)),
        provider=provider,
        pilot_categories=pilot_categories,
    )


def test_limbic_category_resolves_correctly():
    resolver = _resolver(categories=(LIMBIC_CATEGORY,))
    assert resolver.resolve(LIMBIC_CATEGORY) == LIMBIC_CATEGORY


def test_limbic_category_now_takes_the_deterministic_path_via_real_default_pilot_categories():
    # No pilot_categories override - exercises the real, production-default
    # PILOT_CATEGORIES (imported from planning.concept_inventory), proving
    # WP-063's production change actually routes המערכת הלימבית through
    # the zero-LLM-call deterministic path, not merely that the frozenset
    # contains its name.
    provider = _provider()
    planner = _limbic_planner(provider=provider)
    targets = planner.plan_targets(category=LIMBIC_CATEGORY, count=1)
    assert provider.generate_structured.call_count == 0
    assert len(targets) == 1
    assert targets[0].topic == "Hippocampus"
    assert targets[0].category == LIMBIC_CATEGORY


def test_limbic_target_carries_genuine_evidence_chunk_id_provenance():
    planner = _limbic_planner()
    targets = planner.plan_targets(category=LIMBIC_CATEGORY, count=1)
    assert targets[0].supporting_evidence_chunk_ids == ("STUDENT_SUMMARY:s1.pdf:0210:0001",)


def test_limbic_target_is_marked_a_named_entity_target():
    planner = _limbic_planner()
    targets = planner.plan_targets(category=LIMBIC_CATEGORY, count=1)
    assert targets[0].named_entity_target is True


def test_limbic_category_respects_coverage_exclusion():
    from exam_generator.models import CategoryCoverage

    planner = _limbic_planner()
    coverage = CategoryCoverage(tested_concepts=("Hippocampus",))
    targets = planner.plan_targets(category=LIMBIC_CATEGORY, count=1, coverage=coverage)
    assert len(targets) == 1
    assert targets[0].topic == "Amygdala"


def test_limbic_inventory_extraction_is_deterministic_and_reproducible():
    # Calling the real, unmodified refine_concept_inventory() twice against
    # identical evidence must yield an identical result - WP-063 section 28's
    # "inventory is deterministic/reproducible" requirement, verified
    # directly for the newly-selected category's own evidence shape rather
    # than merely relied upon by analogy with the pre-existing categories.
    from exam_generator.planning.concept_anchor import refine_concept_inventory

    chunk = _chunk(
        chunk_id="STUDENT_SUMMARY:s1.pdf:0210:0001",
        text="המערכת הלימבית כוללת מבנים הקשורים לזיכרון:\nHippocampus\nמבנה הקשור לרגש:\nAmygdala\nמסילת חומר לבן:\nFornix",
    )
    first = refine_concept_inventory((chunk,))
    second = refine_concept_inventory((chunk,))
    assert first == second
    assert [c.concept for c in first] == ["Hippocampus", "Amygdala", "Fornix"]


def test_existing_three_pilot_categories_still_take_the_deterministic_path_unchanged():
    # WP-063 section 31: adding a fourth category must not alter the
    # existing three's own behavior. Exercised the same way production
    # wiring would - no pilot_categories override.
    for category, chunk_text in (
        ("גרעיני הבסיס", "גרעיני הבסיס:\nCaudate Nucleus"),
        ("אספקת דם", "אספקת הדם:\nSuperior Cerebellar Artery"),
        ("מסילות עצביות", "מסילות עצביות:\nCorticospinal Tract"),
    ):
        provider = _provider()
        resolver = _resolver(categories=(category,))
        chunk = _chunk(chunk_id=f"STUDENT_SUMMARY:s1.pdf:0001:0001", text=chunk_text)
        planner = _make_planner(
            resolver=resolver,
            index=_StubIndex((RetrievalResult(chunk=chunk, score=0.5, rank=1),)),
            provider=provider,
        )
        targets = planner.plan_targets(category=category, count=1)
        assert provider.generate_structured.call_count == 0, category
        assert len(targets) == 1, category


def test_non_selected_category_still_uses_llm_planning_unchanged():
    # עצבים קרניאליים was directly evaluated and rejected during WP-063's
    # own category selection (implementation/WP-063_CATEGORY_SELECTION.md)
    # - it must remain on the unchanged LLM-based path, not be silently
    # swept into deterministic planning alongside the selected category.
    provider = _provider()
    resolver = _resolver(categories=("עצבים קרניאליים",))
    planner = _make_planner(resolver=resolver, provider=provider)
    targets = planner.plan_targets(category="עצבים קרניאליים", count=1)
    assert provider.generate_structured.call_count == 1
    assert len(targets) == 1


def test_pilot_categories_constructor_default_now_includes_the_limbic_category():
    from exam_generator.planning.concept_inventory import PILOT_CATEGORIES

    planner = _make_planner()
    assert planner._pilot_categories == PILOT_CATEGORIES
    assert LIMBIC_CATEGORY in planner._pilot_categories
