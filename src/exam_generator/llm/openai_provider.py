"""The OpenAI implementation of ``LLMProvider``.

Uses the official ``openai`` SDK's Responses API structured-output
mechanism (``client.responses.parse(..., text_format=response_model)``),
which returns a parsed instance of the caller-supplied Pydantic model
directly - no hand-maintained JSON Schema, no ``json.loads`` of raw prose.

This is the only module in ``exam_generator.llm`` that may import the
OpenAI SDK.
"""

from __future__ import annotations

import os
from typing import Sequence, TypeVar

import openai
from openai import OpenAI
from pydantic import BaseModel

from exam_generator.config.models import LLMConfig, LLMGenerationParams, LLMValidationParams
from exam_generator.llm.errors import (
    LLMAuthenticationError,
    LLMConfigurationError,
    LLMProviderError,
    LLMRateLimitError,
    LLMRefusalError,
    LLMRequestError,
    LLMResponseError,
)
from exam_generator.llm.models import LLMMessage, LLMProfile
from exam_generator.llm.provider import LLMProvider

ResponseModelT = TypeVar("ResponseModelT", bound=BaseModel)

#: Environment variable the API key must come from. Never read from
#: config/llm.yaml, source, or committed files.
API_KEY_ENV_VAR = "OPENAI_API_KEY"

PROVIDER_NAME = "openai"


class OpenAIProvider(LLMProvider):
    """Synchronous OpenAI structured-output provider.

    One ``generate_structured()`` call = exactly one logical application LLM
    call: the underlying client is constructed with ``max_retries=0`` so
    transport-level SDK retries never silently multiply attempts behind a
    future retry/diversity controller's back (see docs/ARCHITECTURE.md).
    """

    def __init__(
        self,
        *,
        model: str,
        api_key: str,
        generation_params: LLMGenerationParams,
        validation_params: LLMValidationParams,
        client: object | None = None,
    ) -> None:
        if not model or not model.strip():
            raise LLMConfigurationError("OpenAI provider requires a non-empty model")
        if not api_key or not api_key.strip():
            raise LLMConfigurationError(
                f"OpenAI provider requires a non-empty API key "
                f"(expected from the {API_KEY_ENV_VAR} environment variable)"
            )

        self._model = model
        self._generation_params = generation_params
        self._validation_params = validation_params
        self._client = client if client is not None else OpenAI(api_key=api_key, max_retries=0)

    @classmethod
    def from_config(
        cls,
        llm_config: LLMConfig,
        *,
        api_key: str | None = None,
        client: object | None = None,
    ) -> "OpenAIProvider":
        """Construct from ``LLMConfig``, resolving the API key from the
        environment unless explicitly supplied (used by tests)."""
        resolved_key = api_key if api_key is not None else os.environ.get(API_KEY_ENV_VAR)
        if not resolved_key or not resolved_key.strip():
            raise LLMConfigurationError(
                f"{API_KEY_ENV_VAR} is not set; the OpenAI provider requires it in the environment"
            )
        return cls(
            model=llm_config.model,
            api_key=resolved_key,
            generation_params=llm_config.generation,
            validation_params=llm_config.validation,
            client=client,
        )

    @property
    def provider_name(self) -> str:
        return PROVIDER_NAME

    @property
    def model_name(self) -> str:
        return self._model

    def _params_for_profile(self, profile: LLMProfile) -> LLMGenerationParams | LLMValidationParams:
        if profile == LLMProfile.GENERATION:
            return self._generation_params
        if profile == LLMProfile.VALIDATION:
            return self._validation_params
        raise LLMConfigurationError(f"Unsupported LLM profile: {profile!r}")

    def generate_structured(
        self,
        *,
        messages: Sequence[LLMMessage],
        response_model: type[ResponseModelT],
        profile: LLMProfile,
    ) -> ResponseModelT:
        if not messages:
            raise LLMRequestError("messages must contain at least one LLMMessage")

        params = self._params_for_profile(profile)
        input_items = [{"role": message.role.value, "content": message.content} for message in messages]

        try:
            response = self._client.responses.parse(
                model=self._model,
                input=input_items,
                text_format=response_model,
                temperature=params.temperature,
                max_output_tokens=params.max_tokens,
            )
        except openai.AuthenticationError as exc:
            raise LLMAuthenticationError(f"OpenAI authentication failed: {exc}") from exc
        except openai.RateLimitError as exc:
            raise LLMRateLimitError(f"OpenAI rate limit exceeded: {exc}") from exc
        except openai.APIConnectionError as exc:
            raise LLMProviderError(f"Failed to connect to the OpenAI API: {exc}") from exc
        except openai.APIStatusError as exc:
            raise LLMProviderError(
                f"OpenAI API returned an error status ({exc.status_code}): {exc}"
            ) from exc
        except openai.APIError as exc:
            raise LLMProviderError(f"OpenAI API request failed: {exc}") from exc

        return self._extract_parsed(response, response_model)

    @staticmethod
    def _extract_parsed(response: object, response_model: type[ResponseModelT]) -> ResponseModelT:
        for output in getattr(response, "output", None) or []:
            if getattr(output, "type", None) != "message":
                continue
            for content in getattr(output, "content", None) or []:
                if getattr(content, "type", None) == "refusal":
                    raise LLMRefusalError(
                        f"The model refused to produce a structured response: {content.refusal}"
                    )

        parsed = getattr(response, "output_parsed", None)
        if parsed is None:
            raise LLMResponseError("The provider returned no usable parsed structured response")
        if not isinstance(parsed, response_model):
            raise LLMResponseError(
                f"The provider returned a parsed object of type {type(parsed).__name__}, "
                f"expected {response_model.__name__}"
            )
        return parsed
