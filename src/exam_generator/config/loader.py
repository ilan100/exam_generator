"""Configuration loading.

Reads external YAML configuration files and constructs validated typed
configuration models (see ``exam_generator.config.models``).

This loader intentionally does not read or require ``OPENAI_API_KEY``: many
commands (ingestion, inspection, configuration validation, tests) must be
able to run without an API key. Secret validation belongs at the point an
LLM provider is actually invoked, in a later Work Package.
"""

from __future__ import annotations

from pathlib import Path

import yaml
from pydantic import ValidationError

from exam_generator.config.models import AppConfig, CategoryMappingConfig, LLMConfig

_ROOT_MARKER = "pyproject.toml"


class ConfigError(Exception):
    """Raised when configuration is missing, malformed, or fails validation."""


def find_project_root(start: Path | None = None) -> Path:
    """Locate the project root by walking upward looking for pyproject.toml.

    This lets configuration loading work regardless of the current working
    directory the process was launched from.
    """
    current = (start or Path(__file__).resolve()).resolve()
    for candidate in (current, *current.parents):
        if (candidate / _ROOT_MARKER).is_file():
            return candidate
    raise ConfigError(
        f"Could not locate project root: no '{_ROOT_MARKER}' found above {current}"
    )


def _default_config_dir() -> Path:
    return find_project_root() / "config"


def _read_yaml(path: Path) -> dict:
    if not path.is_file():
        raise ConfigError(f"Configuration file not found: {path}")
    try:
        with path.open("r", encoding="utf-8") as fh:
            content = yaml.safe_load(fh)
    except yaml.YAMLError as exc:
        raise ConfigError(f"Malformed YAML in {path}: {exc}") from exc

    if content is None:
        raise ConfigError(f"Configuration file is empty: {path}")
    if not isinstance(content, dict):
        raise ConfigError(
            f"Configuration file {path} must contain a mapping at the top level, "
            f"got {type(content).__name__}"
        )
    return content


def load_app_config(config_dir: Path | str | None = None) -> AppConfig:
    """Load and validate config/app.yaml into an AppConfig."""
    directory = Path(config_dir) if config_dir is not None else _default_config_dir()
    raw = _read_yaml(directory / "app.yaml")
    try:
        return AppConfig.model_validate(raw)
    except ValidationError as exc:
        raise ConfigError(f"Invalid app configuration in {directory / 'app.yaml'}:\n{exc}") from exc


def load_llm_config(config_dir: Path | str | None = None) -> LLMConfig:
    """Load and validate config/llm.yaml into an LLMConfig."""
    directory = Path(config_dir) if config_dir is not None else _default_config_dir()
    raw = _read_yaml(directory / "llm.yaml")
    try:
        return LLMConfig.model_validate(raw)
    except ValidationError as exc:
        raise ConfigError(f"Invalid LLM configuration in {directory / 'llm.yaml'}:\n{exc}") from exc


def load_category_mapping(config_dir: Path | str | None = None) -> CategoryMappingConfig:
    """Load and validate config/category_mapping.yaml into a CategoryMappingConfig.

    Only structural validation (non-empty alias keys/targets) happens here;
    cross-checking alias targets against actual canonical categories requires
    the historical repository and is performed by
    ``exam_generator.retrieval.categories.CategoryResolver``.
    """
    directory = Path(config_dir) if config_dir is not None else _default_config_dir()
    raw = _read_yaml(directory / "category_mapping.yaml")
    try:
        return CategoryMappingConfig.model_validate(raw)
    except ValidationError as exc:
        raise ConfigError(
            f"Invalid category mapping configuration in {directory / 'category_mapping.yaml'}:\n{exc}"
        ) from exc
