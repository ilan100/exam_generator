import pytest
from pydantic import ValidationError

from exam_generator.chunking import (
    ChunkingError,
    CorpusConstructionError,
    DuplicateChunkIdError,
    FactualSourceCorpus,
    build_course_book_corpus,
    build_student_summary_corpus,
    chunk_document,
)
from exam_generator.config.models import AppConfig, ChunkingConfig
from exam_generator.ingestion.models import ExtractedDocument, ExtractedPage
from exam_generator.models import HistoricalStyleReference, SourceEvidenceChunk, SourceType

HEBREW_SENTENCE = "המסילה עוברת דרך ה-Corona radiata ומגיעה אל קליפת המוח. זהו תיאור קצר."


def make_document(pages: list[str], source_file="doc.pdf", source_type=SourceType.STUDENT_SUMMARY):
    return ExtractedDocument(
        source_file=source_file,
        source_type=source_type,
        pages=tuple(ExtractedPage(page=i + 1, text=t) for i, t in enumerate(pages)),
    )


# ---------------------------------------------------------------------------
# Chunking configuration
# ---------------------------------------------------------------------------


def test_valid_chunking_configuration_accepted():
    config = ChunkingConfig(chunk_size=1800, chunk_overlap=300)
    assert config.chunk_size == 1800


def test_positive_chunk_size_required():
    with pytest.raises(ValidationError):
        ChunkingConfig(chunk_size=0, chunk_overlap=0)


def test_zero_chunk_size_rejected():
    with pytest.raises(ValidationError):
        ChunkingConfig(chunk_size=0, chunk_overlap=0)


def test_negative_chunk_size_rejected():
    with pytest.raises(ValidationError):
        ChunkingConfig(chunk_size=-10, chunk_overlap=0)


def test_boolean_chunk_size_rejected():
    with pytest.raises(ValidationError):
        ChunkingConfig(chunk_size=True, chunk_overlap=0)


def test_zero_overlap_accepted():
    config = ChunkingConfig(chunk_size=100, chunk_overlap=0)
    assert config.chunk_overlap == 0


def test_negative_overlap_rejected():
    with pytest.raises(ValidationError):
        ChunkingConfig(chunk_size=100, chunk_overlap=-1)


def test_boolean_overlap_rejected():
    with pytest.raises(ValidationError):
        ChunkingConfig(chunk_size=100, chunk_overlap=True)


def test_overlap_equal_to_chunk_size_rejected():
    with pytest.raises(ValidationError):
        ChunkingConfig(chunk_size=100, chunk_overlap=100)


def test_overlap_greater_than_chunk_size_rejected():
    with pytest.raises(ValidationError):
        ChunkingConfig(chunk_size=100, chunk_overlap=150)


def test_configured_values_load_through_project_configuration():
    from exam_generator.config.loader import load_app_config

    config = load_app_config()
    assert isinstance(config, AppConfig)
    assert config.chunking.chunk_size == 1800
    assert config.chunking.chunk_overlap == 300


# ---------------------------------------------------------------------------
# Basic chunking
# ---------------------------------------------------------------------------


def test_page_shorter_than_chunk_size_produces_one_chunk():
    doc = make_document(["short text"])
    chunks = chunk_document(doc, chunk_size=1800, chunk_overlap=300)
    assert len(chunks) == 1


def test_page_equal_to_chunk_size_behaves_correctly():
    text = "x" * 100
    doc = make_document([text])
    chunks = chunk_document(doc, chunk_size=100, chunk_overlap=10)
    assert len(chunks) == 1
    assert chunks[0].text == text


def test_long_page_produces_multiple_chunks():
    doc = make_document(["word " * 1000])
    chunks = chunk_document(doc, chunk_size=1800, chunk_overlap=300)
    assert len(chunks) > 1


def test_blank_page_produces_zero_chunks():
    doc = make_document(["real content here", ""])
    chunks = chunk_document(doc, chunk_size=1800, chunk_overlap=300)
    assert all(c.page != 2 for c in chunks)


def test_whitespace_only_page_produces_zero_chunks():
    doc = make_document(["real content here", "   \n\t  "])
    chunks = chunk_document(doc, chunk_size=1800, chunk_overlap=300)
    assert all(c.page != 2 for c in chunks)


def test_blank_page_between_populated_pages_preserves_provenance():
    doc = make_document(["first page content", "", "third page content"])
    chunks = chunk_document(doc, chunk_size=1800, chunk_overlap=300)
    pages = {c.page for c in chunks}
    assert pages == {1, 3}


def test_chunk_text_is_non_empty():
    doc = make_document(["word " * 1000])
    chunks = chunk_document(doc, chunk_size=1800, chunk_overlap=300)
    assert all(c.text.strip() for c in chunks)


def test_chunk_text_does_not_exceed_configured_maximum():
    doc = make_document(["word " * 1000])
    chunks = chunk_document(doc, chunk_size=1800, chunk_overlap=300)
    assert all(len(c.text) <= 1800 for c in chunks)


def test_chunk_order_is_deterministic():
    doc = make_document(["word " * 1000])
    chunks1 = chunk_document(doc, chunk_size=1800, chunk_overlap=300)
    chunks2 = chunk_document(doc, chunk_size=1800, chunk_overlap=300)
    assert [c.chunk_id for c in chunks1] == [c.chunk_id for c in chunks2]


def test_repeated_chunking_produces_identical_results():
    doc = make_document(["word " * 1000, "more words " * 500])
    chunks1 = chunk_document(doc, chunk_size=1800, chunk_overlap=300)
    chunks2 = chunk_document(doc, chunk_size=1800, chunk_overlap=300)
    assert chunks1 == chunks2


def test_input_document_is_not_mutated():
    doc = make_document(["word " * 1000])
    before = doc.model_dump()
    chunk_document(doc, chunk_size=1800, chunk_overlap=300)
    after = doc.model_dump()
    assert before == after


# ---------------------------------------------------------------------------
# Boundary behavior
# ---------------------------------------------------------------------------


def test_paragraph_newline_boundary_preferred_near_chunk_end():
    text = ("a" * 90) + "\n" + ("b" * 90)
    doc = make_document([text])
    chunks = chunk_document(doc, chunk_size=100, chunk_overlap=10)
    assert chunks[0].text == "a" * 90


def test_sentence_boundary_used_when_appropriate():
    text = ("a" * 88) + ". " + ("b" * 90)
    doc = make_document([text])
    chunks = chunk_document(doc, chunk_size=100, chunk_overlap=10)
    assert chunks[0].text.endswith(".")


def test_whitespace_boundary_used_when_appropriate():
    text = ("a" * 95) + " " + ("b" * 90)
    doc = make_document([text])
    chunks = chunk_document(doc, chunk_size=100, chunk_overlap=10)
    assert chunks[0].text == "a" * 95


def test_hard_split_occurs_when_no_useful_separator_exists():
    text = "a" * 300
    doc = make_document([text])
    chunks = chunk_document(doc, chunk_size=100, chunk_overlap=10)
    assert len(chunks[0].text) == 100


def test_boundary_search_does_not_create_pathological_tiny_chunks():
    # A newline exists very early, far outside the search window near the
    # intended chunk end, so it must not be used.
    text = "x\n" + ("a" * 400)
    doc = make_document([text])
    chunks = chunk_document(doc, chunk_size=100, chunk_overlap=10)
    assert len(chunks[0].text) > 10


def test_hebrew_text_chunks_without_corruption():
    doc = make_document([HEBREW_SENTENCE * 50])
    chunks = chunk_document(doc, chunk_size=200, chunk_overlap=20)
    reconstructed_has_hebrew = any("קליפת המוח" in c.text for c in chunks)
    assert reconstructed_has_hebrew


def test_english_text_chunks_without_corruption():
    doc = make_document(["Medulla Oblongata and spinal cord. " * 50])
    chunks = chunk_document(doc, chunk_size=200, chunk_overlap=20)
    assert any("Medulla Oblongata" in c.text for c in chunks)


def test_mixed_hebrew_english_text_chunks_without_corruption():
    doc = make_document([HEBREW_SENTENCE * 50])
    chunks = chunk_document(doc, chunk_size=200, chunk_overlap=20)
    assert any("Corona radiata" in c.text for c in chunks)


# ---------------------------------------------------------------------------
# Overlap
# ---------------------------------------------------------------------------


def test_zero_overlap_works():
    doc = make_document(["word " * 1000])
    chunks = chunk_document(doc, chunk_size=1800, chunk_overlap=0)
    assert len(chunks) > 1


def test_configured_overlap_creates_shared_context():
    doc = make_document(["word " * 1000])
    chunks = chunk_document(doc, chunk_size=1800, chunk_overlap=300)
    assert chunks[0].text[-50:] in chunks[1].text or chunks[1].text[:50] in chunks[0].text


def test_chunking_always_makes_forward_progress():
    doc = make_document(["a" * 5000])
    # overlap very close to chunk_size to stress-test progress guarantee
    chunks = chunk_document(doc, chunk_size=100, chunk_overlap=99)
    assert len(chunks) > 1
    assert len(chunks) < 5000  # sanity bound against runaway/infinite loop


def test_overlap_does_not_cross_page_boundaries():
    doc = make_document(["word " * 1000, "different content " * 1000])
    chunks = chunk_document(doc, chunk_size=1800, chunk_overlap=300)
    page1_chunks = [c for c in chunks if c.page == 1]
    page2_chunks = [c for c in chunks if c.page == 2]
    assert "different content" not in page1_chunks[-1].text
    assert "word" not in page2_chunks[0].text or page2_chunks[0].text.count("word") == 0


def test_final_page_chunk_behaves_correctly():
    doc = make_document(["word " * 1000])
    chunks = chunk_document(doc, chunk_size=1800, chunk_overlap=300)
    assert chunks[-1].text.strip() != ""


def test_boundary_aware_split_plus_overlap_is_deterministic():
    doc = make_document([HEBREW_SENTENCE * 100])
    chunks1 = chunk_document(doc, chunk_size=300, chunk_overlap=50)
    chunks2 = chunk_document(doc, chunk_size=300, chunk_overlap=50)
    assert chunks1 == chunks2


# ---------------------------------------------------------------------------
# Provenance
# ---------------------------------------------------------------------------


def test_chunk_preserves_source_filename():
    doc = make_document(["content"], source_file="my_doc.pdf")
    chunks = chunk_document(doc, chunk_size=1800, chunk_overlap=300)
    assert chunks[0].source_file == "my_doc.pdf"


def test_chunk_preserves_student_summary_source_type():
    doc = make_document(["content"], source_type=SourceType.STUDENT_SUMMARY)
    chunks = chunk_document(doc, chunk_size=1800, chunk_overlap=300)
    assert chunks[0].source_type == SourceType.STUDENT_SUMMARY


def test_chunk_preserves_course_book_source_type():
    doc = make_document(["content"], source_type=SourceType.COURSE_BOOK)
    chunks = chunk_document(doc, chunk_size=1800, chunk_overlap=300)
    assert chunks[0].source_type == SourceType.COURSE_BOOK


def test_chunk_preserves_physical_one_based_page_number():
    doc = make_document(["a", "b", "c"])
    chunks = chunk_document(doc, chunk_size=1800, chunk_overlap=300)
    assert {c.page for c in chunks} == {1, 2, 3}


def test_page_one_produces_page_equals_one_chunks():
    doc = make_document(["content"])
    chunks = chunk_document(doc, chunk_size=1800, chunk_overlap=300)
    assert chunks[0].page == 1


def test_page_after_blank_page_retains_original_page_number():
    doc = make_document(["first", "", "third"])
    chunks = chunk_document(doc, chunk_size=1800, chunk_overlap=300)
    assert {c.page for c in chunks} == {1, 3}


def test_no_absolute_filesystem_path_in_chunk_metadata():
    doc = make_document(["content"], source_file="student_summary_1.pdf")
    chunks = chunk_document(doc, chunk_size=1800, chunk_overlap=300)
    assert "/" not in chunks[0].source_file
    assert "/" not in chunks[0].chunk_id.split(":")[1]


def test_answer_history_category_metadata_not_introduced():
    doc = make_document(["content"])
    chunks = chunk_document(doc, chunk_size=1800, chunk_overlap=300)
    assert not hasattr(chunks[0], "category")
    assert not hasattr(chunks[0], "correct_answer")
    assert not hasattr(chunks[0], "historical_question_id")


# ---------------------------------------------------------------------------
# Chunk IDs
# ---------------------------------------------------------------------------


def test_chunk_id_is_non_empty():
    doc = make_document(["content"])
    chunks = chunk_document(doc, chunk_size=1800, chunk_overlap=300)
    assert chunks[0].chunk_id.strip() != ""


def test_chunk_ids_are_deterministic():
    doc = make_document(["word " * 1000])
    chunks1 = chunk_document(doc, chunk_size=1800, chunk_overlap=300)
    chunks2 = chunk_document(doc, chunk_size=1800, chunk_overlap=300)
    assert [c.chunk_id for c in chunks1] == [c.chunk_id for c in chunks2]


def test_repeated_construction_produces_identical_ids():
    doc = make_document(["a", "b"])
    ids1 = [c.chunk_id for c in chunk_document(doc, chunk_size=1800, chunk_overlap=300)]
    ids2 = [c.chunk_id for c in chunk_document(doc, chunk_size=1800, chunk_overlap=300)]
    assert ids1 == ids2


def test_different_ordinals_produce_different_ids():
    doc = make_document(["word " * 1000])
    chunks = chunk_document(doc, chunk_size=1800, chunk_overlap=300)
    ids = [c.chunk_id for c in chunks]
    assert len(ids) == len(set(ids))


def test_different_pages_produce_different_ids():
    doc = make_document(["a", "b"])
    chunks = chunk_document(doc, chunk_size=1800, chunk_overlap=300)
    assert chunks[0].chunk_id != chunks[1].chunk_id


def test_different_source_files_produce_different_ids():
    doc1 = make_document(["content"], source_file="doc1.pdf")
    doc2 = make_document(["content"], source_file="doc2.pdf")
    chunks1 = chunk_document(doc1, chunk_size=1800, chunk_overlap=300)
    chunks2 = chunk_document(doc2, chunk_size=1800, chunk_overlap=300)
    assert chunks1[0].chunk_id != chunks2[0].chunk_id


def test_source_type_distinction_prevents_id_collision():
    doc1 = make_document(["content"], source_file="same.pdf", source_type=SourceType.STUDENT_SUMMARY)
    doc2 = make_document(["content"], source_file="same.pdf", source_type=SourceType.COURSE_BOOK)
    chunks1 = chunk_document(doc1, chunk_size=1800, chunk_overlap=300)
    chunks2 = chunk_document(doc2, chunk_size=1800, chunk_overlap=300)
    assert chunks1[0].chunk_id != chunks2[0].chunk_id


def test_chunk_ids_contain_no_random_uuid_component():
    doc = make_document(["content"])
    chunks = chunk_document(doc, chunk_size=1800, chunk_overlap=300)
    import re

    uuid_pattern = re.compile(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}")
    assert not uuid_pattern.search(chunks[0].chunk_id)


def test_duplicate_chunk_ids_rejected_by_corpus():
    doc = make_document(["content"])
    chunk = chunk_document(doc, chunk_size=1800, chunk_overlap=300)[0]
    with pytest.raises(DuplicateChunkIdError):
        FactualSourceCorpus([chunk, chunk])


# ---------------------------------------------------------------------------
# Corpus
# ---------------------------------------------------------------------------


def _chunks_from(texts, source_file="doc.pdf", source_type=SourceType.STUDENT_SUMMARY):
    doc = make_document(texts, source_file=source_file, source_type=source_type)
    return list(chunk_document(doc, chunk_size=1800, chunk_overlap=300))


def test_valid_student_summary_corpus_accepted():
    corpus = FactualSourceCorpus(_chunks_from(["content"], source_type=SourceType.STUDENT_SUMMARY))
    assert corpus.total_chunks == 1


def test_valid_course_book_corpus_accepted():
    corpus = FactualSourceCorpus(_chunks_from(["content"], source_type=SourceType.COURSE_BOOK))
    assert corpus.total_chunks == 1


def test_corpus_requires_at_least_one_chunk():
    with pytest.raises(CorpusConstructionError):
        FactualSourceCorpus([])


def test_all_chunks_collection_is_immutable():
    corpus = FactualSourceCorpus(_chunks_from(["content"]))
    with pytest.raises(TypeError):
        corpus.all_chunks[0] = None


def test_source_file_collection_is_deterministic():
    chunks = _chunks_from(["content"], source_file="a.pdf") + _chunks_from(["content"], source_file="b.pdf")
    corpus1 = FactualSourceCorpus(chunks)
    corpus2 = FactualSourceCorpus(chunks)
    assert corpus1.source_files == corpus2.source_files


def test_chunks_for_source_returns_correct_chunks():
    chunks_a = _chunks_from(["content a"], source_file="a.pdf")
    chunks_b = _chunks_from(["content b"], source_file="b.pdf")
    corpus = FactualSourceCorpus(chunks_a + chunks_b)
    assert corpus.chunks_for_source("a.pdf") == tuple(chunks_a)


def test_chunks_for_source_preserves_order():
    doc = make_document(["word " * 1000], source_file="a.pdf")
    chunks = list(chunk_document(doc, chunk_size=1800, chunk_overlap=300))
    corpus = FactualSourceCorpus(chunks)
    assert corpus.chunks_for_source("a.pdf") == tuple(chunks)


def test_chunks_for_source_and_page_returns_correct_chunks():
    chunks = _chunks_from(["page one", "page two"], source_file="a.pdf")
    corpus = FactualSourceCorpus(chunks)
    page1 = corpus.chunks_for_source_and_page("a.pdf", 1)
    assert all(c.page == 1 for c in page1)
    assert len(page1) == 1


def test_unknown_source_returns_empty_tuple():
    corpus = FactualSourceCorpus(_chunks_from(["content"]))
    assert corpus.chunks_for_source("does-not-exist.pdf") == ()


def test_unknown_page_returns_empty_tuple():
    corpus = FactualSourceCorpus(_chunks_from(["content"], source_file="a.pdf"))
    assert corpus.chunks_for_source_and_page("a.pdf", 999) == ()


def test_total_chunk_count_correct():
    chunks = _chunks_from(["a"], source_file="x.pdf") + _chunks_from(["b"], source_file="y.pdf")
    corpus = FactualSourceCorpus(chunks)
    assert corpus.total_chunks == 2


def test_chunks_per_source_counts_correct():
    chunks = _chunks_from(["a"], source_file="x.pdf") + _chunks_from(["b", "c"], source_file="y.pdf")
    corpus = FactualSourceCorpus(chunks)
    assert corpus.chunk_count_per_source["x.pdf"] == 1
    assert corpus.chunk_count_per_source["y.pdf"] == 2


def test_statistics_use_correct_character_lengths():
    chunks = _chunks_from(["short", "a longer piece of text here"], source_file="x.pdf")
    corpus = FactualSourceCorpus(chunks)
    lengths = [len(c.text) for c in chunks]
    assert corpus.min_chunk_length == min(lengths)
    assert corpus.max_chunk_length == max(lengths)
    assert corpus.average_chunk_length == sum(lengths) / len(lengths)


def test_corpus_does_not_expose_mutation_that_changes_state():
    corpus = FactualSourceCorpus(_chunks_from(["content"], source_file="a.pdf"))
    result = corpus.chunks_for_source("a.pdf")
    with pytest.raises(TypeError):
        result[0] = None
    assert corpus.chunks_for_source("a.pdf") == result


# ---------------------------------------------------------------------------
# Source separation
# ---------------------------------------------------------------------------


def test_student_summary_corpus_contains_only_student_summary_chunks():
    corpus = FactualSourceCorpus(_chunks_from(["content"], source_type=SourceType.STUDENT_SUMMARY))
    assert all(c.source_type == SourceType.STUDENT_SUMMARY for c in corpus.all_chunks)


def test_course_book_corpus_contains_only_course_book_chunks():
    corpus = FactualSourceCorpus(_chunks_from(["content"], source_type=SourceType.COURSE_BOOK))
    assert all(c.source_type == SourceType.COURSE_BOOK for c in corpus.all_chunks)


def test_course_book_chunks_not_automatically_merged_with_student_summary():
    student_chunks = _chunks_from(["content"], source_type=SourceType.STUDENT_SUMMARY)
    course_chunks = _chunks_from(["content"], source_type=SourceType.COURSE_BOOK)
    student_corpus = FactualSourceCorpus(student_chunks)
    assert all(c.source_type != SourceType.COURSE_BOOK for c in student_corpus.all_chunks)
    course_corpus = FactualSourceCorpus(course_chunks)
    assert student_corpus.all_chunks != course_corpus.all_chunks


def test_historical_style_reference_is_not_accepted_as_a_chunk():
    historical = HistoricalStyleReference(
        historical_question_id=1,
        category="cat",
        question="q",
        answers=["a", "b", "c", "d"],
        correct_answer=1,
    )
    assert not isinstance(historical, SourceEvidenceChunk)
    with pytest.raises((ValidationError, CorpusConstructionError, TypeError, AttributeError)):
        FactualSourceCorpus([historical])


def test_no_category_is_assigned_to_chunks():
    doc = make_document(["content"])
    chunks = chunk_document(doc, chunk_size=1800, chunk_overlap=300)
    assert "category" not in SourceEvidenceChunk.model_fields


# ---------------------------------------------------------------------------
# Integration with WP-004 extraction
# ---------------------------------------------------------------------------


def test_extracted_document_can_be_passed_directly_to_chunk_document():
    doc = make_document(["content from an extracted document"])
    chunks = chunk_document(doc, chunk_size=1800, chunk_overlap=300)
    assert len(chunks) >= 1


def test_source_metadata_survives_extraction_to_chunking():
    doc = make_document(["content"], source_file="summary.pdf", source_type=SourceType.STUDENT_SUMMARY)
    chunks = chunk_document(doc, chunk_size=1800, chunk_overlap=300)
    assert chunks[0].source_file == "summary.pdf"
    assert chunks[0].source_type == SourceType.STUDENT_SUMMARY


def test_physical_page_numbers_survive_extraction_to_chunking():
    doc = make_document(["a", "b", "c"])
    chunks = chunk_document(doc, chunk_size=1800, chunk_overlap=300)
    assert {c.page for c in chunks} == {1, 2, 3}


def test_blank_extracted_pages_survive_as_zero_chunk_pages():
    doc = make_document(["content", ""])
    chunks = chunk_document(doc, chunk_size=1800, chunk_overlap=300)
    assert all(c.page != 2 for c in chunks)


def test_multi_page_extraction_chunking_preserves_global_ordering():
    doc = make_document(["word " * 500, "different " * 500])
    chunks = chunk_document(doc, chunk_size=1800, chunk_overlap=300)
    pages_seen = [c.page for c in chunks]
    assert pages_seen == sorted(pages_seen)


# ---------------------------------------------------------------------------
# Coverage: no source-range gaps
# ---------------------------------------------------------------------------


def test_every_non_blank_page_produces_at_least_one_chunk():
    doc = make_document(["a", "b", "c"])
    chunks = chunk_document(doc, chunk_size=1800, chunk_overlap=300)
    assert {c.page for c in chunks} == {1, 2, 3}


def test_every_chunk_references_an_existing_physical_page():
    doc = make_document(["a", "b"])
    chunks = chunk_document(doc, chunk_size=1800, chunk_overlap=300)
    valid_pages = {p.page for p in doc.pages}
    assert all(c.page in valid_pages for c in chunks)


def test_no_unintended_gaps_between_successive_chunk_spans():
    from exam_generator.chunking.chunker import _iter_chunk_spans

    text = "a" * 5000
    spans = _iter_chunk_spans(text, chunk_size=1800, chunk_overlap=300)
    for previous, current in zip(spans, spans[1:]):
        # next span must start at or before the previous span's end (overlap
        # or exact continuation), never leaving an uncovered gap.
        assert current[0] <= previous[1]
    assert spans[0][0] == 0
    assert spans[-1][1] == len(text)
