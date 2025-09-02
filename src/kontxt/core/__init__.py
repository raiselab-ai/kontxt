"""Core module for Kontxt library.

This module exports core classes and exceptions used throughout the library.
"""

from .async_base import AsyncBase, PerformanceMetrics
from .exceptions import (
    AsyncContextError,
    KontxtError,
    PerformanceWarning,
    PromptNotFoundError,
    PromptTypeError,
    PromptVersionError,
    TemplateRenderError,
    VariableValidationError,
)

__all__ = [
    # Base classes
    "AsyncBase",
    "PerformanceMetrics",
    # Exceptions
    "KontxtError",
    "AsyncContextError",
    "PromptNotFoundError",
    "TemplateRenderError",
    "VariableValidationError",
    "PromptVersionError",
    "PromptTypeError",
    "PerformanceWarning",
]