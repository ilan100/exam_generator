"""Deterministic discovery/resolution of the project's configured PDF source
documents (student summaries and the course book).

Source classification lives here, at the discovery boundary, rather than
being inferred from arbitrary filename substrings inside the generic
``extract_pdf`` extractor.
"""

from __future__ import annotations

from pathlib import Path

from exam_generator.config.loader import find_project_root, load_app_config
from exam_generator.ingestion.models import ExtractedDocument
from exam_generator.ingestion.pdf import extract_pdf
from exam_generator.models import SourceType

DEFAULT_COURSE_BOOK_FILENAME = "course_book.pdf"


def _default_data_dir() -> Path:
    app_config = load_app_config()
    return find_project_root() / app_config.paths.data_dir


def discover_student_summary_pdfs(data_dir: Path | str | None = None) -> tuple[Path, ...]:
    """All student-summary PDFs in the data directory, in deterministic order.

    Every ``.pdf`` file in the directory is treated as a student summary
    except the configured course book; non-PDF files and directories are
    ignored. Results are sorted lexically by filename for determinism.
    """
    directory = Path(data_dir) if data_dir is not None else _default_data_dir()
    candidates = sorted(
        entry
        for entry in directory.iterdir()
        if entry.is_file()
        and entry.suffix.lower() == ".pdf"
        and entry.name != DEFAULT_COURSE_BOOK_FILENAME
    )
    return tuple(candidates)


def default_course_book_path(data_dir: Path | str | None = None) -> Path:
    """The configured default location of the course book."""
    directory = Path(data_dir) if data_dir is not None else _default_data_dir()
    return directory / DEFAULT_COURSE_BOOK_FILENAME


def load_student_summaries(data_dir: Path | str | None = None) -> tuple[ExtractedDocument, ...]:
    """Discover and extract all configured student-summary PDFs."""
    return tuple(
        extract_pdf(path, SourceType.STUDENT_SUMMARY)
        for path in discover_student_summary_pdfs(data_dir)
    )


def load_course_book(data_dir: Path | str | None = None) -> ExtractedDocument:
    """Resolve and extract the configured course book.

    Raises ``PdfNotFoundError`` (via ``extract_pdf``) if it is missing.
    """
    return extract_pdf(default_course_book_path(data_dir), SourceType.COURSE_BOOK)
