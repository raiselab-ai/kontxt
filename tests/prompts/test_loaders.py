"""Tests for file loaders and discovery functionality.

This module tests KontxtDiscovery and PromptFileLoader classes
for finding .kontxt directories and loading prompt files.
"""

import asyncio
import gzip
import os
import tempfile
from pathlib import Path
from unittest.mock import patch, mock_open

import pytest

from kontxt.prompts.loaders.discovery import KontxtDiscovery
from kontxt.prompts.loaders.file_loader import PromptFileLoader

from .fixtures import TestData


class TestKontxtDiscovery:
    """Test KontxtDiscovery functionality."""
    
    def test_discover_existing_kontxt_directory(self):
        """Test discovering existing .kontxt directory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create .kontxt directory
            kontxt_dir = Path(temp_dir) / ".kontxt"
            kontxt_dir.mkdir()
            
            # Mock current working directory
            with patch('pathlib.Path.cwd', return_value=Path(temp_dir)):
                result = KontxtDiscovery.discover_kontxt_directory()
                assert result == kontxt_dir
                assert result.exists()
    
    def test_discover_kontxt_directory_up_tree(self):
        """Test discovering .kontxt directory up the directory tree."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create directory structure: temp/parent/.kontxt and temp/parent/child/grandchild
            parent_dir = Path(temp_dir) / "parent"
            kontxt_dir = parent_dir / ".kontxt"
            child_dir = parent_dir / "child"
            grandchild_dir = child_dir / "grandchild"
            
            parent_dir.mkdir()
            kontxt_dir.mkdir()
            child_dir.mkdir()
            grandchild_dir.mkdir()
            
            # Mock current working directory as grandchild
            with patch('pathlib.Path.cwd', return_value=grandchild_dir):
                result = KontxtDiscovery.discover_kontxt_directory()
                assert result == kontxt_dir
                assert result.exists()
    
    def test_discover_creates_kontxt_directory(self):
        """Test that discover creates .kontxt directory if not found."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # Mock current working directory
            with patch('pathlib.Path.cwd', return_value=temp_path):
                result = KontxtDiscovery.discover_kontxt_directory()
                
                expected_path = temp_path / ".kontxt"
                assert result == expected_path
                assert result.exists()
                
                # Check that subdirectories were created
                assert (result / "prompts").exists()
                assert (result / "logs").exists()
    
    def test_discover_with_environment_variable(self):
        """Test discovery using KONTXT_BASE_PATH environment variable."""
        with tempfile.TemporaryDirectory() as temp_dir:
            kontxt_path = Path(temp_dir) / "custom_kontxt"
            kontxt_path.mkdir()
            
            with patch.dict(os.environ, {'KONTXT_BASE_PATH': str(kontxt_path)}):
                result = KontxtDiscovery.discover_kontxt_directory()
                assert result == kontxt_path
    
    def test_discover_with_invalid_environment_variable(self):
        """Test discovery with invalid KONTXT_BASE_PATH environment variable."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # Set invalid environment path
            with patch.dict(os.environ, {'KONTXT_BASE_PATH': '/nonexistent/path'}):
                with patch('pathlib.Path.cwd', return_value=temp_path):
                    result = KontxtDiscovery.discover_kontxt_directory()
                    
                    # Should fall back to creating in current directory
                    expected_path = temp_path / ".kontxt"
                    assert result == expected_path
                    assert result.exists()
    
    def test_discover_permission_error(self):
        """Test handling of permission errors when creating .kontxt directory."""
        with patch('pathlib.Path.cwd', return_value=Path("/read-only-path")):
            with patch('pathlib.Path.mkdir', side_effect=PermissionError("Permission denied")):
                with pytest.raises(PermissionError) as exc_info:
                    KontxtDiscovery.discover_kontxt_directory()
                
                error_msg = str(exc_info.value)
                assert "Cannot create .kontxt directory" in error_msg
                assert "KONTXT_BASE_PATH" in error_msg
    
    def test_list_available_prompts(self):
        """Test listing available prompts."""
        with tempfile.TemporaryDirectory() as temp_dir:
            base_path = Path(temp_dir)
            
            # Create prompt directories
            (base_path / "prompt1" / "versions").mkdir(parents=True)
            (base_path / "prompt2" / "versions").mkdir(parents=True)
            (base_path / "not_a_prompt").mkdir()  # No versions directory
            (base_path / "prompt3" / "versions").mkdir(parents=True)
            
            result = KontxtDiscovery.list_available_prompts(base_path)
            
            assert set(result) == {"prompt1", "prompt2", "prompt3"}
            assert "not_a_prompt" not in result
    
    def test_list_available_prompts_empty_directory(self):
        """Test listing prompts in empty directory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            base_path = Path(temp_dir)
            result = KontxtDiscovery.list_available_prompts(base_path)
            assert result == []
    
    def test_list_available_prompts_nonexistent_directory(self):
        """Test listing prompts in nonexistent directory."""
        nonexistent_path = Path("/nonexistent/path")
        result = KontxtDiscovery.list_available_prompts(nonexistent_path)
        assert result == []
    
    def test_discover_depth_limit(self):
        """Test that discovery has depth limit."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create deeply nested structure without .kontxt
            current_path = Path(temp_dir)
            for i in range(15):  # More than the limit of 10
                current_path = current_path / f"level{i}"
                current_path.mkdir()
            
            # Mock current working directory at deepest level
            with patch('pathlib.Path.cwd', return_value=current_path):
                result = KontxtDiscovery.discover_kontxt_directory()
                
                # Should create .kontxt at deepest level since limit was reached
                expected_path = current_path / ".kontxt"
                assert result == expected_path
                assert result.exists()


class TestPromptFileLoader:
    """Test PromptFileLoader functionality."""
    
    def test_basic_file_loader_creation(self):
        """Test creating PromptFileLoader."""
        loader = PromptFileLoader()
        assert loader.enable_compression is False
        
        loader_with_compression = PromptFileLoader(enable_compression=True)
        assert loader_with_compression.enable_compression is True
    
    def test_load_file_content_regular_file(self):
        """Test loading regular YAML file content."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as temp_file:
            test_content = "test: content\nversion: 1.0"
            temp_file.write(test_content)
            temp_file_path = Path(temp_file.name)
        
        try:
            loader = PromptFileLoader()
            result = loader.load_file_content(temp_file_path)
            assert result == test_content
        finally:
            temp_file_path.unlink()
    
    def test_load_file_content_compressed_file(self):
        """Test loading compressed YAML file content."""
        with tempfile.NamedTemporaryFile(suffix='.yaml.gz', delete=False) as temp_file:
            test_content = "compressed: content\nversion: 2.0"
            with gzip.open(temp_file.name, 'wt', encoding='utf-8') as gz_file:
                gz_file.write(test_content)
            temp_file_path = Path(temp_file.name)
        
        try:
            loader = PromptFileLoader()
            result = loader.load_file_content(temp_file_path)
            assert result == test_content
        finally:
            temp_file_path.unlink()
    
    def test_load_file_content_file_not_found(self):
        """Test handling of file not found error."""
        loader = PromptFileLoader()
        nonexistent_path = Path("/nonexistent/file.yaml")
        
        with pytest.raises((IOError, FileNotFoundError)):
            loader.load_file_content(nonexistent_path)
    
    @pytest.mark.asyncio
    async def test_load_file_content_async_regular_file(self):
        """Test loading regular file content asynchronously."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as temp_file:
            test_content = "async: content\nversion: 3.0"
            temp_file.write(test_content)
            temp_file_path = Path(temp_file.name)
        
        try:
            loader = PromptFileLoader()
            result = await loader.load_file_content_async(temp_file_path)
            assert result == test_content
        finally:
            temp_file_path.unlink()
    
    @pytest.mark.asyncio
    async def test_load_file_content_async_compressed_file(self):
        """Test loading compressed file content asynchronously."""
        with tempfile.NamedTemporaryFile(suffix='.yaml.gz', delete=False) as temp_file:
            test_content = "async_compressed: content\nversion: 4.0"
            with gzip.open(temp_file.name, 'wt', encoding='utf-8') as gz_file:
                gz_file.write(test_content)
            temp_file_path = Path(temp_file.name)
        
        try:
            loader = PromptFileLoader()
            result = await loader.load_file_content_async(temp_file_path)
            assert result == test_content
        finally:
            temp_file_path.unlink()
    
    @pytest.mark.asyncio
    async def test_load_file_content_async_file_not_found(self):
        """Test async handling of file not found error."""
        loader = PromptFileLoader()
        nonexistent_path = Path("/nonexistent/async_file.yaml")
        
        with pytest.raises((IOError, FileNotFoundError)):
            await loader.load_file_content_async(nonexistent_path)
    
    def test_get_prompt_path_basic(self):
        """Test getting prompt path."""
        loader = PromptFileLoader()
        base_path = Path("/base")
        name = "test_prompt"
        version = "1.0"
        
        result = loader.get_prompt_path(base_path, name, version)
        expected = base_path / "test_prompt" / "versions" / "1.0.yaml"
        
        assert result == expected
    
    def test_get_prompt_path_with_compression_disabled(self):
        """Test getting prompt path with compression disabled."""
        loader = PromptFileLoader(enable_compression=False)
        
        with tempfile.TemporaryDirectory() as temp_dir:
            base_path = Path(temp_dir)
            name = "test_prompt"
            version = "1.0"
            
            # Create directories
            prompt_dir = base_path / name / "versions"
            prompt_dir.mkdir(parents=True)
            
            # Create only compressed file
            compressed_file = prompt_dir / "1.0.yaml.gz"
            compressed_file.touch()
            
            result = loader.get_prompt_path(base_path, name, version)
            expected = base_path / name / "versions" / "1.0.yaml"
            
            # Should return regular path even if only compressed exists
            assert result == expected
    
    def test_get_prompt_path_with_compression_enabled(self):
        """Test getting prompt path with compression enabled."""
        loader = PromptFileLoader(enable_compression=True)
        
        with tempfile.TemporaryDirectory() as temp_dir:
            base_path = Path(temp_dir)
            name = "test_prompt"
            version = "1.0"
            
            # Create directories
            prompt_dir = base_path / name / "versions"
            prompt_dir.mkdir(parents=True)
            
            # Create only compressed file
            compressed_file = prompt_dir / "1.0.yaml.gz"
            compressed_file.touch()
            
            result = loader.get_prompt_path(base_path, name, version)
            
            # Should return compressed path since regular doesn't exist
            assert result == compressed_file
    
    def test_get_prompt_path_prefers_regular_over_compressed(self):
        """Test that regular file is preferred over compressed when both exist."""
        loader = PromptFileLoader(enable_compression=True)
        
        with tempfile.TemporaryDirectory() as temp_dir:
            base_path = Path(temp_dir)
            name = "test_prompt"
            version = "1.0"
            
            # Create directories
            prompt_dir = base_path / name / "versions"
            prompt_dir.mkdir(parents=True)
            
            # Create both regular and compressed files
            regular_file = prompt_dir / "1.0.yaml"
            compressed_file = prompt_dir / "1.0.yaml.gz"
            regular_file.touch()
            compressed_file.touch()
            
            result = loader.get_prompt_path(base_path, name, version)
            
            # Should prefer regular file
            assert result == regular_file
    
    def test_file_encoding_handling(self):
        """Test proper UTF-8 encoding handling."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False, encoding='utf-8') as temp_file:
            # Use Unicode content
            test_content = "test: ñáéíóú content\nversion: 1.0\nemoji: 🚀"
            temp_file.write(test_content)
            temp_file_path = Path(temp_file.name)
        
        try:
            loader = PromptFileLoader()
            result = loader.load_file_content(temp_file_path)
            assert result == test_content
            assert "ñáéíóú" in result
            assert "🚀" in result
        finally:
            temp_file_path.unlink()
    
    @pytest.mark.asyncio
    async def test_async_file_encoding_handling(self):
        """Test proper UTF-8 encoding handling in async mode."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False, encoding='utf-8') as temp_file:
            # Use Unicode content
            test_content = "async_test: ñáéíóú content\nversion: 1.0\nemoji: 🎯"
            temp_file.write(test_content)
            temp_file_path = Path(temp_file.name)
        
        try:
            loader = PromptFileLoader()
            result = await loader.load_file_content_async(temp_file_path)
            assert result == test_content
            assert "ñáéíóú" in result
            assert "🎯" in result
        finally:
            temp_file_path.unlink()


class TestLoadersIntegration:
    """Test integration between discovery and file loading."""
    
    def test_complete_prompt_loading_workflow(self):
        """Test complete workflow from discovery to loading."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # Set up directory structure
            with patch('pathlib.Path.cwd', return_value=temp_path):
                kontxt_path = KontxtDiscovery.discover_kontxt_directory()
                prompts_path = kontxt_path / "prompts"
                
                # Create a test prompt
                prompt_dir = prompts_path / "test_prompt" / "versions"
                prompt_dir.mkdir(parents=True)
                
                # Create prompt file with test data
                prompt_file = prompt_dir / "1.0.yaml"
                import yaml
                with open(prompt_file, 'w') as f:
                    yaml.dump(TestData.STRUCTURED_PROMPT_DATA, f)
                
                # List available prompts
                available_prompts = KontxtDiscovery.list_available_prompts(prompts_path)
                assert "test_prompt" in available_prompts
                
                # Load prompt file
                loader = PromptFileLoader()
                prompt_path = loader.get_prompt_path(prompts_path, "test_prompt", "1.0")
                content = loader.load_file_content(prompt_path)
                
                # Verify content
                loaded_data = yaml.safe_load(content)
                assert loaded_data["type"] == "structured"
                assert loaded_data["version"] == "1.2"
    
    @pytest.mark.asyncio
    async def test_async_complete_workflow(self):
        """Test complete async workflow."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            with patch('pathlib.Path.cwd', return_value=temp_path):
                kontxt_path = KontxtDiscovery.discover_kontxt_directory()
                prompts_path = kontxt_path / "prompts"
                
                # Create test prompt
                prompt_dir = prompts_path / "async_prompt" / "versions"
                prompt_dir.mkdir(parents=True)
                
                prompt_file = prompt_dir / "2.0.yaml"
                import yaml
                with open(prompt_file, 'w') as f:
                    yaml.dump(TestData.FREEFORM_PROMPT_DATA, f)
                
                # Load asynchronously
                loader = PromptFileLoader()
                prompt_path = loader.get_prompt_path(prompts_path, "async_prompt", "2.0")
                content = await loader.load_file_content_async(prompt_path)
                
                # Verify content
                loaded_data = yaml.safe_load(content)
                assert loaded_data["type"] == "freeform"
                assert loaded_data["version"] == "1.0"
    
    def test_compressed_file_workflow(self):
        """Test workflow with compressed files."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            with patch('pathlib.Path.cwd', return_value=temp_path):
                kontxt_path = KontxtDiscovery.discover_kontxt_directory()
                prompts_path = kontxt_path / "prompts"
                
                # Create compressed prompt
                prompt_dir = prompts_path / "compressed_prompt" / "versions"
                prompt_dir.mkdir(parents=True)
                
                prompt_file = prompt_dir / "1.0.yaml.gz"
                import yaml
                with gzip.open(prompt_file, 'wt', encoding='utf-8') as f:
                    yaml.dump(TestData.HYBRID_PROMPT_DATA, f)
                
                # Load with compression enabled
                loader = PromptFileLoader(enable_compression=True)
                prompt_path = loader.get_prompt_path(prompts_path, "compressed_prompt", "1.0")
                content = loader.load_file_content(prompt_path)
                
                # Verify content
                loaded_data = yaml.safe_load(content)
                assert loaded_data["type"] == "hybrid"
                assert loaded_data["version"] == "2.0"
    
    def test_error_handling_workflow(self):
        """Test error handling in complete workflow."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            with patch('pathlib.Path.cwd', return_value=temp_path):
                kontxt_path = KontxtDiscovery.discover_kontxt_directory()
                prompts_path = kontxt_path / "prompts"
                
                # Try to list prompts in empty directory
                available_prompts = KontxtDiscovery.list_available_prompts(prompts_path)
                assert available_prompts == []
                
                # Try to load nonexistent prompt
                loader = PromptFileLoader()
                prompt_path = loader.get_prompt_path(prompts_path, "nonexistent", "1.0")
                
                with pytest.raises((IOError, FileNotFoundError)):
                    loader.load_file_content(prompt_path)


class TestLoadersPerformance:
    """Test performance characteristics of loaders."""
    
    def test_large_file_loading(self):
        """Test loading large prompt files."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as temp_file:
            # Create large content
            large_content = "test: content\n" + "data: line\n" * 10000  # 10k lines
            temp_file.write(large_content)
            temp_file_path = Path(temp_file.name)
        
        try:
            loader = PromptFileLoader()
            result = loader.load_file_content(temp_file_path)
            
            # Should handle large files
            assert len(result) > 100000  # Should be quite large
            assert result.startswith("test: content")
        finally:
            temp_file_path.unlink()
    
    @pytest.mark.asyncio
    async def test_concurrent_async_loading(self):
        """Test concurrent async file loading."""
        # Create multiple temp files
        temp_files = []
        for i in range(5):
            temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False)
            content = f"file_{i}: content\nversion: {i}\n"
            temp_file.write(content)
            temp_file.close()
            temp_files.append(Path(temp_file.name))
        
        try:
            loader = PromptFileLoader()
            
            # Load all files concurrently
            tasks = [
                loader.load_file_content_async(path) 
                for path in temp_files
            ]
            results = await asyncio.gather(*tasks)
            
            # Verify all results
            assert len(results) == 5
            for i, result in enumerate(results):
                assert f"file_{i}: content" in result
                assert f"version: {i}" in result
                
        finally:
            for temp_file in temp_files:
                temp_file.unlink()
    
    def test_compression_performance(self):
        """Test performance impact of compression."""
        with tempfile.TemporaryDirectory() as temp_dir:
            base_path = Path(temp_dir)
            
            # Create regular file
            regular_file = base_path / "regular.yaml"
            content = "test: data\n" * 1000  # 1k lines
            with open(regular_file, 'w') as f:
                f.write(content)
            
            # Create compressed file
            compressed_file = base_path / "compressed.yaml.gz"
            with gzip.open(compressed_file, 'wt', encoding='utf-8') as f:
                f.write(content)
            
            loader = PromptFileLoader()
            
            # Load both files
            regular_result = loader.load_file_content(regular_file)
            compressed_result = loader.load_file_content(compressed_file)
            
            # Content should be identical
            assert regular_result == compressed_result
            
            # Compressed file should be smaller on disk
            assert compressed_file.stat().st_size < regular_file.stat().st_size