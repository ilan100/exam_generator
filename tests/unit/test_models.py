import json
from datetime import datetime, timedelta, timezone

import pytest
from pydantic import ValidationError

from exam_generator.models import (
    CandidateQuestion,
    CategoryValidationResult,
    ExamAudit,
    ExamOutput,
    ExamQuestion,
    ExamRequest,
    GenerationMode,
    GroundingValidationResult,
    HistoricalStyleReference,
    MCQValidationResult,
    QualityValidationResult,
    QuestionAudit,
    SourceEvidenceChunk,
    SourceType,
    TextbookCheckResult,
    TextbookCheckStatus,
    candidate_to_exam_question,
)

HEBREW_QUESTION = "איזה מבנה קשור ל-Corona radiata בדוגמה זו?"
HEBREW_ANSWERS = ["חומר לבן", "חומר אפור", "קליפת המוח", "גזע המוח"]


def make_grounding(**overrides) -> GroundingValidationResult:
    base = dict(
        grounded=True,
        correct_answer_supported=True,
        other_answers_not_equally_correct=True,
        evidence_chunk_ids=["chunk-1"],
        evidence_text="supporting text",
        reason="well supported",
        confidence=0.9,
    )
    base.update(overrides)
    return GroundingValidationResult(**base)


def make_question_audit(**overrides) -> QuestionAudit:
    base = dict(
        number=1,
        category="גזע המוח",
        generation_mode=GenerationMode.INDEPENDENT,
        historical_reference_id=None,
        grounding=make_grounding(),
        evidence=[
            SourceEvidenceChunk(
                chunk_id="chunk-1",
                source_file="student_summary_1.pdf",
                page=10,
                text="some evidence text",
                source_type=SourceType.STUDENT_SUMMARY,
            )
        ],
        mcq_validation=MCQValidationResult(
            valid=True, exactly_four_answers=True, single_best_answer=True, reason="ok"
        ),
        category_validation=CategoryValidationResult(
            valid=True, requested_category="גזע המוח", assessed_category="גזע המוח", reason="ok"
        ),
        quality_validation=QualityValidationResult(valid=True, reason="ok"),
        textbook_check=None,
        generation_attempts=1,
        diversity_target=0.7,
    )
    base.update(overrides)
    return QuestionAudit(**base)


# ---------------------------------------------------------------------------
# Exam Request
# ---------------------------------------------------------------------------


def test_exam_request_valid_accepted():
    request = ExamRequest(categories={"גזע המוח": 5, "חומר לבן": 4})
    assert request.categories["גזע המוח"] == 5


def test_exam_request_empty_categories_rejected():
    with pytest.raises(ValidationError):
        ExamRequest(categories={})


def test_exam_request_empty_category_name_rejected():
    with pytest.raises(ValidationError):
        ExamRequest(categories={"": 1})


def test_exam_request_whitespace_only_category_rejected():
    with pytest.raises(ValidationError):
        ExamRequest(categories={"   ": 1})


def test_exam_request_zero_count_rejected():
    with pytest.raises(ValidationError):
        ExamRequest(categories={"cat": 0})


def test_exam_request_negative_count_rejected():
    with pytest.raises(ValidationError):
        ExamRequest(categories={"cat": -1})


def test_exam_request_boolean_count_rejected():
    with pytest.raises(ValidationError):
        ExamRequest(categories={"cat": True})


# ---------------------------------------------------------------------------
# Clean Exam Question
# ---------------------------------------------------------------------------


def _valid_question_kwargs(**overrides):
    base = dict(
        number=1,
        question=HEBREW_QUESTION,
        answer1=HEBREW_ANSWERS[0],
        answer2=HEBREW_ANSWERS[1],
        answer3=HEBREW_ANSWERS[2],
        answer4=HEBREW_ANSWERS[3],
        correct_answer=2,
        category="גזע המוח",
    )
    base.update(overrides)
    return base


def test_exam_question_valid_hebrew_accepted():
    question = ExamQuestion(**_valid_question_kwargs())
    assert question.question == HEBREW_QUESTION


def test_exam_question_mixed_hebrew_english_accepted():
    question = ExamQuestion(**_valid_question_kwargs(question="המסילה עוברת דרך ה-Corona radiata"))
    assert "Corona radiata" in question.question


def test_exam_question_empty_question_rejected():
    with pytest.raises(ValidationError):
        ExamQuestion(**_valid_question_kwargs(question=""))


def test_exam_question_whitespace_only_question_rejected():
    with pytest.raises(ValidationError):
        ExamQuestion(**_valid_question_kwargs(question="   "))


def test_exam_question_empty_answer_rejected():
    with pytest.raises(ValidationError):
        ExamQuestion(**_valid_question_kwargs(answer1=""))


def test_exam_question_whitespace_only_answer_rejected():
    with pytest.raises(ValidationError):
        ExamQuestion(**_valid_question_kwargs(answer2="   "))


def test_exam_question_correct_answer_zero_rejected():
    with pytest.raises(ValidationError):
        ExamQuestion(**_valid_question_kwargs(correct_answer=0))


def test_exam_question_correct_answer_five_rejected():
    with pytest.raises(ValidationError):
        ExamQuestion(**_valid_question_kwargs(correct_answer=5))


def test_exam_question_boolean_correct_answer_rejected():
    with pytest.raises(ValidationError):
        ExamQuestion(**_valid_question_kwargs(correct_answer=True))


def test_exam_question_zero_number_rejected():
    with pytest.raises(ValidationError):
        ExamQuestion(**_valid_question_kwargs(number=0))


def test_exam_question_negative_number_rejected():
    with pytest.raises(ValidationError):
        ExamQuestion(**_valid_question_kwargs(number=-1))


def test_exam_question_boolean_number_rejected():
    with pytest.raises(ValidationError):
        ExamQuestion(**_valid_question_kwargs(number=True))


# ---------------------------------------------------------------------------
# Candidate Question
# ---------------------------------------------------------------------------


def _valid_candidate_kwargs(**overrides):
    base = dict(
        question=HEBREW_QUESTION,
        answers=list(HEBREW_ANSWERS),
        correct_answer=2,
        category="גזע המוח",
        generation_mode=GenerationMode.INDEPENDENT,
    )
    base.update(overrides)
    return base


def test_candidate_valid_accepted():
    candidate = CandidateQuestion(**_valid_candidate_kwargs())
    assert len(candidate.answers) == 4


def test_candidate_fewer_than_four_answers_rejected():
    with pytest.raises(ValidationError):
        CandidateQuestion(**_valid_candidate_kwargs(answers=HEBREW_ANSWERS[:3]))


def test_candidate_more_than_four_answers_rejected():
    with pytest.raises(ValidationError):
        CandidateQuestion(**_valid_candidate_kwargs(answers=HEBREW_ANSWERS + ["extra"]))


def test_candidate_empty_answer_rejected():
    answers = list(HEBREW_ANSWERS)
    answers[0] = ""
    with pytest.raises(ValidationError):
        CandidateQuestion(**_valid_candidate_kwargs(answers=answers))


def test_candidate_correct_answer_outside_range_rejected():
    with pytest.raises(ValidationError):
        CandidateQuestion(**_valid_candidate_kwargs(correct_answer=5))


def test_candidate_boolean_correct_answer_rejected():
    with pytest.raises(ValidationError):
        CandidateQuestion(**_valid_candidate_kwargs(correct_answer=True))


def test_candidate_generation_mode_serializes_correctly():
    candidate = CandidateQuestion(**_valid_candidate_kwargs(generation_mode=GenerationMode.STYLE_SIMILAR))
    dumped = candidate.model_dump(mode="json")
    assert dumped["generation_mode"] == "STYLE_SIMILAR"


# ---------------------------------------------------------------------------
# Conversion
# ---------------------------------------------------------------------------


def test_conversion_candidate_to_clean_question():
    candidate = CandidateQuestion(**_valid_candidate_kwargs())
    question = candidate_to_exam_question(candidate, number=7)
    assert isinstance(question, ExamQuestion)


def test_conversion_preserves_answer_order():
    candidate = CandidateQuestion(**_valid_candidate_kwargs())
    question = candidate_to_exam_question(candidate, number=1)
    assert [question.answer1, question.answer2, question.answer3, question.answer4] == HEBREW_ANSWERS


def test_conversion_preserves_correct_answer_id():
    candidate = CandidateQuestion(**_valid_candidate_kwargs(correct_answer=3))
    question = candidate_to_exam_question(candidate, number=1)
    assert question.correct_answer == 3


def test_conversion_preserves_hebrew_text():
    candidate = CandidateQuestion(**_valid_candidate_kwargs())
    question = candidate_to_exam_question(candidate, number=1)
    assert question.question == HEBREW_QUESTION


def test_conversion_preserves_embedded_english_terminology():
    candidate = CandidateQuestion(**_valid_candidate_kwargs(question="המסילה עוברת דרך ה-Corona radiata"))
    question = candidate_to_exam_question(candidate, number=1)
    assert "Corona radiata" in question.question


def test_conversion_preserves_supplied_number():
    candidate = CandidateQuestion(**_valid_candidate_kwargs())
    question = candidate_to_exam_question(candidate, number=42)
    assert question.number == 42


def test_conversion_invalid_supplied_number_rejected():
    candidate = CandidateQuestion(**_valid_candidate_kwargs())
    with pytest.raises(ValidationError):
        candidate_to_exam_question(candidate, number=0)


# ---------------------------------------------------------------------------
# Source Evidence
# ---------------------------------------------------------------------------


def _valid_chunk_kwargs(**overrides):
    base = dict(
        chunk_id="chunk-1",
        source_file="student_summary_1.pdf",
        page=10,
        text="evidence text",
        source_type=SourceType.STUDENT_SUMMARY,
    )
    base.update(overrides)
    return base


def test_source_evidence_student_summary_accepted():
    chunk = SourceEvidenceChunk(**_valid_chunk_kwargs())
    assert chunk.source_type == SourceType.STUDENT_SUMMARY


def test_source_evidence_course_book_accepted():
    chunk = SourceEvidenceChunk(**_valid_chunk_kwargs(source_type=SourceType.COURSE_BOOK, source_file="course_book.pdf"))
    assert chunk.source_type == SourceType.COURSE_BOOK


def test_source_evidence_page_zero_rejected():
    with pytest.raises(ValidationError):
        SourceEvidenceChunk(**_valid_chunk_kwargs(page=0))


def test_source_evidence_negative_page_rejected():
    with pytest.raises(ValidationError):
        SourceEvidenceChunk(**_valid_chunk_kwargs(page=-1))


def test_source_evidence_boolean_page_rejected():
    with pytest.raises(ValidationError):
        SourceEvidenceChunk(**_valid_chunk_kwargs(page=True))


def test_source_evidence_empty_text_rejected():
    with pytest.raises(ValidationError):
        SourceEvidenceChunk(**_valid_chunk_kwargs(text=""))


def test_source_evidence_empty_chunk_id_rejected():
    with pytest.raises(ValidationError):
        SourceEvidenceChunk(**_valid_chunk_kwargs(chunk_id=""))


def test_source_evidence_empty_source_file_rejected():
    with pytest.raises(ValidationError):
        SourceEvidenceChunk(**_valid_chunk_kwargs(source_file=""))


# ---------------------------------------------------------------------------
# Historical Style Reference
# ---------------------------------------------------------------------------


def _valid_historical_kwargs(**overrides):
    base = dict(
        historical_question_id=101,
        category="גזע המוח",
        question=HEBREW_QUESTION,
        answers=list(HEBREW_ANSWERS),
        correct_answer=2,
    )
    base.update(overrides)
    return base


def test_historical_reference_valid_accepted():
    reference = HistoricalStyleReference(**_valid_historical_kwargs())
    assert reference.historical_question_id == 101


def test_historical_reference_requires_exactly_four_answers():
    with pytest.raises(ValidationError):
        HistoricalStyleReference(**_valid_historical_kwargs(answers=HEBREW_ANSWERS[:3]))


def test_historical_reference_invalid_correct_answer_rejected():
    with pytest.raises(ValidationError):
        HistoricalStyleReference(**_valid_historical_kwargs(correct_answer=5))


def test_historical_reference_is_structurally_separate_from_evidence():
    assert not issubclass(HistoricalStyleReference, SourceEvidenceChunk)
    assert not issubclass(SourceEvidenceChunk, HistoricalStyleReference)


# ---------------------------------------------------------------------------
# Grounding Result
# ---------------------------------------------------------------------------


def test_grounding_fully_passing_reports_passed_true():
    assert make_grounding().passed is True


def test_grounding_not_grounded_fails():
    assert make_grounding(grounded=False).passed is False


def test_grounding_correct_answer_not_supported_fails():
    assert make_grounding(correct_answer_supported=False).passed is False


def test_grounding_other_answers_equally_correct_fails():
    assert make_grounding(other_answers_not_equally_correct=False).passed is False


def test_grounding_confidence_zero_accepted():
    assert make_grounding(confidence=0.0).confidence == 0.0


def test_grounding_confidence_one_accepted():
    assert make_grounding(confidence=1.0).confidence == 1.0


def test_grounding_confidence_below_zero_rejected():
    with pytest.raises(ValidationError):
        make_grounding(confidence=-0.01)


def test_grounding_confidence_above_one_rejected():
    with pytest.raises(ValidationError):
        make_grounding(confidence=1.01)


def test_grounding_non_boolean_decision_rejected():
    with pytest.raises(ValidationError):
        make_grounding(grounded=1)


def test_grounding_failed_result_may_have_no_evidence_chunk_ids():
    result = make_grounding(
        grounded=False,
        correct_answer_supported=False,
        other_answers_not_equally_correct=False,
        evidence_chunk_ids=[],
        evidence_text=None,
        reason="no support found",
    )
    assert result.evidence_chunk_ids == []
    assert result.passed is False


# ---------------------------------------------------------------------------
# Other Validation Models
# ---------------------------------------------------------------------------


def test_mcq_validation_result_valid_accepted():
    result = MCQValidationResult(valid=True, exactly_four_answers=True, single_best_answer=True, reason="ok")
    assert result.valid is True


def test_category_validation_accepts_absent_assessed_category():
    result = CategoryValidationResult(valid=False, requested_category="cat", assessed_category=None, reason="unclear")
    assert result.assessed_category is None


def test_quality_validation_result_accepted():
    result = QualityValidationResult(valid=True, reason="clear")
    assert result.valid is True


@pytest.mark.parametrize("status", list(TextbookCheckStatus))
def test_textbook_status_accepts_approved_values(status):
    result = TextbookCheckResult(status=status, reason="checked")
    assert result.status == status


def test_textbook_status_invalid_value_rejected():
    with pytest.raises(ValidationError):
        TextbookCheckResult(status="UNKNOWN_STATUS", reason="checked")


def test_textbook_optional_page_absent_works():
    result = TextbookCheckResult(status=TextbookCheckStatus.NOT_FOUND, reason="not present")
    assert result.source_page is None


def test_textbook_invalid_page_rejected():
    with pytest.raises(ValidationError):
        TextbookCheckResult(status=TextbookCheckStatus.CONSISTENT, source_page=0, reason="checked")


# ---------------------------------------------------------------------------
# Question Audit
# ---------------------------------------------------------------------------


def test_question_audit_valid_accepted():
    audit = make_question_audit()
    assert audit.number == 1


def test_question_audit_zero_generation_attempts_rejected():
    with pytest.raises(ValidationError):
        make_question_audit(generation_attempts=0)


def test_question_audit_negative_generation_attempts_rejected():
    with pytest.raises(ValidationError):
        make_question_audit(generation_attempts=-1)


def test_question_audit_boolean_generation_attempts_rejected():
    with pytest.raises(ValidationError):
        make_question_audit(generation_attempts=True)


def test_question_audit_diversity_below_zero_rejected():
    with pytest.raises(ValidationError):
        make_question_audit(diversity_target=-0.1)


def test_question_audit_diversity_above_one_rejected():
    with pytest.raises(ValidationError):
        make_question_audit(diversity_target=1.1)


def test_question_audit_optional_historical_reference_id_works():
    audit = make_question_audit(
        generation_mode=GenerationMode.STYLE_SIMILAR, historical_reference_id=55
    )
    assert audit.historical_reference_id == 55


def test_question_audit_optional_textbook_check_works():
    audit = make_question_audit(
        textbook_check=TextbookCheckResult(status=TextbookCheckStatus.CONSISTENT, reason="matches")
    )
    assert audit.textbook_check.status == TextbookCheckStatus.CONSISTENT


def test_question_audit_multiple_evidence_chunks_supported():
    chunks = [
        SourceEvidenceChunk(
            chunk_id=f"chunk-{i}",
            source_file="student_summary_1.pdf",
            page=i,
            text="text",
            source_type=SourceType.STUDENT_SUMMARY,
        )
        for i in range(1, 4)
    ]
    audit = make_question_audit(evidence=chunks)
    assert len(audit.evidence) == 3


# ---------------------------------------------------------------------------
# Clean Exam Output
# ---------------------------------------------------------------------------


def _question(number, **overrides):
    return ExamQuestion(**_valid_question_kwargs(number=number, **overrides))


def test_exam_output_one_question_accepted():
    output = ExamOutput(questions=[_question(1)])
    assert len(output.questions) == 1


def test_exam_output_multi_question_contiguous_accepted():
    output = ExamOutput(questions=[_question(1), _question(2), _question(3)])
    assert len(output.questions) == 3


def test_exam_output_empty_list_rejected():
    with pytest.raises(ValidationError):
        ExamOutput(questions=[])


def test_exam_output_duplicate_numbers_rejected():
    with pytest.raises(ValidationError):
        ExamOutput(questions=[_question(1), _question(1)])


def test_exam_output_missing_sequence_number_rejected():
    with pytest.raises(ValidationError):
        ExamOutput(questions=[_question(1), _question(3)])


def test_exam_output_sequence_beginning_above_one_rejected():
    with pytest.raises(ValidationError):
        ExamOutput(questions=[_question(2), _question(3)])


# ---------------------------------------------------------------------------
# Exam Audit
# ---------------------------------------------------------------------------


def _valid_exam_audit_kwargs(**overrides):
    base = dict(
        exam_id="exam-2026-08-03",
        generated_at=datetime.now(timezone.utc),
        provider="openai",
        model="gpt-4o-mini",
        questions=[make_question_audit()],
    )
    base.update(overrides)
    return base


def test_exam_audit_valid_accepted():
    audit = ExamAudit(**_valid_exam_audit_kwargs())
    assert audit.exam_id == "exam-2026-08-03"


def test_exam_audit_empty_exam_id_rejected():
    with pytest.raises(ValidationError):
        ExamAudit(**_valid_exam_audit_kwargs(exam_id=""))


def test_exam_audit_empty_provider_rejected():
    with pytest.raises(ValidationError):
        ExamAudit(**_valid_exam_audit_kwargs(provider=""))


def test_exam_audit_empty_model_rejected():
    with pytest.raises(ValidationError):
        ExamAudit(**_valid_exam_audit_kwargs(model=""))


def test_exam_audit_empty_question_list_rejected():
    with pytest.raises(ValidationError):
        ExamAudit(**_valid_exam_audit_kwargs(questions=[]))


def test_exam_audit_duplicate_question_numbers_rejected():
    with pytest.raises(ValidationError):
        ExamAudit(**_valid_exam_audit_kwargs(questions=[make_question_audit(number=1), make_question_audit(number=1)]))


def test_exam_audit_timezone_naive_datetime_rejected():
    with pytest.raises(ValidationError):
        ExamAudit(**_valid_exam_audit_kwargs(generated_at=datetime.now()))


def test_exam_audit_timezone_aware_datetime_accepted():
    aware = datetime.now(timezone(timedelta(hours=3)))
    audit = ExamAudit(**_valid_exam_audit_kwargs(generated_at=aware))
    assert audit.generated_at.tzinfo is not None


# ---------------------------------------------------------------------------
# Serialization / Schemas
# ---------------------------------------------------------------------------


def test_generation_mode_serializes_as_string():
    assert json.loads(json.dumps({"mode": GenerationMode.STYLE_SIMILAR}, default=str))["mode"] == "STYLE_SIMILAR"


def test_source_type_serializes_as_string():
    chunk = SourceEvidenceChunk(**_valid_chunk_kwargs())
    assert chunk.model_dump(mode="json")["source_type"] == "STUDENT_SUMMARY"


def test_textbook_status_serializes_as_string():
    result = TextbookCheckResult(status=TextbookCheckStatus.POTENTIAL_CONFLICT, reason="conflict noted")
    assert result.model_dump(mode="json")["status"] == "POTENTIAL_CONFLICT"


def test_hebrew_survives_json_serialization():
    question = _question(1)
    dumped = json.loads(question.model_dump_json())
    assert dumped["question"] == HEBREW_QUESTION


def test_mixed_hebrew_english_survives_json_serialization():
    question = _question(1, question="המסילה עוברת דרך ה-Corona radiata")
    dumped = json.loads(question.model_dump_json())
    assert dumped["question"] == "המסילה עוברת דרך ה-Corona radiata"


def test_datetime_serialization_is_iso_compatible():
    audit = ExamAudit(**_valid_exam_audit_kwargs())
    dumped = audit.model_dump(mode="json")
    # Must be parseable back as an ISO-8601 datetime.
    datetime.fromisoformat(dumped["generated_at"])


@pytest.mark.parametrize(
    "schema_name",
    ["exam_request.schema.json", "exam_output.schema.json", "exam_audit.schema.json"],
)
def test_schema_files_are_valid_json(schema_name):
    from exam_generator.config.loader import find_project_root

    schema_path = find_project_root() / "schemas" / schema_name
    with schema_path.open("r", encoding="utf-8") as fh:
        schema = json.load(fh)
    assert isinstance(schema, dict)
    assert "properties" in schema


def test_example_request_loads_through_exam_request():
    from exam_generator.config.loader import find_project_root

    example_path = find_project_root() / "schemas" / "exam_request.example.json"
    with example_path.open("r", encoding="utf-8") as fh:
        raw = json.load(fh)
    request = ExamRequest(**raw)
    assert len(request.categories) >= 1
