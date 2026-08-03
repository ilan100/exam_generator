"""Deterministic PDF text extraction into page-aware extracted documents.

Uses PyMuPDF (``pymupdf``) for extraction. PyMuPDF was selected over
alternatives (see docs/PROJECT_STATUS.md for the comparison) because it
returns Hebrew/RTL text in correct logical reading order - some alternatives
(e.g. pypdf/pdfminer-based extraction) return Hebrew visually reversed - and
because it is significantly faster on this project's real source PDFs.
"""

from __future__ import annotations

from pathlib import Path

import pymupdf

from exam_generator.ingestion.errors import (
    PdfEncryptedError,
    PdfFormatError,
    PdfNotFoundError,
    PdfTextExtractionError,
)
from exam_generator.ingestion.models import ExtractedDocument, ExtractedPage
from exam_generator.models import SourceType


def extract_pdf(path: Path | str, source_type: SourceType) -> ExtractedDocument:
    """Extract one PDF into a page-aware ``ExtractedDocument``.

    ``source_type`` is a required, explicit parameter so the source role
    (``STUDENT_SUMMARY`` vs. ``COURSE_BOOK``) can never be silently forgotten
    or guessed from the filename by this generic extractor.
    """
    pdf_path = Path(path)

    if not pdf_path.exists():
        raise PdfNotFoundError(f"PDF not found: {pdf_path}")
    if not pdf_path.is_file():
        raise PdfNotFoundError(f"PDF path is not a file: {pdf_path}")

    try:
        # filetype="pdf" forces strict PDF parsing regardless of the path's
        # extension - PyMuPDF otherwise auto-detects format from the
        # extension and will happily "open" e.g. a .txt file as a one-page
        # text document instead of failing.
        document = pymupdf.open(pdf_path, filetype="pdf")
    except (pymupdf.FileDataError, pymupdf.FileNotFoundError, pymupdf.EmptyFileError) as exc:
        raise PdfFormatError(f"Could not open PDF {pdf_path}: {exc}") from exc

    if document.is_encrypted and not document.authenticate(""):
        raise PdfEncryptedError(f"PDF is encrypted and cannot be read: {pdf_path}")

    if document.page_count == 0:
        raise PdfFormatError(f"PDF has zero pages: {pdf_path}")

    pages: list[ExtractedPage] = []
    for index in range(document.page_count):
        try:
            text = document[index].get_text()
        except RuntimeError as exc:
            raise PdfTextExtractionError(
                f"Failed to extract text from {pdf_path.name} page {index + 1}: {exc}"
            ) from exc
        pages.append(ExtractedPage(page=index + 1, text=text))

    if not any(page.text.strip() for page in pages):
        raise PdfTextExtractionError(
            f"No usable text could be extracted from {pdf_path.name} "
            f"({document.page_count} pages, all empty)"
        )

    return ExtractedDocument(
        source_file=pdf_path.name,
        source_type=source_type,
        pages=tuple(pages),
    )
