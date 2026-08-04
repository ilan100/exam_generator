"""Deterministic construction of the final ``ExamAudit`` (WP-002) from a
successful WP-014 ``ExamGenerationResult``.

Zero LLM calls: this is a pure transformation over information the system
already produced and independently validated during generation/production/
orchestration. Nothing here asks a model what evidence it used, infers
missing provenance from question text, or fabricates a value merely to
satisfy a required field - see the module-level "Decisions Made (WP-015)"
notes in docs/PROJECT_STATUS.md for the specific, deliberate gaps
(``historical_reference_id``, ``evidence``) this WP represents as honestly
absent rather than invents.
"""

from __future__ import annotations

from datetime import datetime

from exam_generator.config import LLMConfig
from exam_generator.models import ExamAudit, QuestionAttemptAudit, QuestionAudit
from exam_generator.orchestration import ExamGenerationResult, QuestionProductionRecord
from exam_generator.output.errors import AuditConsistencyError
from exam_generator.production import QuestionAttempt


def _build_question_attempt_audit(attempt: QuestionAttempt) -> QuestionAttemptAudit:
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


def _build_question_audit(record: QuestionProductionRecord, *, diversity_target: float) -> QuestionAudit:
    attempts = tuple(_build_question_attempt_audit(attempt) for attempt in record.production.attempts)
    # QuestionProducer (WP-013) always stops at the first accepted attempt, so
    # the last attempt is always the one that determined this question's
    # final content - its validation results are this question's "final"
    # results, matching QuestionAudit's own pre-WP-015 field semantics.
    final_attempt = record.production.attempts[-1]
    final_validations = final_attempt.validations

    return QuestionAudit(
        number=record.planned.position,
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


def _validate_consistency(generation_result: ExamGenerationResult, audit: ExamAudit) -> None:
    """Fail clearly (WP-015 section 15) rather than silently accept a
    mismatched/tampered ``ExamGenerationResult``. Under normal use (an
    ``ExamGenerationResult`` produced by ``ExamOrchestrator.generate_exam()``
    and never hand-modified), this always passes by construction."""
    exam_questions = generation_result.exam.questions
    productions = generation_result.productions

    if len(exam_questions) != len(productions) or len(exam_questions) != len(audit.questions):
        raise AuditConsistencyError(
            f"Question count mismatch: exam has {len(exam_questions)} question(s), "
            f"production history has {len(productions)}, audit has {len(audit.questions)}"
        )

    for exam_question, record, question_audit in zip(exam_questions, productions, audit.questions):
        candidate = record.production.candidate

        if not (exam_question.number == record.planned.position == question_audit.number):
            raise AuditConsistencyError(
                f"Question number mismatch: exam={exam_question.number}, "
                f"planned={record.planned.position}, audit={question_audit.number}"
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


def build_exam_audit(
    generation_result: ExamGenerationResult,
    *,
    exam_id: str,
    generated_at: datetime,
    llm_config: LLMConfig,
    diversity_target: float,
) -> ExamAudit:
    """Deterministically build the final ``ExamAudit`` for a successful
    ``ExamGenerationResult``.

    Every input beyond ``generation_result`` itself is caller-supplied
    (exam identity/timestamp, LLM provider/model provenance, and the
    configured diversity target) rather than invented here, so the
    transformation is fully deterministic given identical inputs. Makes
    zero LLM calls - ``llm_config`` is plain configuration data (no API
    key, no live provider), never a real ``LLMProvider``/client.

    Raises ``AuditConsistencyError`` if the constructed audit does not
    correspond exactly to ``generation_result.exam`` - never silently
    repairs a mismatch.
    """
    questions = [
        _build_question_audit(record, diversity_target=diversity_target)
        for record in generation_result.productions
    ]
    audit = ExamAudit(
        exam_id=exam_id,
        generated_at=generated_at,
        provider=llm_config.provider,
        model=llm_config.model,
        questions=questions,
    )
    _validate_consistency(generation_result, audit)
    return audit
