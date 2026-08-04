import json
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from exam_generator.cli import EXIT_GENERATION_FAILURE, EXIT_SUCCESS, EXIT_USAGE_ERROR, main
from exam_generator.config import ConfigError
from exam_generator.generation import MissingEvidenceError
from exam_generator.llm import LLMConfigurationError, LLMProviderError
from exam_generator.models import (
    CandidateQuestion,
    CategoryValidationResult,
    ExamOutput,
    GenerationMode,
    GroundingValidationResult,
    MCQValidationResult,
    QualityValidationResult,
    TextbookCheckResult,
    TextbookCheckStatus,
    candidate_to_exam_question,
)
from exam_generator.orchestration import ExamGenerationResult, PlannedQuestion, QuestionProductionFailedError, QuestionProductionRecord
from exam_generator.production import CandidateValidationResults, QuestionAttempt, QuestionAttemptsExhaustedError, QuestionProductionResult
from exam_generator.retrieval import UnknownCategoryError

CATEGORY = "קליפת המוח"
QUESTION_TEXT = "מהו תפקידה העיקרי של קליפת המוח?"


# ---------------------------------------------------------------------------
# Fixture helpers
# ---------------------------------------------------------------------------


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


def _validations() -> CandidateValidationResults:
    return CandidateValidationResults(
        grounding=GroundingValidationResult(
            grounded=True,
            correct_answer_supported=True,
            other_answers_not_equally_correct=True,
            reason="ok",
            confidence=0.9,
        ),
        mcq=MCQValidationResult(valid=True, exactly_four_answers=True, single_best_answer=True, reason="ok"),
        category=CategoryValidationResult(valid=True, requested_category=CATEGORY, assessed_category=CATEGORY, reason="ok"),
        quality=QualityValidationResult(valid=True, reason="ok"),
        textbook=TextbookCheckResult(status=TextbookCheckStatus.CONSISTENT, reason="ok"),
    )


def _generation_result(count: int = 1) -> ExamGenerationResult:
    records = []
    for i in range(1, count + 1):
        candidate = _candidate(question=f"{QUESTION_TEXT} ({i})")
        attempt = QuestionAttempt(attempt_number=1, candidate=candidate, validations=_validations())
        production = QuestionProductionResult(candidate=candidate, attempts=(attempt,))
        planned = PlannedQuestion(position=i, category=CATEGORY, generation_mode=GenerationMode.INDEPENDENT)
        records.append(QuestionProductionRecord(planned=planned, production=production, duplicate_replacement_attempts=0))
    exam = ExamOutput(questions=[candidate_to_exam_question(r.production.candidate, r.planned.position) for r in records])
    return ExamGenerationResult(exam=exam, plan=tuple(r.planned for r in records), productions=tuple(records))


def _mock_orchestrator(*, return_value=None, side_effect=None) -> MagicMock:
    orchestrator = MagicMock()
    if side_effect is not None:
        orchestrator.generate_exam.side_effect = side_effect
    else:
        orchestrator.generate_exam.return_value = return_value or _generation_result()
    return orchestrator


def _write_request(path: Path, categories: dict) -> None:
    path.write_text(json.dumps({"categories": categories}, ensure_ascii=False), encoding="utf-8")


@pytest.fixture(autouse=True)
def _isolated_cwd(tmp_path, monkeypatch):
    """Every test runs with cwd = its own tmp_path, so a test that omits
    --exam-output/--audit-output (exercising the default "exam.json"/
    "exam_audit.json" paths) can never read or write files in the real
    project directory."""
    monkeypatch.chdir(tmp_path)


# ---------------------------------------------------------------------------
# Input
# ---------------------------------------------------------------------------


def test_valid_request_json_is_parsed(tmp_path, monkeypatch):
    request_path = tmp_path / "request.json"
    _write_request(request_path, {CATEGORY: 1})
    exam_path = tmp_path / "exam.json"
    audit_path = tmp_path / "audit.json"

    orchestrator = _mock_orchestrator()
    monkeypatch.setattr("exam_generator.cli.ExamOrchestrator.from_default_configuration", lambda: orchestrator)

    code = main(["generate", "--request", str(request_path), "--exam-output", str(exam_path), "--audit-output", str(audit_path)])

    assert code == EXIT_SUCCESS
    request_arg = orchestrator.generate_exam.call_args.args[0]
    assert request_arg.categories == {CATEGORY: 1}


def test_malformed_json_fails_clearly(tmp_path, capsys):
    request_path = tmp_path / "request.json"
    request_path.write_text("{not valid json", encoding="utf-8")

    code = main(["generate", "--request", str(request_path)])

    assert code == EXIT_USAGE_ERROR
    assert "not valid JSON" in capsys.readouterr().err


def test_missing_request_file_fails_clearly(tmp_path, capsys):
    code = main(["generate", "--request", str(tmp_path / "missing.json")])
    assert code == EXIT_USAGE_ERROR
    assert "not found" in capsys.readouterr().err


def test_invalid_request_structure_fails_clearly(tmp_path, capsys):
    request_path = tmp_path / "request.json"
    request_path.write_text(json.dumps({"wrong": 1}), encoding="utf-8")

    code = main(["generate", "--request", str(request_path)])

    assert code == EXIT_USAGE_ERROR
    assert "Invalid exam request" in capsys.readouterr().err


def test_hebrew_input_survives_parsing(tmp_path, monkeypatch):
    request_path = tmp_path / "request.json"
    _write_request(request_path, {CATEGORY: 2})
    exam_path = tmp_path / "exam.json"
    audit_path = tmp_path / "audit.json"

    orchestrator = _mock_orchestrator(return_value=_generation_result(2))
    monkeypatch.setattr("exam_generator.cli.ExamOrchestrator.from_default_configuration", lambda: orchestrator)

    main(["generate", "--request", str(request_path), "--exam-output", str(exam_path), "--audit-output", str(audit_path)])

    called_request = orchestrator.generate_exam.call_args.args[0]
    assert CATEGORY in called_request.categories


# ---------------------------------------------------------------------------
# Execution
# ---------------------------------------------------------------------------


def test_cli_invokes_orchestration_and_writes_separate_outputs(tmp_path, monkeypatch):
    request_path = tmp_path / "request.json"
    _write_request(request_path, {CATEGORY: 1})
    exam_path = tmp_path / "exam.json"
    audit_path = tmp_path / "audit.json"

    orchestrator = _mock_orchestrator()
    monkeypatch.setattr("exam_generator.cli.ExamOrchestrator.from_default_configuration", lambda: orchestrator)

    code = main(["generate", "--request", str(request_path), "--exam-output", str(exam_path), "--audit-output", str(audit_path)])

    assert code == EXIT_SUCCESS
    orchestrator.generate_exam.assert_called_once()
    assert exam_path.exists()
    assert audit_path.exists()
    assert exam_path.read_text(encoding="utf-8") != audit_path.read_text(encoding="utf-8")


def test_clean_output_remains_clean_and_audit_remains_separate(tmp_path, monkeypatch):
    request_path = tmp_path / "request.json"
    _write_request(request_path, {CATEGORY: 1})
    exam_path = tmp_path / "exam.json"
    audit_path = tmp_path / "audit.json"

    orchestrator = _mock_orchestrator()
    monkeypatch.setattr("exam_generator.cli.ExamOrchestrator.from_default_configuration", lambda: orchestrator)

    main(["generate", "--request", str(request_path), "--exam-output", str(exam_path), "--audit-output", str(audit_path)])

    exam_data = json.loads(exam_path.read_text(encoding="utf-8"))
    audit_data = json.loads(audit_path.read_text(encoding="utf-8"))
    assert "questions" in exam_data
    assert "grounding" not in json.dumps(exam_data)
    assert "attempts" in audit_data["questions"][0]


# ---------------------------------------------------------------------------
# Files
# ---------------------------------------------------------------------------


def test_explicit_output_paths_are_used(tmp_path, monkeypatch):
    request_path = tmp_path / "request.json"
    _write_request(request_path, {CATEGORY: 1})
    exam_path = tmp_path / "custom_exam.json"
    audit_path = tmp_path / "custom_audit.json"

    orchestrator = _mock_orchestrator()
    monkeypatch.setattr("exam_generator.cli.ExamOrchestrator.from_default_configuration", lambda: orchestrator)

    main(["generate", "--request", str(request_path), "--exam-output", str(exam_path), "--audit-output", str(audit_path)])

    assert exam_path.exists()
    assert audit_path.exists()


def test_default_output_paths_used_when_omitted(tmp_path, monkeypatch):
    request_path = tmp_path / "request.json"
    _write_request(request_path, {CATEGORY: 1})

    orchestrator = _mock_orchestrator()
    monkeypatch.setattr("exam_generator.cli.ExamOrchestrator.from_default_configuration", lambda: orchestrator)
    monkeypatch.chdir(tmp_path)

    code = main(["generate", "--request", str(request_path)])

    assert code == EXIT_SUCCESS
    assert (tmp_path / "exam.json").exists()
    assert (tmp_path / "exam_audit.json").exists()


def test_existing_output_without_force_fails(tmp_path, monkeypatch, capsys):
    request_path = tmp_path / "request.json"
    _write_request(request_path, {CATEGORY: 1})
    exam_path = tmp_path / "exam.json"
    audit_path = tmp_path / "audit.json"
    exam_path.write_text("stale content", encoding="utf-8")

    orchestrator = _mock_orchestrator()
    monkeypatch.setattr("exam_generator.cli.ExamOrchestrator.from_default_configuration", lambda: orchestrator)

    code = main(["generate", "--request", str(request_path), "--exam-output", str(exam_path), "--audit-output", str(audit_path)])

    assert code == EXIT_USAGE_ERROR
    assert "already exist" in capsys.readouterr().err
    assert exam_path.read_text(encoding="utf-8") == "stale content"
    orchestrator.generate_exam.assert_not_called()


def test_force_allows_replacement(tmp_path, monkeypatch):
    request_path = tmp_path / "request.json"
    _write_request(request_path, {CATEGORY: 1})
    exam_path = tmp_path / "exam.json"
    audit_path = tmp_path / "audit.json"
    exam_path.write_text("stale content", encoding="utf-8")
    audit_path.write_text("stale audit", encoding="utf-8")

    orchestrator = _mock_orchestrator()
    monkeypatch.setattr("exam_generator.cli.ExamOrchestrator.from_default_configuration", lambda: orchestrator)

    code = main(
        ["generate", "--request", str(request_path), "--exam-output", str(exam_path), "--audit-output", str(audit_path), "--force"]
    )

    assert code == EXIT_SUCCESS
    assert exam_path.read_text(encoding="utf-8") != "stale content"


def test_failure_before_generation_writes_no_output(tmp_path, monkeypatch):
    request_path = tmp_path / "request.json"
    request_path.write_text("not json", encoding="utf-8")
    exam_path = tmp_path / "exam.json"
    audit_path = tmp_path / "audit.json"

    code = main(["generate", "--request", str(request_path), "--exam-output", str(exam_path), "--audit-output", str(audit_path)])

    assert code == EXIT_USAGE_ERROR
    assert not exam_path.exists()
    assert not audit_path.exists()


def test_failed_generation_writes_no_output(tmp_path, monkeypatch):
    request_path = tmp_path / "request.json"
    _write_request(request_path, {CATEGORY: 1})
    exam_path = tmp_path / "exam.json"
    audit_path = tmp_path / "audit.json"

    orchestrator = _mock_orchestrator(side_effect=QuestionAttemptsExhaustedError("exhausted", attempts=()))
    monkeypatch.setattr("exam_generator.cli.ExamOrchestrator.from_default_configuration", lambda: orchestrator)

    code = main(["generate", "--request", str(request_path), "--exam-output", str(exam_path), "--audit-output", str(audit_path)])

    assert code == EXIT_GENERATION_FAILURE
    assert not exam_path.exists()
    assert not audit_path.exists()


def test_output_is_valid_utf8_json(tmp_path, monkeypatch):
    request_path = tmp_path / "request.json"
    _write_request(request_path, {CATEGORY: 1})
    exam_path = tmp_path / "exam.json"
    audit_path = tmp_path / "audit.json"

    orchestrator = _mock_orchestrator()
    monkeypatch.setattr("exam_generator.cli.ExamOrchestrator.from_default_configuration", lambda: orchestrator)

    main(["generate", "--request", str(request_path), "--exam-output", str(exam_path), "--audit-output", str(audit_path)])

    exam_data = json.loads(exam_path.read_text(encoding="utf-8"))
    assert QUESTION_TEXT in exam_data["questions"][0]["question"]
    assert "\\u" not in exam_path.read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# Errors
# ---------------------------------------------------------------------------


def test_missing_api_key_produces_clear_error(tmp_path, monkeypatch, capsys):
    request_path = tmp_path / "request.json"
    _write_request(request_path, {CATEGORY: 1})

    def _raise_missing_key():
        raise LLMConfigurationError("OPENAI_API_KEY is not set")

    monkeypatch.setattr("exam_generator.cli.ExamOrchestrator.from_default_configuration", _raise_missing_key)

    code = main(["generate", "--request", str(request_path)])

    assert code == EXIT_USAGE_ERROR
    assert "OPENAI_API_KEY" in capsys.readouterr().err


def test_generation_exhaustion_produces_nonzero_exit(tmp_path, monkeypatch):
    request_path = tmp_path / "request.json"
    _write_request(request_path, {CATEGORY: 1})

    orchestrator = _mock_orchestrator(side_effect=QuestionAttemptsExhaustedError("exhausted", attempts=()))
    monkeypatch.setattr("exam_generator.cli.ExamOrchestrator.from_default_configuration", lambda: orchestrator)

    code = main(["generate", "--request", str(request_path)])

    assert code == EXIT_GENERATION_FAILURE


def test_exam_level_production_failed_produces_nonzero_exit(tmp_path, monkeypatch):
    request_path = tmp_path / "request.json"
    _write_request(request_path, {CATEGORY: 1})

    planned = PlannedQuestion(position=1, category=CATEGORY, generation_mode=GenerationMode.INDEPENDENT)
    orchestrator = _mock_orchestrator(
        side_effect=QuestionProductionFailedError(
            "duplicate exhaustion", planned_question=planned, completed_productions=(), duplicate_productions=()
        )
    )
    monkeypatch.setattr("exam_generator.cli.ExamOrchestrator.from_default_configuration", lambda: orchestrator)

    code = main(["generate", "--request", str(request_path)])

    assert code == EXIT_GENERATION_FAILURE


def test_provider_failure_produces_nonzero_exit(tmp_path, monkeypatch):
    request_path = tmp_path / "request.json"
    _write_request(request_path, {CATEGORY: 1})

    orchestrator = _mock_orchestrator(side_effect=LLMProviderError("connection failed"))
    monkeypatch.setattr("exam_generator.cli.ExamOrchestrator.from_default_configuration", lambda: orchestrator)

    code = main(["generate", "--request", str(request_path)])

    assert code == EXIT_GENERATION_FAILURE


def test_unknown_category_produces_usage_error(tmp_path, monkeypatch, capsys):
    request_path = tmp_path / "request.json"
    _write_request(request_path, {CATEGORY: 1})

    orchestrator = _mock_orchestrator(side_effect=UnknownCategoryError(f"Unknown category: {CATEGORY!r}"))
    monkeypatch.setattr("exam_generator.cli.ExamOrchestrator.from_default_configuration", lambda: orchestrator)

    code = main(["generate", "--request", str(request_path)])

    assert code == EXIT_USAGE_ERROR
    assert "category" in capsys.readouterr().err.lower()


def test_config_error_produces_usage_error(tmp_path, monkeypatch):
    request_path = tmp_path / "request.json"
    _write_request(request_path, {CATEGORY: 1})

    def _raise_config_error():
        raise ConfigError("invalid config")

    monkeypatch.setattr("exam_generator.cli.ExamOrchestrator.from_default_configuration", _raise_config_error)

    code = main(["generate", "--request", str(request_path)])

    assert code == EXIT_USAGE_ERROR


def test_missing_evidence_generation_error_produces_generation_failure(tmp_path, monkeypatch):
    request_path = tmp_path / "request.json"
    _write_request(request_path, {CATEGORY: 1})

    orchestrator = _mock_orchestrator(side_effect=MissingEvidenceError("no evidence"))
    monkeypatch.setattr("exam_generator.cli.ExamOrchestrator.from_default_configuration", lambda: orchestrator)

    code = main(["generate", "--request", str(request_path)])

    assert code == EXIT_GENERATION_FAILURE


def test_expected_failures_do_not_emit_traceback(tmp_path, monkeypatch, capsys):
    request_path = tmp_path / "request.json"
    _write_request(request_path, {CATEGORY: 1})

    orchestrator = _mock_orchestrator(side_effect=LLMProviderError("boom"))
    monkeypatch.setattr("exam_generator.cli.ExamOrchestrator.from_default_configuration", lambda: orchestrator)

    main(["generate", "--request", str(request_path)])

    captured = capsys.readouterr()
    assert "Traceback" not in captured.err
    assert "Traceback" not in captured.out


def test_unexpected_exception_propagates_with_traceback(tmp_path, monkeypatch):
    request_path = tmp_path / "request.json"
    _write_request(request_path, {CATEGORY: 1})

    orchestrator = _mock_orchestrator(side_effect=RuntimeError("truly unexpected bug"))
    monkeypatch.setattr("exam_generator.cli.ExamOrchestrator.from_default_configuration", lambda: orchestrator)

    with pytest.raises(RuntimeError, match="truly unexpected bug"):
        main(["generate", "--request", str(request_path)])


def test_missing_required_argument_exits_usage_error(capsys):
    with pytest.raises(SystemExit) as excinfo:
        main(["generate"])
    assert excinfo.value.code == EXIT_USAGE_ERROR


# ---------------------------------------------------------------------------
# Security
# ---------------------------------------------------------------------------


def test_api_key_never_printed(tmp_path, monkeypatch, capsys):
    request_path = tmp_path / "request.json"
    _write_request(request_path, {CATEGORY: 1})

    monkeypatch.setenv("OPENAI_API_KEY", "sk-super-secret-value")

    orchestrator = _mock_orchestrator()
    monkeypatch.setattr("exam_generator.cli.ExamOrchestrator.from_default_configuration", lambda: orchestrator)

    main(["generate", "--request", str(request_path)])

    captured = capsys.readouterr()
    assert "sk-super-secret-value" not in captured.out
    assert "sk-super-secret-value" not in captured.err


def test_api_key_never_appears_in_generated_files(tmp_path, monkeypatch):
    request_path = tmp_path / "request.json"
    _write_request(request_path, {CATEGORY: 1})
    exam_path = tmp_path / "exam.json"
    audit_path = tmp_path / "audit.json"

    monkeypatch.setenv("OPENAI_API_KEY", "sk-super-secret-value")

    orchestrator = _mock_orchestrator()
    monkeypatch.setattr("exam_generator.cli.ExamOrchestrator.from_default_configuration", lambda: orchestrator)

    main(["generate", "--request", str(request_path), "--exam-output", str(exam_path), "--audit-output", str(audit_path)])

    assert "sk-super-secret-value" not in exam_path.read_text(encoding="utf-8")
    assert "sk-super-secret-value" not in audit_path.read_text(encoding="utf-8")


def test_cli_does_not_accept_api_key_argument(tmp_path, capsys):
    request_path = tmp_path / "request.json"
    _write_request(request_path, {CATEGORY: 1})

    with pytest.raises(SystemExit):
        main(["generate", "--request", str(request_path), "--api-key", "sk-whatever"])
    assert "unrecognized arguments" in capsys.readouterr().err
