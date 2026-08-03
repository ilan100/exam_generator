"""Deterministic, strict prompt rendering and provider-independent message
construction.

Rendering performs exactly one substitution pass: ``str.format`` only
interprets the placeholders present in the template text itself and never
re-parses substituted values, so source content containing brace-like or
placeholder-like text is preserved as inert data (see WP-008 section 41).
"""

from __future__ import annotations

from typing import Mapping

from exam_generator.llm.models import LLMMessage, MessageRole
from exam_generator.prompts.errors import PromptRenderError
from exam_generator.prompts.models import PromptTemplate


def render_prompt(template: PromptTemplate, **variables: str) -> str:
    """Render ``template`` against exactly its required variable set.

    Rendering is strict: every required variable must be supplied and no
    unexpected variable may be supplied. A missing value is never silently
    substituted with an empty string, and an extra value is never silently
    ignored - both fail with ``PromptRenderError``.
    """
    required = set(template.required_variables)
    supplied = set(variables.keys())

    missing = required - supplied
    if missing:
        raise PromptRenderError(
            f"Missing required variable(s) for prompt {template.prompt_id.value}: "
            f"{sorted(missing)}"
        )

    unexpected = supplied - required
    if unexpected:
        raise PromptRenderError(
            f"Unexpected variable(s) supplied for prompt {template.prompt_id.value}: "
            f"{sorted(unexpected)}"
        )

    try:
        return template.text.format(**variables)
    except (KeyError, IndexError, ValueError) as exc:
        raise PromptRenderError(
            f"Failed to render prompt {template.prompt_id.value}: {exc}"
        ) from exc


def build_prompt_messages(
    *,
    system_template: PromptTemplate,
    task_template: PromptTemplate,
    variables: Mapping[str, str],
) -> tuple[LLMMessage, LLMMessage]:
    """Render ``system_template`` (no variables) and ``task_template`` (with
    ``variables``) into the SYSTEM-then-USER ``LLMMessage`` sequence WP-007's
    ``LLMProvider`` expects.

    Uses only WP-007's provider-independent ``LLMMessage``/``MessageRole`` -
    no competing message model, no OpenAI import, and no provider is ever
    invoked here.
    """
    system_text = render_prompt(system_template)
    task_text = render_prompt(task_template, **dict(variables))
    return (
        LLMMessage(role=MessageRole.SYSTEM, content=system_text),
        LLMMessage(role=MessageRole.USER, content=task_text),
    )
