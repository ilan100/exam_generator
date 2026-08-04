from unittest.mock import MagicMock

import pytest

from exam_generator.chunking import FactualSourceCorpus
from exam_generator.evaluation import (
    CandidateEvaluationRunner,
    RetrievalEvalQuery,
    RetrievalEvaluationRunner,
    UngroundedRetrievalQueryError,
    build_evaluation_plan,
    metrics,
    render_markdown_report,
)
from exam_generator.evaluation.models import (
    CandidateAttemptRecord,
    EvaluationConfig,
    EvaluationReport,
    OperationalFailureRecord,
)
from exam_generator.llm import LLMProviderError
from exam_generator.models import (
    CandidateQuestion,
    CategoryValidationResult,
    GenerationMode,
    GroundingValidationResult,
    MCQValidationResult,
    QualityValidationResult,
    SourceEvidenceChunk,
    SourceType,
    TextbookCheckResult,
    TextbookCheckStatus,
)
from exam_generator.production import CandidateValidationResults, QuestionAttempt, QuestionAttemptsExhaustedError, QuestionProductionResult
from exam_generator.retrieval import FactualRetrievalIndex

CATEGORY = "קליפת המוח"
QUESTION_TEXT = "מהו תפקידה העיקרי של קליפת המוח?"


# ---------------------------------------------------------------------------
# Fixture helpers
# ---------------------------------------------------------------------------


def _attempt_record(**overrides) -> CandidateAttemptRecord:
    defaults = dict(
        question_position=1,
        category=CATEGORY,
        generation_mode=GenerationMode.INDEPENDENT,
        attempt_number=1,
        accepted=True,
        grounding_passed=True,
        mcq_valid=True,
        category_valid=True,
        quality_valid=True,
        textbook_status=TextbookCheckStatus.CONSISTENT,
    )
    defaults.update(overrides)
    return CandidateAttemptRecord(**defaults)


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


def _validations(**overrides) -> CandidateValidationResults:
    defaults = dict(
        grounding=GroundingValidationResult(
            grounded=True, correct_answer_supported=True, other_answers_not_equally_correct=True, reason="ok", confidence=0.9
        ),
        mcq=MCQValidationResult(valid=True, exactly_four_answers=True, single_best_answer=True, reason="ok"),
        category=CategoryValidationResult(valid=True, requested_category=CATEGORY, assessed_category=CATEGORY, reason="ok"),
        quality=QualityValidationResult(valid=True, reason="ok"),
        textbook=TextbookCheckResult(status=TextbookCheckStatus.CONSISTENT, reason="ok"),
    )
    defaults.update(overrides)
    return CandidateValidationResults(**defaults)


def _chunk(text: str, *, chunk_id: str, page: int = 1) -> SourceEvidenceChunk:
    return SourceEvidenceChunk(
        chunk_id=chunk_id, source_file="doc.pdf", page=page, text=text, source_type=SourceType.STUDENT_SUMMARY
    )


# ---------------------------------------------------------------------------
# build_evaluation_plan
# ---------------------------------------------------------------------------


def test_plan_alternates_modes_starting_style_similar_per_category():
    plan = build_evaluation_plan(["A", "B"], 2)
    a_modes = [mode for cat, mode, _ in plan if cat == "A"]
    b_modes = [mode for cat, mode, _ in plan if cat == "B"]
    assert a_modes == [GenerationMode.STYLE_SIMILAR, GenerationMode.INDEPENDENT]
    assert b_modes == [GenerationMode.STYLE_SIMILAR, GenerationMode.INDEPENDENT]


def test_plan_positions_are_globally_contiguous():
    plan = build_evaluation_plan(["A", "B"], 2)
    assert [position for _, _, position in plan] == [1, 2, 3, 4]


def test_plan_preserves_total_requested_count():
    plan = build_evaluation_plan(["A", "B", "C"], 3)
    assert len(plan) == 9


# ---------------------------------------------------------------------------
# Metrics
# ---------------------------------------------------------------------------


def test_candidate_acceptance_rate():
    attempts = [_attempt_record(accepted=True), _attempt_record(accepted=False), _attempt_record(accepted=False)]
    assert metrics.candidate_acceptance_rate(attempts) == pytest.approx(1 / 3)


def test_candidate_acceptance_rate_empty_is_zero():
    assert metrics.candidate_acceptance_rate([]) == 0.0


def test_first_attempt_acceptance_rate():
    attempts = [
        _attempt_record(question_position=1, attempt_number=1, accepted=True),
        _attempt_record(question_position=2, attempt_number=1, accepted=False),
        _attempt_record(question_position=2, attempt_number=2, accepted=True),
    ]
    assert metrics.first_attempt_acceptance_rate(attempts) == pytest.approx(0.5)


def test_attempts_per_accepted_question_stats():
    attempts = [
        _attempt_record(question_position=1, attempt_number=1, accepted=True),
        _attempt_record(question_position=2, attempt_number=1, accepted=False),
        _attempt_record(question_position=2, attempt_number=2, accepted=False),
        _attempt_record(question_position=2, attempt_number=3, accepted=True),
    ]
    stats = metrics.attempts_per_accepted_question_stats(attempts)
    assert stats["n"] == 2
    assert stats["min"] == 1
    assert stats["max"] == 3
    assert stats["mean"] == pytest.approx(2.0)
    assert stats["median"] == pytest.approx(2.0)


def test_attempts_per_accepted_question_stats_no_accepted():
    attempts = [_attempt_record(question_position=1, accepted=False)]
    stats = metrics.attempts_per_accepted_question_stats(attempts)
    assert stats["n"] == 0


def test_exhaustion_rate():
    attempts = [
        _attempt_record(question_position=1, accepted=True),
        _attempt_record(question_position=2, accepted=False),
    ]
    assert metrics.exhaustion_rate(attempts) == pytest.approx(0.5)


def test_exhaustion_rate_no_attempts_is_zero():
    assert metrics.exhaustion_rate([]) == 0.0


def test_validator_failure_counts():
    attempts = [
        _attempt_record(accepted=True),
        _attempt_record(accepted=False, grounding_passed=False),
        _attempt_record(accepted=False, mcq_valid=False, category_valid=False),
    ]
    counts = metrics.validator_failure_counts(attempts)
    assert counts["total_rejected"] == 2
    assert counts["grounding"]["count"] == 1
    assert counts["mcq"]["count"] == 1
    assert counts["category"]["count"] == 1
    assert counts["quality"]["count"] == 0
    assert counts["grounding"]["rate"] == pytest.approx(0.5)


def test_validator_failure_counts_no_rejections():
    counts = metrics.validator_failure_counts([_attempt_record(accepted=True)])
    assert counts["total_rejected"] == 0
    assert counts["grounding"]["rate"] == 0.0


def test_textbook_status_distribution():
    attempts = [
        _attempt_record(textbook_status=TextbookCheckStatus.CONSISTENT),
        _attempt_record(textbook_status=TextbookCheckStatus.NOT_FOUND),
        _attempt_record(textbook_status=TextbookCheckStatus.NOT_FOUND),
    ]
    dist = metrics.textbook_status_distribution(attempts)
    assert dist == {"CONSISTENT": 1, "NOT_FOUND": 2}


def test_build_category_results():
    plan = build_evaluation_plan(["A", "B"], 1)
    attempts = [
        CandidateAttemptRecord(
            question_position=1, category="A", generation_mode=GenerationMode.STYLE_SIMILAR, attempt_number=1,
            accepted=True, grounding_passed=True, mcq_valid=True, category_valid=True, quality_valid=True,
            textbook_status=TextbookCheckStatus.CONSISTENT,
        ),
    ]
    failures = [
        OperationalFailureRecord(
            question_position=2, category="B", generation_mode=GenerationMode.STYLE_SIMILAR,
            failure_type="LLMProviderError", message="boom",
        )
    ]
    results = metrics.build_category_results(plan, attempts, failures)
    by_category = {r.category: r for r in results}
    assert by_category["A"].produced_questions == 1
    assert by_category["A"].accepted_candidates == 1
    assert by_category["B"].produced_questions == 0
    assert by_category["B"].operational_failures == 1


def test_recall_at_k():
    from exam_generator.evaluation.models import RetrievalEvalResult

    results = [
        RetrievalEvalResult(
            query="q1", expected_literal_term="t1", expected_chunk_ids=("c1",), retrieved_chunk_ids=("c1", "c2"),
            hit_at_3=True, hit_at_5=True, hit_at_8=True,
        ),
        RetrievalEvalResult(
            query="q2", expected_literal_term="t2", expected_chunk_ids=("c3",), retrieved_chunk_ids=("c4", "c5"),
            hit_at_3=False, hit_at_5=False, hit_at_8=False,
        ),
    ]
    assert metrics.recall_at_k(results, 3) == pytest.approx(0.5)
    assert len(metrics.retrieval_misses(results)) == 1


# ---------------------------------------------------------------------------
# CandidateEvaluationRunner
# ---------------------------------------------------------------------------


def _production_result(*, rejected_first: bool = False) -> QuestionProductionResult:
    candidate = _candidate()
    attempts = []
    if rejected_first:
        attempts.append(
            QuestionAttempt(
                attempt_number=1, candidate=candidate,
                validations=_validations(mcq=MCQValidationResult(valid=False, exactly_four_answers=True, single_best_answer=False, reason="bad")),
            )
        )
    attempts.append(QuestionAttempt(attempt_number=len(attempts) + 1, candidate=candidate, validations=_validations()))
    return QuestionProductionResult(candidate=candidate, attempts=tuple(attempts))


def test_runner_records_accepted_first_attempt():
    producer = MagicMock()
    producer.produce_question.return_value = _production_result()
    runner = CandidateEvaluationRunner(producer=producer)
    plan = build_evaluation_plan([CATEGORY], 1)

    attempts, failures = runner.run(plan)

    assert len(attempts) == 1
    assert attempts[0].accepted is True
    assert failures == []


def test_runner_captures_question_text_only_for_accepted_attempts():
    producer = MagicMock()
    producer.produce_question.return_value = _production_result(rejected_first=True)
    runner = CandidateEvaluationRunner(producer=producer)
    plan = build_evaluation_plan([CATEGORY], 1)

    attempts, _ = runner.run(plan)

    assert attempts[0].accepted is False
    assert attempts[0].question_text is None
    assert attempts[0].answers is None
    assert attempts[1].accepted is True
    assert attempts[1].question_text == QUESTION_TEXT
    assert attempts[1].answers == ("תשובה א", "תשובה ב", "תשובה ג", "תשובה ד")
    assert attempts[1].correct_answer == 2


def test_runner_records_rejected_then_accepted():
    producer = MagicMock()
    producer.produce_question.return_value = _production_result(rejected_first=True)
    runner = CandidateEvaluationRunner(producer=producer)
    plan = build_evaluation_plan([CATEGORY], 1)

    attempts, failures = runner.run(plan)

    assert len(attempts) == 2
    assert attempts[0].accepted is False
    assert attempts[1].accepted is True


def test_runner_records_exhaustion_via_attempts_exhausted_error():
    candidate = _candidate()
    exhausted_attempts = (
        QuestionAttempt(attempt_number=1, candidate=candidate, validations=_validations(mcq=MCQValidationResult(valid=False, exactly_four_answers=True, single_best_answer=False, reason="bad"))),
    )
    producer = MagicMock()
    producer.produce_question.side_effect = QuestionAttemptsExhaustedError("exhausted", attempts=exhausted_attempts)
    runner = CandidateEvaluationRunner(producer=producer)
    plan = build_evaluation_plan([CATEGORY], 1)

    attempts, failures = runner.run(plan)

    assert len(attempts) == 1
    assert attempts[0].accepted is False
    assert failures == []


def test_runner_records_operational_failure_without_aborting():
    producer = MagicMock()
    producer.produce_question.side_effect = [
        LLMProviderError("connection failed"),
        _production_result(),
    ]
    runner = CandidateEvaluationRunner(producer=producer)
    plan = build_evaluation_plan([CATEGORY], 2)

    attempts, failures = runner.run(plan)

    assert len(failures) == 1
    assert failures[0].failure_type == "LLMProviderError"
    assert len(attempts) == 1
    assert attempts[0].question_position == 2


def test_runner_records_pydantic_validation_error_as_operational_failure():
    # A live baseline run (2026-08-04) showed this happening for real: the
    # OpenAI SDK's own structured-output parser can raise a raw
    # pydantic.ValidationError (e.g. an empty-string "reason" field)
    # before any project LLMError wrapping applies. The runner must record
    # this like any other operational failure, not crash the whole run.
    from pydantic import ValidationError

    from exam_generator.models import QualityValidationResult

    try:
        QualityValidationResult(valid=True, reason="")
    except ValidationError as exc:
        validation_error = exc
    else:  # pragma: no cover - defensive, should always raise
        raise AssertionError("expected a ValidationError")

    producer = MagicMock()
    producer.produce_question.side_effect = [validation_error, _production_result()]
    runner = CandidateEvaluationRunner(producer=producer)
    plan = build_evaluation_plan([CATEGORY], 2)

    attempts, failures = runner.run(plan)

    assert len(failures) == 1
    assert failures[0].failure_type == "ValidationError"
    assert len(attempts) == 1


def test_runner_propagates_unrecognized_exception():
    producer = MagicMock()
    producer.produce_question.side_effect = RuntimeError("truly unexpected")
    runner = CandidateEvaluationRunner(producer=producer)
    plan = build_evaluation_plan([CATEGORY], 1)

    with pytest.raises(RuntimeError, match="truly unexpected"):
        runner.run(plan)


# ---------------------------------------------------------------------------
# RetrievalEvaluationRunner
# ---------------------------------------------------------------------------


def _synthetic_index(texts: list[str]) -> tuple[FactualRetrievalIndex, FactualSourceCorpus]:
    chunks = [_chunk(text, chunk_id=f"STUDENT_SUMMARY:doc.pdf:{i:04d}:0001", page=i + 1) for i, text in enumerate(texts)]
    corpus = FactualSourceCorpus(chunks)
    index = FactualRetrievalIndex.from_corpus(corpus, source_type=SourceType.STUDENT_SUMMARY, top_k=8, ngram_range=(3, 5))
    return index, corpus


def test_retrieval_runner_hit():
    index, corpus = _synthetic_index(
        ["קליפת המוח אחראית לתפקודים גבוהים", "גזע המוח מחבר בין המוח לחוט השדרה", "מבנה כללי של מערכת העצבים"]
    )
    runner = RetrievalEvaluationRunner(index=index, corpus=corpus)
    query = RetrievalEvalQuery(query="קליפת המוח", expected_literal_term="קליפת המוח")

    results = runner.run([query], top_k=3)

    assert len(results) == 1
    assert results[0].hit_at_3 is True
    assert results[0].expected_chunk_ids == ("STUDENT_SUMMARY:doc.pdf:0000:0001",)


def test_retrieval_runner_miss():
    # Chunk 0 closely matches the query text; chunk 1 contains the expected
    # literal term but is textually unrelated to the query - with top_k=1,
    # chunk 1 (the only chunk satisfying "expected") cannot appear in the
    # results, giving a deterministic miss.
    index, corpus = _synthetic_index(
        [
            "קליפת המוח אחראית לתפקודים גבוהים כמו חשיבה ותכנון מורכב",
            "נושא נדיר לחלוטין שאינו קשור בכלל לשאלה שנשאלה כאן",
        ]
    )
    runner = RetrievalEvaluationRunner(index=index, corpus=corpus)
    query = RetrievalEvalQuery(query="קליפת המוח אחראית לתפקודים גבוהים", expected_literal_term="נושא נדיר לחלוטין")

    results = runner.run([query], top_k=1)

    assert len(results) == 1
    assert results[0].expected_chunk_ids == ("STUDENT_SUMMARY:doc.pdf:0001:0001",)
    assert results[0].hit_at_3 is False
    assert "STUDENT_SUMMARY:doc.pdf:0001:0001" not in results[0].retrieved_chunk_ids


def test_retrieval_runner_raises_on_ungrounded_fixture_entry():
    index, corpus = _synthetic_index(["טקסט כלשהו שאינו מכיל את המונח המבוקש"])
    runner = RetrievalEvaluationRunner(index=index, corpus=corpus)
    query = RetrievalEvalQuery(query="שאילתה", expected_literal_term="מונח שלא קיים בקורפוס בכלל")

    with pytest.raises(UngroundedRetrievalQueryError):
        runner.run([query])


# ---------------------------------------------------------------------------
# Report rendering
# ---------------------------------------------------------------------------


def test_render_markdown_report_produces_expected_sections():
    from datetime import datetime, timezone

    config = EvaluationConfig(
        provider="openai",
        model="gpt-4o-mini",
        generation_temperature=0.7,
        generation_max_tokens=800,
        validation_temperature=0.2,
        validation_max_tokens=500,
        chunk_size=1800,
        chunk_overlap=300,
        retrieval_top_k=8,
        retrieval_ngram_min=3,
        retrieval_ngram_max=5,
        max_generation_attempts=3,
        max_duplicate_replacement_attempts=2,
        canonical_categories=("A", "B"),
        evaluated_categories=("A",),
        questions_per_category_requested=2,
        baseline_type="REDUCED",
    )
    report = EvaluationReport(
        config=config,
        generated_at=datetime.now(timezone.utc),
        candidate_attempts=(_attempt_record(),),
    )

    markdown = render_markdown_report(report, human_quality_notes="looked fine", recommendations="do X next")

    assert "# WP-017 Evaluation Report" in markdown
    assert "## Acceptance Metrics" in markdown
    assert "## Validator Failure Metrics" in markdown
    assert "## Category Results" in markdown
    assert "## Retrieval Metrics" in markdown
    assert "## Operational/Provenance Failures" in markdown
    assert "looked fine" in markdown
    assert "do X next" in markdown
