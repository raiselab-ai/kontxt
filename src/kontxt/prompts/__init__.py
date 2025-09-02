"""Kontxt prompts module - clean public API.

This module provides prompt management and rendering capabilities with
async-first architecture and modular design.
"""

from .prompt import Prompt
from .types import PromptType, PromptMetadata, PromptVariable

# Advanced imports for power users
from .renderers import StructuredRenderer, FreeformRenderer, HybridRenderer
from .variables.validator import VariableValidator
from .utils.logging import OutputLogger

# Try to import PromptRegistry if it exists
try:
    from .registry import PromptRegistry
    _has_registry = True
except ImportError:
    # Registry not yet implemented
    _has_registry = False
    PromptRegistry = None

__all__ = [
    "Prompt", 
    "PromptType", 
    "PromptMetadata",
    "PromptVariable",
    # Advanced classes available but not part of main API
]

if _has_registry:
    __all__.append("PromptRegistry")