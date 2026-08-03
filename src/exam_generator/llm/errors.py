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
