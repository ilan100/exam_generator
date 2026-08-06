"""Deterministic construction of the final ``ExamAudit`` (WP-002) from an
``ExamGenerationResult`` (WP-014) that safely reached the end of its plan.

Zero LLM calls: this is a pure transformation over information the system
already produced and independently validated during generation/production/
orchestration. Nothing here asks a model what evidence it used, infers
missing provenance from question text, or fabricates a value merely to
satisfy a required field - see the module-level "Decisions Made (WP-015)"
notes in docs/PROJECT_STATUS.md for the specific, deliberate gaps
(``historical_reference_id``, ``evidence``) this WP represents as honestly
absent rather than invents.

Since WP-023, ``generation_result`` may be ``PARTIAL`` (one or more
planned questions failed for a question-local reason) - each failed
planned question is represented honestly, via ``FailedQuestionAudit``,
using whatever attempt history actually exists.
"""

from __future__ import annotations

from datetime import datetime

from exam_generator.config import LLMConfig
from exam_generator.models import ExamAudit, FailedQuestionAudit, QuestionAttemptAudit, QuestionAudit
from exam_generator.orchestration import ExamGenerationResult, FailedPlannedQuestion, QuestionProductionRecord
from exam_generator.output.errors import AuditConsistencyError
from exam_generator.production import QuestionAttempt


def _build_question_attempt_audit(attempt: QuestionAttempt) -> QuestionAttemptAudit:
    if attempt.validations is None:
        # WP-019: a recoverable generation-contract failure never reached
        # any validator - represented honestly, with no fabricated
        # candidate or validation results.
        return QuestionAttemptAudit(
            attempt_number=attempt.attempt_number,
            accepted=False,
            generation_failure_type=attempt.generation_failure_type,
            generation_failure_message=attempt.generation_failure_message,
        )
    validations = attempt.validations
    return QuestionAttemptAudit(
        attempt_number=attempt.attempt_number,
        accepted=attempt.accepted,
        grounding=validations.grounding,
        mcq_validation=validations.mcq,
        category_validation=validations.category,
        quality_validation=validations.quality,
        textbook_check=validations.textbook,
    )


def _build_question_audit(record: QuestionProductionRecord, *, number: int, diversity_target: float) -> QuestionAudit:
    attempts = tuple(_build_question_attempt_audit(attempt) for attempt in record.production.attempts)
    # QuestionProducer (WP-013) always stops at the first accepted attempt, so
    # the last attempt is always the one that determined this question's
    # final content - its validation results are this question's "final"
    # results, matching QuestionAudit's own pre-WP-015 field semantics.
    final_attempt = record.production.attempts[-1]
    final_validations = final_attempt.validations

    return QuestionAudit(
        number=number,
        # WP-023: the plan position this question was originally assigned,
        # distinct from ``number`` (the final, contiguous clean-exam
        # number) once a failed planned question elsewhere in the plan
        # makes the two diverge.
        planned_position=record.planned.position,
        category=record.planned.category,
        generation_mode=record.production.candidate.generation_mode,
        # Genuinely unavailable from current production history: WP-009
        # deliberately validates, then discards, any claimed
        # historical_reference_id rather than persisting it onto
        # CandidateQuestion - see docs/PROJECT_STATUS.md "Decisions Made
        # (WP-015)". Represented honestly as absent, per WP-015 section 9,
        # rather than inferred/fabricated.
        historical_reference_id=None,
        grounding=final_validations.grounding,
        # Genuinely unavailable: QuestionGenerator retrieves student-summary
        # evidence internally but never returns the chunks it used to the
        # caller - see docs/PROJECT_STATUS.md "Decisions Made (WP-015)".
        # Grounding-evidence identity (evidence_chunk_ids/evidence_text) IS
        # preserved, nested inside each attempt's own grounding result.
        evidence=[],
        mcq_validation=final_validations.mcq,
        category_validation=final_validations.category,
        quality_validation=final_validations.quality,
        textbook_check=final_validations.textbook,
        generation_attempts=len(attempts),
        diversity_target=diversity_target,
        attempts=list(attempts),
    )


def _build_failed_question_audit(failed: FailedPlannedQuestion) -> FailedQuestionAudit:
    attempts = tuple(_build_question_attempt_audit(attempt) for attempt in failed.attempts)
    return FailedQuestionAudit(
        planned_position=failed.planned.position,
        category=failed.planned.category,
        generation_mode=failed.planned.generation_mode,
        failure_type=failed.failure_type,
        failure_message=failed.failure_message,
        attempts=list(attempts),
    )


def _validate_consistency(generation_result: ExamGenerationResult, audit: ExamAudit) -> None:
    """Fail clearly (WP-015 section 15) rather than silently accept a
    mismatched/tampered ``ExamGenerationResult``. Under normal use (an
    ``ExamGenerationResult`` produced by ``ExamOrchestrator.generate_exam()``
    and never hand-modified), this always passes by construction."""
    exam_questions = generation_result.exam.questions if generation_result.exam is not None else []
    productions = generation_result.productions

    if len(exam_questions) != len(productions) or len(exam_questions) != len(audit.questions):
        raise AuditConsistencyError(
            f"Question count mismatch: exam has {len(exam_questions)} question(s), "
            f"production history has {len(productions)}, audit has {len(audit.questions)}"
        )
    if len(generation_result.failed_questions) != len(audit.failed_questions):
        raise AuditConsistencyError(
            f"Failed-question count mismatch: generation result has "
            f"{len(generation_result.failed_questions)}, audit has {len(audit.failed_questions)}"
        )

    for exam_question, record, question_audit in zip(exam_questions, productions, audit.questions):
        candidate = record.production.candidate

        if exam_question.number != question_audit.number:
            raise AuditConsistencyError(
                f"Question number mismatch: exam={exam_question.number}, audit={question_audit.number}"
            )
        if question_audit.planned_position != record.planned.position:
            raise AuditConsistencyError(
                f"Planned-position mismatch for question {exam_question.number}: "
                f"production={record.planned.position}, audit={question_audit.planned_position}"
            )
        if not (exam_question.category == record.planned.category == question_audit.category):
            raise AuditConsistencyError(
                f"Category mismatch for question {exam_question.number}: "
                f"exam={exam_question.category!r}, planned={record.planned.category!r}, "
                f"audit={question_audit.category!r}"
            )
        if exam_question.question != candidate.question:
            raise AuditConsistencyError(f"Question text mismatch for question {exam_question.number}")
        if (
            exam_question.answer1,
            exam_question.answer2,
            exam_question.answer3,
            exam_question.answer4,
        ) != tuple(candidate.answers):
            raise AuditConsistencyError(f"Answer choices mismatch for question {exam_question.number}")
        if exam_question.correct_answer != candidate.correct_answer:
            raise AuditConsistencyError(f"Correct-answer mismatch for question {exam_question.number}")
        if not record.production.attempts[-1].accepted:
            raise AuditConsistencyError(
                f"Question {exam_question.number}'s final production attempt is not accepted - "
                "a rejected candidate must never be represented as a completed exam question"
            )

    for failed, failed_audit in zip(generation_result.failed_questions, audit.failed_questions):
        if failed_audit.planned_position != failed.planned.position:
            raise AuditConsistencyError(
                f"Planned-position mismatch for a failed question: "
                f"result={failed.planned.position}, audit={failed_audit.planned_position}"
            )
        if failed_audit.category != failed.planned.category:
            raise AuditConsistencyError(
                f"Category mismatch for failed question {failed.planned.position}: "
                f"result={failed.planned.category!r}, audit={failed_audit.category!r}"
            )
        if failed_audit.generation_mode != failed.planned.generation_mode:
            raise AuditConsistencyError(
                f"Generation-mode mismatch for failed question {failed.planned.position}"
            )


def build_exam_audit(
    generation_result: ExamGenerationResult,
    *,
    exam_id: str,
    generated_at: datetime,
    llm_config: LLMConfig,
    diversity_target: float,
) -> ExamAudit:
    """Deterministically build the final ``ExamAudit`` for an
    ``ExamGenerationResult`` that safely reached the end of its plan
    (``COMPLETE`` or, since WP-023, ``PARTIAL``).

    Every input beyond ``generation_result`` itself is caller-supplied
    (exam identity/timestamp, LLM provider/model provenance, and the
    configured diversity target) rather than invented here, so the
    transformation is fully deterministic given identical inputs. Makes
    zero LLM calls - ``llm_config`` is plain configuration data (no API
    key, no live provider), never a real ``LLMProvider``/client.

    Raises ``AuditConsistencyError`` if the constructed audit does not
    correspond exactly to ``generation_result`` - never silently repairs a
    mismatch.
    """
    questions = [
        _build_question_audit(record, number=number, diversity_target=diversity_target)
        for number, record in enumerate(generation_result.productions, start=1)
    ]
    failed_questions = [
        _build_failed_question_audit(failed) for failed in generation_result.failed_questions
    ]
    audit = ExamAudit(
        exam_id=exam_id,
        generated_at=generated_at,
        provider=llm_config.provider,
        model=llm_config.model,
        status=generation_result.status,
        planned_question_count=len(generation_result.plan),
        accepted_count=len(questions),
        failed_count=len(failed_questions),
        questions=questions,
        failed_questions=failed_questions,
    )
    _validate_consistency(generation_result, audit)
    return audit
