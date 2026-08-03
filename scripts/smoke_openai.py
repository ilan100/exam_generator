"""Manual, optional live smoke test for the configured OpenAI provider.

NOT part of the automated pytest suite. Makes exactly one small, non-domain-
specific structured-output request against the real OpenAI API, to verify
the configured provider/model are compatible with this project's structured-
output mechanism.

Requires OPENAI_API_KEY in the environment.

Usage:
    .venv/bin/python scripts/smoke_openai.py
"""

from __future__ import annotations

from pydantic import BaseModel

from exam_generator.config.loader import load_llm_config
from exam_generator.llm import LLMMessage, LLMProfile, MessageRole, build_llm_provider


class _SmokeTestResponse(BaseModel):
    value: str


def main() -> None:
    llm_config = load_llm_config()
    provider = build_llm_provider(llm_config)

    messages = [
        LLMMessage(
            role=MessageRole.USER,
            content="Reply with a structured object where the value field is exactly the string 'ok'.",
        )
    ]
    result = provider.generate_structured(
        messages=messages,
        response_model=_SmokeTestResponse,
        profile=LLMProfile.GENERATION,
    )

    print(f"provider: {provider.provider_name}")
    print(f"model: {provider.model_name}")
    print(f"response type: {type(result).__name__}")
    print(f"response.value: {result.value!r}")


if __name__ == "__main__":
    main()
