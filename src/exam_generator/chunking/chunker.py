"""Deterministic, character-based chunking of extracted PDF pages into
``SourceEvidenceChunk`` factual-evidence chunks.

A chunk never spans more than one physical PDF page (WP-005 section 6): this
guarantees ``chunk.page`` always identifies the single physical page
containing all of that chunk's text. Chunking is intentionally
model-independent (no tokenizer) and purely local/deterministic (no
embeddings, no NLP).
"""

from __future__ import annotations

from exam_generator.chunking.errors import ChunkingError
from exam_generator.ingestion.models import ExtractedDocument
from exam_generator.models import SourceEvidenceChunk, SourceType

# Sentence-ending punctuation relevant to both Hebrew and English prose.
_SENTENCE_BOUNDARY_CHARS = (".", "?", "!")


def _find_boundary_end(text: str, start: int, tentative_end: int, search_window: int) -> int:
    """Choose a chunk end near ``tentative_end``, preferring a natural boundary.

    Searches backward from ``tentative_end`` within ``search_window``
    characters for, in order of preference: a newline, sentence-ending
    punctuation, then any whitespace. Falls back to a hard split at
    ``tentative_end`` if nothing suitable is found. The search floor is
    clamped to ``start + 1`` so the returned end always makes at least one
    character of forward progress.
    """
    floor = max(start + 1, tentative_end - search_window)

    newline_index = text.rfind("\n", floor, tentative_end)
    if newline_index != -1:
        return newline_index + 1

    best_sentence_index = -1
    for char in _SENTENCE_BOUNDARY_CHARS:
        index = text.rfind(char, floor, tentative_end)
        if index > best_sentence_index:
            best_sentence_index = index
    if best_sentence_index != -1:
        return best_sentence_index + 1

    for index in range(tentative_end - 1, floor - 1, -1):
        if text[index].isspace():
            return index + 1

    return tentative_end


def _iter_chunk_spans(text: str, chunk_size: int, chunk_overlap: int) -> list[tuple[int, int]]:
    """Compute deterministic ``(start, end)`` character spans covering ``text``.

    Spans always make forward progress (``end > start`` for every span, and
    each subsequent span starts strictly after the previous span's start),
    so this terminates for any non-empty ``text`` and any valid
    ``0 <= chunk_overlap < chunk_size``.
    """
    length = len(text)
    if length <= chunk_size:
        return [(0, length)]

    # Boundary search window: a fixed fraction of chunk_size, so it scales
    # with the configured chunk size without exposing another config knob.
    search_window = max(1, chunk_size // 4)

    spans: list[tuple[int, int]] = []
    start = 0
    while start < length:
        tentative_end = min(start + chunk_size, length)
        if tentative_end == length:
            spans.append((start, length))
            break

        end = _find_boundary_end(text, start, tentative_end, search_window)
        spans.append((start, end))

        next_start = end - chunk_overlap
        if next_start <= start:
            next_start = end
        start = next_start

    return spans


def _build_chunk_id(source_type: SourceType, source_file: str, page: int, ordinal: int) -> str:
    """A stable, deterministic, human-readable chunk ID.

    Format: ``{source_type}:{source_file}:{page:04d}:{ordinal:04d}``, e.g.
    ``STUDENT_SUMMARY:student_summary_1.pdf:0005:0001``. Uniquely determined
    by source identity, physical page, and within-page chunk ordinal - no
    random/process-dependent component.
    """
    return f"{source_type.value}:{source_file}:{page:04d}:{ordinal:04d}"


def chunk_document(
    document: ExtractedDocument, *, chunk_size: int, chunk_overlap: int
) -> tuple[SourceEvidenceChunk, ...]:
    """Chunk one extracted document into ``SourceEvidenceChunk`` objects.

    Chunking occurs independently within each non-blank page; chunks never
    span physical page boundaries. Blank/whitespace-only pages produce zero
    chunks but do not affect later pages' numbering. Does not mutate
    ``document`` (its models are frozen).
    """
    if chunk_size <= 0:
        raise ChunkingError(f"chunk_size must be positive, got {chunk_size}")
    if chunk_overlap < 0:
        raise ChunkingError(f"chunk_overlap must be non-negative, got {chunk_overlap}")
    if chunk_overlap >= chunk_size:
        raise ChunkingError(
            f"chunk_overlap ({chunk_overlap}) must be strictly less than chunk_size ({chunk_size})"
        )

    chunks: list[SourceEvidenceChunk] = []
    for page in document.pages:
        if not page.text.strip():
            continue

        spans = _iter_chunk_spans(page.text, chunk_size, chunk_overlap)
        for ordinal, (span_start, span_end) in enumerate(spans, start=1):
            chunk_text = page.text[span_start:span_end].strip()
            if not chunk_text:
                continue
            chunks.append(
                SourceEvidenceChunk(
                    chunk_id=_build_chunk_id(document.source_type, document.source_file, page.page, ordinal),
                    source_file=document.source_file,
                    page=page.page,
                    text=chunk_text,
                    source_type=document.source_type,
                )
            )

    if not chunks:
        raise ChunkingError(
            f"No chunks could be produced from {document.source_file}: no usable page text found"
        )

    return tuple(chunks)
