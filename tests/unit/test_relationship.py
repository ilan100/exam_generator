import pytest
from pydantic import ValidationError

from exam_generator.generation import UNSPECIFIED_RELATIONSHIP_TYPE, extract_relationship
from exam_generator.models import QuestionRelationship, QuestionTarget

CATEGORY = "אספקת דם"


def _target(**kwargs) -> QuestionTarget:
    defaults = dict(target_id=1, category=CATEGORY, topic="topic", factual_focus="factual focus")
    defaults.update(kwargs)
    return QuestionTarget(**defaults)


# ---------------------------------------------------------------------------
# Keyword classification - one representative case per relationship type
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("factual_focus", "expected_type"),
    [
        ("העורק הזה מספק דם לצרבלום", "SUPPLIES"),
        ("The vessel supplies blood to the region", "SUPPLIES"),
        ("העצב הזה מעצבב את השריר", "INNERVATES"),
        ("This nerve innervates the muscle", "INNERVATES"),
        ("סיבי אסוציאציה מחברים אזורים קורטיקליים", "CONNECTS"),
        ("These fibers connect two regions", "CONNECTS"),
        ("החומר הלבן כולל שלושה סוגי סיבים", "CONTAINS"),
        ("White matter consists of three fiber types", "CONTAINS"),
        ("המסילה מקרינה אל התלמוס", "PROJECTS_TO"),
        ("The tract projects to the thalamus", "PROJECTS_TO"),
        ("הגרעין ממוקם בתוך התלמוס", "LOCATED_IN"),
        ("The nucleus is located in the thalamus", "LOCATED_IN"),
        ("התלמוס מתפתח מהדיאנצפלון", "DEVELOPS_INTO"),
        ("The thalamus develops from the diencephalon", "DEVELOPS_INTO"),
        ("הגרעין מקבל קלט מהקורטקס", "RECEIVES_INPUT_FROM"),
        ("The nucleus receives input from the cortex", "RECEIVES_INPUT_FROM"),
        ("הסינוס מתנקז אל הוריד הצווארי", "DRAINS_INTO"),
        ("The sinus drains into the jugular vein", "DRAINS_INTO"),
        ("הקרום מקיף את המוח", "SURROUNDS"),
        ("The membrane surrounds the brain", "SURROUNDS"),
    ],
)
def test_extract_relationship_classifies_known_keywords(factual_focus, expected_type):
    target = _target(factual_focus=factual_focus)
    relationship = extract_relationship(target)
    assert relationship.relationship_type == expected_type


def test_extract_relationship_is_case_insensitive_for_english_keywords():
    target = _target(factual_focus="THE ARTERY SUPPLIES BLOOD TO THE REGION")
    relationship = extract_relationship(target)
    assert relationship.relationship_type == "SUPPLIES"


def test_extract_relationship_falls_back_to_unspecified():
    target = _target(factual_focus="עובדה כלשהי ללא מילת מפתח מוכרת כלל")
    relationship = extract_relationship(target)
    assert relationship.relationship_type == UNSPECIFIED_RELATIONSHIP_TYPE == "UNSPECIFIED"


# ---------------------------------------------------------------------------
# Determinism / purity
# ---------------------------------------------------------------------------


def test_extract_relationship_is_deterministic():
    target = _target(factual_focus="העורק מספק דם לצרבלום")
    first = extract_relationship(target)
    second = extract_relationship(target)
    assert first == second


def test_extract_relationship_does_not_mutate_target():
    target = _target(factual_focus="העורק מספק דם לצרבלום")
    before = target.model_dump()
    extract_relationship(target)
    assert target.model_dump() == before


def test_extract_relationship_statement_matches_factual_focus_exactly():
    target = _target(factual_focus="טקסט מדויק לבדיקה")
    relationship = extract_relationship(target)
    assert relationship.statement == target.factual_focus == "טקסט מדויק לבדיקה"


def test_extract_relationship_makes_no_llm_or_network_call():
    # Purely a signature/behavior check: extract_relationship takes only a
    # QuestionTarget - there is structurally nowhere for a provider or
    # prompt repository to be injected.
    import inspect

    params = inspect.signature(extract_relationship).parameters
    assert set(params) == {"target"}


# ---------------------------------------------------------------------------
# QuestionRelationship model
# ---------------------------------------------------------------------------


def test_question_relationship_is_immutable():
    relationship = QuestionRelationship(relationship_type="SUPPLIES", statement="x")
    with pytest.raises(ValidationError):
        relationship.relationship_type = "CONNECTS"


def test_question_relationship_forbids_unknown_fields():
    with pytest.raises(ValidationError):
        QuestionRelationship(relationship_type="SUPPLIES", statement="x", invented_field="not allowed")


def test_question_relationship_type_cannot_be_blank():
    with pytest.raises(ValidationError):
        QuestionRelationship(relationship_type="", statement="x")


def test_question_relationship_statement_cannot_be_blank():
    with pytest.raises(ValidationError):
        QuestionRelationship(relationship_type="SUPPLIES", statement="")


# ---------------------------------------------------------------------------
# QuestionTarget compatibility / backward compatibility
# ---------------------------------------------------------------------------


def test_question_target_gained_no_new_field():
    # WP-030 section 3: extend QuestionTarget only where necessary - it
    # turned out not to be necessary at all for WP-030 itself. The
    # relationship is computed transiently by generation, never stored on
    # the target. WP-040 later added named_entity_target, so this guard
    # now reflects that field set, not zero fields since WP-025.
    assert set(QuestionTarget.model_fields) == {
        "target_id",
        "category",
        "topic",
        "factual_focus",
        "supporting_evidence_chunk_ids",
        "named_entity_target",
    }


def test_existing_question_target_construction_still_works_unchanged():
    target = QuestionTarget(
        target_id=1,
        category=CATEGORY,
        topic="topic",
        factual_focus="factual focus",
        supporting_evidence_chunk_ids=["STUDENT_SUMMARY:s1.pdf:0001:0001"],
    )
    assert target.target_id == 1
    assert target.supporting_evidence_chunk_ids == ("STUDENT_SUMMARY:s1.pdf:0001:0001",)
