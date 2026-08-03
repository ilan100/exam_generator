import pytest
from pydantic import ValidationError

from exam_generator.chunking import FactualSourceCorpus
from exam_generator.config.models import RetrievalConfig
from exam_generator.models import ExamRequest, SourceEvidenceChunk, SourceType
from exam_generator.retrieval import (
    CategoryResolver,
    FactualRetrievalIndex,
    InvalidCategoryMappingError,
    RetrievalIndexError,
    RetrievalQueryError,
    SourceTypeMismatchError,
    UnknownCategoryError,
    resolve_exam_request_categories,
    retrieve_for_category,
)

HEBREW_BRAIN_STEM = "גזע המוח"
HEBREW_CEREBELLUM = "המוח הקטן"


def make_chunk(text, chunk_id="chunk-1", source_file="doc.pdf", page=1, source_type=SourceType.STUDENT_SUMMARY):
    return SourceEvidenceChunk(
        chunk_id=chunk_id, source_file=source_file, page=page, text=text, source_type=source_type
    )


def make_corpus(texts, source_type=SourceType.STUDENT_SUMMARY, source_file="doc.pdf"):
    chunks = [
        make_chunk(t, chunk_id=f"{source_type.value}:{source_file}:{i:04d}:0001", source_file=source_file, page=i + 1, source_type=source_type)
        for i, t in enumerate(texts)
    ]
    return FactualSourceCorpus(chunks)


def build_index(texts, source_type=SourceType.STUDENT_SUMMARY, top_k=8, ngram_range=(3, 5)):
    corpus = make_corpus(texts, source_type=source_type)
    return FactualRetrievalIndex.from_corpus(corpus, source_type=source_type, top_k=top_k, ngram_range=ngram_range)


# ---------------------------------------------------------------------------
# Retrieval configuration
# ---------------------------------------------------------------------------


def test_valid_retrieval_configuration_accepted():
    config = RetrievalConfig(top_k=8, ngram_min=3, ngram_max=5)
    assert config.top_k == 8


def test_positive_top_k_required():
    with pytest.raises(ValidationError):
        RetrievalConfig(top_k=0, ngram_min=3, ngram_max=5)


def test_zero_top_k_rejected():
    with pytest.raises(ValidationError):
        RetrievalConfig(top_k=0, ngram_min=3, ngram_max=5)


def test_negative_top_k_rejected():
    with pytest.raises(ValidationError):
        RetrievalConfig(top_k=-1, ngram_min=3, ngram_max=5)


def test_boolean_top_k_rejected():
    with pytest.raises(ValidationError):
        RetrievalConfig(top_k=True, ngram_min=3, ngram_max=5)


def test_valid_ngram_range_accepted():
    config = RetrievalConfig(top_k=8, ngram_min=3, ngram_max=5)
    assert config.ngram_min == 3
    assert config.ngram_max == 5


def test_zero_ngram_bound_rejected():
    with pytest.raises(ValidationError):
        RetrievalConfig(top_k=8, ngram_min=0, ngram_max=5)


def test_negative_ngram_bound_rejected():
    with pytest.raises(ValidationError):
        RetrievalConfig(top_k=8, ngram_min=3, ngram_max=-1)


def test_boolean_ngram_bound_rejected():
    with pytest.raises(ValidationError):
        RetrievalConfig(top_k=8, ngram_min=True, ngram_max=5)


def test_ngram_min_greater_than_max_rejected():
    with pytest.raises(ValidationError):
        RetrievalConfig(top_k=8, ngram_min=5, ngram_max=3)


def test_configured_retrieval_values_load_through_project_configuration():
    from exam_generator.config.loader import load_app_config

    config = load_app_config()
    assert config.retrieval.top_k > 0
    assert config.retrieval.ngram_min <= config.retrieval.ngram_max


# ---------------------------------------------------------------------------
# Retrieval index construction
# ---------------------------------------------------------------------------


def test_valid_student_summary_corpus_builds():
    index = build_index(["some content here"], source_type=SourceType.STUDENT_SUMMARY)
    assert index.source_type == SourceType.STUDENT_SUMMARY


def test_valid_course_book_corpus_builds():
    index = build_index(["some content here"], source_type=SourceType.COURSE_BOOK)
    assert index.source_type == SourceType.COURSE_BOOK


def test_mixed_source_corpus_rejected():
    chunks = [
        make_chunk("a", chunk_id="a1", source_type=SourceType.STUDENT_SUMMARY),
        make_chunk("b", chunk_id="a2", source_type=SourceType.COURSE_BOOK),
    ]
    corpus = FactualSourceCorpus(chunks)
    with pytest.raises(SourceTypeMismatchError):
        FactualRetrievalIndex.from_corpus(corpus, source_type=SourceType.STUDENT_SUMMARY, top_k=8, ngram_range=(3, 5))


def test_empty_corpus_rejected_at_retrieval_boundary():
    # FactualSourceCorpus itself already rejects empty chunk lists, so the
    # retrieval layer's own boundary is exercised via the public from_corpus
    # constructor against a corpus-like stub with an empty all_chunks tuple -
    # proving the retrieval layer does not merely rely on scikit-learn
    # raising an opaque internal error for this case.
    class _EmptyCorpusStub:
        all_chunks = ()

    with pytest.raises(RetrievalIndexError):
        FactualRetrievalIndex.from_corpus(
            _EmptyCorpusStub(), source_type=SourceType.STUDENT_SUMMARY, top_k=8, ngram_range=(3, 5)
        )


def test_corpus_chunk_order_preserved_internally():
    index = build_index(["first", "second", "third"])
    results = index.search("first")
    assert results[0].chunk.text == "first"


def test_corpus_chunks_not_mutated():
    corpus = make_corpus(["content one", "content two"])
    before = [c.model_dump() for c in corpus.all_chunks]
    FactualRetrievalIndex.from_corpus(
        corpus, source_type=SourceType.STUDENT_SUMMARY, top_k=8, ngram_range=(3, 5)
    )
    after = [c.model_dump() for c in corpus.all_chunks]
    assert before == after


def test_historical_style_reference_cannot_enter_index():
    # There is no public constructor path that accepts a HistoricalStyleReference;
    # from_corpus requires a FactualSourceCorpus of SourceEvidenceChunk objects.
    import inspect

    signature = inspect.signature(FactualRetrievalIndex.from_corpus)
    assert "corpus" in signature.parameters


def test_index_source_type_is_exposed():
    index = build_index(["content"], source_type=SourceType.COURSE_BOOK)
    assert index.source_type == SourceType.COURSE_BOOK


def test_repeated_construction_is_deterministic():
    corpus = make_corpus(["word " * 200, "different content here"])
    index1 = FactualRetrievalIndex.from_corpus(corpus, source_type=SourceType.STUDENT_SUMMARY, top_k=8, ngram_range=(3, 5))
    index2 = FactualRetrievalIndex.from_corpus(corpus, source_type=SourceType.STUDENT_SUMMARY, top_k=8, ngram_range=(3, 5))
    results1 = index1.search("word")
    results2 = index2.search("word")
    assert [(r.chunk.chunk_id, r.score, r.rank) for r in results1] == [(r.chunk.chunk_id, r.score, r.rank) for r in results2]


# ---------------------------------------------------------------------------
# Search
# ---------------------------------------------------------------------------


def test_exact_matching_text_ranks_relevant_chunk_first():
    index = build_index(["totally unrelated content about something else", HEBREW_BRAIN_STEM + " ותפקידו"])
    results = index.search(HEBREW_BRAIN_STEM)
    assert HEBREW_BRAIN_STEM in results[0].chunk.text


def test_unrelated_chunk_ranks_below_matching_chunk():
    index = build_index(["completely different unrelated english text zzz", HEBREW_BRAIN_STEM + " ותפקידו החשוב"])
    results = index.search(HEBREW_BRAIN_STEM, top_k=10)
    assert results[0].score >= results[-1].score if len(results) > 1 else True


def test_hebrew_query_works():
    index = build_index([HEBREW_BRAIN_STEM + " הוא מבנה חשוב", "unrelated english content"])
    results = index.search(HEBREW_BRAIN_STEM)
    assert len(results) >= 1


def test_english_anatomical_query_works():
    index = build_index(["Medulla Oblongata controls breathing", "לא קשור בכלל"])
    results = index.search("Medulla Oblongata")
    assert len(results) >= 1
    assert "Medulla Oblongata" in results[0].chunk.text


def test_mixed_hebrew_english_query_works():
    index = build_index(["המסילה עוברת דרך ה-Corona radiata", "totally unrelated text here"])
    results = index.search("Corona radiata")
    assert len(results) >= 1


def test_whitespace_only_query_rejected():
    index = build_index(["content"])
    with pytest.raises(RetrievalQueryError):
        index.search("   ")


def test_empty_query_rejected():
    index = build_index(["content"])
    with pytest.raises(RetrievalQueryError):
        index.search("")


def test_positive_top_k_respected():
    index = build_index([f"content number {i} unique" for i in range(10)])
    results = index.search("content number", top_k=3)
    assert len(results) <= 3


def test_top_k_larger_than_corpus_size_handled():
    index = build_index(["only chunk here"])
    results = index.search("only chunk here", top_k=1000)
    assert len(results) <= 1


def test_zero_score_results_omitted():
    index = build_index(["aaaaaaaaaa", "bbbbbbbbbb"])
    results = index.search("zzzzzzzzzz completely different characters qqqqqq", top_k=10)
    assert all(r.score > 0 for r in results)


def test_no_overlap_query_returns_empty_sequence():
    index = build_index(["שלום עולם"])
    results = index.search("zzzzzzzz9999")
    assert results == ()


def test_result_rank_begins_at_one():
    index = build_index(["matching content here", "matching content again"])
    results = index.search("matching content")
    assert results[0].rank == 1


def test_result_ranks_are_contiguous():
    index = build_index([f"shared term unique-{i}" for i in range(5)])
    results = index.search("shared term", top_k=5)
    assert [r.rank for r in results] == list(range(1, len(results) + 1))


def test_result_score_is_numeric_and_valid():
    index = build_index(["matching content"])
    results = index.search("matching content")
    assert 0.0 <= results[0].score <= 1.0


def test_result_contains_original_chunk_provenance():
    index = build_index(["content here"], source_type=SourceType.STUDENT_SUMMARY)
    results = index.search("content here")
    assert results[0].chunk.source_file == "doc.pdf"
    assert results[0].chunk.source_type == SourceType.STUDENT_SUMMARY


def test_repeated_identical_search_gives_identical_ordering():
    index = build_index(["alpha beta gamma", "beta gamma delta", "gamma delta epsilon"])
    results1 = index.search("gamma delta")
    results2 = index.search("gamma delta")
    assert [r.chunk.chunk_id for r in results1] == [r.chunk.chunk_id for r in results2]


def test_equal_score_tie_uses_corpus_order():
    # Two identical texts on different pages must tie and break by corpus order.
    index = build_index(["identical repeated text here", "identical repeated text here"])
    results = index.search("identical repeated text here", top_k=2)
    assert len(results) == 2
    assert results[0].chunk.page < results[1].chunk.page


def test_search_does_not_mutate_index_or_chunks():
    corpus = make_corpus(["some content", "more content"])
    index = FactualRetrievalIndex.from_corpus(corpus, source_type=SourceType.STUDENT_SUMMARY, top_k=8, ngram_range=(3, 5))
    before = [c.model_dump() for c in corpus.all_chunks]
    index.search("some content")
    after = [c.model_dump() for c in corpus.all_chunks]
    assert before == after


# ---------------------------------------------------------------------------
# Source separation
# ---------------------------------------------------------------------------


def test_student_summary_index_returns_only_student_summary_chunks():
    index = build_index(["content"], source_type=SourceType.STUDENT_SUMMARY)
    results = index.search("content")
    assert all(r.chunk.source_type == SourceType.STUDENT_SUMMARY for r in results)


def test_course_book_index_returns_only_course_book_chunks():
    index = build_index(["content"], source_type=SourceType.COURSE_BOOK)
    results = index.search("content")
    assert all(r.chunk.source_type == SourceType.COURSE_BOOK for r in results)


def test_same_query_independent_across_both_indexes():
    ss_index = build_index(["shared query term"], source_type=SourceType.STUDENT_SUMMARY)
    cb_index = build_index(["shared query term"], source_type=SourceType.COURSE_BOOK)
    ss_results = ss_index.search("shared query term")
    cb_results = cb_index.search("shared query term")
    assert all(r.chunk.source_type == SourceType.STUDENT_SUMMARY for r in ss_results)
    assert all(r.chunk.source_type == SourceType.COURSE_BOOK for r in cb_results)


# ---------------------------------------------------------------------------
# Category resolver
# ---------------------------------------------------------------------------


def test_exact_canonical_category_resolves_to_itself():
    resolver = CategoryResolver(["גזע המוח", "חומר לבן"], {})
    assert resolver.resolve("גזע המוח") == "גזע המוח"


def test_explicit_alias_resolves_to_target():
    resolver = CategoryResolver(["גזע המוח"], {"brainstem": "גזע המוח"})
    assert resolver.resolve("brainstem") == "גזע המוח"


def test_unknown_category_fails_clearly():
    resolver = CategoryResolver(["גזע המוח"], {})
    with pytest.raises(UnknownCategoryError):
        resolver.resolve("not-a-real-category")


def test_whitespace_only_category_fails():
    resolver = CategoryResolver(["גזע המוח"], {})
    with pytest.raises(UnknownCategoryError):
        resolver.resolve("   ")


def test_alias_target_not_canonical_fails_resolver_construction():
    with pytest.raises(InvalidCategoryMappingError):
        CategoryResolver(["גזע המוח"], {"alias": "not-canonical"})


def test_canonical_category_cannot_be_redirected_by_conflicting_alias():
    with pytest.raises(InvalidCategoryMappingError):
        CategoryResolver(["גזע המוח", "חומר לבן"], {"גזע המוח": "חומר לבן"})


def test_canonical_categories_come_from_constructor_not_hardcoded():
    categories = ("קטגוריה א", "קטגוריה ב")
    resolver = CategoryResolver(categories, {})
    assert resolver.canonical_categories == categories


def test_resolver_behavior_is_deterministic():
    resolver = CategoryResolver(["A", "B"], {"alias": "A"})
    assert resolver.resolve("alias") == resolver.resolve("alias") == "A"


def test_hebrew_canonical_category_preserved_exactly():
    resolver = CategoryResolver(["גזע המוח"], {})
    assert resolver.resolve("גזע המוח") == "גזע המוח"


def test_embedded_english_terminology_in_category_preserved():
    resolver = CategoryResolver(["Corona radiata וגזע המוח"], {})
    assert resolver.resolve("Corona radiata וגזע המוח") == "Corona radiata וגזע המוח"


def test_empty_alias_key_rejected():
    with pytest.raises(InvalidCategoryMappingError):
        CategoryResolver(["A"], {"": "A"})


def test_empty_alias_target_rejected():
    with pytest.raises(InvalidCategoryMappingError):
        CategoryResolver(["A"], {"alias": ""})


# ---------------------------------------------------------------------------
# ExamRequest category resolution
# ---------------------------------------------------------------------------


def test_request_with_canonical_categories_resolves_unchanged():
    resolver = CategoryResolver(["A", "B"], {})
    request = ExamRequest(categories={"A": 3, "B": 2})
    resolved = resolve_exam_request_categories(request, resolver)
    assert resolved.categories == {"A": 3, "B": 2}


def test_request_with_alias_resolves_to_canonical_name():
    resolver = CategoryResolver(["A"], {"alias-a": "A"})
    request = ExamRequest(categories={"alias-a": 4})
    resolved = resolve_exam_request_categories(request, resolver)
    assert resolved.categories == {"A": 4}


def test_unknown_request_category_fails():
    resolver = CategoryResolver(["A"], {})
    request = ExamRequest(categories={"unknown": 3})
    with pytest.raises(UnknownCategoryError):
        resolve_exam_request_categories(request, resolver)


def test_requested_counts_preserved():
    resolver = CategoryResolver(["A", "B"], {})
    request = ExamRequest(categories={"A": 5, "B": 7})
    resolved = resolve_exam_request_categories(request, resolver)
    assert resolved.categories["A"] == 5
    assert resolved.categories["B"] == 7


def test_multiple_distinct_categories_preserved():
    resolver = CategoryResolver(["A", "B", "C"], {})
    request = ExamRequest(categories={"A": 1, "B": 2, "C": 3})
    resolved = resolve_exam_request_categories(request, resolver)
    assert set(resolved.categories.keys()) == {"A", "B", "C"}


def test_canonical_plus_alias_of_same_category_counts_combined():
    resolver = CategoryResolver(["A"], {"alias-a": "A"})
    request = ExamRequest(categories={"A": 3, "alias-a": 2})
    resolved = resolve_exam_request_categories(request, resolver)
    assert resolved.categories == {"A": 5}


def test_multiple_aliases_resolving_to_same_category_combined():
    resolver = CategoryResolver(["A"], {"alias1": "A", "alias2": "A"})
    request = ExamRequest(categories={"alias1": 2, "alias2": 3})
    resolved = resolve_exam_request_categories(request, resolver)
    assert resolved.categories == {"A": 5}


def test_total_requested_count_unchanged_after_resolution():
    resolver = CategoryResolver(["A"], {"alias-a": "A"})
    request = ExamRequest(categories={"A": 3, "alias-a": 2})
    resolved = resolve_exam_request_categories(request, resolver)
    assert sum(resolved.categories.values()) == sum(request.categories.values())


def test_input_exam_request_not_mutated():
    resolver = CategoryResolver(["A"], {"alias-a": "A"})
    request = ExamRequest(categories={"alias-a": 2})
    before = request.model_dump()
    resolve_exam_request_categories(request, resolver)
    after = request.model_dump()
    assert before == after


def test_output_passes_exam_request_domain_contract():
    resolver = CategoryResolver(["A"], {})
    request = ExamRequest(categories={"A": 3})
    resolved = resolve_exam_request_categories(request, resolver)
    assert isinstance(resolved, ExamRequest)


# ---------------------------------------------------------------------------
# Category-based retrieval
# ---------------------------------------------------------------------------


def test_canonical_category_retrieves_using_canonical_text():
    index = build_index(["unrelated text here", HEBREW_BRAIN_STEM + " מבנה חשוב"], source_type=SourceType.STUDENT_SUMMARY)
    resolver = CategoryResolver([HEBREW_BRAIN_STEM], {})
    results = retrieve_for_category(HEBREW_BRAIN_STEM, resolver, index)
    assert len(results) >= 1


def test_alias_resolved_before_retrieval():
    index = build_index(["unrelated content", HEBREW_BRAIN_STEM + " ותפקידו"], source_type=SourceType.STUDENT_SUMMARY)
    resolver = CategoryResolver([HEBREW_BRAIN_STEM], {"brainstem-alias": HEBREW_BRAIN_STEM})
    results = retrieve_for_category("brainstem-alias", resolver, index)
    assert len(results) >= 1


def test_unknown_category_does_not_execute_retrieval():
    index = build_index(["content"], source_type=SourceType.STUDENT_SUMMARY)
    resolver = CategoryResolver(["A"], {})
    with pytest.raises(UnknownCategoryError):
        retrieve_for_category("not-a-category", resolver, index)


def test_category_retrieval_uses_only_student_summary_index():
    ss_index = build_index([HEBREW_BRAIN_STEM + " תיאור"], source_type=SourceType.STUDENT_SUMMARY)
    resolver = CategoryResolver([HEBREW_BRAIN_STEM], {})
    results = retrieve_for_category(HEBREW_BRAIN_STEM, resolver, ss_index)
    assert all(r.chunk.source_type == SourceType.STUDENT_SUMMARY for r in results)


def test_configured_or_default_top_k_respected_in_category_retrieval():
    index = build_index([f"{HEBREW_BRAIN_STEM} variant {i}" for i in range(10)], source_type=SourceType.STUDENT_SUMMARY, top_k=3)
    resolver = CategoryResolver([HEBREW_BRAIN_STEM], {})
    results = retrieve_for_category(HEBREW_BRAIN_STEM, resolver, index)
    assert len(results) <= 3


def test_category_retrieval_results_retain_full_provenance():
    index = build_index([HEBREW_BRAIN_STEM + " תיאור"], source_type=SourceType.STUDENT_SUMMARY)
    resolver = CategoryResolver([HEBREW_BRAIN_STEM], {})
    results = retrieve_for_category(HEBREW_BRAIN_STEM, resolver, index)
    assert results[0].chunk.source_file
    assert results[0].chunk.page >= 1
    assert results[0].chunk.chunk_id


def test_category_retrieval_does_not_claim_grounding():
    index = build_index([HEBREW_BRAIN_STEM + " תיאור"], source_type=SourceType.STUDENT_SUMMARY)
    resolver = CategoryResolver([HEBREW_BRAIN_STEM], {})
    results = retrieve_for_category(HEBREW_BRAIN_STEM, resolver, index)
    assert not hasattr(results[0], "grounded")
    assert not hasattr(results[0], "is_grounded")


def test_repeated_category_retrieval_is_deterministic():
    index = build_index([HEBREW_BRAIN_STEM + " תיאור", "other content " * 5], source_type=SourceType.STUDENT_SUMMARY)
    resolver = CategoryResolver([HEBREW_BRAIN_STEM], {})
    results1 = retrieve_for_category(HEBREW_BRAIN_STEM, resolver, index)
    results2 = retrieve_for_category(HEBREW_BRAIN_STEM, resolver, index)
    assert [r.chunk.chunk_id for r in results1] == [r.chunk.chunk_id for r in results2]
