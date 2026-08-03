from unittest.mock import MagicMock

import openai
import pytest
from pydantic import BaseModel, ValidationError

from exam_generator.config.models import LLMConfig, LLMGenerationParams, LLMValidationParams
from exam_generator.llm import (
    API_KEY_ENV_VAR,
    LLMAuthenticationError,
    LLMConfigurationError,
    LLMMessage,
    LLMProfile,
    LLMProviderError,
    LLMRateLimitError,
    LLMRefusalError,
    LLMRequestError,
    LLMResponseError,
    MessageRole,
    OpenAIProvider,
    build_llm_provider,
)

HEBREW_MIXED = "מה תפקיד ה-Medulla Oblongata?"


class _TestStructuredResponse(BaseModel):
    value: str


# ---------------------------------------------------------------------------
# Fakes mimicking the OpenAI Responses API's ParsedResponse shape
# ---------------------------------------------------------------------------


class _FakeTextContent:
    type = "output_text"

    def __init__(self, parsed):
        self.parsed = parsed


class _FakeRefusalContent:
    type = "refusal"

    def __init__(self, refusal: str):
        self.refusal = refusal


class _FakeOutputMessage:
    type = "message"

    def __init__(self, content):
        self.content = content


class _FakeParsedResponse:
    def __init__(self, output, parsed=None):
        self.output = output
        self._parsed = parsed

    @property
    def output_parsed(self):
        return self._parsed


def _successful_response(parsed) -> _FakeParsedResponse:
    return _FakeParsedResponse(
        output=[_FakeOutputMessage([_FakeTextContent(parsed)])],
        parsed=parsed,
    )


def _refusal_response(reason: str) -> _FakeParsedResponse:
    return _FakeParsedResponse(output=[_FakeOutputMessage([_FakeRefusalContent(reason)])], parsed=None)


def _empty_response() -> _FakeParsedResponse:
    return _FakeParsedResponse(output=[], parsed=None)


def make_provider(client=None, model="gpt-4o-mini", api_key="test-api-key"):
    return OpenAIProvider(
        model=model,
        api_key=api_key,
        generation_params=LLMGenerationParams(temperature=0.7, max_tokens=1024),
        validation_params=LLMValidationParams(temperature=0.0, max_tokens=512),
        client=client if client is not None else MagicMock(),
    )


def _llm_config(provider="openai", model="gpt-4o-mini"):
    return LLMConfig(
        provider=provider,
        model=model,
        generation={"temperature": 0.7, "max_tokens": 1024},
        validation={"temperature": 0.0, "max_tokens": 512},
    )


# ---------------------------------------------------------------------------
# Configuration (existing LLM config, unaffected by WP-007)
# ---------------------------------------------------------------------------


def test_existing_llm_configuration_still_loads():
    from exam_generator.config.loader import load_llm_config

    config = load_llm_config()
    assert config.provider
    assert config.model


def test_llm_config_provider_preserved():
    config = _llm_config(provider="openai")
    assert config.provider == "openai"


def test_llm_config_model_preserved():
    config = _llm_config(model="gpt-4o-mini")
    assert config.model == "gpt-4o-mini"


def test_llm_config_generation_parameters_preserved():
    config = _llm_config()
    assert config.generation.temperature == 0.7
    assert config.generation.max_tokens == 1024


def test_llm_config_validation_parameters_preserved():
    config = _llm_config()
    assert config.validation.temperature == 0.0
    assert config.validation.max_tokens == 512


def test_empty_provider_still_rejected():
    with pytest.raises(ValidationError):
        LLMConfig(
            provider="",
            model="gpt-4o-mini",
            generation={"temperature": 0.7, "max_tokens": 1024},
            validation={"temperature": 0.0, "max_tokens": 512},
        )


def test_empty_model_still_rejected():
    with pytest.raises(ValidationError):
        LLMConfig(
            provider="openai",
            model="",
            generation={"temperature": 0.7, "max_tokens": 1024},
            validation={"temperature": 0.0, "max_tokens": 512},
        )


def test_configuration_loading_succeeds_without_api_key(monkeypatch):
    monkeypatch.delenv(API_KEY_ENV_VAR, raising=False)
    from exam_generator.config.loader import load_llm_config

    config = load_llm_config()
    assert config.provider


# ---------------------------------------------------------------------------
# Message models
# ---------------------------------------------------------------------------


def test_valid_system_message_accepted():
    message = LLMMessage(role=MessageRole.SYSTEM, content="You are a helpful assistant.")
    assert message.role == MessageRole.SYSTEM


def test_valid_user_message_accepted():
    message = LLMMessage(role=MessageRole.USER, content="Hello")
    assert message.role == MessageRole.USER


def test_assistant_message_accepted():
    message = LLMMessage(role=MessageRole.ASSISTANT, content="Sure, here you go.")
    assert message.role == MessageRole.ASSISTANT


def test_unsupported_role_rejected():
    with pytest.raises(ValidationError):
        LLMMessage(role="developer", content="hello")


def test_empty_content_rejected():
    with pytest.raises(ValidationError):
        LLMMessage(role=MessageRole.USER, content="")


def test_whitespace_only_content_rejected():
    with pytest.raises(ValidationError):
        LLMMessage(role=MessageRole.USER, content="   ")


def test_hebrew_content_preserved():
    message = LLMMessage(role=MessageRole.USER, content="שלום עולם")
    assert message.content == "שלום עולם"


def test_english_content_preserved():
    message = LLMMessage(role=MessageRole.USER, content="Medulla Oblongata")
    assert message.content == "Medulla Oblongata"


def test_mixed_hebrew_english_content_preserved():
    message = LLMMessage(role=MessageRole.USER, content=HEBREW_MIXED)
    assert message.content == HEBREW_MIXED


def test_message_not_mutated_during_provider_execution():
    message = LLMMessage(role=MessageRole.USER, content=HEBREW_MIXED)
    client = MagicMock()
    client.responses.parse.return_value = _successful_response(_TestStructuredResponse(value="ok"))
    provider = make_provider(client=client)
    before = message.model_dump()
    provider.generate_structured(messages=[message], response_model=_TestStructuredResponse, profile=LLMProfile.GENERATION)
    after = message.model_dump()
    assert before == after


# ---------------------------------------------------------------------------
# Provider factory
# ---------------------------------------------------------------------------


def test_configured_openai_provider_constructs_openai_implementation():
    provider = build_llm_provider(_llm_config(), api_key="test-api-key")
    assert isinstance(provider, OpenAIProvider)


def test_provider_and_model_metadata_correct():
    provider = build_llm_provider(_llm_config(model="gpt-4o-mini"), api_key="test-api-key")
    assert provider.provider_name == "openai"
    assert provider.model_name == "gpt-4o-mini"


def test_unsupported_provider_fails_clearly():
    with pytest.raises(LLMConfigurationError):
        build_llm_provider(_llm_config(provider="anthropic"), api_key="test-api-key")


def test_missing_api_key_fails_at_provider_boundary(monkeypatch):
    monkeypatch.delenv(API_KEY_ENV_VAR, raising=False)
    with pytest.raises(LLMConfigurationError):
        build_llm_provider(_llm_config())


def test_blank_api_key_fails():
    with pytest.raises(LLMConfigurationError):
        build_llm_provider(_llm_config(), api_key="   ")


def test_configuration_loading_does_not_require_key(monkeypatch):
    monkeypatch.delenv(API_KEY_ENV_VAR, raising=False)
    # Constructing the LLMConfig itself never touches the environment.
    config = _llm_config()
    assert config.provider == "openai"


def test_api_key_not_exposed_in_provider_repr_or_errors():
    provider = build_llm_provider(_llm_config(), api_key="super-secret-value")
    assert "super-secret-value" not in repr(provider)
    assert "super-secret-value" not in str(provider)
    try:
        build_llm_provider(_llm_config(provider="unknown"), api_key="super-secret-value")
    except LLMConfigurationError as exc:
        assert "super-secret-value" not in str(exc)


def test_env_provided_api_key_used_when_not_explicit(monkeypatch):
    monkeypatch.setenv(API_KEY_ENV_VAR, "env-key-value")
    provider = build_llm_provider(_llm_config())
    assert isinstance(provider, OpenAIProvider)


# ---------------------------------------------------------------------------
# Profile selection
# ---------------------------------------------------------------------------


def test_generation_profile_uses_generation_configuration():
    client = MagicMock()
    client.responses.parse.return_value = _successful_response(_TestStructuredResponse(value="ok"))
    provider = make_provider(client=client)
    provider.generate_structured(
        messages=[LLMMessage(role=MessageRole.USER, content="hi")],
        response_model=_TestStructuredResponse,
        profile=LLMProfile.GENERATION,
    )
    kwargs = client.responses.parse.call_args.kwargs
    assert kwargs["temperature"] == 0.7
    assert kwargs["max_output_tokens"] == 1024


def test_validation_profile_uses_validation_configuration():
    client = MagicMock()
    client.responses.parse.return_value = _successful_response(_TestStructuredResponse(value="ok"))
    provider = make_provider(client=client)
    provider.generate_structured(
        messages=[LLMMessage(role=MessageRole.USER, content="hi")],
        response_model=_TestStructuredResponse,
        profile=LLMProfile.VALIDATION,
    )
    kwargs = client.responses.parse.call_args.kwargs
    assert kwargs["temperature"] == 0.0
    assert kwargs["max_output_tokens"] == 512


def test_generation_and_validation_parameters_not_interchangeable():
    client = MagicMock()
    client.responses.parse.return_value = _successful_response(_TestStructuredResponse(value="ok"))
    provider = make_provider(client=client)

    provider.generate_structured(
        messages=[LLMMessage(role=MessageRole.USER, content="hi")],
        response_model=_TestStructuredResponse,
        profile=LLMProfile.GENERATION,
    )
    gen_temp = client.responses.parse.call_args.kwargs["temperature"]

    provider.generate_structured(
        messages=[LLMMessage(role=MessageRole.USER, content="hi")],
        response_model=_TestStructuredResponse,
        profile=LLMProfile.VALIDATION,
    )
    val_temp = client.responses.parse.call_args.kwargs["temperature"]

    assert gen_temp != val_temp


def test_invalid_profile_does_not_silently_select_default():
    client = MagicMock()
    provider = make_provider(client=client)
    with pytest.raises(LLMConfigurationError):
        provider.generate_structured(
            messages=[LLMMessage(role=MessageRole.USER, content="hi")],
            response_model=_TestStructuredResponse,
            profile="not-a-real-profile",
        )


# ---------------------------------------------------------------------------
# Structured output
# ---------------------------------------------------------------------------


def test_structured_response_model_passed_through():
    client = MagicMock()
    client.responses.parse.return_value = _successful_response(_TestStructuredResponse(value="ok"))
    provider = make_provider(client=client)
    provider.generate_structured(
        messages=[LLMMessage(role=MessageRole.USER, content="hi")],
        response_model=_TestStructuredResponse,
        profile=LLMProfile.GENERATION,
    )
    assert client.responses.parse.call_args.kwargs["text_format"] is _TestStructuredResponse


def test_parsed_pydantic_result_returned():
    client = MagicMock()
    client.responses.parse.return_value = _successful_response(_TestStructuredResponse(value="ok"))
    provider = make_provider(client=client)
    result = provider.generate_structured(
        messages=[LLMMessage(role=MessageRole.USER, content="hi")],
        response_model=_TestStructuredResponse,
        profile=LLMProfile.GENERATION,
    )
    assert result.value == "ok"


def test_returned_result_is_instance_of_requested_model():
    client = MagicMock()
    client.responses.parse.return_value = _successful_response(_TestStructuredResponse(value="ok"))
    provider = make_provider(client=client)
    result = provider.generate_structured(
        messages=[LLMMessage(role=MessageRole.USER, content="hi")],
        response_model=_TestStructuredResponse,
        profile=LLMProfile.GENERATION,
    )
    assert isinstance(result, _TestStructuredResponse)


def test_message_order_preserved():
    client = MagicMock()
    client.responses.parse.return_value = _successful_response(_TestStructuredResponse(value="ok"))
    provider = make_provider(client=client)
    messages = [
        LLMMessage(role=MessageRole.SYSTEM, content="first"),
        LLMMessage(role=MessageRole.USER, content="second"),
        LLMMessage(role=MessageRole.ASSISTANT, content="third"),
    ]
    provider.generate_structured(messages=messages, response_model=_TestStructuredResponse, profile=LLMProfile.GENERATION)
    sent = client.responses.parse.call_args.kwargs["input"]
    assert [item["content"] for item in sent] == ["first", "second", "third"]


def test_message_roles_preserved():
    client = MagicMock()
    client.responses.parse.return_value = _successful_response(_TestStructuredResponse(value="ok"))
    provider = make_provider(client=client)
    messages = [LLMMessage(role=MessageRole.SYSTEM, content="a"), LLMMessage(role=MessageRole.USER, content="b")]
    provider.generate_structured(messages=messages, response_model=_TestStructuredResponse, profile=LLMProfile.GENERATION)
    sent = client.responses.parse.call_args.kwargs["input"]
    assert [item["role"] for item in sent] == ["system", "user"]


def test_message_contents_preserved_hebrew_english_mixed():
    client = MagicMock()
    client.responses.parse.return_value = _successful_response(_TestStructuredResponse(value="ok"))
    provider = make_provider(client=client)
    provider.generate_structured(
        messages=[LLMMessage(role=MessageRole.USER, content=HEBREW_MIXED)],
        response_model=_TestStructuredResponse,
        profile=LLMProfile.GENERATION,
    )
    sent = client.responses.parse.call_args.kwargs["input"]
    assert sent[0]["content"] == HEBREW_MIXED


def test_configured_model_passed_to_sdk():
    client = MagicMock()
    client.responses.parse.return_value = _successful_response(_TestStructuredResponse(value="ok"))
    provider = make_provider(client=client, model="gpt-4o-mini")
    provider.generate_structured(
        messages=[LLMMessage(role=MessageRole.USER, content="hi")],
        response_model=_TestStructuredResponse,
        profile=LLMProfile.GENERATION,
    )
    assert client.responses.parse.call_args.kwargs["model"] == "gpt-4o-mini"


def test_generation_parameters_passed_for_generation_profile():
    client = MagicMock()
    client.responses.parse.return_value = _successful_response(_TestStructuredResponse(value="ok"))
    provider = make_provider(client=client)
    provider.generate_structured(
        messages=[LLMMessage(role=MessageRole.USER, content="hi")],
        response_model=_TestStructuredResponse,
        profile=LLMProfile.GENERATION,
    )
    assert client.responses.parse.call_args.kwargs["temperature"] == 0.7


def test_validation_parameters_passed_for_validation_profile():
    client = MagicMock()
    client.responses.parse.return_value = _successful_response(_TestStructuredResponse(value="ok"))
    provider = make_provider(client=client)
    provider.generate_structured(
        messages=[LLMMessage(role=MessageRole.USER, content="hi")],
        response_model=_TestStructuredResponse,
        profile=LLMProfile.VALIDATION,
    )
    assert client.responses.parse.call_args.kwargs["temperature"] == 0.0


def test_raw_provider_response_does_not_leak_through_public_api():
    client = MagicMock()
    raw = _successful_response(_TestStructuredResponse(value="ok"))
    client.responses.parse.return_value = raw
    provider = make_provider(client=client)
    result = provider.generate_structured(
        messages=[LLMMessage(role=MessageRole.USER, content="hi")],
        response_model=_TestStructuredResponse,
        profile=LLMProfile.GENERATION,
    )
    assert result is not raw
    assert not hasattr(result, "output")


def test_empty_message_sequence_rejected_before_sdk_invocation():
    client = MagicMock()
    provider = make_provider(client=client)
    with pytest.raises(LLMRequestError):
        provider.generate_structured(messages=[], response_model=_TestStructuredResponse, profile=LLMProfile.GENERATION)
    client.responses.parse.assert_not_called()


# ---------------------------------------------------------------------------
# Structured response failures
# ---------------------------------------------------------------------------


def test_missing_parsed_output_fails_clearly():
    client = MagicMock()
    client.responses.parse.return_value = _empty_response()
    provider = make_provider(client=client)
    with pytest.raises(LLMResponseError):
        provider.generate_structured(
            messages=[LLMMessage(role=MessageRole.USER, content="hi")],
            response_model=_TestStructuredResponse,
            profile=LLMProfile.GENERATION,
        )


def test_refusal_becomes_llm_refusal_error():
    client = MagicMock()
    client.responses.parse.return_value = _refusal_response("cannot comply with this request")
    provider = make_provider(client=client)
    with pytest.raises(LLMRefusalError, match="cannot comply"):
        provider.generate_structured(
            messages=[LLMMessage(role=MessageRole.USER, content="hi")],
            response_model=_TestStructuredResponse,
            profile=LLMProfile.GENERATION,
        )


def test_malformed_response_becomes_llm_response_error():
    client = MagicMock()

    class _WrongModel(BaseModel):
        other_field: int

    client.responses.parse.return_value = _successful_response(_WrongModel(other_field=1))
    provider = make_provider(client=client)
    with pytest.raises(LLMResponseError):
        provider.generate_structured(
            messages=[LLMMessage(role=MessageRole.USER, content="hi")],
            response_model=_TestStructuredResponse,
            profile=LLMProfile.GENERATION,
        )


def test_authentication_failure_translates_correctly():
    client = MagicMock()
    client.responses.parse.side_effect = openai.AuthenticationError(
        message="invalid api key", response=MagicMock(status_code=401, headers={}), body=None
    )
    provider = make_provider(client=client)
    with pytest.raises(LLMAuthenticationError):
        provider.generate_structured(
            messages=[LLMMessage(role=MessageRole.USER, content="hi")],
            response_model=_TestStructuredResponse,
            profile=LLMProfile.GENERATION,
        )


def test_rate_limit_failure_translates_correctly():
    client = MagicMock()
    client.responses.parse.side_effect = openai.RateLimitError(
        message="rate limited", response=MagicMock(status_code=429, headers={}), body=None
    )
    provider = make_provider(client=client)
    with pytest.raises(LLMRateLimitError):
        provider.generate_structured(
            messages=[LLMMessage(role=MessageRole.USER, content="hi")],
            response_model=_TestStructuredResponse,
            profile=LLMProfile.GENERATION,
        )


def test_connection_transport_failure_translates_correctly():
    client = MagicMock()
    client.responses.parse.side_effect = openai.APIConnectionError(request=MagicMock())
    provider = make_provider(client=client)
    with pytest.raises(LLMProviderError):
        provider.generate_structured(
            messages=[LLMMessage(role=MessageRole.USER, content="hi")],
            response_model=_TestStructuredResponse,
            profile=LLMProfile.GENERATION,
        )


def test_original_sdk_exception_preserved_as_cause():
    client = MagicMock()
    original = openai.AuthenticationError(message="bad key", response=MagicMock(status_code=401, headers={}), body=None)
    client.responses.parse.side_effect = original
    provider = make_provider(client=client)
    try:
        provider.generate_structured(
            messages=[LLMMessage(role=MessageRole.USER, content="hi")],
            response_model=_TestStructuredResponse,
            profile=LLMProfile.GENERATION,
        )
        pytest.fail("expected LLMAuthenticationError")
    except LLMAuthenticationError as exc:
        assert exc.__cause__ is original


def test_failure_does_not_expose_api_key():
    client = MagicMock()
    client.responses.parse.side_effect = openai.AuthenticationError(
        message="invalid api key", response=MagicMock(status_code=401, headers={}), body=None
    )
    provider = make_provider(client=client, api_key="super-secret-test-key")
    try:
        provider.generate_structured(
            messages=[LLMMessage(role=MessageRole.USER, content="hi")],
            response_model=_TestStructuredResponse,
            profile=LLMProfile.GENERATION,
        )
        pytest.fail("expected LLMAuthenticationError")
    except LLMAuthenticationError as exc:
        assert "super-secret-test-key" not in str(exc)
