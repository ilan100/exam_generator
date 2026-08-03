from pathlib import Path

import pymupdf
import pytest
from pydantic import ValidationError

from exam_generator.ingestion import (
    ExtractedDocument,
    ExtractedPage,
    PdfEncryptedError,
    PdfFormatError,
    PdfNotFoundError,
    PdfTextExtractionError,
    default_course_book_path,
    discover_student_summary_pdfs,
    extract_pdf,
    load_course_book,
    load_student_summaries,
)
from exam_generator.models import HistoricalStyleReference, SourceEvidenceChunk, SourceType

HEBREW_TEXT = "איזה מבנה קשור ל-Corona radiata בדוגמה זו?"


def make_pdf(tmp_path: Path, texts: list[str | None], filename: str = "doc.pdf") -> Path:
    """Build a small synthetic PDF with one page per entry in ``texts``.

    A ``None``/empty entry produces a genuinely blank page (no text
    inserted). Uses PyMuPDF itself, so no extra test-only dependency or
    committed binary fixture is needed.
    """
    document = pymupdf.open()
    for text in texts:
        page = document.new_page()
        if text:
            page.insert_text((72, 72), text)
    path = tmp_path / filename
    document.save(path)
    document.close()
    return path


def make_encrypted_pdf(tmp_path: Path, filename: str = "encrypted.pdf") -> Path:
    document = pymupdf.open()
    page = document.new_page()
    page.insert_text((72, 72), "secret content")
    path = tmp_path / filename
    document.save(path, encryption=pymupdf.PDF_ENCRYPT_AES_256, user_pw="secret", owner_pw="owner-secret")
    document.close()
    return path


# ---------------------------------------------------------------------------
# Extracted models
# ---------------------------------------------------------------------------


def test_valid_extracted_page_accepted():
    page = ExtractedPage(page=1, text="hello")
    assert page.page == 1


def test_extracted_page_zero_rejected():
    with pytest.raises(ValidationError):
        ExtractedPage(page=0, text="hello")


def test_extracted_page_negative_rejected():
    with pytest.raises(ValidationError):
        ExtractedPage(page=-1, text="hello")


def test_extracted_page_boolean_rejected():
    with pytest.raises(ValidationError):
        ExtractedPage(page=True, text="hello")


def test_extracted_page_hebrew_text_accepted():
    page = ExtractedPage(page=1, text=HEBREW_TEXT)
    assert page.text == HEBREW_TEXT


def test_extracted_page_mixed_hebrew_english_accepted():
    text = "המסילה עוברת דרך ה-Corona radiata"
    page = ExtractedPage(page=1, text=text)
    assert page.text == text


def test_valid_student_summary_document_accepted():
    doc = ExtractedDocument(
        source_file="student_summary_1.pdf",
        source_type=SourceType.STUDENT_SUMMARY,
        pages=(ExtractedPage(page=1, text="x"),),
    )
    assert doc.source_type == SourceType.STUDENT_SUMMARY


def test_valid_course_book_document_accepted():
    doc = ExtractedDocument(
        source_file="course_book.pdf",
        source_type=SourceType.COURSE_BOOK,
        pages=(ExtractedPage(page=1, text="x"),),
    )
    assert doc.source_type == SourceType.COURSE_BOOK


def test_document_requires_at_least_one_page():
    with pytest.raises(ValidationError):
        ExtractedDocument(source_file="a.pdf", source_type=SourceType.STUDENT_SUMMARY, pages=())


def test_document_page_sequence_must_be_contiguous():
    with pytest.raises(ValidationError):
        ExtractedDocument(
            source_file="a.pdf",
            source_type=SourceType.STUDENT_SUMMARY,
            pages=(ExtractedPage(page=1, text="x"), ExtractedPage(page=3, text="y")),
        )


def test_document_page_order_is_preserved():
    doc = ExtractedDocument(
        source_file="a.pdf",
        source_type=SourceType.STUDENT_SUMMARY,
        pages=(ExtractedPage(page=1, text="one"), ExtractedPage(page=2, text="two")),
    )
    assert [p.text for p in doc.pages] == ["one", "two"]


def test_document_pages_cannot_be_mutated():
    doc = ExtractedDocument(
        source_file="a.pdf",
        source_type=SourceType.STUDENT_SUMMARY,
        pages=(ExtractedPage(page=1, text="one"),),
    )
    with pytest.raises(TypeError):
        doc.pages[0] = ExtractedPage(page=1, text="changed")
    with pytest.raises(ValidationError):
        doc.pages = (ExtractedPage(page=1, text="changed"),)


# ---------------------------------------------------------------------------
# PDF extraction
# ---------------------------------------------------------------------------


def test_valid_one_page_pdf_extracts(tmp_path):
    path = make_pdf(tmp_path, ["hello world"])
    doc = extract_pdf(path, SourceType.STUDENT_SUMMARY)
    assert len(doc.pages) == 1
    assert "hello world" in doc.pages[0].text


def test_valid_multi_page_pdf_extracts(tmp_path):
    path = make_pdf(tmp_path, ["page one", "page two", "page three"])
    doc = extract_pdf(path, SourceType.STUDENT_SUMMARY)
    assert len(doc.pages) == 3


def test_physical_page_order_is_preserved(tmp_path):
    path = make_pdf(tmp_path, ["first", "second", "third"])
    doc = extract_pdf(path, SourceType.STUDENT_SUMMARY)
    assert "first" in doc.pages[0].text
    assert "second" in doc.pages[1].text
    assert "third" in doc.pages[2].text


def test_public_page_numbers_are_one_based(tmp_path):
    path = make_pdf(tmp_path, ["a", "b"])
    doc = extract_pdf(path, SourceType.STUDENT_SUMMARY)
    assert [p.page for p in doc.pages] == [1, 2]


def test_source_filename_is_preserved(tmp_path):
    path = make_pdf(tmp_path, ["a"], filename="my_summary.pdf")
    doc = extract_pdf(path, SourceType.STUDENT_SUMMARY)
    assert doc.source_file == "my_summary.pdf"


def test_student_summary_source_type_is_preserved(tmp_path):
    path = make_pdf(tmp_path, ["a"])
    doc = extract_pdf(path, SourceType.STUDENT_SUMMARY)
    assert doc.source_type == SourceType.STUDENT_SUMMARY


def test_course_book_source_type_is_preserved(tmp_path):
    path = make_pdf(tmp_path, ["a"])
    doc = extract_pdf(path, SourceType.COURSE_BOOK)
    assert doc.source_type == SourceType.COURSE_BOOK


def test_english_extraction_works(tmp_path):
    path = make_pdf(tmp_path, ["Corona radiata and Medulla Oblongata"])
    doc = extract_pdf(path, SourceType.COURSE_BOOK)
    assert "Corona radiata" in doc.pages[0].text
    assert "Medulla Oblongata" in doc.pages[0].text


def test_repeated_extraction_is_deterministic(tmp_path):
    path = make_pdf(tmp_path, ["one", "two"])
    doc1 = extract_pdf(path, SourceType.STUDENT_SUMMARY)
    doc2 = extract_pdf(path, SourceType.STUDENT_SUMMARY)
    assert doc1 == doc2


# ---------------------------------------------------------------------------
# File failures
# ---------------------------------------------------------------------------


def test_missing_pdf_path_fails_clearly(tmp_path):
    with pytest.raises(PdfNotFoundError):
        extract_pdf(tmp_path / "does_not_exist.pdf", SourceType.STUDENT_SUMMARY)


def test_directory_instead_of_pdf_fails_clearly(tmp_path):
    with pytest.raises(PdfNotFoundError):
        extract_pdf(tmp_path, SourceType.STUDENT_SUMMARY)


def test_obvious_non_pdf_file_fails_clearly(tmp_path):
    bad = tmp_path / "notes.txt"
    bad.write_text("just a plain text file, not a pdf", encoding="utf-8")
    with pytest.raises(PdfFormatError):
        extract_pdf(bad, SourceType.STUDENT_SUMMARY)


def test_corrupt_pdf_fails_clearly(tmp_path):
    bad = tmp_path / "corrupt.pdf"
    bad.write_text("this is not a real pdf file" * 20, encoding="utf-8")
    with pytest.raises(PdfFormatError):
        extract_pdf(bad, SourceType.STUDENT_SUMMARY)


def test_no_usable_text_document_fails(tmp_path):
    path = make_pdf(tmp_path, [None, None])
    with pytest.raises(PdfTextExtractionError):
        extract_pdf(path, SourceType.STUDENT_SUMMARY)


def test_encrypted_pdf_fails_clearly(tmp_path):
    path = make_encrypted_pdf(tmp_path)
    with pytest.raises(PdfEncryptedError):
        extract_pdf(path, SourceType.STUDENT_SUMMARY)


# ---------------------------------------------------------------------------
# Blank pages
# ---------------------------------------------------------------------------


def test_blank_page_does_not_renumber_later_pages(tmp_path):
    path = make_pdf(tmp_path, ["first", None, "third"])
    doc = extract_pdf(path, SourceType.STUDENT_SUMMARY)
    assert [p.page for p in doc.pages] == [1, 2, 3]


def test_page_provenance_correct_across_blank_pages(tmp_path):
    path = make_pdf(tmp_path, ["first", None, "third"])
    doc = extract_pdf(path, SourceType.STUDENT_SUMMARY)
    assert doc.pages[1].text.strip() == ""
    assert "first" in doc.pages[0].text
    assert "third" in doc.pages[2].text


def test_document_with_text_plus_blank_page_succeeds(tmp_path):
    path = make_pdf(tmp_path, ["useful content", None])
    doc = extract_pdf(path, SourceType.STUDENT_SUMMARY)
    assert len(doc.pages) == 2


def test_document_with_no_usable_text_fails(tmp_path):
    path = make_pdf(tmp_path, [None, None, None])
    with pytest.raises(PdfTextExtractionError):
        extract_pdf(path, SourceType.STUDENT_SUMMARY)


# ---------------------------------------------------------------------------
# Source discovery
# ---------------------------------------------------------------------------


def _touch(path: Path, content: bytes = b"") -> Path:
    path.write_bytes(content)
    return path


def test_intended_student_summary_pdfs_are_discovered(tmp_path):
    make_pdf(tmp_path, ["a"], filename="summary_a.pdf")
    make_pdf(tmp_path, ["b"], filename="summary_b.pdf")
    found = discover_student_summary_pdfs(tmp_path)
    assert {p.name for p in found} == {"summary_a.pdf", "summary_b.pdf"}


def test_course_book_excluded_from_student_summary_discovery(tmp_path):
    make_pdf(tmp_path, ["a"], filename="summary_a.pdf")
    make_pdf(tmp_path, ["c"], filename="course_book.pdf")
    found = discover_student_summary_pdfs(tmp_path)
    assert "course_book.pdf" not in {p.name for p in found}


def test_non_pdf_files_are_ignored_in_discovery(tmp_path):
    make_pdf(tmp_path, ["a"], filename="summary_a.pdf")
    _touch(tmp_path / "notes.txt", b"not a pdf")
    found = discover_student_summary_pdfs(tmp_path)
    assert {p.name for p in found} == {"summary_a.pdf"}


def test_directories_are_ignored_in_discovery(tmp_path):
    make_pdf(tmp_path, ["a"], filename="summary_a.pdf")
    (tmp_path / "subdir.pdf").mkdir()
    found = discover_student_summary_pdfs(tmp_path)
    assert {p.name for p in found} == {"summary_a.pdf"}


def test_student_summary_discovery_ordering_is_deterministic(tmp_path):
    make_pdf(tmp_path, ["a"], filename="zeta.pdf")
    make_pdf(tmp_path, ["b"], filename="alpha.pdf")
    found = discover_student_summary_pdfs(tmp_path)
    assert [p.name for p in found] == ["alpha.pdf", "zeta.pdf"]


def test_course_book_resolution_produces_course_book_source_type(tmp_path):
    make_pdf(tmp_path, ["a"], filename="course_book.pdf")
    doc = load_course_book(tmp_path)
    assert doc.source_type == SourceType.COURSE_BOOK


def test_missing_course_book_fails_clearly_when_requested(tmp_path):
    with pytest.raises(PdfNotFoundError):
        load_course_book(tmp_path)


def test_default_course_book_path_uses_configured_data_dir(tmp_path):
    make_pdf(tmp_path, ["a"], filename="course_book.pdf")
    path = default_course_book_path(tmp_path)
    assert path == tmp_path / "course_book.pdf"


def test_load_student_summaries_extracts_all_discovered(tmp_path):
    make_pdf(tmp_path, ["a"], filename="summary_a.pdf")
    make_pdf(tmp_path, ["b"], filename="summary_b.pdf")
    docs = load_student_summaries(tmp_path)
    assert len(docs) == 2
    assert all(d.source_type == SourceType.STUDENT_SUMMARY for d in docs)


# ---------------------------------------------------------------------------
# Architectural separation
# ---------------------------------------------------------------------------


def test_student_summary_extraction_uses_correct_source_type(tmp_path):
    path = make_pdf(tmp_path, ["a"])
    doc = extract_pdf(path, SourceType.STUDENT_SUMMARY)
    assert doc.source_type is SourceType.STUDENT_SUMMARY


def test_course_book_extraction_uses_correct_source_type(tmp_path):
    path = make_pdf(tmp_path, ["a"])
    doc = extract_pdf(path, SourceType.COURSE_BOOK)
    assert doc.source_type is SourceType.COURSE_BOOK


def test_historical_style_references_not_involved_in_pdf_extraction(tmp_path):
    path = make_pdf(tmp_path, ["a"])
    doc = extract_pdf(path, SourceType.STUDENT_SUMMARY)
    assert not isinstance(doc, HistoricalStyleReference)
    assert not any(isinstance(p, HistoricalStyleReference) for p in doc.pages)


def test_extracted_pages_are_not_historical_style_references(tmp_path):
    path = make_pdf(tmp_path, ["a"])
    doc = extract_pdf(path, SourceType.STUDENT_SUMMARY)
    assert not isinstance(doc.pages[0], HistoricalStyleReference)


def test_extracted_pages_are_not_automatically_source_evidence_chunks(tmp_path):
    path = make_pdf(tmp_path, ["a"])
    doc = extract_pdf(path, SourceType.STUDENT_SUMMARY)
    assert not isinstance(doc.pages[0], SourceEvidenceChunk)


def test_no_chunk_ids_are_generated(tmp_path):
    path = make_pdf(tmp_path, ["a"])
    doc = extract_pdf(path, SourceType.STUDENT_SUMMARY)
    assert not hasattr(doc.pages[0], "chunk_id")
    assert "chunk_id" not in ExtractedPage.model_fields


def test_no_retrieval_or_indexing_metadata_introduced():
    assert "embedding" not in ExtractedPage.model_fields
    assert "score" not in ExtractedPage.model_fields
    assert "vector_id" not in ExtractedPage.model_fields
