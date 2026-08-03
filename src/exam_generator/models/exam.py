"""Top-level exam request and clean exam output contracts."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, field_validator

from exam_generator.models._common import NonBlankStr, PositiveIntStrict
from exam_generator.models.question import ExamQuestion


class ExamRequest(BaseModel):
    """Structural contract for an exam-generation request.

    Validates structure only: category names are checked for non-emptiness
    and requested counts for strict positivity, but whether a category name
    is a *known* canonical category is not checked here (that requires the
    historical-Excel-derived category list from a later Work Package).
    """

    model_config = ConfigDict(extra="forbid")

    categories: dict[NonBlankStr, PositiveIntStrict] = Field(min_length=1)


class ExamOutput(BaseModel):
    """The V1 clean exam output contract: ``{"questions": [...]}``.

    Contains only clean question content, no audit/traceability information.
    """

    model_config = ConfigDict(extra="forbid")

    questions: list[ExamQuestion] = Field(min_length=1)

    @field_validator("questions")
    @classmethod
    def _numbers_form_contiguous_sequence(cls, value: list[ExamQuestion]) -> list[ExamQuestion]:
        numbers = sorted(question.number for question in value)
        expected = list(range(1, len(numbers) + 1))
        if numbers != expected:
            raise ValueError(
                "question numbers must be unique and form the contiguous sequence "
                f"1..{len(numbers)}, got {numbers}"
            )
        return value
