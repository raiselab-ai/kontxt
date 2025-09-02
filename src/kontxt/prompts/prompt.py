"""Prompt class for managing and rendering prompt templates.

This module provides the main Prompt class with async-first architecture,
supporting structured, freeform, and hybrid prompt types with Jinja2 templating.

Features:
- Multiple prompt types (structured, freeform, hybrid)
- Async-first architecture with educational sync wrappers
- Jinja2 templating with variable validation
- Version management and auto-discovery
- Performance tracking and optimization tips
- Output logging and version diffing
- Extensible variable types with optional Pydantic validation
"""

import asyncio
import logging
import threading
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Union

import yaml
from jinja2 import Environment

from .types import (
    PromptType, 
    PromptMetadata, 
    PromptVariable,
    StructuredPromptContent,
    FreeformPromptContent,
    HybridPromptContent
)
from .renderers import get_renderer
from .variables.validator import VariableValidator
from .variables.filters import get_custom_filters
from .loaders.discovery import KontxtDiscovery
from .loaders.file_loader import PromptFileLoader
from .utils.logging import OutputLogger
from .utils.versioning import VersionManager
from ..core import (
    AsyncBase,
    PromptNotFoundError,
    PromptTypeError,
    PromptVersionError,
    TemplateRenderError,
)

# Configure logging
logger = logging.getLogger(__name__)

# Thread-local storage for Jinja environments
_thread_local = threading.local()


class Prompt(AsyncBase):
    """Main Prompt class for loading and rendering prompt templates.
    
    This class provides async-first architecture with educational sync wrappers,
    supporting multiple prompt types and Jinja2 templating. It orchestrates
    all the modular components for a clean, maintainable architecture.
    
    Examples:
        Basic usage:
        >>> prompt = Prompt("sales_agent")
        >>> messages = prompt.render(variables={"role": "sales rep"})
        
        Async usage (recommended for production):
        >>> messages = await prompt.async_render(variables={"role": "sales rep"})
        
        Selective rendering:
        >>> messages = prompt.render(sections=["system_role", "behavior"])
        
        Version management:
        >>> v2_prompt = prompt.create_version("2.1")
        >>> diff = prompt.diff_versions("2.0")
        
        Output logging:
        >>> prompt.log_output(messages, "AI response here")
    """
    
    def __init__(self, 
                 name: str,
                 version: str = "latest",
                 base_path: Optional[Union[str, Path]] = None,
                 enable_performance_tracking: bool = True,
                 enable_educational_tips: bool = None,
                 performance_threshold: float = 0.1,
                 enable_compression: bool = False,
                 max_recursion_depth: int = 50):
        """Initialize a Prompt instance with dependency injection.
        
        Args:
            name: Name of the prompt to load
            version: Version of the prompt (default: "latest")
            base_path: Base path for prompt storage (default: auto-discover .kontxt)
            enable_performance_tracking: Whether to track performance metrics
            enable_educational_tips: Whether to show educational tips (default: from env)
            performance_threshold: Threshold for performance warnings in seconds
            enable_compression: Whether to enable gzip compression for large files
            max_recursion_depth: Maximum recursion depth for hybrid rendering (default: 50)
        """
        super().__init__(enable_performance_tracking)
        
        # Core properties
        self.name = name
        self.version = version
        self.performance_threshold = performance_threshold
        self.max_recursion_depth = max_recursion_depth
        
        # Educational tips from environment or parameter
        import os
        if enable_educational_tips is None:
            self.enable_educational_tips = os.getenv("KONTXT_EDUCATIONAL_TIPS", "1") != "0"
        else:
            self.enable_educational_tips = enable_educational_tips
        
        # Initialize helper components
        self._discovery = KontxtDiscovery()
        self._file_loader = PromptFileLoader(enable_compression)
        self._version_manager = VersionManager()
        self._validator = VariableValidator()
        
        # Set up paths and logging
        self._setup_paths_and_logging(base_path)
        
        # Initialize renderers
        self._renderers = self._create_renderers()
        
        # Storage for loaded prompt data
        self._metadata: Optional[PromptMetadata] = None
        self._variables: Dict[str, PromptVariable] = {}
        self._prompt_content: Union[StructuredPromptContent, FreeformPromptContent, HybridPromptContent, None] = None
        self._loaded = False
        
        # Performance tracking
        self._last_render_time: Optional[float] = None
        
        # Load the prompt synchronously in init for convenience
        self._load_prompt_sync()
    
    def _setup_paths_and_logging(self, base_path: Optional[Union[str, Path]]) -> None:
        """Set up paths and optional logging.
        
        Args:
            base_path: Optional base path override
        """
        # Auto-discover or use provided base path
        if base_path:
            self.base_path = Path(base_path) / "prompts"
        else:
            kontxt_path = self._discovery.discover_kontxt_directory()
            self.base_path = kontxt_path / "prompts"
        
        # Set up output logger
        log_dir = self.base_path.parent / "logs"
        self._output_logger = OutputLogger(log_dir)
    
    def _create_renderers(self) -> Dict[PromptType, Any]:
        """Create renderer instances with injected dependencies.
        
        Returns:
            Dictionary mapping prompt types to renderer instances
        """
        jinja_env = self._get_jinja_env()
        
        return {
            PromptType.STRUCTURED: get_renderer(PromptType.STRUCTURED, jinja_env),
            PromptType.FREEFORM: get_renderer(PromptType.FREEFORM, jinja_env),
            PromptType.HYBRID: get_renderer(PromptType.HYBRID, jinja_env, max_recursion_depth=self.max_recursion_depth)
        }
    
    def _get_jinja_env(self) -> Environment:
        """Get thread-safe Jinja environment with custom filters.
        
        Returns:
            Configured Jinja2 environment
        """
        if not hasattr(_thread_local, 'jinja_env'):
            _thread_local.jinja_env = Environment(
                trim_blocks=True,
                lstrip_blocks=True,
                keep_trailing_newline=True
            )
            # Add custom filters
            _thread_local.jinja_env.filters.update(get_custom_filters())
        
        return _thread_local.jinja_env
    
    def _get_prompt_path(self, version: Optional[str] = None) -> Path:
        """Get the path to a specific prompt version.
        
        Args:
            version: Version to get path for (defaults to current version)
            
        Returns:
            Path to the prompt file
        """
        version = version or self.version
        if version == "latest":
            versions_dir = self.base_path / self.name / "versions"
            version = self._version_manager.find_latest_version(versions_dir)
        
        return self._file_loader.get_prompt_path(self.base_path, self.name, version)
    
    def _load_prompt_sync(self) -> None:
        """Load prompt data from YAML file synchronously."""
        prompt_path = self._get_prompt_path()
        
        if not prompt_path.exists():
            available_versions = self.list_versions()
            raise PromptVersionError(self.name, self.version, available_versions)
        
        try:
            content = self._file_loader.load_file_content(prompt_path)
            data = yaml.safe_load(content)
        except yaml.YAMLError as e:
            raise TemplateRenderError(
                self.name,
                f"Invalid YAML syntax in prompt file: {e}",
                missing_variables=None
            ) from e
        except (IOError, OSError) as e:
            available_prompts = self._discovery.list_available_prompts(self.base_path)
            raise PromptNotFoundError(self.name, available_prompts) from e
        except Exception as e:
            available_prompts = self._discovery.list_available_prompts(self.base_path)
            raise PromptNotFoundError(self.name, available_prompts) from e
        
        self._parse_prompt_data(data)
        self._loaded = True
    
    async def _load_prompt_async(self) -> None:
        """Load prompt data from YAML file asynchronously."""
        prompt_path = self._get_prompt_path()
        
        if not prompt_path.exists():
            available_versions = await self.async_list_versions()
            raise PromptVersionError(self.name, self.version, available_versions)
        
        try:
            content = await self._file_loader.load_file_content_async(prompt_path)
            data = yaml.safe_load(content)
        except yaml.YAMLError as e:
            raise TemplateRenderError(
                self.name,
                f"Invalid YAML syntax in prompt file: {e}",
                missing_variables=None
            ) from e
        except (IOError, OSError) as e:
            available_prompts = self._discovery.list_available_prompts(self.base_path)
            raise PromptNotFoundError(self.name, available_prompts) from e
        except Exception as e:
            available_prompts = self._discovery.list_available_prompts(self.base_path)
            raise PromptNotFoundError(self.name, available_prompts) from e
        
        self._parse_prompt_data(data)
        self._loaded = True
    
    def _parse_prompt_data(self, data: Dict[str, Any]) -> None:
        """Parse loaded YAML data into prompt components.
        
        Args:
            data: Raw YAML data dictionary
        """
        # Handle both nested and flat structures
        if self.name in data:
            data = data[self.name]
        
        prompt_type = PromptType(data.get("type", "structured"))
        raw_content = data.get("prompt", {})
        
        # Create content based on type
        content_classes = {
            PromptType.STRUCTURED: StructuredPromptContent,
            PromptType.FREEFORM: FreeformPromptContent,
            PromptType.HYBRID: HybridPromptContent
        }
        
        content_class = content_classes[prompt_type]
        self._prompt_content = content_class.from_dict(raw_content)
        
        # Parse variables
        self._variables = self._parse_variables(data.get("variables", {}))
        
        # Extract metadata
        metadata_dict = data.get("metadata", {})
        self._metadata = PromptMetadata(
            name=self.name,
            version=data.get("version", self.version),
            type=prompt_type,
            created_by=metadata_dict.get("created_by"),
            created_at=metadata_dict.get("created_at"),
            updated_at=metadata_dict.get("updated_at"),
            tags=metadata_dict.get("tags", []),
            performance_score=metadata_dict.get("performance_score"),
            description=metadata_dict.get("description"),
            available_sections=self._prompt_content.get_available_sections(),
            variable_count=len(self._variables)
        )
    
    def _parse_variables(self, variables_data: Dict[str, Any]) -> Dict[str, PromptVariable]:
        """Parse variable definitions with enhanced type support.
        
        Args:
            variables_data: Raw variables data from YAML
            
        Returns:
            Dictionary of parsed PromptVariable instances
        """
        variables = {}
        
        for var_name, var_def in variables_data.items():
            if isinstance(var_def, dict):
                variables[var_name] = PromptVariable(
                    name=var_name,
                    type=var_def.get("type", "string"),
                    default=var_def.get("default"),
                    required=var_def.get("required", True),
                    values=var_def.get("values"),
                    description=var_def.get("description"),
                    schema=var_def.get("schema")
                )
            else:
                # Simple format: just the type
                variables[var_name] = PromptVariable(name=var_name, type=str(var_def))
        
        return variables
    
    def _validate_sections(self, sections: Optional[List[str]]) -> None:
        """Validate requested sections exist in the prompt.
        
        Args:
            sections: List of sections to validate
            
        Raises:
            ValueError: If invalid sections are requested
        """
        if not sections:
            return
        
        available = self._metadata.available_sections
        invalid = set(sections) - available
        
        if invalid:
            available_list = ", ".join(sorted(available))
            invalid_list = ", ".join(sorted(invalid))
            raise ValueError(
                f"Invalid sections for prompt '{self.name}': [{invalid_list}]. "
                f"Available sections: [{available_list}]. "
                f"Use get_available_sections() to see all options."
            )
    
    def _show_performance_tip(self, execution_time: float, is_async: bool = False) -> None:
        """Show performance tip using logger instead of print.
        
        Args:
            execution_time: Time taken for execution
            is_async: Whether this was an async operation
        """
        if not self.enable_educational_tips:
            return
        
        self._last_render_time = execution_time
        
        if execution_time > self.performance_threshold:
            try:
                if is_async:
                    logger.info(f"Performance: Async render completed in {execution_time:.3f}s")
                else:
                    logger.info(f"Performance: Sync render took {execution_time:.3f}s")
                    logger.info("Tip: Consider using async_render() for better performance in production")
                    
                    # Show comparison if available
                    metrics = self.get_performance_comparison(f"render_{self.name}")
                    if isinstance(metrics, dict) and "performance_gain" in metrics:
                        gain = metrics["performance_gain"]
                        if gain != "0.0%":
                            logger.info(f"     Async version is {gain} faster based on historical data")
            except Exception as e:
                logger.debug(f"Error showing performance tip: {e}")
    
    # Public API Methods
    
    async def async_render(self, 
                          variables: Optional[Dict[str, Any]] = None,
                          sections: Optional[List[str]] = None) -> Union[List[Dict], str, Dict]:
        """Asynchronously render the prompt with given variables.
        
        Args:
            variables: Variables to use in rendering
            sections: Optional list of sections to render
            
        Returns:
            Rendered prompt based on type:
            - STRUCTURED: List[Dict] of chat messages
            - FREEFORM: str of rendered text  
            - HYBRID: Dict of rendered content
            
        Raises:
            TemplateRenderError: If rendering fails
            VariableValidationError: If variable validation fails
            ValueError: If invalid sections are requested
        """
        variables = variables or {}
        
        if sections:
            self._validate_sections(sections)
        
        if not self._loaded:
            await self._load_prompt_async()
        
        # Track performance
        operation = f"render_{self.name}"
        start_time = time.perf_counter()
        
        async def _render():
            validated_vars = self._validator.validate_all_variables(self._variables, variables)
            # Convert to tuple for caching
            vars_tuple = tuple(sorted(validated_vars.items()))
            
            renderer = self._renderers[self._metadata.type]
            return renderer.render(self._prompt_content, dict(vars_tuple), sections)
        
        result = await self._run_async_with_tracking(operation, _render)
        
        # Show performance tip
        execution_time = time.perf_counter() - start_time
        self._show_performance_tip(execution_time, is_async=True)
        
        return result
    
    def render(self, 
               variables: Optional[Dict[str, Any]] = None,
               sections: Optional[List[str]] = None) -> Union[List[Dict], str, Dict]:
        """Synchronously render the prompt with given variables.
        
        This is the learning/development method. In production, use async_render().
        
        Args:
            variables: Variables to use in rendering
            sections: Optional list of sections to render
            
        Returns:
            Rendered prompt based on type
            
        Raises:
            AsyncContextError: If called in async context
            TemplateRenderError: If rendering fails
            VariableValidationError: If variable validation fails
            ValueError: If invalid sections are requested
        """
        self._check_async_context("render", "async_render")
        
        variables = variables or {}
        
        if sections:
            self._validate_sections(sections)
        
        if not self._loaded:
            self._load_prompt_sync()
        
        # Track performance
        operation = f"render_{self.name}"
        start_time = time.perf_counter()
        
        def _render():
            validated_vars = self._validator.validate_all_variables(self._variables, variables)
            # Convert to tuple for caching
            vars_tuple = tuple(sorted(validated_vars.items()))
            
            renderer = self._renderers[self._metadata.type]
            return renderer.render(self._prompt_content, dict(vars_tuple), sections)
        
        result = self._run_sync_with_tracking(operation, _render)
        
        # Show performance tip
        execution_time = time.perf_counter() - start_time
        self._show_performance_tip(execution_time, is_async=False)
        
        return result
    
    def create_version(self, version: str) -> 'Prompt':
        """Create a new Prompt instance for a specific version.
        
        Args:
            version: Version to create instance for
            
        Returns:
            New Prompt instance for the specified version
        """
        return Prompt(
            name=self.name,
            version=version,
            base_path=self.base_path.parent,
            enable_performance_tracking=self._enable_performance_tracking,
            enable_educational_tips=self.enable_educational_tips,
            performance_threshold=self.performance_threshold,
            enable_compression=self._file_loader.enable_compression,
            max_recursion_depth=self.max_recursion_depth
        )
    
    async def async_create_version(self, version: str) -> 'Prompt':
        """Asynchronously create a new Prompt instance for a specific version.
        
        Args:
            version: Version to create instance for
            
        Returns:
            New Prompt instance for the specified version
        """
        prompt = self.create_version(version)
        await prompt._load_prompt_async()
        return prompt
    
    def log_output(self, rendered_prompt: Any, llm_response: str, 
                   metadata: Optional[Dict[str, Any]] = None) -> None:
        """Log rendered prompt and LLM response for tracking.
        
        Args:
            rendered_prompt: The rendered prompt output
            llm_response: The LLM's response
            metadata: Additional metadata to log
        """
        self._output_logger.log_output(
            self.name, 
            self.get_version(), 
            rendered_prompt, 
            llm_response, 
            metadata
        )
    
    def diff_versions(self, other_version: str) -> str:
        """Compare this version with another version.
        
        Args:
            other_version: Version to compare against
            
        Returns:
            Diff string showing changes
        """
        current_path = self._get_prompt_path()
        other_path = self._get_prompt_path(other_version)
        
        return self._version_manager.diff_versions(
            current_path, 
            other_path, 
            self.get_version(), 
            other_version, 
            self.name
        )
    
    def list_versions(self) -> List[str]:
        """List available versions of this prompt.
        
        Returns:
            List of available version strings (latest first)
        """
        versions_dir = self.base_path / self.name / "versions"
        return self._version_manager.list_versions(versions_dir)
    
    async def async_list_versions(self) -> List[str]:
        """Asynchronously list available versions of this prompt.
        
        Returns:
            List of available version strings (latest first)
        """
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.list_versions)
    
    # Property accessors
    
    def get_version(self) -> str:
        """Get the current version string.
        
        Returns:
            Current version string
        """
        if not self._loaded:
            self._load_prompt_sync()
        return self._metadata.version
    
    def get_metadata(self) -> PromptMetadata:
        """Get prompt metadata.
        
        Returns:
            Prompt metadata object
        """
        if not self._loaded:
            self._load_prompt_sync()
        return self._metadata
    
    def get_variables(self) -> Dict[str, PromptVariable]:
        """Get prompt variable definitions.
        
        Returns:
            Dictionary of variable definitions
        """
        if not self._loaded:
            self._load_prompt_sync()
        return self._variables
    
    def get_available_sections(self) -> Set[str]:
        """Get all available sections in this prompt.
        
        Returns:
            Set of available section names
        """
        if not self._loaded:
            self._load_prompt_sync()
        return self._metadata.available_sections
    
    def get_performance_comparison(self, operation: Optional[str] = None) -> Dict[str, Any]:
        """Get sync vs async performance comparison for prompts.
        
        Args:
            operation: Optional operation name to get comparison for
            
        Returns:
            Performance comparison metrics
        """
        base_comparison = super().get_performance_comparison(operation)
        
        # Add prompt-specific metrics
        prompt_metrics = {
            "last_render_time": f"{self._last_render_time:.3f}s" if self._last_render_time else "N/A",
            "performance_threshold": f"{self.performance_threshold:.3f}s",
            "sections_available": list(self.get_available_sections()),
            "variable_count": len(self._variables),
            "recommendation": (
                "Use async_render() for production workloads" 
                if self._last_render_time and self._last_render_time > self.performance_threshold
                else "Current performance is acceptable for sync usage"
            )
        }
        
        return {**base_comparison, "prompt_specific": prompt_metrics}
    
    def get_async_guidance(self) -> Dict[str, Any]:
        """Get detailed async migration guidance specific to prompts.
        
        Returns:
            Dictionary with async guidance information
        """
        base_guidance = super().get_async_guidance()
        
        prompt_guidance = {
            "prompt_specific": {
                "current_prompt": self.name,
                "current_version": self.get_version(),
                "last_render_time": f"{self._last_render_time:.3f}s" if self._last_render_time else "N/A",
                "available_sections": list(self.get_available_sections()),
                "variable_count": len(self._variables),
                "tips": [
                    "Use async_render() for production workloads",
                    "Leverage sections parameter for partial rendering",
                    "Use caching benefits with consistent variable sets",
                    "Use get_performance_comparison() to see async benefits",
                    "Consider async_create_version() for A/B testing",
                    "Use log_output() to track prompt performance",
                    "Use diff_versions() to understand prompt evolution"
                ]
            }
        }
        
        return {**base_guidance, **prompt_guidance}
    
    # Class methods and utilities
    
    @classmethod
    def from_data(cls, name: str, data: Dict[str, Any], **kwargs) -> 'Prompt':
        """Create a Prompt instance from dictionary data (testing hook).
        
        Args:
            name: Name for the prompt
            data: Prompt data dictionary
            **kwargs: Additional initialization parameters
            
        Returns:
            Prompt instance
        """
        instance = cls.__new__(cls)
        super(Prompt, instance).__init__(kwargs.get('enable_performance_tracking', True))
        
        instance.name = name
        instance.version = "test"
        instance.enable_educational_tips = kwargs.get('enable_educational_tips', False)
        instance.performance_threshold = kwargs.get('performance_threshold', 0.1)
        instance.max_recursion_depth = kwargs.get('max_recursion_depth', 50)
        
        # Initialize components
        instance._discovery = KontxtDiscovery()
        instance._file_loader = PromptFileLoader(kwargs.get('enable_compression', False))
        instance._version_manager = VersionManager()
        instance._validator = VariableValidator()
        
        # Initialize without file loading
        instance._renderers = instance._create_renderers()
        instance._output_logger = None  # Not needed for testing
        
        instance._parse_prompt_data(data)
        instance._loaded = True
        
        return instance
    
    def __repr__(self) -> str:
        """Enhanced string representation of the Prompt.
        
        Returns:
            String representation
        """
        if not self._metadata:
            return f"Prompt(name='{self.name}', version='{self.version}', status='unloaded')"
        
        return (
            f"Prompt(name='{self.name}', version='{self._metadata.version}', "
            f"type={self._metadata.type.value}, "
            f"sections={len(self._metadata.available_sections)}, "
            f"variables={self._metadata.variable_count})"
        )