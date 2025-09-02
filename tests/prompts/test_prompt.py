"""Integration tests for the main Prompt class.

Tests the complete Prompt class functionality including:
- Initialization and configuration
- File loading and YAML parsing
- Sync and async rendering
- Version management
- Performance tracking
- Educational features
- Error handling
- Integration between all components
"""

import asyncio
import os
import time
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
import pytest
import yaml

from kontxt.prompts import Prompt, PromptType, PromptMetadata
from kontxt.core.exceptions import (
    PromptNotFoundError,
    PromptVersionError,
    TemplateRenderError,
    AsyncContextError
)
from .fixtures import TestData


class TestPromptInitialization:
    """Test Prompt class initialization and configuration."""
    
    def test_basic_initialization(self, mock_file_system, sample_structured_prompt):
        """Test basic prompt initialization."""
        with patch('kontxt.prompts.prompt.KontxtDiscovery') as mock_discovery:
            mock_discovery.return_value.discover_kontxt_directory.return_value = mock_file_system.kontxt_path
            
            prompt = Prompt("test_prompt")
            
            assert prompt.name == "test_prompt"
            assert prompt.version == "latest"
            assert prompt.enable_educational_tips is True
            assert prompt.performance_threshold == 0.1
            assert prompt._loaded is True  # Should auto-load in init
    
    def test_initialization_with_custom_config(self, mock_file_system):
        """Test prompt initialization with custom configuration."""
        with patch('kontxt.prompts.prompt.KontxtDiscovery') as mock_discovery:
            mock_discovery.return_value.discover_kontxt_directory.return_value = mock_file_system.kontxt_path
            
            prompt = Prompt(
                "test_prompt",
                version="2.0",
                enable_performance_tracking=False,
                enable_educational_tips=False,
                performance_threshold=0.05,
                enable_compression=True,
                max_recursion_depth=100
            )
            
            assert prompt.version == "2.0"
            assert prompt._enable_performance_tracking is False
            assert prompt.enable_educational_tips is False
            assert prompt.performance_threshold == 0.05
            assert prompt._file_loader.enable_compression is True
            assert prompt.max_recursion_depth == 100
    
    def test_initialization_with_environment_variables(self, mock_file_system):
        """Test environment variable configuration."""
        with patch('kontxt.prompts.prompt.KontxtDiscovery') as mock_discovery, \
             patch.dict(os.environ, {
                 'KONTXT_EDUCATIONAL_TIPS': '0',
                 'KONTXT_BASE_PATH': str(mock_file_system.kontxt_path)
             }):
            
            mock_discovery.return_value.discover_kontxt_directory.return_value = mock_file_system.kontxt_path
            
            prompt = Prompt("test_prompt")
            
            assert prompt.enable_educational_tips is False
    
    def test_initialization_with_base_path(self, mock_file_system):
        """Test initialization with explicit base path."""
        prompt = Prompt("test_prompt", base_path=str(mock_file_system.kontxt_path))
        
        assert prompt.base_path == mock_file_system.kontxt_path / "prompts"


class TestPromptLoading:
    """Test prompt loading functionality."""
    
    def test_load_structured_prompt(self, mock_file_system, sample_structured_prompt):
        """Test loading a structured prompt."""
        prompt = Prompt.from_data("test_structured", sample_structured_prompt)
        
        assert prompt.name == "test_structured"
        assert prompt._metadata.type == PromptType.STRUCTURED
        assert prompt._metadata.name == "test_structured"
        assert len(prompt._variables) == 2
        assert "role" in prompt._variables
        assert "customer_name" in prompt._variables
        assert prompt._loaded is True
    
    def test_load_freeform_prompt(self, mock_file_system, sample_freeform_prompt):
        """Test loading a freeform prompt."""
        prompt = Prompt.from_data("test_freeform", sample_freeform_prompt)
        
        assert prompt._metadata.type == PromptType.FREEFORM
        assert hasattr(prompt._prompt_content, 'content')
        assert "Write a brief summary" in prompt._prompt_content.content
    
    def test_load_hybrid_prompt(self, mock_file_system, sample_hybrid_prompt):
        """Test loading a hybrid prompt."""
        prompt = Prompt.from_data("test_hybrid", sample_hybrid_prompt)
        
        assert prompt._metadata.type == PromptType.HYBRID
        assert hasattr(prompt._prompt_content, 'sections')
        assert "introduction" in prompt._prompt_content.sections
    
    def test_load_from_file(self, mock_file_system, sample_structured_prompt):
        """Test loading prompt from YAML file."""
        with patch('kontxt.prompts.prompt.KontxtDiscovery') as mock_discovery, \
             patch('kontxt.prompts.prompt.PromptFileLoader') as mock_loader:
            
            mock_discovery.return_value.discover_kontxt_directory.return_value = mock_file_system.kontxt_path
            mock_loader.return_value.get_prompt_path.return_value = mock_file_system.prompt_file_path
            mock_loader.return_value.load_file_content.return_value = yaml.dump(sample_structured_prompt)
            
            prompt = Prompt("test_prompt")
            
            assert prompt._loaded is True
            assert prompt._metadata.type == PromptType.STRUCTURED
    
    async def test_async_load_from_file(self, mock_file_system, sample_structured_prompt):
        """Test asynchronous loading from file."""
        with patch('kontxt.prompts.prompt.KontxtDiscovery') as mock_discovery, \
             patch('kontxt.prompts.prompt.PromptFileLoader') as mock_loader:
            
            mock_discovery.return_value.discover_kontxt_directory.return_value = mock_file_system.kontxt_path
            mock_loader.return_value.get_prompt_path.return_value = mock_file_system.prompt_file_path
            mock_loader.return_value.load_file_content_async.return_value = yaml.dump(sample_structured_prompt)
            
            # Create prompt without auto-loading
            prompt = Prompt.__new__(Prompt)
            prompt.name = "test_prompt"
            prompt.version = "1.0"
            prompt._loaded = False
            prompt._setup_paths_and_logging(mock_file_system.kontxt_path)
            prompt._renderers = prompt._create_renderers()
            
            await prompt._load_prompt_async()
            
            assert prompt._loaded is True
    
    def test_load_prompt_not_found(self, mock_file_system):
        """Test handling of non-existent prompt."""
        with patch('kontxt.prompts.prompt.KontxtDiscovery') as mock_discovery:
            mock_discovery.return_value.discover_kontxt_directory.return_value = mock_file_system.kontxt_path
            mock_discovery.return_value.list_available_prompts.return_value = ["other_prompt"]
            
            with pytest.raises(PromptNotFoundError) as exc_info:
                Prompt("nonexistent_prompt")
            
            assert "nonexistent_prompt" in str(exc_info.value)
            assert "other_prompt" in str(exc_info.value)
    
    def test_load_prompt_invalid_yaml(self, mock_file_system):
        """Test handling of invalid YAML."""
        with patch('kontxt.prompts.prompt.KontxtDiscovery') as mock_discovery, \
             patch('kontxt.prompts.prompt.PromptFileLoader') as mock_loader:
            
            mock_discovery.return_value.discover_kontxt_directory.return_value = mock_file_system.kontxt_path
            mock_loader.return_value.get_prompt_path.return_value = mock_file_system.prompt_file_path
            mock_loader.return_value.load_file_content.return_value = "invalid: yaml: content: ["
            
            with pytest.raises(TemplateRenderError) as exc_info:
                Prompt("test_prompt")
            
            assert "Invalid YAML syntax" in str(exc_info.value)
    
    def test_load_prompt_version_not_found(self, mock_file_system):
        """Test handling of non-existent version."""
        with patch('kontxt.prompts.prompt.KontxtDiscovery') as mock_discovery, \
             patch('kontxt.prompts.prompt.PromptFileLoader') as mock_loader, \
             patch('kontxt.prompts.prompt.VersionManager') as mock_version_manager:
            
            mock_discovery.return_value.discover_kontxt_directory.return_value = mock_file_system.kontxt_path
            mock_loader.return_value.get_prompt_path.return_value = Path("/nonexistent/file.yaml")
            mock_version_manager.return_value.list_versions.return_value = ["1.0", "2.0"]
            
            with pytest.raises(PromptVersionError) as exc_info:
                Prompt("test_prompt", version="3.0")
            
            assert "3.0" in str(exc_info.value)
            assert "1.0" in str(exc_info.value)
    
    def test_parse_nested_prompt_data(self, sample_structured_prompt):
        """Test parsing of nested prompt data structure."""
        nested_data = {"test_prompt": sample_structured_prompt}
        
        prompt = Prompt.from_data("test_prompt", nested_data)
        
        assert prompt._metadata.type == PromptType.STRUCTURED
        assert len(prompt._variables) == 2
    
    def test_parse_simple_variables(self):
        """Test parsing of simple variable definitions."""
        data = {
            "type": "freeform",
            "prompt": {"content": "Hello {{name}}"},
            "variables": {
                "name": "string",
                "age": "int"
            }
        }
        
        prompt = Prompt.from_data("test", data)
        
        assert len(prompt._variables) == 2
        assert prompt._variables["name"].type == "string"
        assert prompt._variables["age"].type == "int"
        assert prompt._variables["name"].required is True


class TestPromptRendering:
    """Test prompt rendering functionality."""
    
    def test_render_structured_prompt(self, sample_structured_prompt):
        """Test rendering structured prompt."""
        prompt = Prompt.from_data("test", sample_structured_prompt)
        
        variables = {"role": "sales_rep", "customer_name": "Alice"}
        result = prompt.render(variables)
        
        assert isinstance(result, list)
        assert len(result) >= 1
        assert result[0]["role"] == "system"
        assert "sales_rep" in result[0]["content"]
    
    async def test_async_render_structured_prompt(self, sample_structured_prompt):
        """Test async rendering of structured prompt."""
        prompt = Prompt.from_data("test", sample_structured_prompt, enable_educational_tips=False)
        
        variables = {"role": "sales_rep", "customer_name": "Alice"}
        result = await prompt.async_render(variables)
        
        assert isinstance(result, list)
        assert len(result) >= 1
        assert "sales_rep" in result[0]["content"]
    
    def test_render_freeform_prompt(self, sample_freeform_prompt):
        """Test rendering freeform prompt."""
        prompt = Prompt.from_data("test", sample_freeform_prompt)
        
        variables = {"topic": "Python", "word_count": 100}
        result = prompt.render(variables)
        
        assert isinstance(result, str)
        assert "Python" in result
        assert "100" in result
    
    def test_render_hybrid_prompt(self, sample_hybrid_prompt):
        """Test rendering hybrid prompt."""
        prompt = Prompt.from_data("test", sample_hybrid_prompt)
        
        variables = {"name": "Bob", "skills": ["Python", "AI"]}
        result = prompt.render(variables)
        
        assert isinstance(result, dict)
        assert "introduction" in result
        assert "Bob" in result["introduction"]
    
    def test_render_with_sections(self, sample_structured_prompt):
        """Test selective section rendering."""
        prompt = Prompt.from_data("test", sample_structured_prompt)
        
        variables = {"role": "sales_rep", "customer_name": "Alice"}
        result = prompt.render(variables, sections=["system_role"])
        
        assert isinstance(result, list)
        # Should only include system role section
        assert len(result) == 1
        assert result[0]["role"] == "system"
    
    def test_render_with_invalid_sections(self, sample_structured_prompt):
        """Test rendering with invalid sections."""
        prompt = Prompt.from_data("test", sample_structured_prompt)
        
        with pytest.raises(ValueError) as exc_info:
            prompt.render({}, sections=["nonexistent_section"])
        
        assert "Invalid sections" in str(exc_info.value)
        assert "nonexistent_section" in str(exc_info.value)
    
    def test_render_with_missing_variables(self, sample_structured_prompt):
        """Test rendering with missing required variables."""
        prompt = Prompt.from_data("test", sample_structured_prompt)
        
        # Missing required variables
        with pytest.raises(TemplateRenderError) as exc_info:
            prompt.render({"role": "sales_rep"})  # Missing customer_name
        
        assert "Missing required variables" in str(exc_info.value)
    
    def test_render_with_default_variables(self):
        """Test rendering with default variable values."""
        data = {
            "type": "freeform",
            "prompt": {"content": "Hello {{name}}! You are {{age}} years old."},
            "variables": {
                "name": {"type": "string", "required": True},
                "age": {"type": "int", "default": 25, "required": False}
            }
        }
        
        prompt = Prompt.from_data("test", data)
        result = prompt.render({"name": "Alice"})
        
        assert "Alice" in result
        assert "25" in result
    
    def test_render_caching_behavior(self, sample_structured_prompt):
        """Test template rendering caching."""
        prompt = Prompt.from_data("test", sample_structured_prompt)
        
        variables = {"role": "sales_rep", "customer_name": "Alice"}
        
        # First render
        result1 = prompt.render(variables)
        
        # Second render with same variables should use cache
        result2 = prompt.render(variables)
        
        assert result1 == result2
    
    def test_sync_render_in_async_context(self, sample_structured_prompt):
        """Test sync render detection in async context."""
        async def async_test():
            prompt = Prompt.from_data("test", sample_structured_prompt)
            with pytest.raises(AsyncContextError):
                prompt.render({"role": "test", "customer_name": "test"})
        
        asyncio.run(async_test())


class TestVersionManagement:
    """Test version management functionality."""
    
    def test_create_version(self, mock_file_system, sample_structured_prompt):
        """Test creating new version instances."""
        prompt = Prompt.from_data("test", sample_structured_prompt)
        
        new_version = prompt.create_version("2.0")
        
        assert new_version.name == prompt.name
        assert new_version.version == "2.0"
        assert new_version is not prompt
    
    async def test_async_create_version(self, mock_file_system, sample_structured_prompt):
        """Test async version creation."""
        prompt = Prompt.from_data("test", sample_structured_prompt)
        
        with patch.object(prompt, '_load_prompt_async', new_callable=AsyncMock) as mock_load:
            new_version = await prompt.async_create_version("2.0")
            
            assert new_version.version == "2.0"
            mock_load.assert_called_once()
    
    def test_list_versions(self, mock_file_system):
        """Test listing available versions."""
        with patch('kontxt.prompts.prompt.KontxtDiscovery') as mock_discovery, \
             patch('kontxt.prompts.prompt.VersionManager') as mock_version_manager:
            
            mock_discovery.return_value.discover_kontxt_directory.return_value = mock_file_system.kontxt_path
            mock_version_manager.return_value.list_versions.return_value = ["2.0", "1.5", "1.0"]
            
            prompt = Prompt("test_prompt")
            versions = prompt.list_versions()
            
            assert versions == ["2.0", "1.5", "1.0"]
    
    async def test_async_list_versions(self, mock_file_system, sample_structured_prompt):
        """Test async version listing."""
        prompt = Prompt.from_data("test", sample_structured_prompt)
        
        with patch.object(prompt, 'list_versions', return_value=["2.0", "1.0"]) as mock_list:
            versions = await prompt.async_list_versions()
            
            assert versions == ["2.0", "1.0"]
            mock_list.assert_called_once()
    
    def test_diff_versions(self, mock_file_system, sample_structured_prompt):
        """Test version diffing."""
        with patch('kontxt.prompts.prompt.VersionManager') as mock_version_manager:
            mock_version_manager.return_value.diff_versions.return_value = "- old line\n+ new line"
            
            prompt = Prompt.from_data("test", sample_structured_prompt)
            diff = prompt.diff_versions("1.0")
            
            assert "old line" in diff
            assert "new line" in diff
    
    def test_get_version(self, sample_structured_prompt):
        """Test getting current version."""
        data = dict(sample_structured_prompt)
        data["version"] = "1.5"
        
        prompt = Prompt.from_data("test", data)
        
        assert prompt.get_version() == "1.5"


class TestPerformanceTracking:
    """Test performance tracking and educational features."""
    
    def test_performance_tracking_enabled(self, sample_structured_prompt):
        """Test performance tracking functionality."""
        prompt = Prompt.from_data("test", sample_structured_prompt, enable_performance_tracking=True)
        
        variables = {"role": "sales_rep", "customer_name": "Alice"}
        
        with patch('time.perf_counter', side_effect=[0.0, 0.15]):  # 150ms execution
            prompt.render(variables)
        
        assert prompt._last_render_time == 0.15
    
    def test_performance_comparison(self, sample_structured_prompt):
        """Test performance comparison functionality."""
        prompt = Prompt.from_data("test", sample_structured_prompt, enable_performance_tracking=True)
        
        # Simulate some render time
        prompt._last_render_time = 0.12
        
        comparison = prompt.get_performance_comparison()
        
        assert "prompt_specific" in comparison
        assert "last_render_time" in comparison["prompt_specific"]
        assert "recommendation" in comparison["prompt_specific"]
    
    def test_async_guidance(self, sample_structured_prompt):
        """Test async guidance functionality."""
        prompt = Prompt.from_data("test", sample_structured_prompt)
        
        guidance = prompt.get_async_guidance()
        
        assert "prompt_specific" in guidance
        assert "current_prompt" in guidance["prompt_specific"]
        assert "tips" in guidance["prompt_specific"]
        assert len(guidance["prompt_specific"]["tips"]) > 0
    
    def test_educational_tips_logging(self, sample_structured_prompt, caplog):
        """Test educational tips logging."""
        prompt = Prompt.from_data("test", sample_structured_prompt, 
                                enable_educational_tips=True, 
                                performance_threshold=0.05)
        
        # Mock slow execution
        with patch('time.perf_counter', side_effect=[0.0, 0.1]):  # 100ms execution
            prompt.render({"role": "sales_rep", "customer_name": "Alice"})
        
        # Check that educational tip was logged
        assert any("Consider using async_render" in record.message for record in caplog.records)
    
    def test_educational_tips_disabled(self, sample_structured_prompt, caplog):
        """Test that educational tips can be disabled."""
        prompt = Prompt.from_data("test", sample_structured_prompt, 
                                enable_educational_tips=False,
                                performance_threshold=0.05)
        
        # Mock slow execution
        with patch('time.perf_counter', side_effect=[0.0, 0.1]):
            prompt.render({"role": "sales_rep", "customer_name": "Alice"})
        
        # Check that no educational tip was logged
        assert not any("Consider using async_render" in record.message for record in caplog.records)


class TestOutputLogging:
    """Test output logging functionality."""
    
    def test_log_output(self, sample_structured_prompt):
        """Test output logging."""
        with patch('kontxt.prompts.prompt.OutputLogger') as mock_logger_class:
            mock_logger = MagicMock()
            mock_logger_class.return_value = mock_logger
            
            prompt = Prompt.from_data("test", sample_structured_prompt)
            
            rendered_output = [{"role": "system", "content": "Test"}]
            llm_response = "Test response"
            metadata = {"model": "gpt-4"}
            
            prompt.log_output(rendered_output, llm_response, metadata)
            
            mock_logger.log_output.assert_called_once_with(
                "test", "test", rendered_output, llm_response, metadata
            )


class TestPropertyAccessors:
    """Test property accessor methods."""
    
    def test_get_metadata(self, sample_structured_prompt):
        """Test metadata accessor."""
        prompt = Prompt.from_data("test", sample_structured_prompt)
        
        metadata = prompt.get_metadata()
        
        assert isinstance(metadata, PromptMetadata)
        assert metadata.name == "test"
        assert metadata.type == PromptType.STRUCTURED
    
    def test_get_variables(self, sample_structured_prompt):
        """Test variables accessor."""
        prompt = Prompt.from_data("test", sample_structured_prompt)
        
        variables = prompt.get_variables()
        
        assert len(variables) == 2
        assert "role" in variables
        assert "customer_name" in variables
    
    def test_get_available_sections(self, sample_structured_prompt):
        """Test available sections accessor."""
        prompt = Prompt.from_data("test", sample_structured_prompt)
        
        sections = prompt.get_available_sections()
        
        assert isinstance(sections, set)
        assert "system_role" in sections


class TestPromptRepresentation:
    """Test string representation and debugging features."""
    
    def test_repr_loaded_prompt(self, sample_structured_prompt):
        """Test string representation of loaded prompt."""
        prompt = Prompt.from_data("test", sample_structured_prompt)
        
        repr_str = repr(prompt)
        
        assert "Prompt(name='test'" in repr_str
        assert "type=structured" in repr_str
        assert "sections=" in repr_str
        assert "variables=" in repr_str
    
    def test_repr_unloaded_prompt(self):
        """Test string representation of unloaded prompt."""
        # Create unloaded prompt
        prompt = Prompt.__new__(Prompt)
        prompt.name = "test"
        prompt.version = "1.0"
        prompt._metadata = None
        
        repr_str = repr(prompt)
        
        assert "status='unloaded'" in repr_str


class TestEdgeCases:
    """Test edge cases and error conditions."""
    
    def test_empty_variables_dict(self, sample_structured_prompt):
        """Test handling of empty variables."""
        data = dict(sample_structured_prompt)
        data["variables"] = {}
        
        prompt = Prompt.from_data("test", data)
        
        assert len(prompt._variables) == 0
    
    def test_missing_metadata_fields(self):
        """Test handling of missing metadata fields."""
        data = {
            "type": "freeform",
            "prompt": {"content": "Hello world"}
            # Missing metadata section
        }
        
        prompt = Prompt.from_data("test", data)
        metadata = prompt.get_metadata()
        
        assert metadata.created_by is None
        assert metadata.created_at is None
        assert metadata.tags == []
    
    def test_invalid_prompt_type(self):
        """Test handling of invalid prompt type."""
        data = {
            "type": "invalid_type",
            "prompt": {"content": "Hello world"}
        }
        
        with pytest.raises(ValueError):
            Prompt.from_data("test", data)
    
    def test_large_recursion_depth(self):
        """Test handling of large recursion depth in hybrid prompts."""
        data = {
            "type": "hybrid",
            "prompt": {
                "sections": {
                    "intro": "Hello {{name}}",
                    "nested": "{{intro}} - more content"
                }
            },
            "variables": {
                "name": "string"
            }
        }
        
        prompt = Prompt.from_data("test", data, max_recursion_depth=2)
        
        # This should work with small recursion
        result = prompt.render({"name": "Alice"})
        assert "Alice" in str(result)
    
    def test_thread_safety_jinja_env(self, sample_structured_prompt):
        """Test thread safety of Jinja environment."""
        import threading
        
        prompt = Prompt.from_data("test", sample_structured_prompt)
        results = []
        
        def render_in_thread():
            result = prompt.render({"role": "sales_rep", "customer_name": "Alice"})
            results.append(result)
        
        threads = [threading.Thread(target=render_in_thread) for _ in range(3)]
        
        for thread in threads:
            thread.start()
        
        for thread in threads:
            thread.join()
        
        # All results should be identical
        assert len(results) == 3
        assert all(r == results[0] for r in results)


class TestAsyncIntegration:
    """Test async/await integration patterns."""
    
    async def test_async_render_performance_tracking(self, sample_structured_prompt):
        """Test async render with performance tracking."""
        prompt = Prompt.from_data("test", sample_structured_prompt, 
                                enable_performance_tracking=True,
                                enable_educational_tips=False)
        
        variables = {"role": "sales_rep", "customer_name": "Alice"}
        
        start_time = time.perf_counter()
        result = await prompt.async_render(variables)
        end_time = time.perf_counter()
        
        assert isinstance(result, list)
        assert prompt._last_render_time is not None
        assert prompt._last_render_time <= (end_time - start_time)
    
    async def test_concurrent_async_renders(self, sample_structured_prompt):
        """Test concurrent async rendering."""
        prompt = Prompt.from_data("test", sample_structured_prompt, enable_educational_tips=False)
        
        variables = {"role": "sales_rep", "customer_name": "Alice"}
        
        # Run multiple renders concurrently
        tasks = [prompt.async_render(variables) for _ in range(3)]
        results = await asyncio.gather(*tasks)
        
        # All results should be identical
        assert len(results) == 3
        assert all(r == results[0] for r in results)
    
    async def test_async_loading_and_rendering(self, mock_file_system, sample_structured_prompt):
        """Test complete async workflow."""
        with patch('kontxt.prompts.prompt.KontxtDiscovery') as mock_discovery, \
             patch('kontxt.prompts.prompt.PromptFileLoader') as mock_loader:
            
            mock_discovery.return_value.discover_kontxt_directory.return_value = mock_file_system.kontxt_path
            mock_loader.return_value.get_prompt_path.return_value = mock_file_system.prompt_file_path
            mock_loader.return_value.load_file_content_async.return_value = yaml.dump(sample_structured_prompt)
            
            # Create unloaded prompt
            prompt = Prompt.__new__(Prompt)
            prompt.name = "test"
            prompt.version = "1.0"
            prompt._loaded = False
            prompt.enable_educational_tips = False
            prompt.performance_threshold = 0.1
            prompt.max_recursion_depth = 50
            prompt._setup_paths_and_logging(mock_file_system.kontxt_path)
            prompt._renderers = prompt._create_renderers()
            prompt._validator = MagicMock()
            prompt._validator.validate_all_variables.return_value = {"role": "test", "customer_name": "Alice"}
            
            # Test async loading and rendering
            result = await prompt.async_render({"role": "test", "customer_name": "Alice"})
            
            assert prompt._loaded is True
            assert isinstance(result, list)