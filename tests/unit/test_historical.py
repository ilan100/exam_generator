from pathlib import Path

import openpyxl
import pytest

from exam_generator.historical import HistoricalQuestionRepository
from exam_generator.historical.errors import (
    HistoricalQuestionRowError,
    WorkbookFormatError,
    WorkbookNotFoundError,
    WorkbookSchemaError,
)
from exam_generator.models import HistoricalStyleReference, SourceEvidenceChunk

FULL_HEADERS = [
    "id",
    "category",
    "categories_json",
    "question",
    "answer1",
    "answer2",
    "answer3",
    "answer4",
    "correct_answer_id",
    "accuracy_values",
    "distinction_values",
    "source",
    "uploaded_at",
    "created_at",
    "updated_at",
]

REQUIRED_HEADERS = [
    "id",
    "category",
    "question",
    "answer1",
    "answer2",
    "answer3",
    "answer4",
    "correct_answer_id",
]

HEBREW_QUESTION = "איזה מבנה קשור ל-Corona radiata בדוגמה זו?"
HEBREW_ANSWERS = ["חומר לבן", "חומר אפור", "קליפת המוח", "גזע המוח"]


def _row(id_=1, category="גזע המוח", question=HEBREW_QUESTION, answers=None, correct=1):
    answers = answers if answers is not None else HEBREW_ANSWERS
    return [id_, category, question, *answers, correct]


def make_workbook(
    tmp_path: Path,
    rows: list,
    headers: list[str] | None = None,
    filename: str = "workbook.xlsx",
    sheet_names: list[str] | None = None,
) -> Path:
    """Build a small synthetic .xlsx fixture and return its path."""
    headers = headers if headers is not None else REQUIRED_HEADERS
    workbook = openpyxl.Workbook()
    sheet = workbook.active
    if sheet_names:
        sheet.title = sheet_names[0]
        for name in sheet_names[1:]:
            workbook.create_sheet(name)
    sheet.append(headers)
    for row in rows:
        sheet.append(row)
    path = tmp_path / filename
    workbook.save(path)
    return path


# ---------------------------------------------------------------------------
# Valid workbook
# ---------------------------------------------------------------------------


def test_valid_workbook_loads(tmp_path):
    path = make_workbook(tmp_path, [_row(1), _row(2, category="חומר לבן")])
    repo = HistoricalQuestionRepository.from_workbook(path)
    assert repo.total_questions == 2


def test_required_columns_may_appear_in_different_order(tmp_path):
    shuffled = list(reversed(REQUIRED_HEADERS))
    row = [None] * len(shuffled)
    values = {"id": 1, "category": "גזע המוח", "question": HEBREW_QUESTION,
              "answer1": HEBREW_ANSWERS[0], "answer2": HEBREW_ANSWERS[1],
              "answer3": HEBREW_ANSWERS[2], "answer4": HEBREW_ANSWERS[3],
              "correct_answer_id": 2}
    for i, name in enumerate(shuffled):
        row[i] = values[name]
    path = make_workbook(tmp_path, [row], headers=shuffled)
    repo = HistoricalQuestionRepository.from_workbook(path)
    question = repo.all_questions[0]
    assert question.correct_answer == 2
    assert question.category == "גזע המוח"


def test_extra_columns_are_ignored(tmp_path):
    row = [1, "גזע המוח", "{}", HEBREW_QUESTION, *HEBREW_ANSWERS, 1, "0.5", "0.1", "manual", "t", "t", "t"]
    path = make_workbook(tmp_path, [row], headers=FULL_HEADERS)
    repo = HistoricalQuestionRepository.from_workbook(path)
    assert repo.total_questions == 1


def test_blank_rows_are_skipped(tmp_path):
    blank = [None] * len(REQUIRED_HEADERS)
    path = make_workbook(tmp_path, [_row(1), blank, _row(2)])
    repo = HistoricalQuestionRepository.from_workbook(path)
    assert repo.total_questions == 2


def test_valid_rows_preserve_workbook_order(tmp_path):
    path = make_workbook(tmp_path, [_row(5), _row(3), _row(9)])
    repo = HistoricalQuestionRepository.from_workbook(path)
    assert [q.historical_question_id for q in repo.all_questions] == [5, 3, 9]


def test_answer_order_is_preserved(tmp_path):
    path = make_workbook(tmp_path, [_row(1, answers=["a1", "a2", "a3", "a4"])])
    repo = HistoricalQuestionRepository.from_workbook(path)
    assert repo.all_questions[0].answers == ["a1", "a2", "a3", "a4"]


def test_hebrew_text_is_preserved(tmp_path):
    path = make_workbook(tmp_path, [_row(1)])
    repo = HistoricalQuestionRepository.from_workbook(path)
    assert repo.all_questions[0].question == HEBREW_QUESTION


def test_embedded_english_terminology_is_preserved(tmp_path):
    path = make_workbook(tmp_path, [_row(1, answers=["Anterior limb", "Posterior limb", "a3", "a4"])])
    repo = HistoricalQuestionRepository.from_workbook(path)
    assert "Anterior limb" in repo.all_questions[0].answers


def test_canonical_categories_derived_correctly(tmp_path):
    path = make_workbook(tmp_path, [_row(1, category="A"), _row(2, category="B")])
    repo = HistoricalQuestionRepository.from_workbook(path)
    assert set(repo.canonical_categories) == {"A", "B"}


def test_category_ordering_is_deterministic_first_seen(tmp_path):
    path = make_workbook(tmp_path, [_row(1, category="B"), _row(2, category="A"), _row(3, category="B")])
    repo = HistoricalQuestionRepository.from_workbook(path)
    assert repo.canonical_categories == ("B", "A")


def test_duplicate_category_names_collapse(tmp_path):
    path = make_workbook(tmp_path, [_row(1, category="A"), _row(2, category="A")])
    repo = HistoricalQuestionRepository.from_workbook(path)
    assert repo.canonical_categories == ("A",)


def test_questions_for_category_returns_only_matching(tmp_path):
    path = make_workbook(tmp_path, [_row(1, category="A"), _row(2, category="B")])
    repo = HistoricalQuestionRepository.from_workbook(path)
    matched = repo.questions_for_category("A")
    assert [q.historical_question_id for q in matched] == [1]


def test_question_order_within_category_preserved(tmp_path):
    path = make_workbook(tmp_path, [_row(1, category="A"), _row(2, category="B"), _row(3, category="A")])
    repo = HistoricalQuestionRepository.from_workbook(path)
    assert [q.historical_question_id for q in repo.questions_for_category("A")] == [1, 3]


def test_unknown_category_returns_empty_tuple(tmp_path):
    path = make_workbook(tmp_path, [_row(1, category="A")])
    repo = HistoricalQuestionRepository.from_workbook(path)
    assert repo.questions_for_category("does-not-exist") == ()


def test_total_question_count_correct(tmp_path):
    path = make_workbook(tmp_path, [_row(1), _row(2), _row(3)])
    repo = HistoricalQuestionRepository.from_workbook(path)
    assert repo.total_questions == 3


def test_category_count_correct(tmp_path):
    path = make_workbook(tmp_path, [_row(1, category="A"), _row(2, category="B"), _row(3, category="A")])
    repo = HistoricalQuestionRepository.from_workbook(path)
    assert repo.category_count == 2


def test_per_category_counts_correct(tmp_path):
    path = make_workbook(tmp_path, [_row(1, category="A"), _row(2, category="B"), _row(3, category="A")])
    repo = HistoricalQuestionRepository.from_workbook(path)
    assert repo.counts_per_category["A"] == 2
    assert repo.counts_per_category["B"] == 1


# ---------------------------------------------------------------------------
# Header / workbook failures
# ---------------------------------------------------------------------------


def test_missing_workbook_path_fails_clearly(tmp_path):
    with pytest.raises(WorkbookNotFoundError):
        HistoricalQuestionRepository.from_workbook(tmp_path / "does_not_exist.xlsx")


def test_directory_instead_of_file_fails_clearly(tmp_path):
    with pytest.raises(WorkbookNotFoundError):
        HistoricalQuestionRepository.from_workbook(tmp_path)


def test_invalid_corrupt_workbook_fails_clearly(tmp_path):
    bad = tmp_path / "corrupt.xlsx"
    bad.write_text("this is not a real xlsx file", encoding="utf-8")
    with pytest.raises(WorkbookFormatError):
        HistoricalQuestionRepository.from_workbook(bad)


@pytest.mark.parametrize("missing", ["id", "category", "question", "answer1", "correct_answer_id"])
def test_missing_required_header_rejected(tmp_path, missing):
    headers = [h for h in REQUIRED_HEADERS if h != missing]
    row = [v for h, v in zip(REQUIRED_HEADERS, _row(1)) if h != missing]
    path = make_workbook(tmp_path, [row], headers=headers)
    with pytest.raises(WorkbookSchemaError):
        HistoricalQuestionRepository.from_workbook(path)


def test_column_order_does_not_matter(tmp_path):
    headers = REQUIRED_HEADERS[::-1]
    values = dict(zip(REQUIRED_HEADERS, _row(1)))
    row = [values[h] for h in headers]
    path = make_workbook(tmp_path, [row], headers=headers)
    repo = HistoricalQuestionRepository.from_workbook(path)
    assert repo.total_questions == 1


def test_extra_columns_do_not_fail(tmp_path):
    headers = REQUIRED_HEADERS + ["notes"]
    row = _row(1) + ["some note"]
    path = make_workbook(tmp_path, [row], headers=headers)
    repo = HistoricalQuestionRepository.from_workbook(path)
    assert repo.total_questions == 1


def test_duplicate_required_header_rejected(tmp_path):
    headers = REQUIRED_HEADERS + ["id"]
    row = _row(1) + [999]
    path = make_workbook(tmp_path, [row], headers=headers)
    with pytest.raises(WorkbookSchemaError):
        HistoricalQuestionRepository.from_workbook(path)


def test_headers_only_workbook_rejected(tmp_path):
    path = make_workbook(tmp_path, [])
    with pytest.raises(WorkbookSchemaError):
        HistoricalQuestionRepository.from_workbook(path)


def test_headers_plus_blank_rows_only_rejected(tmp_path):
    blank = [None] * len(REQUIRED_HEADERS)
    path = make_workbook(tmp_path, [blank, blank])
    with pytest.raises(WorkbookSchemaError):
        HistoricalQuestionRepository.from_workbook(path)


# ---------------------------------------------------------------------------
# Row validation
# ---------------------------------------------------------------------------


def test_duplicate_historical_id_rejected(tmp_path):
    path = make_workbook(tmp_path, [_row(1), _row(1)])
    with pytest.raises(HistoricalQuestionRowError):
        HistoricalQuestionRepository.from_workbook(path)


def test_missing_id_rejected(tmp_path):
    path = make_workbook(tmp_path, [_row(None)])
    with pytest.raises(HistoricalQuestionRowError):
        HistoricalQuestionRepository.from_workbook(path)


def test_zero_id_rejected(tmp_path):
    path = make_workbook(tmp_path, [_row(0)])
    with pytest.raises(HistoricalQuestionRowError):
        HistoricalQuestionRepository.from_workbook(path)


def test_negative_id_rejected(tmp_path):
    path = make_workbook(tmp_path, [_row(-1)])
    with pytest.raises(HistoricalQuestionRowError):
        HistoricalQuestionRepository.from_workbook(path)


def test_fractional_numeric_id_rejected(tmp_path):
    path = make_workbook(tmp_path, [_row(1.5)])
    with pytest.raises(HistoricalQuestionRowError):
        HistoricalQuestionRepository.from_workbook(path)


def test_blank_category_rejected(tmp_path):
    path = make_workbook(tmp_path, [_row(1, category="")])
    with pytest.raises(HistoricalQuestionRowError):
        HistoricalQuestionRepository.from_workbook(path)


def test_whitespace_only_category_rejected(tmp_path):
    path = make_workbook(tmp_path, [_row(1, category="   ")])
    with pytest.raises(HistoricalQuestionRowError):
        HistoricalQuestionRepository.from_workbook(path)


def test_blank_question_rejected(tmp_path):
    path = make_workbook(tmp_path, [_row(1, question="")])
    with pytest.raises(HistoricalQuestionRowError):
        HistoricalQuestionRepository.from_workbook(path)


def test_whitespace_only_question_rejected(tmp_path):
    path = make_workbook(tmp_path, [_row(1, question="   ")])
    with pytest.raises(HistoricalQuestionRowError):
        HistoricalQuestionRepository.from_workbook(path)


def test_missing_answer_rejected(tmp_path):
    path = make_workbook(tmp_path, [_row(1, answers=[HEBREW_ANSWERS[0], None, HEBREW_ANSWERS[2], HEBREW_ANSWERS[3]])])
    with pytest.raises(HistoricalQuestionRowError):
        HistoricalQuestionRepository.from_workbook(path)


def test_blank_answer_rejected(tmp_path):
    path = make_workbook(tmp_path, [_row(1, answers=[HEBREW_ANSWERS[0], "", HEBREW_ANSWERS[2], HEBREW_ANSWERS[3]])])
    with pytest.raises(HistoricalQuestionRowError):
        HistoricalQuestionRepository.from_workbook(path)


def test_whitespace_only_answer_rejected(tmp_path):
    path = make_workbook(tmp_path, [_row(1, answers=[HEBREW_ANSWERS[0], "   ", HEBREW_ANSWERS[2], HEBREW_ANSWERS[3]])])
    with pytest.raises(HistoricalQuestionRowError):
        HistoricalQuestionRepository.from_workbook(path)


def test_correct_answer_zero_rejected(tmp_path):
    path = make_workbook(tmp_path, [_row(1, correct=0)])
    with pytest.raises(HistoricalQuestionRowError):
        HistoricalQuestionRepository.from_workbook(path)


def test_correct_answer_five_rejected(tmp_path):
    path = make_workbook(tmp_path, [_row(1, correct=5)])
    with pytest.raises(HistoricalQuestionRowError):
        HistoricalQuestionRepository.from_workbook(path)


def test_fractional_correct_answer_rejected(tmp_path):
    path = make_workbook(tmp_path, [_row(1, correct=1.5)])
    with pytest.raises(HistoricalQuestionRowError):
        HistoricalQuestionRepository.from_workbook(path)


def test_partially_populated_row_is_not_silently_skipped(tmp_path):
    row = [1, "גזע המוח", None, None, None, None, None, None]
    path = make_workbook(tmp_path, [row])
    with pytest.raises(HistoricalQuestionRowError):
        HistoricalQuestionRepository.from_workbook(path)


def test_row_error_includes_worksheet_row_number(tmp_path):
    path = make_workbook(tmp_path, [_row(1), _row(2, question="")])
    with pytest.raises(HistoricalQuestionRowError, match="row 3"):
        HistoricalQuestionRepository.from_workbook(path)


def test_duplicate_id_error_includes_duplicate_id(tmp_path):
    path = make_workbook(tmp_path, [_row(42), _row(42)])
    with pytest.raises(HistoricalQuestionRowError, match="42"):
        HistoricalQuestionRepository.from_workbook(path)


def test_duplicate_id_error_includes_row_number(tmp_path):
    path = make_workbook(tmp_path, [_row(42), _row(42)])
    with pytest.raises(HistoricalQuestionRowError, match="row 3"):
        HistoricalQuestionRepository.from_workbook(path)


# ---------------------------------------------------------------------------
# Domain separation
# ---------------------------------------------------------------------------


def test_repository_returns_historical_style_reference_objects(tmp_path):
    path = make_workbook(tmp_path, [_row(1)])
    repo = HistoricalQuestionRepository.from_workbook(path)
    assert isinstance(repo.all_questions[0], HistoricalStyleReference)


def test_historical_references_are_not_source_evidence_chunks(tmp_path):
    path = make_workbook(tmp_path, [_row(1)])
    repo = HistoricalQuestionRepository.from_workbook(path)
    assert not isinstance(repo.all_questions[0], SourceEvidenceChunk)


def test_historical_repository_does_not_expose_source_type(tmp_path):
    path = make_workbook(tmp_path, [_row(1)])
    repo = HistoricalQuestionRepository.from_workbook(path)
    assert not hasattr(repo.all_questions[0], "source_type")
    assert "source_type" not in HistoricalStyleReference.model_fields


def test_no_automatic_conversion_to_grounding_evidence(tmp_path):
    path = make_workbook(tmp_path, [_row(1)])
    repo = HistoricalQuestionRepository.from_workbook(path)
    for question in repo.all_questions:
        assert not isinstance(question, SourceEvidenceChunk)
        assert not hasattr(question, "chunk_id")


# ---------------------------------------------------------------------------
# Immutability / defensive behavior
# ---------------------------------------------------------------------------


def test_all_questions_cannot_mutate_repository_state(tmp_path):
    path = make_workbook(tmp_path, [_row(1), _row(2)])
    repo = HistoricalQuestionRepository.from_workbook(path)
    questions = repo.all_questions
    with pytest.raises(TypeError):
        questions[0] = None  # tuples are immutable
    assert repo.total_questions == 2


def test_canonical_categories_cannot_mutate_repository_state(tmp_path):
    path = make_workbook(tmp_path, [_row(1, category="A")])
    repo = HistoricalQuestionRepository.from_workbook(path)
    categories = repo.canonical_categories
    with pytest.raises(TypeError):
        categories[0] = "B"
    assert repo.canonical_categories == ("A",)


def test_category_query_result_cannot_mutate_repository_state(tmp_path):
    path = make_workbook(tmp_path, [_row(1, category="A")])
    repo = HistoricalQuestionRepository.from_workbook(path)
    result = repo.questions_for_category("A")
    with pytest.raises(TypeError):
        result[0] = None
    assert len(repo.questions_for_category("A")) == 1


# ---------------------------------------------------------------------------
# Worksheet selection
# ---------------------------------------------------------------------------


def test_single_worksheet_selected_automatically(tmp_path):
    path = make_workbook(tmp_path, [_row(1)], sheet_names=["OnlySheet"])
    repo = HistoricalQuestionRepository.from_workbook(path)
    assert repo.total_questions == 1


def test_multiple_worksheets_without_explicit_name_fails_clearly(tmp_path):
    path = make_workbook(tmp_path, [_row(1)], sheet_names=["First", "Second"])
    with pytest.raises(WorkbookFormatError):
        HistoricalQuestionRepository.from_workbook(path)


def test_multiple_worksheets_with_explicit_name_succeeds(tmp_path):
    path = make_workbook(tmp_path, [_row(1)], sheet_names=["First", "Second"])
    repo = HistoricalQuestionRepository.from_workbook(path, sheet_name="First")
    assert repo.total_questions == 1
