import inspect
import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

from exam_generator.config import LLMConfig, LLMGenerationParams, LLMValidationParams
from exam_generator.models import (
    CandidateQuestion,
    CategoryValidationResult,
    ExamOutput,
    ExamQuestion,
    GenerationMode,
    GroundingValidationResult,
    MCQValidationResult,
    QualityValidationResult,
    TextbookCheckResult,
    TextbookCheckStatus,
    candidate_to_exam_question,
)
from exam_generator.orchestration import ExamGenerationResult, PlannedQuestion, QuestionProductionRecord
import exam_generator.output.audit as audit_module
import exam_generator.output.bundle as bundle_module
import exam_generator.output.serialization as serialization_module
from exam_generator.output import (
    AuditConsistencyError,
    ExamOutputBundle,
    build_exam_audit,
    build_exam_output_bundle,
    serialize_audit_json,
    serialize_exam_json,
    write_audit_json,
    write_exam_json,
    write_exam_output_bundle,
)
from exam_generator.production import CandidateValidationResults, QuestionAttempt, QuestionProductionResult

CATEGORY = "קליפת המוח"
QUESTION_TEXT = "מהו תפקידה העיקרי של קליפת המוח?"
NOW = datetime(2026, 8, 4, 12, 0, 0, tzinfo=timezone.utc)


# ---------------------------------------------------------------------------
# Fixture helpers
# ---------------------------------------------------------------------------


def _candidate(question: str = QUESTION_TEXT, **kwargs) -> CandidateQuestion:
    defaults = dict(
        question=question,
        answers=["תשובה א", "תשובה ב", "תשובה ג", "תשובה ד"],
        correct_answer=2,
        category=CATEGORY,
        generation_mode=GenerationMode.INDEPENDENT,
    )
    defaults.update(kwargs)
    return CandidateQuestion(**defaults)


def _validations(**overrides) -> CandidateValidationResults:
    defaults = dict(
        grounding=GroundingValidationResult(
            grounded=True,
            correct_answer_supported=True,
            other_answers_not_equally_correct=True,
            evidence_chunk_ids=["STUDENT_SUMMARY:student_summary_1.pdf:0001:0001"],
            evidence_text="supporting text",
            reason="well supported",
            confidence=0.9,
        ),
        mcq=MCQValidationResult(valid=True, exactly_four_answers=True, single_best_answer=True, reason="ok"),
        category=CategoryValidationResult(
            valid=True, requested_category=CATEGORY, assessed_category=CATEGORY, reason="ok"
        ),
        quality=QualityValidationResult(valid=True, reason="ok"),
        textbook=TextbookCheckResult(status=TextbookCheckStatus.CONSISTENT, reason="ok"),
    )
    defaults.update(overrides)
    return CandidateValidationResults(**defaults)


def _production_result(candidate: CandidateQuestion, *, rejected_first: bool = False) -> QuestionProductionResult:
    attempts = []
    if rejected_first:
        attempts.append(
            QuestionAttempt(
                attempt_number=1,
                candidate=candidate,
                validations=_validations(mcq=MCQValidationResult(valid=False, exactly_four_answers=True, single_best_answer=False, reason="ambiguous")),
            )
        )
    attempts.append(
        QuestionAttempt(attempt_number=len(attempts) + 1, candidate=candidate, validations=_validations())
    )
    return QuestionProductionResult(candidate=candidate, attempts=tuple(attempts))


def _record(
    position: int, category: str, candidate: CandidateQuestion, *, rejected_first: bool = False, duplicate_replacement_attempts: int = 0
) -> QuestionProductionRecord:
    planned = PlannedQuestion(position=position, category=category, generation_mode=candidate.generation_mode)
    production = _production_result(candidate, rejected_first=rejected_first)
    return QuestionProductionRecord(
        planned=planned, production=production, duplicate_replacement_attempts=duplicate_replacement_attempts
    )


def _generation_result(records: list[QuestionProductionRecord]) -> ExamGenerationResult:
    exam_questions = [candidate_to_exam_question(r.production.candidate, r.planned.position) for r in records]
    exam = ExamOutput(questions=exam_questions)
    return ExamGenerationResult(
        exam=exam, plan=tuple(r.planned for r in records), productions=tuple(records)
    )


def _llm_config(**overrides) -> LLMConfig:
    defaults = dict(
        provider="openai",
        model="gpt-4o-mini",
        generation=LLMGenerationParams(temperature=0.7, max_tokens=800),
        validation=LLMValidationParams(temperature=0.2, max_tokens=500),
    )
    defaults.update(overrides)
    return LLMConfig(**defaults)


def _build_audit(records, **overrides):
    kwargs = dict(
        exam_id="exam-2026-08-04",
        generated_at=NOW,
        llm_config=_llm_config(),
        diversity_target=0.7,
    )
    kwargs.update(overrides)
    return build_exam_audit(_generation_result(records), **kwargs)


# ---------------------------------------------------------------------------
# Clean output
# ---------------------------------------------------------------------------


def test_generation_result_exam_contains_expected_question_fields():
    result = _generation_result([_record(1, CATEGORY, _candidate())])
    question = result.exam.questions[0]
    assert question.number == 1
    assert question.question == QUESTION_TEXT
    assert (question.answer1, question.answer2, question.answer3, question.answer4) == (
        "תשובה א",
        "תשובה ב",
        "תשובה ג",
        "תשובה ד",
    )
    assert question.correct_answer == 2
    assert question.category == CATEGORY


def test_clean_output_exposes_no_validation_or_evidence_fields():
    assert "grounding" not in ExamQuestion.model_fields
    assert "mcq_validation" not in ExamQuestion.model_fields
    assert "evidence" not in ExamQuestion.model_fields
    assert "generation_mode" not in ExamQuestion.model_fields
    assert "historical_reference_id" not in ExamQuestion.model_fields


def test_hebrew_survives_clean_exam_serialization():
    result = _generation_result([_record(1, CATEGORY, _candidate())])
    serialized = serialize_exam_json(result.exam)
    assert QUESTION_TEXT in serialized
    assert "\\u" not in serialized


def test_exactly_four_answers_and_correct_answer_preserved():
    candidate = _candidate(answers=["1", "2", "3", "4"], correct_answer=3)
    result = _generation_result([_record(1, CATEGORY, candidate)])
    question = result.exam.questions[0]
    assert (question.answer1, question.answer2, question.answer3, question.answer4) == ("1", "2", "3", "4")
    assert question.correct_answer == 3


# ---------------------------------------------------------------------------
# Audit
# ---------------------------------------------------------------------------


def test_every_clean_question_has_one_accepted_audit_record():
    records = [_record(1, CATEGORY, _candidate(question="שאלה 1")), _record(2, CATEGORY, _candidate(question="שאלה 2"))]
    audit = _build_audit(records)
    assert len(audit.questions) == 2
    assert [q.number for q in audit.questions] == [1, 2]


def test_all_production_attempts_are_preserved_in_audit():
    records = [_record(1, CATEGORY, _candidate(), rejected_first=True)]
    audit = _build_audit(records)
    assert len(audit.questions[0].attempts) == 2


def test_rejected_attempts_remain_visible_in_audit():
    records = [_record(1, CATEGORY, _candidate(), rejected_first=True)]
    audit = _build_audit(records)
    attempts = audit.questions[0].attempts
    assert attempts[0].accepted is False
    assert attempts[0].mcq_validation.valid is False
    assert attempts[1].accepted is True


def test_all_five_validator_results_preserved_per_attempt():
    records = [_record(1, CATEGORY, _candidate())]
    audit = _build_audit(records)
    attempt = audit.questions[0].attempts[0]
    assert attempt.grounding.passed is True
    assert attempt.mcq_validation.valid is True
    assert attempt.category_validation.valid is True
    assert attempt.quality_validation.valid is True
    assert attempt.textbook_check.status == TextbookCheckStatus.CONSISTENT


def test_generation_mode_is_preserved():
    candidate = _candidate(generation_mode=GenerationMode.STYLE_SIMILAR)
    records = [_record(1, CATEGORY, candidate)]
    audit = _build_audit(records)
    assert audit.questions[0].generation_mode == GenerationMode.STYLE_SIMILAR


def test_final_accepted_attempt_is_identifiable():
    records = [_record(1, CATEGORY, _candidate(), rejected_first=True)]
    audit = _build_audit(records)
    accepted = [a for a in audit.questions[0].attempts if a.accepted]
    assert len(accepted) == 1
    assert accepted[0].attempt_number == 2


def test_grounding_evidence_identity_preserved_within_attempt():
    records = [_record(1, CATEGORY, _candidate())]
    audit = _build_audit(records)
    assert audit.questions[0].attempts[0].grounding.evidence_chunk_ids == [
        "STUDENT_SUMMARY:student_summary_1.pdf:0001:0001"
    ]


def test_historical_reference_id_is_honestly_absent_not_fabricated():
    candidate = _candidate(generation_mode=GenerationMode.STYLE_SIMILAR)
    records = [_record(1, CATEGORY, candidate)]
    audit = _build_audit(records)
    assert audit.questions[0].historical_reference_id is None


def test_generation_evidence_is_honestly_absent_not_fabricated():
    records = [_record(1, CATEGORY, _candidate())]
    audit = _build_audit(records)
    assert audit.questions[0].evidence == []


def test_textbook_result_and_status_preserved():
    candidate = _candidate()
    records = [_record(1, CATEGORY, candidate)]
    audit = _build_audit(records)
    assert audit.questions[0].textbook_check.status == TextbookCheckStatus.CONSISTENT


def test_provider_and_model_recorded_from_llm_config():
    records = [_record(1, CATEGORY, _candidate())]
    audit = _build_audit(records, llm_config=_llm_config(provider="openai", model="gpt-4o"))
    assert audit.provider == "openai"
    assert audit.model == "gpt-4o"


def test_generation_attempts_count_matches_actual_attempts():
    records = [_record(1, CATEGORY, _candidate(), rejected_first=True)]
    audit = _build_audit(records)
    assert audit.questions[0].generation_attempts == 2


def test_diversity_target_recorded_as_supplied():
    records = [_record(1, CATEGORY, _candidate())]
    audit = _build_audit(records, diversity_target=0.42)
    assert audit.questions[0].diversity_target == 0.42


def test_exam_id_and_generated_at_recorded_as_supplied():
    records = [_record(1, CATEGORY, _candidate())]
    audit = _build_audit(records, exam_id="exam-xyz", generated_at=NOW)
    assert audit.exam_id == "exam-xyz"
    assert audit.generated_at == NOW


# ---------------------------------------------------------------------------
# Consistency
# ---------------------------------------------------------------------------


def test_matching_generation_result_passes_consistency_check():
    records = [_record(1, CATEGORY, _candidate())]
    audit = _build_audit(records)
    assert len(audit.questions) == 1


def test_question_count_mismatch_fails_clearly():
    candidate = _candidate()
    record = _record(1, CATEGORY, candidate)
    tampered = ExamGenerationResult(
        exam=ExamOutput(
            questions=[
                candidate_to_exam_question(candidate, 1),
                candidate_to_exam_question(_candidate(question="שאלה נוספת"), 2),
            ]
        ),
        plan=(record.planned,),
        productions=(record,),
    )
    with pytest.raises(AuditConsistencyError):
        build_exam_audit(tampered, exam_id="x", generated_at=NOW, llm_config=_llm_config(), diversity_target=0.5)


def test_mismatched_question_text_fails_consistency_check():
    candidate = _candidate()
    record = _record(1, CATEGORY, candidate)
    wrong_question = ExamQuestion(
        number=1,
        question="שאלה שונה לגמרי שלא נוצרה",
        answer1=candidate.answers[0],
        answer2=candidate.answers[1],
        answer3=candidate.answers[2],
        answer4=candidate.answers[3],
        correct_answer=candidate.correct_answer,
        category=candidate.category,
    )
    tampered = ExamGenerationResult(
        exam=ExamOutput(questions=[wrong_question]), plan=(record.planned,), productions=(record,)
    )
    with pytest.raises(AuditConsistencyError):
        build_exam_audit(tampered, exam_id="x", generated_at=NOW, llm_config=_llm_config(), diversity_target=0.5)


def test_mismatched_category_fails_consistency_check():
    candidate = _candidate()
    record = _record(1, CATEGORY, candidate)
    wrong_question = candidate_to_exam_question(candidate, 1).model_copy(update={"category": "קטגוריה אחרת"})
    tampered = ExamGenerationResult(
        exam=ExamOutput(questions=[wrong_question]), plan=(record.planned,), productions=(record,)
    )
    with pytest.raises(AuditConsistencyError):
        build_exam_audit(tampered, exam_id="x", generated_at=NOW, llm_config=_llm_config(), diversity_target=0.5)


def test_mismatched_correct_answer_fails_consistency_check():
    candidate = _candidate(correct_answer=2)
    record = _record(1, CATEGORY, candidate)
    wrong_question = candidate_to_exam_question(candidate, 1).model_copy(update={"correct_answer": 4})
    tampered = ExamGenerationResult(
        exam=ExamOutput(questions=[wrong_question]), plan=(record.planned,), productions=(record,)
    )
    with pytest.raises(AuditConsistencyError):
        build_exam_audit(tampered, exam_id="x", generated_at=NOW, llm_config=_llm_config(), diversity_target=0.5)


def test_rejected_final_attempt_never_represented_as_accepted():
    candidate = _candidate()
    rejected_only = QuestionProductionResult(
        candidate=candidate,
        attempts=(
            QuestionAttempt(
                attempt_number=1,
                candidate=candidate,
                validations=_validations(mcq=MCQValidationResult(valid=False, exactly_four_answers=True, single_best_answer=False, reason="bad")),
            ),
        ),
    )
    planned = PlannedQuestion(position=1, category=CATEGORY, generation_mode=candidate.generation_mode)
    record = QuestionProductionRecord(planned=planned, production=rejected_only, duplicate_replacement_attempts=0)
    tampered = ExamGenerationResult(
        exam=ExamOutput(questions=[candidate_to_exam_question(candidate, 1)]),
        plan=(planned,),
        productions=(record,),
    )
    with pytest.raises(AuditConsistencyError):
        build_exam_audit(tampered, exam_id="x", generated_at=NOW, llm_config=_llm_config(), diversity_target=0.5)


# ---------------------------------------------------------------------------
# Security
# ---------------------------------------------------------------------------


def test_no_api_key_or_secret_in_serialized_audit():
    records = [_record(1, CATEGORY, _candidate())]
    audit = _build_audit(records)
    serialized = serialize_audit_json(audit)
    assert "OPENAI_API_KEY" not in serialized
    assert "sk-" not in serialized


def test_llm_config_has_no_credential_field():
    assert "api_key" not in LLMConfig.model_fields
    assert "credentials" not in LLMConfig.model_fields


def test_output_modules_never_import_llm_provider_or_call_generate_structured():
    for module in (audit_module, bundle_module, serialization_module):
        source = inspect.getsource(module)
        assert "generate_structured" not in source
        assert "from exam_generator.llm" not in source
        assert "import exam_generator.llm" not in source
        assert "OPENAI_API_KEY" not in source


# ---------------------------------------------------------------------------
# Serialization
# ---------------------------------------------------------------------------


def test_clean_exam_serializes_to_valid_json():
    records = [_record(1, CATEGORY, _candidate())]
    result = _generation_result(records)
    parsed = json.loads(serialize_exam_json(result.exam))
    assert parsed["questions"][0]["question"] == QUESTION_TEXT


def test_audit_serializes_to_valid_json():
    records = [_record(1, CATEGORY, _candidate())]
    audit = _build_audit(records)
    parsed = json.loads(serialize_audit_json(audit))
    assert parsed["exam_id"] == "exam-2026-08-04"
    assert parsed["questions"][0]["attempts"][0]["accepted"] is True


def test_serialization_is_deterministic():
    records = [_record(1, CATEGORY, _candidate())]
    result = _generation_result(records)
    audit = _build_audit(records)
    assert serialize_exam_json(result.exam) == serialize_exam_json(result.exam)
    assert serialize_audit_json(audit) == serialize_audit_json(audit)


def test_hebrew_survives_audit_serialization():
    records = [_record(1, CATEGORY, _candidate())]
    audit = _build_audit(records)
    serialized = serialize_audit_json(audit)
    assert CATEGORY in serialized
    assert "\\u" not in serialized


def test_enum_fields_serialize_to_plain_string_values():
    candidate = _candidate(generation_mode=GenerationMode.STYLE_SIMILAR)
    records = [_record(1, CATEGORY, candidate)]
    audit = _build_audit(records)
    parsed = json.loads(serialize_audit_json(audit))
    assert parsed["questions"][0]["generation_mode"] == "STYLE_SIMILAR"


def test_write_exam_json_and_write_audit_json_write_separate_files(tmp_path: Path):
    records = [_record(1, CATEGORY, _candidate())]
    result = _generation_result(records)
    audit = _build_audit(records)

    exam_path = tmp_path / "exam.json"
    audit_path = tmp_path / "exam.audit.json"
    write_exam_json(exam_path, result.exam)
    write_audit_json(audit_path, audit)

    assert json.loads(exam_path.read_text(encoding="utf-8"))["questions"][0]["question"] == QUESTION_TEXT
    assert json.loads(audit_path.read_text(encoding="utf-8"))["exam_id"] == "exam-2026-08-04"


def test_write_exam_output_bundle_writes_both_files_from_one_bundle(tmp_path: Path):
    records = [_record(1, CATEGORY, _candidate())]
    generation_result = _generation_result(records)
    bundle = build_exam_output_bundle(
        generation_result, exam_id="exam-bundle", generated_at=NOW, llm_config=_llm_config(), diversity_target=0.5
    )
    exam_path = tmp_path / "exam.json"
    audit_path = tmp_path / "exam.audit.json"
    write_exam_output_bundle(exam_path=exam_path, audit_path=audit_path, bundle=bundle)

    assert exam_path.exists()
    assert audit_path.exists()


# ---------------------------------------------------------------------------
# Output bundle
# ---------------------------------------------------------------------------


def test_build_exam_output_bundle_associates_matching_exam_and_audit():
    records = [_record(1, CATEGORY, _candidate())]
    generation_result = _generation_result(records)
    bundle = build_exam_output_bundle(
        generation_result, exam_id="exam-1", generated_at=NOW, llm_config=_llm_config(), diversity_target=0.5
    )
    assert isinstance(bundle, ExamOutputBundle)
    assert bundle.exam is generation_result.exam
    assert bundle.audit.exam_id == "exam-1"
    assert len(bundle.audit.questions) == len(bundle.exam.questions)
