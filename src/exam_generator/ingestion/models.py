"""Extraction-layer domain models: one extracted page, and one extracted
source document.

Deliberately distinct from ``SourceEvidenceChunk`` (WP-002), which represents
material after future chunking/retrieval processing. Nothing here is, or is
automatically convertible into, factual grounding evidence.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, field_validator

from exam_generator.models import SourceType
from exam_generator.models._common import NonBlankStr, PositiveIntStrict


class ExtractedPage(BaseModel):
    """One physically-extracted PDF page.

    ``text`` may legitimately be empty (a genuine blank PDF page); only a
    whole document containing no usable text anywhere fails ingestion - see
    ``exam_generator.ingestion.pdf.extract_pdf``.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    page: PositiveIntStrict
    text: str


class ExtractedDocument(BaseModel):
    """A successfully extracted source PDF, with page-level provenance."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    source_file: NonBlankStr
    source_type: SourceType
    pages: tuple[ExtractedPage, ...] = Field(min_length=1)

    @field_validator("pages")
    @classmethod
    def _pages_are_contiguous_in_physical_order(
        cls, value: tuple[ExtractedPage, ...]
    ) -> tuple[ExtractedPage, ...]:
        numbers = [page.page for page in value]
        expected = list(range(1, len(numbers) + 1))
        if numbers != expected:
            raise ValueError(
                "page numbers must be contiguous 1..N in physical PDF order, "
                f"got {numbers}"
            )
        return value
