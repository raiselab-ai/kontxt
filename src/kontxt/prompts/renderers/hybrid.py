"""Hybrid prompt renderer implementation."""

import functools
import logging
from typing import Any, Dict, List, Optional

from jinja2 import Environment, TemplateError

from .base import PromptRenderer
from ..types import HybridPromptContent
from ...core.exceptions import TemplateRenderError

logger = logging.getLogger(__name__)


class HybridRenderer(PromptRenderer):
    """Renderer for hybrid prompts with deep nesting support.
    
    Renders hybrid prompt content with recursive template processing,
    supporting nested dictionaries and lists with configurable recursion limits.
    """
    
    def __init__(self, jinja_env: Environment, max_recursion_depth: int = 50):
        """Initialize with configurable recursion depth limit.
        
        Args:
            jinja_env: Jinja2 environment for template rendering
            max_recursion_depth: Maximum recursion depth to prevent stack overflow
        """
        super().__init__(jinja_env)
        self.max_recursion_depth = max_recursion_depth
    
    def render(self, content: HybridPromptContent,
               variables: Dict[str, Any],
               sections: Optional[List[str]] = None) -> Dict[str, Any]:
        """Render hybrid prompt with recursive nesting.
        
        Args:
            content: Hybrid prompt content to render
            variables: Variables to use in rendering
            sections: Optional list of sections to render
            
        Returns:
            Rendered prompt as nested dictionary
            
        Raises:
            TemplateRenderError: If rendering fails
            RecursionError: If maximum recursion depth is exceeded
        """
        rendered = {}
        
        for key, value in content.data.items():
            if sections and key not in sections:
                continue
            
            rendered[key] = self._render_value_recursively(value, variables, depth=0)
        
        return rendered
    
    def _render_value_recursively(self, value: Any, variables: Dict[str, Any], depth: int = 0) -> Any:
        """Recursively render nested structures with depth limit.
        
        Args:
            value: The value to render
            variables: Template variables
            depth: Current recursion depth
            
        Returns:
            Rendered value
            
        Raises:
            RecursionError: If maximum recursion depth is exceeded
        """
        if depth > self.max_recursion_depth:
            logger.warning(f"Maximum recursion depth ({self.max_recursion_depth}) exceeded in hybrid rendering")
            raise RecursionError(
                f"Maximum recursion depth ({self.max_recursion_depth}) exceeded. "
                "This may indicate circular references or excessively nested data. "
                "Consider simplifying your data structure or increasing max_recursion_depth."
            )
        
        if isinstance(value, str):
            vars_tuple = tuple(sorted(variables.items()))
            return self._render_template(value, vars_tuple)
        elif isinstance(value, list):
            return [self._render_value_recursively(item, variables, depth + 1) for item in value]
        elif isinstance(value, dict):
            return {
                k: self._render_value_recursively(v, variables, depth + 1)
                for k, v in value.items()
            }
        else:
            return value
    
    @functools.lru_cache(maxsize=128)
    def _render_template(self, template_str: str, variables_tuple: tuple) -> str:
        """Render template with caching.
        
        Args:
            template_str: Template string to render
            variables_tuple: Variables as tuple for caching
            
        Returns:
            Rendered template string
            
        Raises:
            TemplateRenderError: If rendering fails
        """
        variables = dict(variables_tuple)
        try:
            template = self.jinja_env.from_string(template_str)
            return template.render(**variables)
        except TemplateError as e:
            raise TemplateRenderError("template", str(e))
