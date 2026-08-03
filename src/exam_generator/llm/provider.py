"""The provider-independent LLM abstraction.

Application/generation/validation code must depend only on this interface -
never on a provider SDK - so a future provider can be added without touching
callers. Nothing here depends on the OpenAI SDK.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Sequence, TypeVar

from pydantic import BaseModel

from exam_generator.llm.models import LLMMessage, LLMProfile

ResponseModelT = TypeVar("ResponseModelT", bound=BaseModel)


class LLMProvider(ABC):
    """A synchronous, provider-independent structured-output LLM client."""

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """A stable provider identifier (e.g. ``"openai"``), for future audit use."""

    @property
    @abstractmethod
    def model_name(self) -> str:
        """The configured model identifier, for future audit use."""

    @abstractmethod
    def generate_structured(
        self,
        *,
        messages: Sequence[LLMMessage],
        response_model: type[ResponseModelT],
        profile: LLMProfile,
    ) -> ResponseModelT:
        """Request a structured response validated against ``response_model``.

        ``messages`` must contain at least one message and is never mutated.
        Returns a validated instance of ``response_model`` on success; raises
        an ``exam_generator.llm.errors.LLMError`` subclass otherwise. Never
        returns ``None``, a raw dict, or unparsed text when a response model
        is requested.
        """
