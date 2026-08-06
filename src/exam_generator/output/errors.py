"""Domain-specific exceptions for the WP-015 output/audit layer.

Nothing here is raised because a candidate/question was rejected - that is
WP-013/WP-014's job. Since WP-023, an ``ExamGenerationResult`` reaching
this layer may be ``PARTIAL`` (one or more planned questions failed for a
question-local reason) as a normal, legitimate case - only a genuinely
system-level failure aborts before any result reaches this layer at all
(see ``exam_generator.output.audit``'s module docstring). These exceptions
exist only for genuine internal inconsistency in an ``ExamGenerationResult``
that did reach this layer.
"""

from __future__ import annotations


class OutputError(Exception):
    """Base class for all output/audit-layer failures."""


class AuditConsistencyError(OutputError):
    """The clean exam and the constructed audit do not correspond exactly
    (see WP-015 section 15) - raised rather than silently repaired, since
    this indicates an internally inconsistent ``ExamGenerationResult``."""
