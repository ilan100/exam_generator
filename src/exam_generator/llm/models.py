"""Provider-independent LLM message and execution-profile contracts.

Nothing in this module depends on the OpenAI SDK - only the concrete
``openai_provider`` implementation is allowed to do that.
"""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, ConfigDict

from exam_generator.models._common import NonBlankStr, PositiveIntStrict, StrictBool


class MessageRole(str, Enum):
    """A constrained set of supported message roles."""

    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"


class LLMMessage(BaseModel):
    """One provider-independent prompt message.

    Unicode content (Hebrew, English, mixed, source evidence text) is
    preserved exactly - never translated, normalized, or rewritten here.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    role: MessageRole
    content: NonBlankStr


class LLMProfile(str, Enum):
    """Which configured parameter section (see ``config/llm.yaml``) a call
    should use. Generation and validation are distinct LLM operations and
    must never share parameters by accident."""

    GENERATION = "GENERATION"
    VALIDATION = "VALIDATION"


class StructuredOutputRetryEvent(BaseModel):
    """Observability record (WP-020) for one logical
    ``generate_structured()`` operation that needed at least one
    provider-level structured-output retry - recorded only once the
    operation is fully resolved (recovered or exhausted). Never used to
    make any application decision; purely for evaluation/debugging
    inspection. Never carries prompt/message content or secrets."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    response_model_name: NonBlankStr
    profile: LLMProfile
    attempts_made: PositiveIntStrict
    recovered: StrictBool
