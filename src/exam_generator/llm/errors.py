"""Domain-specific exceptions for the provider-independent LLM layer.

Callers should never need to interpret raw OpenAI SDK exceptions for expected
provider-boundary failures.
"""

from __future__ import annotations


class LLMError(Exception):
    """Base class for all LLM-layer failures."""


class LLMConfigurationError(LLMError):
    """Invalid/missing LLM configuration: unsupported provider, missing API
    key, empty model, or an unsupported execution profile."""


class LLMRequestError(LLMError):
    """The caller's request is structurally invalid before any provider call
    is made (e.g. an empty message sequence)."""


class LLMProviderError(LLMError):
    """A provider-boundary failure not covered by a more specific error
    (transport/connection failure, unexpected API status)."""


class LLMAuthenticationError(LLMProviderError):
    """The provider rejected authentication (invalid/missing API key)."""


class LLMRateLimitError(LLMProviderError):
    """The provider signaled a rate limit."""


class LLMResponseError(LLMError):
    """The provider returned a missing/malformed/unusable structured
    response - never repaired or guessed at by this layer."""


class LLMRefusalError(LLMResponseError):
    """The model explicitly refused to produce the requested structured
    output."""


class LLMStructuredOutputError(LLMResponseError):
    """The provider returned a response, but the requested structured
    result could not be obtained because the response text itself was
    malformed/unparseable JSON (e.g. truncated by a token limit) - raised
    only after the provider's own small, bounded structured-output retry
    (WP-020) is exhausted.

    Distinct from a response that parsed successfully but failed one of
    this project's own domain-level validators (a ``pydantic.ValidationError``
    whose errors are not all ``json_invalid``) - that case is never
    retried or reinterpreted here; the provider does not decide domain
    validity, only whether it managed to obtain usable structured output.
    """
