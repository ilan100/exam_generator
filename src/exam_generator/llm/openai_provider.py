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
from pydantic import BaseModel, ValidationError

from exam_generator.config.models import LLMConfig, LLMGenerationParams, LLMValidationParams
from exam_generator.llm.errors import (
    LLMAuthenticationError,
    LLMConfigurationError,
    LLMProviderError,
    LLMRateLimitError,
    LLMRefusalError,
    LLMRequestError,
    LLMResponseError,
    LLMStructuredOutputError,
)
from exam_generator.llm.models import LLMMessage, LLMProfile, StructuredOutputRetryEvent
from exam_generator.llm.provider import LLMProvider


def _is_malformed_structured_output(exc: ValidationError) -> bool:
    """True only for a pure JSON-parse-level failure - the response text
    itself could not be parsed as JSON at all (e.g. truncated by a token
    limit), reported by pydantic-core as a single ``json_invalid`` error.

    False for a response that parsed successfully but failed one of this
    project's own domain-level validators (e.g. ``NonBlankStr``'s
    non-empty check, reported as ``value_error``) - that is never a
    provider-level structured-output failure and must never be retried
    here (WP-020 section 6).
    """
    errors = exc.errors()
    return len(errors) == 1 and errors[0]["type"] == "json_invalid"

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
        structured_output_retries: int = 1,
    ) -> None:
        if not model or not model.strip():
            raise LLMConfigurationError("OpenAI provider requires a non-empty model")
        if not api_key or not api_key.strip():
            raise LLMConfigurationError(
                f"OpenAI provider requires a non-empty API key "
                f"(expected from the {API_KEY_ENV_VAR} environment variable)"
            )
        if isinstance(structured_output_retries, bool) or (
            not isinstance(structured_output_retries, int) or structured_output_retries < 0
        ):
            raise LLMConfigurationError(
                f"structured_output_retries must be an integer >= 0, got {structured_output_retries!r}"
            )

        self._model = model
        self._generation_params = generation_params
        self._validation_params = validation_params
        self._client = client if client is not None else OpenAI(api_key=api_key, max_retries=0)
        self._structured_output_retries = structured_output_retries
        self._structured_output_retry_events: list[StructuredOutputRetryEvent] = []

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
            structured_output_retries=llm_config.structured_output_retries,
        )

    @property
    def provider_name(self) -> str:
        return PROVIDER_NAME

    @property
    def model_name(self) -> str:
        return self._model

    @property
    def structured_output_retry_events(self) -> tuple[StructuredOutputRetryEvent, ...]:
        """Observability only (WP-020): every completed logical
        ``generate_structured()`` operation that needed at least one
        provider-level structured-output retry, in call order. Never used
        to make any application decision."""
        return tuple(self._structured_output_retry_events)

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
        """Make one logical structured-output operation.

        A logical operation may involve up to ``1 + structured_output_retries``
        *physical* API calls (WP-020) - but only when the provider's
        response text itself could not be parsed as JSON at all (e.g.
        truncated by a token limit), never when a successfully-parsed
        response merely fails one of this project's own domain-level
        validators, and never for auth/rate-limit/connection/status
        failures or refusals - those still make exactly one physical call
        and propagate immediately, unchanged from before WP-020. Retrying
        repeats the exact same request (same messages, same response
        model, same profile parameters); nothing about the request is
        regenerated or altered between physical attempts.
        """
        if not messages:
            raise LLMRequestError("messages must contain at least one LLMMessage")

        params = self._params_for_profile(profile)
        input_items = [{"role": message.role.value, "content": message.content} for message in messages]

        max_physical_calls = 1 + self._structured_output_retries

        for attempt in range(1, max_physical_calls + 1):
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
            except ValidationError as exc:
                if not _is_malformed_structured_output(exc):
                    # A successfully-parsed response that violates one of
                    # our own domain-level constraints - never a
                    # structured-output failure, never retried here.
                    raise
                if attempt < max_physical_calls:
                    continue
                if attempt > 1:
                    self._structured_output_retry_events.append(
                        StructuredOutputRetryEvent(
                            response_model_name=response_model.__name__,
                            profile=profile,
                            attempts_made=attempt,
                            recovered=False,
                        )
                    )
                raise LLMStructuredOutputError(
                    f"The provider returned malformed/unparseable structured output for "
                    f"{response_model.__name__} after {attempt} attempt(s): {exc}"
                ) from exc
            else:
                if attempt > 1:
                    self._structured_output_retry_events.append(
                        StructuredOutputRetryEvent(
                            response_model_name=response_model.__name__,
                            profile=profile,
                            attempts_made=attempt,
                            recovered=True,
                        )
                    )
                return self._extract_parsed(response, response_model)

        raise AssertionError("unreachable: the attempt loop always returns or raises")

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
