"""Domain-specific exceptions for chunking and factual-corpus construction."""

from __future__ import annotations


class ChunkingError(Exception):
    """A chunking-configuration or chunking-algorithm failure."""


class CorpusConstructionError(Exception):
    """A factual-corpus construction/invariant failure (e.g. no chunks, no
    source documents available)."""


class DuplicateChunkIdError(CorpusConstructionError):
    """A duplicate ``chunk_id`` was encountered while constructing a corpus."""
