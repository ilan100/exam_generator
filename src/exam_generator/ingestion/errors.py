"""Domain-specific exceptions for PDF source-document ingestion.

Callers should never need to interpret raw PyMuPDF exceptions for expected
ingestion failures.
"""

from __future__ import annotations


class PdfIngestionError(Exception):
    """Base class for all PDF ingestion failures."""


class PdfNotFoundError(PdfIngestionError):
    """The PDF path does not exist or is not a regular file."""


class PdfFormatError(PdfIngestionError):
    """The file cannot be opened as a valid PDF, or has zero pages."""


class PdfEncryptedError(PdfIngestionError):
    """The PDF is encrypted/password-protected and cannot be read."""


class PdfTextExtractionError(PdfIngestionError):
    """No usable text could be extracted from the document."""
