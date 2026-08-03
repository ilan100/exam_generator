"""Provider construction boundary.

Application code should call ``build_llm_provider(llm_config)`` rather than
importing or constructing a specific provider implementation directly - this
is what makes adding a future provider possible without touching
generation/validation application code.
"""

from __future__ import annotations

from exam_generator.config.models import LLMConfig
from exam_generator.llm.errors import LLMConfigurationError
from exam_generator.llm.openai_provider import OpenAIProvider
from exam_generator.llm.provider import LLMProvider

_SUPPORTED_PROVIDERS = ("openai",)


def build_llm_provider(llm_config: LLMConfig, *, api_key: str | None = None) -> LLMProvider:
    """Construct the ``LLMProvider`` selected by ``llm_config.provider``.

    ``api_key`` may be supplied explicitly (used by tests); otherwise it is
    resolved from the ``OPENAI_API_KEY`` environment variable at this point,
    not during configuration loading.
    """
    if llm_config.provider == "openai":
        return OpenAIProvider.from_config(llm_config, api_key=api_key)

    raise LLMConfigurationError(
        f"Unsupported LLM provider: {llm_config.provider!r}. "
        f"Supported providers: {list(_SUPPORTED_PROVIDERS)}"
    )
