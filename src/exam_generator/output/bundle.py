"""Combines the clean exam already present on a successful
``ExamGenerationResult`` with its deterministically-built audit into one
``ExamOutputBundle`` - the WP-015 output boundary's single entry point."""

from __future__ import annotations

from datetime import datetime

from exam_generator.config import LLMConfig
from exam_generator.orchestration import ExamGenerationResult
from exam_generator.output.audit import build_exam_audit
from exam_generator.output.models import ExamOutputBundle


def build_exam_output_bundle(
    generation_result: ExamGenerationResult,
    *,
    exam_id: str,
    generated_at: datetime,
    llm_config: LLMConfig,
    diversity_target: float,
) -> ExamOutputBundle:
    """Build the paired clean-exam/audit output for a successful
    ``ExamGenerationResult``.

    The clean exam is ``generation_result.exam`` itself - already the
    established WP-002 ``ExamOutput`` contract, never rebuilt or
    hand-assembled here. The audit is built by ``build_exam_audit()``,
    which also verifies the two correspond exactly
    (``AuditConsistencyError`` otherwise). Makes zero LLM calls.
    """
    audit = build_exam_audit(
        generation_result,
        exam_id=exam_id,
        generated_at=generated_at,
        llm_config=llm_config,
        diversity_target=diversity_target,
    )
    return ExamOutputBundle(exam=generation_result.exam, audit=audit)
