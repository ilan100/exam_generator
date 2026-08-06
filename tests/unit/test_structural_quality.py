from exam_generator.models import CandidateQuestion, GenerationMode
from exam_generator.validation.structural import detect_duplicated_answer_numbering

CATEGORY = "קליפת המוח"
QUESTION_TEXT = "מהו תפקידה העיקרי של קליפת המוח?"


def _candidate(**kwargs) -> CandidateQuestion:
    defaults = dict(
        question=QUESTION_TEXT,
        answers=["תשובה א", "תשובה ב", "תשובה ג", "תשובה ד"],
        correct_answer=2,
        category=CATEGORY,
        generation_mode=GenerationMode.INDEPENDENT,
    )
    defaults.update(kwargs)
    return CandidateQuestion(**defaults)


def test_no_defect_on_ordinary_answers():
    candidate = _candidate()
    assert detect_duplicated_answer_numbering(candidate) is None


def test_defect_detected_when_all_four_answers_have_leading_numbering():
    candidate = _candidate(
        answers=[
            "1. לטרלית ל-Olfactory Tract",
            "2. מדיאלית ל-Olfactory Tract",
            "3. אנטריורית ל-Olfactory Bulb",
            "4. פוסטריורית ל-Olfactory Bulb",
        ]
    )
    reason = detect_duplicated_answer_numbering(candidate)
    assert reason is not None
    assert "answer1" in reason
    assert "answer2" in reason
    assert "answer3" in reason
    assert "answer4" in reason


def test_defect_detected_with_parenthesis_and_colon_separators():
    candidate = _candidate(
        answers=[
            "1) לטרלית ל-Olfactory Tract",
            "2: מדיאלית ל-Olfactory Tract",
            "תשובה ג",
            "תשובה ד",
        ]
    )
    assert detect_duplicated_answer_numbering(candidate) is not None


def test_single_answer_with_leading_number_not_falsely_rejected():
    # Only one of four - plausibly legitimate content, not a systematic artifact.
    candidate = _candidate(
        answers=[
            "1. לטרלית ל-Olfactory Tract",
            "תשובה ב",
            "תשובה ג",
            "תשובה ד",
        ]
    )
    assert detect_duplicated_answer_numbering(candidate) is None


def test_ordinary_numeric_content_not_falsely_rejected():
    candidate = _candidate(
        answers=[
            "12 זוגות עצבים גולגולתיים",
            "2:1 יחס בין חומר אפור לחומר לבן",
            "31 זוגות עצבי שדרה",
            "24 חוליות בעמוד השדרה",
        ]
    )
    assert detect_duplicated_answer_numbering(candidate) is None


def test_candidate_not_mutated():
    candidate = _candidate(
        answers=[
            "1. לטרלית ל-Olfactory Tract",
            "2. מדיאלית ל-Olfactory Tract",
            "תשובה ג",
            "תשובה ד",
        ]
    )
    before = candidate.model_dump()
    detect_duplicated_answer_numbering(candidate)
    assert candidate.model_dump() == before
