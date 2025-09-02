"""Freeform prompt renderer implementation."""

import functools
from typing import Any, Dict, List, Optional

from jinja2 import TemplateError

from .base import PromptRenderer
from ..types import FreeformPromptContent
from ...core.exceptions import TemplateRenderError


class FreeformRenderer(PromptRenderer):
    """Renderer for freeform prompts.
    
    Renders freeform prompt content to simple string output,
    with support for selective section rendering.
    """
    
    def render(self, content: FreeformPromptContent,
               variables: Dict[str, Any],
               sections: Optional[List[str]] = None) -> str:
        """Render freeform prompt.
        
        Args:
            content: Freeform prompt content to render
            variables: Variables to use in rendering
            sections: Optional list of sections to render
            
        Returns:
            Rendered prompt as string
            
        Raises:
            TemplateRenderError: If rendering fails
        """
        vars_tuple = tuple(sorted(variables.items()))
        
        if sections:
            # Render only requested sections in order
            parts = []
            for section in sections:
                if section in content.sections:
                    parts.append(self._render_template(content.sections[section], vars_tuple))
            return "\n\n".join(parts)
        else:
            return self._render_template(content.template, vars_tuple)
    
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
