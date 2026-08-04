"""Control-layer result contracts for WP-014's exam orchestration.

These wrap the existing, unmodified ``ExamRequest``/``ExamOutput``/
``CandidateQuestion`` (WP-002) and ``QuestionProductionResult`` (WP-013)
contracts; they do not replace or redesign any of them, and they carry no
final-audit-serialization fields - that remains a later output-focused WP.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from exam_generator.models import ExamOutput, GenerationMode
from exam_generator.models._common import NonBlankStr, NonNegativeIntStrict, PositiveIntStrict
from exam_generator.production import QuestionProductionResult


class PlannedQuestion(BaseModel):
    """One deterministically-planned exam question slot: a global 1-based
    position (directly reusable as the final ``ExamQuestion.number``), its
    canonical category, and its assigned generation mode."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    position: PositiveIntStrict
    category: NonBlankStr
    generation_mode: GenerationMode


class QuestionProductionRecord(BaseModel):
    """One planned question's successful production outcome: the plan
    entry it fulfills, WP-013's full production result (accepted candidate
    plus every attempt that led to it), and how many exam-level duplicate
    replacements were needed before this result was accepted. Preserved
    for future audit assembly (WP-015+)."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    planned: PlannedQuestion
    production: QuestionProductionResult
    duplicate_replacement_attempts: NonNegativeIntStrict


class ExamGenerationResult(BaseModel):
    """The outcome of one successful WP-014 orchestration run: the
    completed clean exam, the plan that produced it, and the full
    per-question production history needed for future audit assembly.
    Never constructed for a partial/incomplete exam."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    exam: ExamOutput
    plan: tuple[PlannedQuestion, ...]
    productions: tuple[QuestionProductionRecord, ...]
