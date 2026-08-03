"""Loading external prompt files into validated, immutable ``PromptTemplate``
instances.

The ``PromptId`` -> filesystem mapping lives entirely in this module; no
other code should reference prompt file paths directly (see WP-008 section
8).
"""

from __future__ import annotations

import hashlib
import string
from pathlib import Path
from types import MappingProxyType
from typing import Mapping

from exam_generator.config.loader import find_project_root, load_app_config
from exam_generator.prompts.errors import (
    PromptNotFoundError,
    PromptRepositoryError,
    PromptTemplateError,
)
from exam_generator.prompts.models import PromptId, PromptTemplate

# PromptId -> (subdirectory, filename) under the configured prompts directory.
_PROMPT_FILES: Mapping[PromptId, tuple[str, str]] = MappingProxyType(
    {
        PromptId.SYSTEM: ("system", "exam_generator.txt"),
        PromptId.QUESTION_GENERATION: ("generation", "question.txt"),
        PromptId.GROUNDING_VALIDATION: ("validation", "grounding.txt"),
        PromptId.MCQ_VALIDATION: ("validation", "mcq.txt"),
        PromptId.CATEGORY_VALIDATION: ("validation", "category.txt"),
        PromptId.QUALITY_VALIDATION: ("validation", "quality.txt"),
        PromptId.TEXTBOOK_VALIDATION: ("validation", "textbook.txt"),
    }
)

_formatter = string.Formatter()


def _extract_required_variables(prompt_id: PromptId, text: str) -> tuple[str, ...]:
    """Deterministically derive the named placeholders a template requires,
    in first-appearance order.

    Only a plain named field (``{name}``) is supported. Positional/numbered
    fields (``{0}``, ``{}``), attribute/index access (``{name.attr}``,
    ``{name[0]}``), conversion syntax (``{name!r}``), and format specs
    (``{name:>10}``) are all deliberately rejected - the template system
    supports only static text plus named placeholders, nothing more
    expressive.
    """
    try:
        parsed_fields = list(_formatter.parse(text))
    except ValueError as exc:
        raise PromptTemplateError(
            f"Malformed placeholder syntax in prompt {prompt_id.value}: {exc}"
        ) from exc

    variables: list[str] = []
    for _literal_text, field_name, format_spec, conversion in parsed_fields:
        if field_name is None:
            continue
        if not field_name.isidentifier():
            raise PromptTemplateError(
                f"Prompt {prompt_id.value} uses an unsupported placeholder "
                f"'{{{field_name}}}' - only plain named placeholders are supported"
            )
        if format_spec:
            raise PromptTemplateError(
                f"Prompt {prompt_id.value} uses an unsupported format-spec on "
                f"placeholder '{{{field_name}}}'"
            )
        if conversion is not None:
            raise PromptTemplateError(
                f"Prompt {prompt_id.value} uses an unsupported conversion on "
                f"placeholder '{{{field_name}}}'"
            )
        if field_name not in variables:
            variables.append(field_name)
    return tuple(variables)


def _load_template(prompt_id: PromptId, path: Path) -> PromptTemplate:
    if not path.is_file():
        raise PromptRepositoryError(f"Prompt file not found for {prompt_id.value}: {path}")

    raw_bytes = path.read_bytes()
    try:
        text = raw_bytes.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise PromptRepositoryError(
            f"Prompt file for {prompt_id.value} is not valid UTF-8: {path}"
        ) from exc

    if text.strip() == "":
        raise PromptRepositoryError(
            f"Prompt file for {prompt_id.value} is empty or whitespace-only: {path}"
        )

    required_variables = _extract_required_variables(prompt_id, text)
    # SHA-256 of the exact file bytes (not the decoded str) so the version
    # identity is unaffected by any text-mode newline translation.
    version = hashlib.sha256(raw_bytes).hexdigest()
    return PromptTemplate(
        prompt_id=prompt_id,
        text=text,
        required_variables=required_variables,
        version=version,
    )


class PromptRepository:
    """Read-only, in-memory collection of every loaded production prompt.

    Construction fails early: every required prompt is located, read, and
    validated up front, so a missing/malformed prompt file is discovered at
    repository-construction time, not when an exam is later generated.
    """

    def __init__(self, templates: Mapping[PromptId, PromptTemplate]) -> None:
        self._templates: Mapping[PromptId, PromptTemplate] = MappingProxyType(dict(templates))

    @classmethod
    def from_directory(cls, directory: Path | str) -> "PromptRepository":
        """Load every required production prompt from an explicit prompt
        directory (used by tests, and by callers with a non-default path)."""
        base = Path(directory)
        templates = {
            prompt_id: _load_template(prompt_id, base / subdir / filename)
            for prompt_id, (subdir, filename) in _PROMPT_FILES.items()
        }
        return cls(templates)

    @classmethod
    def from_default_location(cls) -> "PromptRepository":
        """Load from the project's configured prompts directory
        (``config/app.yaml``'s ``paths.prompts_dir``, resolved relative to
        the project root)."""
        app_config = load_app_config()
        return cls.from_directory(find_project_root() / app_config.paths.prompts_dir)

    def get(self, prompt_id: PromptId) -> PromptTemplate:
        """Return the template for ``prompt_id``.

        Raises ``PromptNotFoundError`` for any identifier the repository did
        not load - never a default/fallback template.
        """
        try:
            return self._templates[prompt_id]
        except KeyError:
            raise PromptNotFoundError(f"Unknown prompt id: {prompt_id!r}") from None

    @property
    def prompt_ids(self) -> tuple[PromptId, ...]:
        """Every prompt identifier this repository has loaded."""
        return tuple(self._templates.keys())
