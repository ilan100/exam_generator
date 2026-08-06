from pathlib import Path

import pytest
from pydantic import ValidationError

from exam_generator.config.loader import (
    ConfigError,
    load_app_config,
    load_category_mapping,
    load_llm_config,
)
from exam_generator.config.models import GenerationBehaviorConfig, LLMConfig


def test_load_default_app_config_succeeds():
    config = load_app_config()

    assert config.paths.data_dir == "data"
    assert config.paths.output_dir == "output"
    assert config.paths.index_dir == "index"
    assert config.paths.prompts_dir == "prompts"
    assert config.paths.schemas_dir == "schemas"
    assert 0.0 <= config.generation.initial_diversity_target <= 1.0
    assert config.generation.max_generation_attempts > 0
    assert config.generation.max_duplicate_replacement_attempts > 0
    assert config.chunking.chunk_size > 0
    assert 0 <= config.chunking.chunk_overlap < config.chunking.chunk_size
    assert config.retrieval.top_k > 0
    assert config.retrieval.ngram_min <= config.retrieval.ngram_max


def test_load_default_category_mapping_succeeds():
    config = load_category_mapping()

    assert isinstance(config.mapping, dict)


def test_load_default_llm_config_succeeds():
    config = load_llm_config()

    assert config.provider == "openai"
    assert config.model
    assert config.generation.max_tokens > 0
    assert config.validation.max_tokens > 0
    assert config.structured_output_retries >= 0


def test_missing_config_file_raises_clear_error(tmp_path: Path):
    with pytest.raises(ConfigError, match="not found"):
        load_app_config(config_dir=tmp_path)


def test_malformed_yaml_raises_clear_error(tmp_path: Path):
    bad_file = tmp_path / "app.yaml"
    bad_file.write_text("paths: [this is not: valid: yaml", encoding="utf-8")

    with pytest.raises(ConfigError, match="Malformed YAML"):
        load_app_config(config_dir=tmp_path)


def _valid_generation_kwargs(**overrides):
    base = dict(
        initial_diversity_target=0.7,
        minimum_diversity_target=0.3,
        diversity_relaxation_step=0.1,
        max_generation_attempts=3,
        max_duplicate_replacement_attempts=2,
    )
    base.update(overrides)
    return base


def test_diversity_target_out_of_range_rejected():
    with pytest.raises(ValidationError):
        GenerationBehaviorConfig(**_valid_generation_kwargs(initial_diversity_target=1.5))


def test_minimum_diversity_exceeding_initial_rejected():
    with pytest.raises(ValidationError, match="minimum_diversity_target cannot exceed"):
        GenerationBehaviorConfig(
            **_valid_generation_kwargs(
                initial_diversity_target=0.3,
                minimum_diversity_target=0.7,
            )
        )


def test_non_positive_relaxation_step_rejected():
    with pytest.raises(ValidationError):
        GenerationBehaviorConfig(**_valid_generation_kwargs(diversity_relaxation_step=0))


def test_non_positive_max_attempts_rejected():
    with pytest.raises(ValidationError):
        GenerationBehaviorConfig(**_valid_generation_kwargs(max_generation_attempts=0))


def test_non_positive_max_duplicate_replacement_attempts_rejected():
    with pytest.raises(ValidationError):
        GenerationBehaviorConfig(**_valid_generation_kwargs(max_duplicate_replacement_attempts=0))


def _valid_llm_kwargs(**overrides):
    base = dict(
        provider="openai",
        model="gpt-4o-mini",
        generation={"temperature": 0.7, "max_tokens": 1024},
        validation={"temperature": 0.0, "max_tokens": 1024},
    )
    base.update(overrides)
    return base


def test_empty_provider_rejected():
    with pytest.raises(ValidationError):
        LLMConfig(**_valid_llm_kwargs(provider=""))


def test_empty_model_rejected():
    with pytest.raises(ValidationError):
        LLMConfig(**_valid_llm_kwargs(model=""))


def test_structured_output_retries_defaults_to_one():
    config = LLMConfig(**_valid_llm_kwargs())
    assert config.structured_output_retries == 1


def test_structured_output_retries_zero_accepted():
    config = LLMConfig(**_valid_llm_kwargs(structured_output_retries=0))
    assert config.structured_output_retries == 0


def test_structured_output_retries_positive_integer_accepted():
    config = LLMConfig(**_valid_llm_kwargs(structured_output_retries=3))
    assert config.structured_output_retries == 3


def test_structured_output_retries_negative_rejected():
    with pytest.raises(ValidationError):
        LLMConfig(**_valid_llm_kwargs(structured_output_retries=-1))


def test_structured_output_retries_bool_rejected():
    with pytest.raises(ValidationError):
        LLMConfig(**_valid_llm_kwargs(structured_output_retries=True))
