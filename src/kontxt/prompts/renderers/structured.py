"""Structured prompt renderer implementation."""

import functools
from typing import Any, Dict, List, Optional

from jinja2 import TemplateError, meta

from .base import PromptRenderer
from ..types import StructuredPromptContent, FewShotExample
from ...core.exceptions import TemplateRenderError


class StructuredRenderer(PromptRenderer):
    """Renderer for structured prompts.
    
    Renders structured prompt content to chat messages format,
    with support for system messages, few-shot examples, and custom sections.
    """
    
    def render(self, content: StructuredPromptContent, 
               variables: Dict[str, Any],
               sections: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """Render structured prompt to chat messages.
        
        Args:
            content: Structured prompt content to render
            variables: Variables to use in rendering
            sections: Optional list of sections to render
            
        Returns:
            List of chat message dictionaries
            
        Raises:
            TemplateRenderError: If rendering fails
        """
        messages = []
        render_sections = sections or list(content.get_available_sections())
        
        # Build system message
        system_parts = self._build_system_parts(content, variables, render_sections)
        if system_parts:
            messages.append({"role": "system", "content": "\n\n".join(system_parts)})
        
        # Add few-shot examples
        if "few_shots" in render_sections:
            messages.extend(self._render_few_shots(content.few_shots, variables))
        
        # Add user/assistant messages
        messages.extend(self._render_user_assistant(content, variables, render_sections))
        
        # Handle custom sections
        messages.extend(self._render_custom_sections(content, variables, render_sections))
        
        return messages
    
    def _build_system_parts(self, content: StructuredPromptContent, 
                           variables: Dict[str, Any],
                           render_sections: List[str]) -> List[str]:
        """Build system message parts.
        
        Args:
            content: Structured prompt content
            variables: Variables for rendering
            render_sections: Sections to render
            
        Returns:
            List of system message parts
        """
        parts = []
        
        vars_tuple = tuple(sorted(variables.items()))
        
        if "system_role" in render_sections and content.system_role:
            parts.append(self._render_template(content.system_role, vars_tuple))
        
        if "behavior" in render_sections and content.behavior:
            parts.append(self._render_template(content.behavior, vars_tuple))
        
        if "restrictions" in render_sections and content.restrictions:
            parts.append(f"RESTRICTIONS:\n{self._render_template(content.restrictions, vars_tuple)}")
        
        if "format" in render_sections and content.format:
            parts.append(f"FORMAT:\n{self._render_template(content.format, vars_tuple)}")
        
        return parts
    
    def _render_few_shots(self, few_shots: List[FewShotExample], 
                         variables: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Render few-shot examples with multi-turn support.
        
        Args:
            few_shots: List of few-shot examples
            variables: Variables for rendering
            
        Returns:
            List of chat messages for examples
        """
        messages = []
        vars_tuple = tuple(sorted(variables.items()))
        
        for example in few_shots:
            if isinstance(example.input, list):
                # Multi-turn example
                for turn in example.input:
                    messages.append({
                        "role": turn.get("role", "user"),
                        "content": self._render_template(turn.get("content", ""), vars_tuple)
                    })
            else:
                # Single turn
                messages.append({
                    "role": "user",
                    "content": self._render_template(example.input, vars_tuple)
                })
            
            if isinstance(example.output, list):
                # Multi-turn output
                for turn in example.output:
                    messages.append({
                        "role": turn.get("role", "assistant"),
                        "content": self._render_template(turn.get("content", ""), vars_tuple)
                    })
            else:
                # Single turn output
                messages.append({
                    "role": "assistant",
                    "content": self._render_template(example.output, vars_tuple)
                })
        
        return messages
    
    def _render_user_assistant(self, content: StructuredPromptContent,
                              variables: Dict[str, Any],
                              render_sections: List[str]) -> List[Dict[str, Any]]:
        """Render user and assistant messages.
        
        Args:
            content: Structured prompt content
            variables: Variables for rendering
            render_sections: Sections to render
            
        Returns:
            List of user/assistant chat messages
        """
        messages = []
        vars_tuple = tuple(sorted(variables.items()))
        
        if "user" in render_sections and content.user:
            messages.append({
                "role": "user",
                "content": self._render_template(content.user, vars_tuple)
            })
        
        if "assistant" in render_sections and content.assistant:
            messages.append({
                "role": "assistant",
                "content": self._render_template(content.assistant, vars_tuple)
            })
        
        return messages
    
    def _render_custom_sections(self, content: StructuredPromptContent,
                               variables: Dict[str, Any],
                               render_sections: List[str]) -> List[Dict[str, Any]]:
        """Render custom sections.
        
        Args:
            content: Structured prompt content
            variables: Variables for rendering
            render_sections: Sections to render
            
        Returns:
            List of custom section messages
        """
        messages = []
        vars_tuple = tuple(sorted(variables.items()))
        standard_sections = {
            "system_role", "behavior", "restrictions", "format", 
            "few_shots", "user", "assistant"
        }
        
        custom_sections_to_render = [
            s for s in render_sections 
            if s in content.custom_sections and s not in standard_sections
        ]
        
        for section in custom_sections_to_render:
            messages.append({
                "role": "system",
                "content": f"{section.upper()}:\n{self._render_template(content.custom_sections[section], vars_tuple)}"
            })
        
        return messages
    
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
            
            # Find missing variables
            ast = self.jinja_env.parse(template_str)
            required_vars = meta.find_undeclared_variables(ast)
            missing_vars = required_vars - set(variables.keys())
            
            if missing_vars:
                raise TemplateRenderError(
                    "template",
                    "Missing required variables",
                    missing_variables=list(missing_vars)
                )
            
            return template.render(**variables)
        except TemplateError as e:
            raise TemplateRenderError("template", str(e))
