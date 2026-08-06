"""Deterministic, non-LLM structural quality checks (WP-018).

Complements the LLM-based ``QualityValidator``: a small, purely mechanical
check for a specific construction artifact that live testing showed the
LLM-based quality/MCQ validators can miss - answer choices that redundantly
repeat the exam format's own answer numbering inside their own text (for
example ``"1. לטרלית ל-..."`` as the text of ``answer1``). This is not a
general heuristic quality engine: it looks for exactly this one artifact and
nothing else.
"""

from __future__ import annotations

import re

from exam_generator.models import CandidateQuestion

#: Matches a leading enumeration marker such as "1. ", "2) ", "3: " at the
#: very start of an answer. Requires whitespace after the separator, so
#: ordinary numeric content (e.g. "12 pairs of cranial nerves", "2:1 ratio")
#: is never matched.
_LEADING_NUMBERING_PATTERN = re.compile(r"^\s*\d+\s*[.):]\s+")

#: A single answer starting with a leading number is plausibly legitimate
#: content; requiring at least two is strong evidence of a systematic
#: enumeration artifact rather than coincidental phrasing.
_MIN_AFFECTED_ANSWERS = 2


def detect_duplicated_answer_numbering(candidate: CandidateQuestion) -> str | None:
    """Return a rejection reason if 2+ answer choices redundantly repeat
    leading enumeration numbering inside their own text, else ``None``.

    Pure and deterministic - no LLM call, no I/O.
    """
    affected = [
        index + 1 for index, answer in enumerate(candidate.answers) if _LEADING_NUMBERING_PATTERN.match(answer)
    ]
    if len(affected) < _MIN_AFFECTED_ANSWERS:
        return None

    positions = ", ".join(f"answer{position}" for position in affected)
    return (
        f"Answer choices {positions} redundantly repeat leading enumeration numbering "
        f"inside their own text (e.g. '1. ...'), duplicating the exam format's own "
        f"answer numbering."
    )
