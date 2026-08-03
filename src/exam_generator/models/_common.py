"""Shared strict-validation building blocks used across domain models.

Not part of the public API - import concrete domain models from
``exam_generator.models`` instead.
"""

from __future__ import annotations

from typing import Annotated

from pydantic import BeforeValidator, Field


def _reject_bool(value: object) -> object:
    """Reject bool where an int is expected.

    ``bool`` is a subclass of ``int`` in Python, so a plain ``int``-typed
    field would otherwise silently accept ``True``/``False`` as ``1``/``0``.
    """
    if isinstance(value, bool):
        raise ValueError("boolean values are not accepted where an integer is expected")
    return value


def _reject_blank(value: object) -> object:
    """Reject strings that are empty or contain only whitespace."""
    if isinstance(value, str) and value.strip() == "":
        raise ValueError("value must not be empty or whitespace-only")
    return value


# Non-empty, non-whitespace-only text. The original text is preserved
# unchanged (no trimming, no case changes) so Hebrew/English terminology
# survives exactly as supplied.
NonBlankStr = Annotated[str, BeforeValidator(_reject_blank)]

# A strictly positive integer; bool is rejected even though bool is an int subtype.
PositiveIntStrict = Annotated[int, BeforeValidator(_reject_bool), Field(gt=0)]

# A 1-based answer identifier: exactly one of 1, 2, 3, 4.
CorrectAnswerId = Annotated[int, BeforeValidator(_reject_bool), Field(ge=1, le=4)]

# A confidence/target value bounded to the inclusive unit interval.
UnitInterval = Annotated[float, Field(ge=0.0, le=1.0)]

# A strict boolean (bool subclasses int, but int/str must not coerce into it).
StrictBool = Annotated[bool, Field(strict=True)]
