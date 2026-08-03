"""Retrieval-layer result contract.

Deliberately separate from ``SourceEvidenceChunk``: retrieval relevance is
not factual grounding confidence, LLM confidence, or probability of
correctness - it means only "lexically similar to the retrieval query".
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from exam_generator.models import SourceEvidenceChunk
from exam_generator.models._common import PositiveIntStrict


class RetrievalResult(BaseModel):
    """One ranked retrieval hit: the original chunk, its score, and its rank."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    chunk: SourceEvidenceChunk
    score: float = Field(ge=0.0, le=1.0)
    rank: PositiveIntStrict
