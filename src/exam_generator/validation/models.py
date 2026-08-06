"""Observability contracts for the validation layer (WP-021).

Deliberately separate from ``exam_generator.llm.models.StructuredOutputRetryEvent``
(WP-020): that event describes a provider-level physical-call retry for
malformed/unparseable structured output; this one describes an
application-level logical-validation retry after a *syntactically valid*
response claimed provenance that was never supplied. The two mechanisms
have independent, un-merged retry budgets (see
``exam_generator.validation.grounding``/``textbook``).
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict

from exam_generator.models._common import PositiveIntStrict, StrictBool


class ProvenanceRetryEvent(BaseModel):
    """Observability record for one logical grounding/textbook validation
    operation that needed at least one provenance retry - recorded only
    once the operation is fully resolved (recovered or exhausted). Never
    used to make any application decision; purely for evaluation/debugging
    inspection. Never carries prompt/message content or secrets."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    validator: Literal["grounding", "textbook"]
    attempts_made: PositiveIntStrict
    recovered: StrictBool
