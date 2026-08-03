"""Deterministic local lexical (TF-IDF) retrieval over a WP-005
``FactualSourceCorpus``.

A character n-gram TF-IDF representation is used rather than word-based
features: it handles Hebrew, English, mixed anatomical terminology, and
spelling/inflectional variation without any language-specific stemming,
stop-word list, or language model.
"""

from __future__ import annotations

from pathlib import Path

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from exam_generator.chunking import FactualSourceCorpus, build_course_book_corpus, build_student_summary_corpus
from exam_generator.config.loader import load_app_config
from exam_generator.models import SourceEvidenceChunk, SourceType
from exam_generator.retrieval.errors import RetrievalIndexError, RetrievalQueryError, SourceTypeMismatchError
from exam_generator.retrieval.models import RetrievalResult

# Fixed internal V1 analyzer policy (not exposed as configuration - see
# docs/ARCHITECTURE.md): character n-grams within word boundaries handle
# Hebrew/English/mixed terminology without language-specific assumptions.
_ANALYZER = "char_wb"

# Similarity values at or below this are treated as "no lexical overlap" and
# excluded. This absorbs floating-point noise around true zero (e.g. 1e-17
# from floating-point arithmetic) rather than acting as a meaningful
# similarity threshold.
_ZERO_SCORE_TOLERANCE = 1e-9


def _validate_top_k(value: object, *, error_cls: type[Exception]) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise error_cls(f"top_k must be a positive integer, got {value!r}")
    return value


class FactualRetrievalIndex:
    """A read-only, single-``SourceType`` local TF-IDF retrieval index.

    Construction retains the corpus's chunk ordering and never mutates the
    supplied corpus/chunks. The index is not persisted; it is rebuilt in
    memory from the deterministic WP-005 corpus.
    """

    def __init__(
        self,
        chunks: tuple[SourceEvidenceChunk, ...],
        vectorizer: TfidfVectorizer,
        matrix,
        source_type: SourceType,
        default_top_k: int,
    ) -> None:
        self._chunks = chunks
        self._vectorizer = vectorizer
        self._matrix = matrix
        self._source_type = source_type
        self._default_top_k = default_top_k

    @classmethod
    def from_corpus(
        cls,
        corpus: FactualSourceCorpus,
        *,
        source_type: SourceType,
        top_k: int,
        ngram_range: tuple[int, int],
    ) -> "FactualRetrievalIndex":
        """Build an index over exactly one source type from ``corpus``.

        Fails clearly (``SourceTypeMismatchError``) if the corpus contains
        any chunk whose ``source_type`` differs from the requested one, so a
        single retrieval index can never silently mix student-summary and
        course-book material.
        """
        validated_top_k = _validate_top_k(top_k, error_cls=RetrievalIndexError)

        chunks = corpus.all_chunks
        if not chunks:
            raise RetrievalIndexError("Cannot build a retrieval index from an empty corpus")

        mismatched_types = sorted({chunk.source_type.value for chunk in chunks if chunk.source_type != source_type})
        if mismatched_types:
            raise SourceTypeMismatchError(
                f"Corpus contains chunk(s) with source_type(s) {mismatched_types}, "
                f"but this index requires exactly {source_type.value}"
            )

        vectorizer = TfidfVectorizer(analyzer=_ANALYZER, ngram_range=ngram_range)
        try:
            matrix = vectorizer.fit_transform([chunk.text for chunk in chunks])
        except ValueError as exc:
            raise RetrievalIndexError(f"Failed to build retrieval index: {exc}") from exc

        if matrix.shape[1] == 0:
            raise RetrievalIndexError(
                "Retrieval index has an empty vocabulary/feature set for the supplied corpus"
            )

        return cls(chunks, vectorizer, matrix, source_type, validated_top_k)

    @property
    def source_type(self) -> SourceType:
        return self._source_type

    @property
    def feature_count(self) -> int:
        return self._matrix.shape[1]

    @property
    def indexed_chunk_count(self) -> int:
        return len(self._chunks)

    def search(self, query: str, *, top_k: int | None = None) -> tuple[RetrievalResult, ...]:
        """Rank indexed chunks by lexical similarity to ``query``.

        Only chunks with score strictly greater than a tiny floating-point
        tolerance are returned (never zero-padded up to ``top_k``); ties are
        broken deterministically by original corpus position. Never mutates
        the index, its chunks, or the underlying corpus.
        """
        if not isinstance(query, str) or query.strip() == "":
            raise RetrievalQueryError("query must be a non-empty, non-whitespace-only string")

        resolved_top_k = self._default_top_k if top_k is None else _validate_top_k(top_k, error_cls=RetrievalQueryError)

        query_vector = self._vectorizer.transform([query])
        scores = cosine_similarity(query_vector, self._matrix).ravel()

        candidates = [
            (index, min(1.0, max(0.0, float(score))))
            for index, score in enumerate(scores)
            if score > _ZERO_SCORE_TOLERANCE
        ]
        candidates.sort(key=lambda pair: (-pair[1], pair[0]))

        return tuple(
            RetrievalResult(chunk=self._chunks[index], score=score, rank=rank)
            for rank, (index, score) in enumerate(candidates[:resolved_top_k], start=1)
        )


def _resolve_retrieval_params(
    top_k: int | None, ngram_range: tuple[int, int] | None
) -> tuple[int, tuple[int, int]]:
    if top_k is not None and ngram_range is not None:
        return top_k, ngram_range
    configured = load_app_config().retrieval
    resolved_top_k = configured.top_k if top_k is None else top_k
    resolved_ngram = (configured.ngram_min, configured.ngram_max) if ngram_range is None else ngram_range
    return resolved_top_k, resolved_ngram


def build_student_summary_retrieval_index(
    *,
    top_k: int | None = None,
    ngram_range: tuple[int, int] | None = None,
    data_dir: Path | str | None = None,
) -> FactualRetrievalIndex:
    """Build a ready-to-query retrieval index over the student-summary corpus only."""
    resolved_top_k, resolved_ngram = _resolve_retrieval_params(top_k, ngram_range)
    corpus = build_student_summary_corpus(data_dir=data_dir)
    return FactualRetrievalIndex.from_corpus(
        corpus, source_type=SourceType.STUDENT_SUMMARY, top_k=resolved_top_k, ngram_range=resolved_ngram
    )


def build_course_book_retrieval_index(
    *,
    top_k: int | None = None,
    ngram_range: tuple[int, int] | None = None,
    data_dir: Path | str | None = None,
) -> FactualRetrievalIndex:
    """Build a ready-to-query retrieval index over the course-book corpus only.

    Never combined with the student-summary index/results.
    """
    resolved_top_k, resolved_ngram = _resolve_retrieval_params(top_k, ngram_range)
    corpus = build_course_book_corpus(data_dir=data_dir)
    return FactualRetrievalIndex.from_corpus(
        corpus, source_type=SourceType.COURSE_BOOK, top_k=resolved_top_k, ngram_range=resolved_ngram
    )
