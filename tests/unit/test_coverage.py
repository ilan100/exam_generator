import pytest
from pydantic import ValidationError

from exam_generator.generation import classify_relationship_type, extract_relationship
from exam_generator.models import CategoryCoverage, QuestionTarget
from exam_generator.planning import extract_category_coverage


# ---------------------------------------------------------------------------
# CategoryCoverage: internal-only model
# ---------------------------------------------------------------------------


def test_default_coverage_is_empty():
    coverage = CategoryCoverage()
    assert coverage.tested_concepts == ()
    assert coverage.tested_relationship_types == ()


def test_coverage_is_frozen_and_forbids_unknown_fields():
    coverage = CategoryCoverage()
    with pytest.raises(ValidationError):
        coverage.tested_concepts = ("x",)
    with pytest.raises(ValidationError):
        CategoryCoverage(unexpected="x")


# ---------------------------------------------------------------------------
# extract_category_coverage(): empty / 1 / 2 / 3 existing questions
# (WP-034 section 9)
# ---------------------------------------------------------------------------


def test_empty_existing_questions_yields_empty_coverage():
    coverage = extract_category_coverage(())
    assert coverage == CategoryCoverage()


def test_one_existing_question_yields_one_concept():
    coverage = extract_category_coverage([("איזה עורק מספק דם לצרבלום?", "Superior Cerebellar Artery")])
    assert coverage.tested_concepts == ("Superior Cerebellar Artery",)


def test_two_existing_questions_yield_two_concepts():
    coverage = extract_category_coverage(
        [
            ("שאלה 1", "תשובה 1"),
            ("שאלה 2", "תשובה 2"),
        ]
    )
    assert coverage.tested_concepts == ("תשובה 1", "תשובה 2")


def test_three_existing_questions_yield_three_concepts():
    coverage = extract_category_coverage(
        [
            ("שאלה 1", "תשובה 1"),
            ("שאלה 2", "תשובה 2"),
            ("שאלה 3", "תשובה 3"),
        ]
    )
    assert coverage.tested_concepts == ("תשובה 1", "תשובה 2", "תשובה 3")


# ---------------------------------------------------------------------------
# Deterministic extraction (WP-034 section 4/9)
# ---------------------------------------------------------------------------


def test_extraction_is_deterministic_for_identical_input():
    existing = [("איזה עורק מספק דם לצרבלום?", "Superior Cerebellar Artery")]
    assert extract_category_coverage(existing) == extract_category_coverage(existing)


def test_duplicate_concepts_are_deduplicated_preserving_first_occurrence_order():
    coverage = extract_category_coverage(
        [
            ("שאלה 1", "תשובה משותפת"),
            ("שאלה 2", "תשובה אחרת"),
            ("שאלה 3", "תשובה משותפת"),
        ]
    )
    assert coverage.tested_concepts == ("תשובה משותפת", "תשובה אחרת")


def test_blank_correct_answer_text_is_not_recorded_as_a_concept():
    coverage = extract_category_coverage([("שאלה", "   ")])
    assert coverage.tested_concepts == ()


# ---------------------------------------------------------------------------
# Relationship-type extraction reuses the WP-030 classifier unchanged
# ---------------------------------------------------------------------------


def test_relationship_type_is_classified_from_question_and_answer_text():
    coverage = extract_category_coverage([("איזה עורק מספק דם לצרבלום?", "Superior Cerebellar Artery")])
    assert coverage.tested_relationship_types == ("SUPPLIES",)


def test_unspecified_relationship_is_never_recorded():
    coverage = extract_category_coverage([("שאלה כללית ללא מילת מפתח", "תשובה")])
    assert coverage.tested_relationship_types == ()


def test_duplicate_relationship_types_are_deduplicated():
    coverage = extract_category_coverage(
        [
            ("איזה עורק מספק דם לצרבלום?", "Superior Cerebellar Artery"),
            ("איזה עורק מספק דם לגזע המוח?", "Basilar Artery"),
        ]
    )
    assert coverage.tested_relationship_types == ("SUPPLIES",)


def test_coverage_classifier_agrees_with_extract_relationship_for_the_same_text():
    # The same keyword-matching rules must produce the same classification
    # whether reached via extract_relationship() (a QuestionTarget) or via
    # extract_category_coverage() (free question/answer text) - one shared
    # implementation, never two copies of the keyword table.
    text = "מבנה זה מספק דם לאונה הטמפורלית"
    target = QuestionTarget(target_id=1, category="c", topic="t", factual_focus=text)
    assert extract_relationship(target).relationship_type == classify_relationship_type(text.lower())


def test_no_llm_or_embedding_call_in_coverage_extraction():
    import inspect

    import exam_generator.planning.coverage as coverage_module

    source = inspect.getsource(coverage_module)
    assert "generate_structured" not in source
    assert "vector" not in source.lower()
