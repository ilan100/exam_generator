"""Domain-specific exceptions for the WP-015 output/audit layer.

Nothing here is raised because a candidate/exam was rejected - that is
WP-013/WP-014's job, and a rejected/exhausted ``ExamGenerationResult`` never
reaches this layer at all (see ``exam_generator.output.audit``'s module
docstring). These exceptions exist only for genuine internal
inconsistency in an already-successful ``ExamGenerationResult``.
"""

from __future__ import annotations


class OutputError(Exception):
    """Base class for all output/audit-layer failures."""


class AuditConsistencyError(OutputError):
    """The clean exam and the constructed audit do not correspond exactly
    (see WP-015 section 15) - raised rather than silently repaired, since
    this indicates an internally inconsistent ``ExamGenerationResult``."""
