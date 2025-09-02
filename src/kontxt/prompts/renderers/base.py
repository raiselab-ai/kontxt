"""Abstract base class for prompt renderers."""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from jinja2 import Environment


class PromptRenderer(ABC):
    """Abstract base class for prompt renderers.
    
    This class defines the interface that all prompt renderers must implement,
    following the strategy pattern to handle different prompt types.
    """
    
    def __init__(self, jinja_env: Environment):
        """Initialize renderer with Jinja environment.
        
        Args:
            jinja_env: Jinja2 environment for template rendering
        """
        self.jinja_env = jinja_env
    
    @abstractmethod
    def render(self, content: Any, variables: Dict[str, Any], 
               sections: Optional[List[str]] = None) -> Any:
        """Render prompt content.
        
        Args:
            content: The prompt content to render (type varies by renderer)
            variables: Variables to use in rendering
            sections: Optional list of sections to render
            
        Returns:
            Rendered prompt (type varies by renderer)
            
        Raises:
            TemplateRenderError: If rendering fails
        """
        pass
