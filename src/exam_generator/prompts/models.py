"""Provider-independent prompt identity and template contracts.

Nothing here depends on the OpenAI SDK or any concrete provider - only
``exam_generator.llm``'s provider-independent ``LLMMessage``/``MessageRole``
may be depended on by this package (see ``renderer.py``).
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class PromptId(str, Enum):
    """Stable, provider-independent identity for one production prompt.

    Application code requests prompts by identifier
    (``repository.get(PromptId.GROUNDING_VALIDATION)``); it must never
    reference filesystem paths directly - that mapping is owned entirely by
    ``repository.py``.
    """

    SYSTEM = "SYSTEM"
    QUESTION_TARGET_PLANNING = "QUESTION_TARGET_PLANNING"
    QUESTION_GENERATION = "QUESTION_GENERATION"
    GROUNDING_VALIDATION = "GROUNDING_VALIDATION"
    MCQ_VALIDATION = "MCQ_VALIDATION"
    CATEGORY_VALIDATION = "CATEGORY_VALIDATION"
    QUALITY_VALIDATION = "QUALITY_VALIDATION"
    TEXTBOOK_VALIDATION = "TEXTBOOK_VALIDATION"


@dataclass(frozen=True)
class PromptTemplate:
    """An immutable, loaded-and-validated prompt template.

    ``required_variables`` is always deterministically derived from
    ``text``'s actual placeholders (see
    ``repository._extract_required_variables``) - never a second,
    hand-maintained list that could drift from the file. ``version`` is the
    SHA-256 hex digest of the exact prompt-file bytes, for future audit use
    (a content-identity aid, not a security mechanism).
    """

    prompt_id: PromptId
    text: str
    required_variables: tuple[str, ...]
    version: str
