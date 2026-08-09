"""Domain-specific exceptions for the WP-032 category-generation service.

Existing generation/validation/production error hierarchies are reused
where they already describe the failure - an operational LLM/provider/
prompt/retrieval failure raised beneath ``CategoryGenerationService``
simply propagates unchanged (see ``exam_generator.category_generation.
service.SYSTEM_LEVEL_ERROR_TYPES``). This is only for a configuration
concern no existing error hierarchy covers.
"""

from __future__ import annotations


class CategoryGenerationError(Exception):
    """Base class for all category-generation-service failures."""


class InvalidCategoryGenerationConfigurationError(CategoryGenerationError):
    """The configured/supplied ``max_duplicate_replacement_attempts`` is
    invalid (must be >= 1)."""
