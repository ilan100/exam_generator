"""Domain-specific exceptions for historical-workbook ingestion.

Callers should never need to interpret raw openpyxl/zipfile exceptions for
expected ingestion failures.
"""

from __future__ import annotations


class HistoricalIngestionError(Exception):
    """Base class for all historical-workbook ingestion failures."""


class WorkbookNotFoundError(HistoricalIngestionError):
    """The workbook path does not exist or is not a regular file."""


class WorkbookFormatError(HistoricalIngestionError):
    """The workbook cannot be opened, or a worksheet cannot be selected."""


class WorkbookSchemaError(HistoricalIngestionError):
    """The workbook's header row does not satisfy the required column contract,
    or the worksheet contains no valid question rows."""


class HistoricalQuestionRowError(HistoricalIngestionError):
    """A specific worksheet row failed row-level validation."""
