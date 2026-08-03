"""Read-only, in-memory factual-source corpora built from chunked PDFs.

A single generic ``FactualSourceCorpus`` type backs both the student-summary
and course-book corpora; callers must keep the two corpora themselves
separate (student-summary chunks must never satisfy grounding merely because
matching material also exists in the course book).
"""

from __future__ import annotations

from pathlib import Path
from types import MappingProxyType
from typing import Mapping, Sequence

from exam_generator.chunking.chunker import chunk_document
from exam_generator.chunking.errors import CorpusConstructionError, DuplicateChunkIdError
from exam_generator.config.loader import load_app_config
from exam_generator.ingestion.discovery import load_course_book, load_student_summaries
from exam_generator.models import SourceEvidenceChunk, SourceType


class FactualSourceCorpus:
    """A read-only collection of ``SourceEvidenceChunk`` factual evidence."""

    def __init__(self, chunks: Sequence[SourceEvidenceChunk]) -> None:
        chunks = tuple(chunks)
        if not chunks:
            raise CorpusConstructionError("A factual source corpus must contain at least one chunk")

        seen_ids: set[str] = set()
        for chunk in chunks:
            if chunk.chunk_id in seen_ids:
                raise DuplicateChunkIdError(f"Duplicate chunk_id in corpus: {chunk.chunk_id}")
            seen_ids.add(chunk.chunk_id)

        self._chunks: tuple[SourceEvidenceChunk, ...] = chunks

        source_files: list[str] = []
        source_types: list[SourceType] = []
        by_source: dict[str, list[SourceEvidenceChunk]] = {}
        by_source_page: dict[tuple[str, int], list[SourceEvidenceChunk]] = {}
        for chunk in chunks:
            if chunk.source_file not in by_source:
                source_files.append(chunk.source_file)
                by_source[chunk.source_file] = []
            if chunk.source_type not in source_types:
                source_types.append(chunk.source_type)
            by_source[chunk.source_file].append(chunk)
            by_source_page.setdefault((chunk.source_file, chunk.page), []).append(chunk)

        self._source_files: tuple[str, ...] = tuple(source_files)
        self._source_types: tuple[SourceType, ...] = tuple(source_types)
        self._by_source: dict[str, tuple[SourceEvidenceChunk, ...]] = {
            source: tuple(items) for source, items in by_source.items()
        }
        self._by_source_page: dict[tuple[str, int], tuple[SourceEvidenceChunk, ...]] = {
            key: tuple(items) for key, items in by_source_page.items()
        }
        self._chunk_count_per_source: Mapping[str, int] = MappingProxyType(
            {source: len(items) for source, items in self._by_source.items()}
        )

    @property
    def all_chunks(self) -> tuple[SourceEvidenceChunk, ...]:
        return self._chunks

    @property
    def total_chunks(self) -> int:
        return len(self._chunks)

    @property
    def source_files(self) -> tuple[str, ...]:
        return self._source_files

    @property
    def source_types(self) -> tuple[SourceType, ...]:
        return self._source_types

    def chunks_for_source(self, source_file: str) -> tuple[SourceEvidenceChunk, ...]:
        """Chunks for an exact source filename, in corpus order. Unknown
        source names return an empty tuple rather than raising."""
        return self._by_source.get(source_file, ())

    def chunks_for_source_and_page(self, source_file: str, page: int) -> tuple[SourceEvidenceChunk, ...]:
        """Chunks for an exact (source filename, physical page) pair, in
        corpus order. Unknown source/page returns an empty tuple rather than
        raising."""
        return self._by_source_page.get((source_file, page), ())

    @property
    def chunk_count_per_source(self) -> Mapping[str, int]:
        return self._chunk_count_per_source

    @property
    def min_chunk_length(self) -> int:
        return min(len(chunk.text) for chunk in self._chunks)

    @property
    def max_chunk_length(self) -> int:
        return max(len(chunk.text) for chunk in self._chunks)

    @property
    def average_chunk_length(self) -> float:
        return sum(len(chunk.text) for chunk in self._chunks) / len(self._chunks)


def _resolve_chunk_params(chunk_size: int | None, chunk_overlap: int | None) -> tuple[int, int]:
    if chunk_size is not None and chunk_overlap is not None:
        return chunk_size, chunk_overlap
    configured = load_app_config().chunking
    return (
        chunk_size if chunk_size is not None else configured.chunk_size,
        chunk_overlap if chunk_overlap is not None else configured.chunk_overlap,
    )


def build_student_summary_corpus(
    *,
    chunk_size: int | None = None,
    chunk_overlap: int | None = None,
    data_dir: Path | str | None = None,
) -> FactualSourceCorpus:
    """Discover, extract, and chunk every configured student-summary PDF into
    one read-only ``FactualSourceCorpus`` (all chunks ``SourceType.STUDENT_SUMMARY``).

    ``chunk_size``/``chunk_overlap`` default to the configured
    ``config/app.yaml`` chunking parameters when not supplied explicitly.
    """
    size, overlap = _resolve_chunk_params(chunk_size, chunk_overlap)
    documents = load_student_summaries(data_dir)
    if not documents:
        raise CorpusConstructionError("No student-summary source documents were found")

    chunks: list[SourceEvidenceChunk] = []
    for document in documents:
        chunks.extend(chunk_document(document, chunk_size=size, chunk_overlap=overlap))

    return FactualSourceCorpus(chunks)


def build_course_book_corpus(
    *,
    chunk_size: int | None = None,
    chunk_overlap: int | None = None,
    data_dir: Path | str | None = None,
) -> FactualSourceCorpus:
    """Resolve, extract, and chunk the configured course book into one
    read-only ``FactualSourceCorpus`` (all chunks ``SourceType.COURSE_BOOK``).

    Never merged with the student-summary corpus.
    """
    size, overlap = _resolve_chunk_params(chunk_size, chunk_overlap)
    document = load_course_book(data_dir)
    chunks = chunk_document(document, chunk_size=size, chunk_overlap=overlap)
    return FactualSourceCorpus(chunks)
