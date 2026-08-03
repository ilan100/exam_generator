"""Typed, validated configuration models.

These models represent only the configuration introduced by WP-001
(paths, generation-behavior placeholders, and LLM provider/model/parameter
configuration). They do not implement any of the behavior they describe.
"""

from __future__ import annotations

from typing import Annotated

from pydantic import BaseModel, BeforeValidator, ConfigDict, Field, model_validator


def _reject_bool(value: object) -> object:
    """Reject bool where an int is expected (bool is an int subtype in Python)."""
    if isinstance(value, bool):
        raise ValueError("boolean values are not accepted where an integer is expected")
    return value


StrictPositiveInt = Annotated[int, BeforeValidator(_reject_bool), Field(gt=0)]
StrictNonNegativeInt = Annotated[int, BeforeValidator(_reject_bool), Field(ge=0)]


class PathsConfig(BaseModel):
    """Project-relative filesystem paths used by the application."""

    model_config = ConfigDict(extra="forbid")

    data_dir: str = Field(min_length=1)
    output_dir: str = Field(min_length=1)
    index_dir: str = Field(min_length=1)
    prompts_dir: str = Field(min_length=1)
    schemas_dir: str = Field(min_length=1)


class GenerationBehaviorConfig(BaseModel):
    """Diversity/retry parameters.

    These values are architecturally defined but their behavior is not
    implemented until a later Work Package.
    """

    model_config = ConfigDict(extra="forbid")

    initial_diversity_target: float = Field(ge=0.0, le=1.0)
    minimum_diversity_target: float = Field(ge=0.0, le=1.0)
    diversity_relaxation_step: float = Field(gt=0.0)
    max_generation_attempts: int = Field(gt=0)

    @model_validator(mode="after")
    def _check_diversity_ordering(self) -> "GenerationBehaviorConfig":
        if self.minimum_diversity_target > self.initial_diversity_target:
            raise ValueError(
                "minimum_diversity_target cannot exceed initial_diversity_target "
                f"(got minimum={self.minimum_diversity_target}, "
                f"initial={self.initial_diversity_target})"
            )
        return self


class ChunkingConfig(BaseModel):
    """Deterministic character-based chunking parameters (WP-005)."""

    model_config = ConfigDict(extra="forbid")

    chunk_size: StrictPositiveInt
    chunk_overlap: StrictNonNegativeInt

    @model_validator(mode="after")
    def _check_overlap_less_than_size(self) -> "ChunkingConfig":
        if self.chunk_overlap >= self.chunk_size:
            raise ValueError(
                f"chunk_overlap ({self.chunk_overlap}) must be strictly less than "
                f"chunk_size ({self.chunk_size})"
            )
        return self


class AppConfig(BaseModel):
    """Top-level application configuration (config/app.yaml)."""

    model_config = ConfigDict(extra="forbid")

    paths: PathsConfig
    generation: GenerationBehaviorConfig
    chunking: ChunkingConfig


class LLMGenerationParams(BaseModel):
    """LLM parameters used for question generation calls."""

    model_config = ConfigDict(extra="forbid")

    temperature: float = Field(ge=0.0, le=2.0)
    max_tokens: int = Field(gt=0)


class LLMValidationParams(BaseModel):
    """LLM parameters used for validation calls."""

    model_config = ConfigDict(extra="forbid")

    temperature: float = Field(ge=0.0, le=2.0)
    max_tokens: int = Field(gt=0)


class LLMConfig(BaseModel):
    """Top-level LLM configuration (config/llm.yaml).

    Provider and model are plain configuration data; application logic must
    not hard-code them. No credentials live in this model.
    """

    model_config = ConfigDict(extra="forbid")

    provider: str = Field(min_length=1)
    model: str = Field(min_length=1)
    generation: LLMGenerationParams
    validation: LLMValidationParams
