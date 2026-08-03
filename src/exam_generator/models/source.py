"""Factual source evidence and the structurally separate historical style
reference.

Architectural boundary (see docs/ARCHITECTURE.md):

- ``SourceEvidenceChunk`` (student summary / course book) is factual
  grounding material.
- ``HistoricalStyleReference`` is a style/structure reference only and must
  never be exposed as, or mixed into, factual grounding evidence.
"""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, ConfigDict, Field

from exam_generator.models._common import CorrectAnswerId, NonBlankStr, PositiveIntStrict


class SourceType(str, Enum):
    """Factual source types. Historical exam questions are intentionally not
    a member of this enum - see ``HistoricalStyleReference``."""

    STUDENT_SUMMARY = "STUDENT_SUMMARY"
    COURSE_BOOK = "COURSE_BOOK"


class SourceEvidenceChunk(BaseModel):
    """A chunk of factual source text produced by future ingestion/retrieval."""

    model_config = ConfigDict(extra="forbid")

    chunk_id: NonBlankStr
    source_file: NonBlankStr
    page: PositiveIntStrict
    text: NonBlankStr
    source_type: SourceType


class HistoricalStyleReference(BaseModel):
    """A historical exam question used only as a style/structure reference.

    Deliberately does not inherit from ``SourceEvidenceChunk``: historical
    questions must never be usable as factual grounding evidence.
    """

    model_config = ConfigDict(extra="forbid")

    historical_question_id: PositiveIntStrict
    category: NonBlankStr
    question: NonBlankStr
    answers: list[NonBlankStr] = Field(min_length=4, max_length=4)
    correct_answer: CorrectAnswerId
