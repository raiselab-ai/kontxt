"""Renderer modules for different prompt types.

This module provides the rendering strategy pattern implementation for
structured, freeform, and hybrid prompt types.
"""

from .base import PromptRenderer
from .structured import StructuredRenderer
from .freeform import FreeformRenderer
from .hybrid import HybridRenderer
from ..types import PromptType

__all__ = [
    "PromptRenderer",
    "StructuredRenderer", 
    "FreeformRenderer",
    "HybridRenderer",
    "get_renderer"
]


def get_renderer(prompt_type: PromptType, jinja_env, **kwargs) -> PromptRenderer:
    """Get the appropriate renderer for a prompt type.
    
    Args:
        prompt_type: The type of prompt to render
        jinja_env: Jinja2 environment for template rendering
        **kwargs: Additional arguments for specific renderers
        
    Returns:
        Appropriate renderer instance
    """
    renderers = {
        PromptType.STRUCTURED: StructuredRenderer,
        PromptType.FREEFORM: FreeformRenderer,
        PromptType.HYBRID: HybridRenderer
    }
    
    renderer_class = renderers.get(prompt_type)
    if not renderer_class:
        raise ValueError(f"Unknown prompt type: {prompt_type}")
    
    # Pass additional kwargs for specific renderers (like max_recursion_depth for HybridRenderer)
    if prompt_type == PromptType.HYBRID:
        max_recursion_depth = kwargs.get('max_recursion_depth', 50)
        return renderer_class(jinja_env, max_recursion_depth)
    else:
        return renderer_class(jinja_env)
