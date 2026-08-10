import pytest
from pydantic import ValidationError

from exam_generator.generation import UNSPECIFIED_RELATIONSHIP_TYPE, discover_competitors
from exam_generator.models import CompetitorCandidate, QuestionRelationship, QuestionTarget, SourceEvidenceChunk, SourceType

CATEGORY = "אספקת דם"


def _target(**kwargs) -> QuestionTarget:
    defaults = dict(
        target_id=1,
        category=CATEGORY,
        topic="topic",
        factual_focus="עורק זה מספק דם לצרבלום",
        supporting_evidence_chunk_ids=["STUDENT_SUMMARY:s1.pdf:0001:0001"],
    )
    defaults.update(kwargs)
    return QuestionTarget(**defaults)


def _relationship(**kwargs) -> QuestionRelationship:
    defaults = dict(relationship_type="SUPPLIES", statement="עורק זה מספק דם לצרבלום")
    defaults.update(kwargs)
    return QuestionRelationship(**defaults)


def _chunk(*, chunk_id, text) -> SourceEvidenceChunk:
    return SourceEvidenceChunk(
        chunk_id=chunk_id, source_file="s1.pdf", page=1, text=text, source_type=SourceType.STUDENT_SUMMARY
    )


# ---------------------------------------------------------------------------
# Deterministic discovery
# ---------------------------------------------------------------------------


def test_discovers_competitor_sharing_the_same_relationship_keyword():
    target = _target()
    relationship = _relationship()
    other_chunk = _chunk(chunk_id="STUDENT_SUMMARY:s1.pdf:0002:0001", text="עורק אחר מספק דם לחוט השדרה")
    own_chunk = _chunk(chunk_id="STUDENT_SUMMARY:s1.pdf:0001:0001", text="עורק זה מספק דם לצרבלום")
    competitors = discover_competitors(target=target, relationship=relationship, source_evidence=(own_chunk, other_chunk))
    assert len(competitors) == 1
    assert competitors[0].source_evidence_chunk_id == "STUDENT_SUMMARY:s1.pdf:0002:0001"
    assert "מספק" in competitors[0].concept
    assert competitors[0].relationship_relevance == "SUPPLIES"


def test_target_own_supporting_evidence_is_never_a_competitor_of_itself():
    target = _target(supporting_evidence_chunk_ids=["STUDENT_SUMMARY:s1.pdf:0001:0001"])
    relationship = _relationship()
    own_chunk = _chunk(chunk_id="STUDENT_SUMMARY:s1.pdf:0001:0001", text="עורק זה מספק דם לצרבלום")
    competitors = discover_competitors(target=target, relationship=relationship, source_evidence=(own_chunk,))
    assert competitors == ()


def test_unrelated_evidence_is_not_a_competitor():
    target = _target()
    relationship = _relationship()
    unrelated = _chunk(chunk_id="STUDENT_SUMMARY:s1.pdf:0003:0001", text="עובדה כלשהי שאינה קשורה בכלל לנושא")
    competitors = discover_competitors(target=target, relationship=relationship, source_evidence=(unrelated,))
    assert competitors == ()


def test_unspecified_relationship_yields_no_competitors():
    target = _target(factual_focus="עובדה כלשהי ללא מילת מפתח מוכרת")
    relationship = QuestionRelationship(relationship_type=UNSPECIFIED_RELATIONSHIP_TYPE, statement=target.factual_focus)
    other_chunk = _chunk(chunk_id="STUDENT_SUMMARY:s1.pdf:0002:0001", text="עורק אחר מספק דם לחוט השדרה")
    competitors = discover_competitors(target=target, relationship=relationship, source_evidence=(other_chunk,))
    assert competitors == ()


def test_empty_evidence_yields_no_competitors():
    target = _target()
    relationship = _relationship()
    competitors = discover_competitors(target=target, relationship=relationship, source_evidence=())
    assert competitors == ()


# ---------------------------------------------------------------------------
# Ranking stability / determinism
# ---------------------------------------------------------------------------


def test_ranking_preserves_source_evidence_order():
    # WP-031 section 5: ranking reuses the already-computed retrieval-rank
    # order of source_evidence - no new ranking logic.
    target = _target()
    relationship = _relationship()
    first = _chunk(chunk_id="STUDENT_SUMMARY:s1.pdf:0002:0001", text="עורק א' מספק דם לאזור 1")
    second = _chunk(chunk_id="STUDENT_SUMMARY:s1.pdf:0003:0001", text="עורק ב' מספק דם לאזור 2")
    competitors = discover_competitors(target=target, relationship=relationship, source_evidence=(first, second))
    assert [c.source_evidence_chunk_id for c in competitors] == [
        "STUDENT_SUMMARY:s1.pdf:0002:0001",
        "STUDENT_SUMMARY:s1.pdf:0003:0001",
    ]

    # Reversed input order -> reversed output order (pure pass-through, not re-sorted).
    competitors_reversed = discover_competitors(target=target, relationship=relationship, source_evidence=(second, first))
    assert [c.source_evidence_chunk_id for c in competitors_reversed] == [
        "STUDENT_SUMMARY:s1.pdf:0003:0001",
        "STUDENT_SUMMARY:s1.pdf:0002:0001",
    ]


def test_discovery_is_deterministic():
    target = _target()
    relationship = _relationship()
    other_chunk = _chunk(chunk_id="STUDENT_SUMMARY:s1.pdf:0002:0001", text="עורק אחר מספק דם לחוט השדרה")
    first = discover_competitors(target=target, relationship=relationship, source_evidence=(other_chunk,))
    second = discover_competitors(target=target, relationship=relationship, source_evidence=(other_chunk,))
    assert first == second


def test_discovery_does_not_mutate_inputs():
    target = _target()
    relationship = _relationship()
    other_chunk = _chunk(chunk_id="STUDENT_SUMMARY:s1.pdf:0002:0001", text="עורק אחר מספק דם לחוט השדרה")
    target_before = target.model_dump()
    chunk_before = other_chunk.model_dump()
    discover_competitors(target=target, relationship=relationship, source_evidence=(other_chunk,))
    assert target.model_dump() == target_before
    assert other_chunk.model_dump() == chunk_before


def test_discovery_makes_no_llm_or_retrieval_call():
    import inspect

    params = inspect.signature(discover_competitors).parameters
    assert set(params) == {"target", "relationship", "source_evidence"}


# ---------------------------------------------------------------------------
# CompetitorCandidate model
# ---------------------------------------------------------------------------


def test_competitor_candidate_is_immutable():
    candidate = CompetitorCandidate(
        concept="x", source_evidence_chunk_id="STUDENT_SUMMARY:s1.pdf:0001:0001", relationship_relevance="SUPPLIES", similarity_reason="y"
    )
    with pytest.raises(ValidationError):
        candidate.concept = "z"


def test_competitor_candidate_forbids_unknown_fields():
    with pytest.raises(ValidationError):
        CompetitorCandidate(
            concept="x",
            source_evidence_chunk_id="STUDENT_SUMMARY:s1.pdf:0001:0001",
            relationship_relevance="SUPPLIES",
            similarity_reason="y",
            distractor_text="not allowed",
        )


def test_competitor_candidate_concept_cannot_be_blank():
    with pytest.raises(ValidationError):
        CompetitorCandidate(
            concept="", source_evidence_chunk_id="STUDENT_SUMMARY:s1.pdf:0001:0001", relationship_relevance="SUPPLIES", similarity_reason="y"
        )


# ---------------------------------------------------------------------------
# Backward compatibility
# ---------------------------------------------------------------------------


def test_question_target_still_gained_no_new_field():
    # WP-031 itself added no field - WP-040 later added named_entity_target,
    # so this guard now reflects that field set, not zero fields since WP-025.
    assert set(QuestionTarget.model_fields) == {
        "target_id",
        "category",
        "topic",
        "factual_focus",
        "supporting_evidence_chunk_ids",
        "named_entity_target",
    }


def test_question_relationship_still_unchanged():
    assert set(QuestionRelationship.model_fields) == {"relationship_type", "statement"}
