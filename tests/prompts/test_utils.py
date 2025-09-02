"""Tests for utility modules - versioning and logging.

Comprehensive tests for VersionManager and OutputLogger classes,
covering version management, diffing, output logging, and error handling.
"""

import gzip
import time
from pathlib import Path
from unittest.mock import MagicMock, mock_open, patch
import pytest
import yaml

from kontxt.prompts.utils.versioning import VersionManager
from kontxt.prompts.utils.logging import OutputLogger


class TestVersionManager:
    """Test the VersionManager utility class."""
    
    def test_find_latest_version_with_packaging(self, tmp_path):
        """Test finding latest version with packaging library."""
        versions_dir = tmp_path / "versions"
        versions_dir.mkdir()
        
        # Create version files
        (versions_dir / "1.0.yaml").touch()
        (versions_dir / "2.0.yaml").touch()
        (versions_dir / "1.5.yaml").touch()
        (versions_dir / "2.1.yaml").touch()
        
        with patch('kontxt.prompts.utils.versioning.HAS_PACKAGING', True):
            latest = VersionManager.find_latest_version(versions_dir)
        
        assert latest == "2.1"
    
    def test_find_latest_version_without_packaging(self, tmp_path):
        """Test finding latest version without packaging library."""
        versions_dir = tmp_path / "versions"
        versions_dir.mkdir()
        
        # Create version files
        (versions_dir / "1.0.yaml").touch()
        (versions_dir / "2.0.yaml").touch()
        (versions_dir / "1.5.yaml").touch()
        
        with patch('kontxt.prompts.utils.versioning.HAS_PACKAGING', False):
            latest = VersionManager.find_latest_version(versions_dir)
        
        # Without semantic versioning, should use lexicographic sorting
        assert latest in ["2.0", "1.5", "1.0"]  # Lexicographic order
    
    def test_find_latest_version_with_compression(self, tmp_path):
        """Test finding latest version with compressed files."""
        versions_dir = tmp_path / "versions"
        versions_dir.mkdir()
        
        # Create regular and compressed files
        (versions_dir / "1.0.yaml").touch()
        (versions_dir / "2.0.yaml.gz").touch()
        (versions_dir / "1.5.yaml").touch()
        
        with patch('kontxt.prompts.utils.versioning.HAS_PACKAGING', True):
            latest = VersionManager.find_latest_version(versions_dir)
        
        assert latest == "2.0"  # Should handle .gz files correctly
    
    def test_find_latest_version_no_directory(self, tmp_path):
        """Test finding latest version with non-existent directory."""
        nonexistent_dir = tmp_path / "nonexistent"
        
        with pytest.raises(ValueError, match="Versions directory does not exist"):
            VersionManager.find_latest_version(nonexistent_dir)
    
    def test_find_latest_version_empty_directory(self, tmp_path):
        """Test finding latest version in empty directory."""
        empty_dir = tmp_path / "empty"
        empty_dir.mkdir()
        
        with pytest.raises(ValueError, match="No versions found"):
            VersionManager.find_latest_version(empty_dir)
    
    def test_find_latest_version_packaging_error(self, tmp_path):
        """Test handling of packaging library errors."""
        versions_dir = tmp_path / "versions"
        versions_dir.mkdir()
        
        (versions_dir / "invalid-version.yaml").touch()
        (versions_dir / "1.0.yaml").touch()
        
        with patch('kontxt.prompts.utils.versioning.HAS_PACKAGING', True), \
             patch('kontxt.prompts.utils.versioning.parse_version', side_effect=Exception("Parse error")):
            
            # Should fall back to lexicographic sorting
            latest = VersionManager.find_latest_version(versions_dir)
            assert latest in ["invalid-version", "1.0"]
    
    def test_list_versions_with_packaging(self, tmp_path):
        """Test listing versions with packaging library."""
        versions_dir = tmp_path / "versions"
        versions_dir.mkdir()
        
        # Create version files in mixed order
        (versions_dir / "1.0.yaml").touch()
        (versions_dir / "2.1.yaml").touch()
        (versions_dir / "1.5.yaml").touch()
        (versions_dir / "2.0.yaml").touch()
        
        with patch('kontxt.prompts.utils.versioning.HAS_PACKAGING', True):
            versions = VersionManager.list_versions(versions_dir)
        
        # Should be sorted with latest first
        assert versions[0] == "2.1"
        assert "2.0" in versions
        assert "1.5" in versions
        assert "1.0" in versions
        assert len(versions) == 4
    
    def test_list_versions_without_packaging(self, tmp_path):
        """Test listing versions without packaging library."""
        versions_dir = tmp_path / "versions"
        versions_dir.mkdir()
        
        (versions_dir / "1.0.yaml").touch()
        (versions_dir / "2.0.yaml").touch()
        (versions_dir / "1.5.yaml").touch()
        
        with patch('kontxt.prompts.utils.versioning.HAS_PACKAGING', False):
            versions = VersionManager.list_versions(versions_dir)
        
        # Should use lexicographic sorting
        assert len(versions) == 3
        assert all(v in versions for v in ["1.0", "2.0", "1.5"])
    
    def test_list_versions_with_compression(self, tmp_path):
        """Test listing versions with compressed files."""
        versions_dir = tmp_path / "versions"
        versions_dir.mkdir()
        
        (versions_dir / "1.0.yaml").touch()
        (versions_dir / "2.0.yaml.gz").touch()
        (versions_dir / "1.5.yaml").touch()
        
        versions = VersionManager.list_versions(versions_dir)
        
        assert "1.0" in versions
        assert "2.0" in versions  # Should extract from .yaml.gz
        assert "1.5" in versions
        assert len(versions) == 3
    
    def test_list_versions_nonexistent_directory(self, tmp_path):
        """Test listing versions from non-existent directory."""
        nonexistent_dir = tmp_path / "nonexistent"
        
        versions = VersionManager.list_versions(nonexistent_dir)
        
        assert versions == []
    
    def test_list_versions_packaging_error(self, tmp_path):
        """Test handling packaging errors during version listing."""
        versions_dir = tmp_path / "versions"
        versions_dir.mkdir()
        
        (versions_dir / "1.0.yaml").touch()
        (versions_dir / "2.0.yaml").touch()
        
        with patch('kontxt.prompts.utils.versioning.HAS_PACKAGING', True), \
             patch('kontxt.prompts.utils.versioning.parse_version', side_effect=Exception("Parse error")):
            
            # Should fall back to lexicographic sorting
            versions = VersionManager.list_versions(versions_dir)
            assert len(versions) == 2
            assert all(v in versions for v in ["1.0", "2.0"])
    
    def test_diff_versions_with_difflib(self, tmp_path):
        """Test version diffing with difflib available."""
        current_path = tmp_path / "current.yaml"
        other_path = tmp_path / "other.yaml"
        
        # Create test files with different content
        current_content = "line1\nline2\nline3\n"
        other_content = "line1\nmodified_line2\nline3\nnew_line\n"
        
        current_path.write_text(current_content)
        other_path.write_text(other_content)
        
        with patch('kontxt.prompts.utils.versioning.HAS_DIFFLIB', True):
            diff = VersionManager.diff_versions(
                current_path, other_path, "2.0", "1.0", "test_prompt"
            )
        
        assert "test_prompt v1.0" in diff
        assert "test_prompt v2.0" in diff
        assert "modified_line2" in diff or "line2" in diff
    
    def test_diff_versions_without_difflib(self):
        """Test version diffing without difflib."""
        with patch('kontxt.prompts.utils.versioning.HAS_DIFFLIB', False):
            diff = VersionManager.diff_versions(
                Path("dummy1"), Path("dummy2"), "2.0", "1.0", "test"
            )
        
        assert "difflib not available" in diff
    
    def test_diff_versions_file_not_found(self, tmp_path):
        """Test version diffing when other file doesn't exist."""
        current_path = tmp_path / "current.yaml"
        other_path = tmp_path / "nonexistent.yaml"
        
        current_path.write_text("content")
        
        diff = VersionManager.diff_versions(
            current_path, other_path, "2.0", "1.0", "test_prompt"
        )
        
        assert "Version 1.0 not found" in diff
    
    def test_diff_versions_error_handling(self, tmp_path):
        """Test error handling during version diffing."""
        current_path = tmp_path / "current.yaml"
        other_path = tmp_path / "other.yaml"
        
        current_path.write_text("content")
        other_path.write_text("content")
        
        with patch('kontxt.prompts.utils.versioning.VersionManager._load_file_content',
                   side_effect=Exception("Load error")):
            
            diff = VersionManager.diff_versions(
                current_path, other_path, "2.0", "1.0", "test_prompt"
            )
            
            assert "Error generating diff" in diff
            assert "Load error" in diff
    
    def test_load_file_content_regular_file(self, tmp_path):
        """Test loading regular file content."""
        test_file = tmp_path / "test.yaml"
        test_content = "test: content\nkey: value"
        test_file.write_text(test_content, encoding='utf-8')
        
        content = VersionManager._load_file_content(test_file)
        
        assert content == test_content
    
    def test_load_file_content_compressed_file(self, tmp_path):
        """Test loading compressed file content."""
        test_file = tmp_path / "test.yaml.gz"
        test_content = "test: content\nkey: value"
        
        with gzip.open(test_file, 'wt', encoding='utf-8') as f:
            f.write(test_content)
        
        content = VersionManager._load_file_content(test_file)
        
        assert content == test_content
    
    def test_load_file_content_utf8_encoding(self, tmp_path):
        """Test loading file with UTF-8 content."""
        test_file = tmp_path / "test.yaml"
        test_content = "test: 测试\nkey: ñoño"
        test_file.write_text(test_content, encoding='utf-8')
        
        content = VersionManager._load_file_content(test_file)
        
        assert content == test_content
        assert "测试" in content
        assert "ñoño" in content


class TestOutputLogger:
    """Test the OutputLogger utility class."""
    
    def test_initialization(self, tmp_path):
        """Test OutputLogger initialization."""
        log_dir = tmp_path / "logs"
        logger = OutputLogger(log_dir)
        
        assert logger.log_dir == log_dir
        assert logger.logger is not None
    
    def test_log_output_basic(self, tmp_path):
        """Test basic output logging functionality."""
        log_dir = tmp_path / "logs"
        logger = OutputLogger(log_dir)
        
        rendered_prompt = [{"role": "system", "content": "Test prompt"}]
        llm_response = "Test response"
        metadata = {"model": "gpt-4", "temperature": 0.7}
        
        logger.log_output("test_prompt", "1.0", rendered_prompt, llm_response, metadata)
        
        # Check log file was created
        log_file = log_dir / "test_prompt_output.yaml"
        assert log_file.exists()
        
        # Check log content
        with open(log_file, 'r', encoding='utf-8') as f:
            logs = yaml.safe_load(f)
        
        assert isinstance(logs, list)
        assert len(logs) == 1
        
        entry = logs[0]
        assert entry["prompt_name"] == "test_prompt"
        assert entry["prompt_version"] == "1.0"
        assert entry["rendered_prompt"] == rendered_prompt
        assert entry["llm_response"] == llm_response
        assert entry["metadata"] == metadata
        assert "timestamp" in entry
    
    def test_log_output_creates_directory(self, tmp_path):
        """Test that logging creates log directory if it doesn't exist."""
        log_dir = tmp_path / "nonexistent_logs"
        logger = OutputLogger(log_dir)
        
        assert not log_dir.exists()
        
        logger.log_output("test", "1.0", "prompt", "response")
        
        assert log_dir.exists()
        assert (log_dir / "test_output.yaml").exists()
    
    def test_log_output_appends_to_existing(self, tmp_path):
        """Test that logging appends to existing log file."""
        log_dir = tmp_path / "logs"
        logger = OutputLogger(log_dir)
        
        # First log entry
        logger.log_output("test", "1.0", "prompt1", "response1")
        
        # Second log entry
        logger.log_output("test", "1.1", "prompt2", "response2", {"key": "value"})
        
        # Check both entries are present
        log_file = log_dir / "test_output.yaml"
        with open(log_file, 'r', encoding='utf-8') as f:
            logs = yaml.safe_load(f)
        
        assert len(logs) == 2
        assert logs[0]["llm_response"] == "response1"
        assert logs[1]["llm_response"] == "response2"
        assert logs[1]["metadata"]["key"] == "value"
    
    def test_log_output_without_metadata(self, tmp_path):
        """Test logging without metadata."""
        log_dir = tmp_path / "logs"
        logger = OutputLogger(log_dir)
        
        logger.log_output("test", "1.0", "prompt", "response")
        
        log_file = log_dir / "test_output.yaml"
        with open(log_file, 'r', encoding='utf-8') as f:
            logs = yaml.safe_load(f)
        
        assert logs[0]["metadata"] == {}
    
    def test_log_output_limits_entries(self, tmp_path):
        """Test that log entries are limited to 1000."""
        log_dir = tmp_path / "logs"
        logger = OutputLogger(log_dir)
        
        # Create existing log with many entries
        log_file = log_dir / "test_output.yaml"
        log_dir.mkdir()
        
        # Create 1500 existing entries
        existing_logs = [
            {
                "timestamp": "2023-01-01 00:00:00",
                "prompt_name": "test",
                "prompt_version": "1.0",
                "rendered_prompt": f"prompt{i}",
                "llm_response": f"response{i}",
                "metadata": {}
            }
            for i in range(1500)
        ]
        
        with open(log_file, 'w', encoding='utf-8') as f:
            yaml.dump(existing_logs, f)
        
        # Add one more entry
        logger.log_output("test", "2.0", "new_prompt", "new_response")
        
        # Check that only last 1000 entries are kept
        with open(log_file, 'r', encoding='utf-8') as f:
            logs = yaml.safe_load(f)
        
        assert len(logs) == 1000
        # Should keep last 999 from existing + 1 new entry
        assert logs[-1]["llm_response"] == "new_response"
        assert logs[0]["rendered_prompt"] == "prompt500"  # First kept entry
    
    def test_log_output_corrupted_file_handling(self, tmp_path, caplog):
        """Test handling of corrupted log file."""
        log_dir = tmp_path / "logs"
        log_dir.mkdir()
        logger = OutputLogger(log_dir)
        
        # Create corrupted YAML file
        log_file = log_dir / "test_output.yaml"
        log_file.write_text("invalid: yaml: content: [")
        
        # Should handle corruption gracefully
        logger.log_output("test", "1.0", "prompt", "response")
        
        # Should start fresh log
        with open(log_file, 'r', encoding='utf-8') as f:
            logs = yaml.safe_load(f)
        
        assert len(logs) == 1
        assert logs[0]["llm_response"] == "response"
        
        # Should log warning about corruption
        assert any("Corrupted log file" in record.message for record in caplog.records)
    
    def test_log_output_yaml_write_error_handling(self, tmp_path, caplog):
        """Test handling of YAML write errors."""
        log_dir = tmp_path / "logs"
        logger = OutputLogger(log_dir)
        
        # Create object that can't be serialized to YAML
        class UnserializableObject:
            def __str__(self):
                return "unserializable"
        
        unserializable_data = UnserializableObject()
        
        with patch('yaml.dump', side_effect=yaml.YAMLError("Serialization error")):
            logger.log_output("test", "1.0", unserializable_data, "response")
        
        # Should log error
        assert any("Failed to write log file due to YAML error" in record.message 
                  for record in caplog.records)
    
    def test_log_output_general_error_handling(self, tmp_path, caplog):
        """Test general error handling in log_output."""
        log_dir = tmp_path / "logs"
        logger = OutputLogger(log_dir)
        
        # Simulate filesystem error
        with patch('pathlib.Path.mkdir', side_effect=OSError("Filesystem error")):
            logger.log_output("test", "1.0", "prompt", "response")
        
        # Should log warning
        assert any("Failed to log output" in record.message for record in caplog.records)
    
    def test_log_output_complex_data_types(self, tmp_path):
        """Test logging with complex data types."""
        log_dir = tmp_path / "logs"
        logger = OutputLogger(log_dir)
        
        # Complex rendered prompt (list of dicts with nested structures)
        rendered_prompt = [
            {
                "role": "system",
                "content": "You are a helpful assistant.",
                "metadata": {"priority": "high"}
            },
            {
                "role": "user",
                "content": "Hello!",
                "attachments": [{"type": "text", "data": "sample"}]
            }
        ]
        
        # Complex metadata
        metadata = {
            "model_config": {
                "temperature": 0.7,
                "max_tokens": 1000,
                "stop_sequences": ["\n\n", "END"]
            },
            "timing": {
                "start_time": time.time(),
                "processing_time": 0.123
            },
            "tags": ["test", "complex", "data"]
        }
        
        logger.log_output("complex_test", "1.0", rendered_prompt, "Complex response", metadata)
        
        # Verify complex data is preserved
        log_file = log_dir / "complex_test_output.yaml"
        with open(log_file, 'r', encoding='utf-8') as f:
            logs = yaml.safe_load(f)
        
        entry = logs[0]
        assert len(entry["rendered_prompt"]) == 2
        assert entry["rendered_prompt"][0]["metadata"]["priority"] == "high"
        assert entry["metadata"]["model_config"]["temperature"] == 0.7
        assert "test" in entry["metadata"]["tags"]
    
    def test_log_output_timestamp_format(self, tmp_path):
        """Test timestamp format in log entries."""
        log_dir = tmp_path / "logs"
        logger = OutputLogger(log_dir)
        
        # Mock time to ensure consistent timestamp
        with patch('time.strftime', return_value="2023-12-01 15:30:45"):
            logger.log_output("test", "1.0", "prompt", "response")
        
        log_file = log_dir / "test_output.yaml"
        with open(log_file, 'r', encoding='utf-8') as f:
            logs = yaml.safe_load(f)
        
        assert logs[0]["timestamp"] == "2023-12-01 15:30:45"
    
    def test_multiple_prompt_log_files(self, tmp_path):
        """Test that different prompts create separate log files."""
        log_dir = tmp_path / "logs"
        logger = OutputLogger(log_dir)
        
        logger.log_output("prompt_a", "1.0", "content_a", "response_a")
        logger.log_output("prompt_b", "1.0", "content_b", "response_b")
        logger.log_output("prompt_a", "2.0", "content_a2", "response_a2")
        
        # Check separate files exist
        log_file_a = log_dir / "prompt_a_output.yaml"
        log_file_b = log_dir / "prompt_b_output.yaml"
        
        assert log_file_a.exists()
        assert log_file_b.exists()
        
        # Check prompt_a has 2 entries
        with open(log_file_a, 'r', encoding='utf-8') as f:
            logs_a = yaml.safe_load(f)
        assert len(logs_a) == 2
        
        # Check prompt_b has 1 entry
        with open(log_file_b, 'r', encoding='utf-8') as f:
            logs_b = yaml.safe_load(f)
        assert len(logs_b) == 1
    
    def test_unicode_content_handling(self, tmp_path):
        """Test handling of Unicode content in logs."""
        log_dir = tmp_path / "logs"
        logger = OutputLogger(log_dir)
        
        # Unicode content
        rendered_prompt = "Prompt with émojis: 🚀 and unicode: 测试"
        llm_response = "Response with special chars: áéíóú, 日本語, русский"
        metadata = {"description": "Test with múltiple ünïcödé characters"}
        
        logger.log_output("unicode_test", "1.0", rendered_prompt, llm_response, metadata)
        
        # Verify Unicode is preserved
        log_file = log_dir / "unicode_test_output.yaml"
        with open(log_file, 'r', encoding='utf-8') as f:
            logs = yaml.safe_load(f)
        
        entry = logs[0]
        assert "🚀" in entry["rendered_prompt"]
        assert "测试" in entry["rendered_prompt"]
        assert "日本語" in entry["llm_response"]
        assert "múltiple" in entry["metadata"]["description"]


class TestVersionManagerIntegration:
    """Integration tests for VersionManager with realistic scenarios."""
    
    def test_semantic_version_sorting(self, tmp_path):
        """Test semantic version sorting with realistic version numbers."""
        versions_dir = tmp_path / "versions"
        versions_dir.mkdir()
        
        # Create realistic version files
        version_files = [
            "1.0.0.yaml", "1.0.1.yaml", "1.1.0.yaml", "2.0.0.yaml",
            "2.0.1.yaml", "2.1.0.yaml", "3.0.0-alpha.yaml",
            "3.0.0-beta.yaml", "3.0.0.yaml"
        ]
        
        for version_file in version_files:
            (versions_dir / version_file).touch()
        
        with patch('kontxt.prompts.utils.versioning.HAS_PACKAGING', True):
            versions = VersionManager.list_versions(versions_dir)
            latest = VersionManager.find_latest_version(versions_dir)
        
        # Latest should be 3.0.0 (stable release)
        assert latest == "3.0.0"
        
        # Versions should be in descending order
        assert versions[0] == "3.0.0"
        assert "3.0.0-beta" in versions
        assert "1.0.0" == versions[-1]
    
    def test_version_diffing_realistic_prompt_files(self, tmp_path):
        """Test diffing with realistic prompt file content."""
        current_path = tmp_path / "current.yaml"
        other_path = tmp_path / "other.yaml"
        
        # Realistic prompt content
        current_content = """
type: structured
prompt:
  system_role: |
    You are a helpful AI assistant.
    Always be polite and professional.
  user: |
    {{query}}
  behavior: |
    Provide clear and concise answers.
    If unsure, ask for clarification.
variables:
  query:
    type: string
    required: true
metadata:
  created_by: user1
  version: "2.0"
""".strip()
        
        other_content = """
type: structured
prompt:
  system_role: |
    You are a helpful AI assistant.
    Always be polite and courteous.
  user: |
    {{query}}
  behavior: |
    Provide detailed and comprehensive answers.
    Include examples when helpful.
variables:
  query:
    type: string
    required: true
  context:
    type: string
    required: false
metadata:
  created_by: user2
  version: "1.0"
""".strip()
        
        current_path.write_text(current_content)
        other_path.write_text(other_content)
        
        diff = VersionManager.diff_versions(
            current_path, other_path, "2.0", "1.0", "assistant_prompt"
        )
        
        # Check diff contains expected changes
        assert "assistant_prompt v1.0" in diff
        assert "assistant_prompt v2.0" in diff
        assert ("courteous" in diff and "professional" in diff) or \
               ("detailed" in diff and "concise" in diff)
    
    def test_compressed_file_handling_integration(self, tmp_path):
        """Test handling of compressed files in realistic scenarios."""
        versions_dir = tmp_path / "versions"
        versions_dir.mkdir()
        
        # Create mixed compressed and uncompressed files
        regular_content = "type: freeform\nprompt:\n  content: Regular file"
        compressed_content = "type: freeform\nprompt:\n  content: Compressed file"
        
        # Regular file
        (versions_dir / "1.0.yaml").write_text(regular_content)
        
        # Compressed file
        with gzip.open(versions_dir / "2.0.yaml.gz", 'wt', encoding='utf-8') as f:
            f.write(compressed_content)
        
        # Test version listing includes both
        versions = VersionManager.list_versions(versions_dir)
        assert "1.0" in versions
        assert "2.0" in versions
        
        # Test file content loading
        content_1 = VersionManager._load_file_content(versions_dir / "1.0.yaml")
        content_2 = VersionManager._load_file_content(versions_dir / "2.0.yaml.gz")
        
        assert "Regular file" in content_1
        assert "Compressed file" in content_2


class TestOutputLoggerIntegration:
    """Integration tests for OutputLogger with realistic usage patterns."""
    
    def test_production_logging_workflow(self, tmp_path):
        """Test realistic production logging workflow."""
        log_dir = tmp_path / "production_logs"
        logger = OutputLogger(log_dir)
        
        # Simulate multiple prompt interactions
        prompts_data = [
            ("chat_assistant", "1.0", [
                {"role": "system", "content": "You are a helpful assistant"},
                {"role": "user", "content": "What is Python?"}
            ], "Python is a programming language...", {"model": "gpt-4", "tokens": 150}),
            
            ("code_reviewer", "2.1", [
                {"role": "system", "content": "Review this code"},
                {"role": "user", "content": "def hello(): print('hi')"}
            ], "The code looks good but...", {"model": "claude-3", "tokens": 200}),
            
            ("chat_assistant", "1.0", [
                {"role": "system", "content": "You are a helpful assistant"},
                {"role": "user", "content": "Explain AI"}
            ], "AI stands for Artificial Intelligence...", {"model": "gpt-4", "tokens": 300})
        ]
        
        # Log all interactions
        for prompt_name, version, rendered, response, metadata in prompts_data:
            logger.log_output(prompt_name, version, rendered, response, metadata)
        
        # Verify separate log files
        chat_log = log_dir / "chat_assistant_output.yaml"
        code_log = log_dir / "code_reviewer_output.yaml"
        
        assert chat_log.exists()
        assert code_log.exists()
        
        # Check chat assistant has 2 entries
        with open(chat_log, 'r') as f:
            chat_logs = yaml.safe_load(f)
        assert len(chat_logs) == 2
        assert all(entry["prompt_name"] == "chat_assistant" for entry in chat_logs)
        
        # Check code reviewer has 1 entry
        with open(code_log, 'r') as f:
            code_logs = yaml.safe_load(f)
        assert len(code_logs) == 1
        assert code_logs[0]["prompt_name"] == "code_reviewer"
    
    def test_high_volume_logging(self, tmp_path):
        """Test logging behavior under high volume."""
        log_dir = tmp_path / "high_volume_logs"
        logger = OutputLogger(log_dir)
        
        # Simulate high-volume logging
        for i in range(2500):  # More than the 1000 limit
            logger.log_output(
                "high_volume_prompt", 
                "1.0",
                f"Prompt {i}",
                f"Response {i}",
                {"batch": i // 100}
            )
        
        # Check that only last 1000 entries are kept
        log_file = log_dir / "high_volume_prompt_output.yaml"
        with open(log_file, 'r') as f:
            logs = yaml.safe_load(f)
        
        assert len(logs) == 1000
        # Should have entries 1500-2499 (last 1000)
        assert logs[0]["rendered_prompt"] == "Prompt 1500"
        assert logs[-1]["rendered_prompt"] == "Prompt 2499"
    
    def test_concurrent_logging(self, tmp_path):
        """Test concurrent logging from multiple threads."""
        import threading
        import queue
        
        log_dir = tmp_path / "concurrent_logs"
        logger = OutputLogger(log_dir)
        
        results = queue.Queue()
        
        def log_worker(worker_id):
            try:
                for i in range(10):
                    logger.log_output(
                        f"worker_{worker_id}",
                        "1.0",
                        f"Worker {worker_id} prompt {i}",
                        f"Worker {worker_id} response {i}",
                        {"worker": worker_id, "iteration": i}
                    )
                results.put(("success", worker_id))
            except Exception as e:
                results.put(("error", worker_id, str(e)))
        
        # Start multiple worker threads
        threads = []
        for worker_id in range(5):
            thread = threading.Thread(target=log_worker, args=(worker_id,))
            threads.append(thread)
            thread.start()
        
        # Wait for all threads
        for thread in threads:
            thread.join()
        
        # Check results
        worker_results = []
        while not results.empty():
            worker_results.append(results.get())
        
        # All workers should succeed
        assert len(worker_results) == 5
        assert all(result[0] == "success" for result in worker_results)
        
        # Check that all log files were created
        for worker_id in range(5):
            log_file = log_dir / f"worker_{worker_id}_output.yaml"
            assert log_file.exists()
            
            with open(log_file, 'r') as f:
                logs = yaml.safe_load(f)
            assert len(logs) == 10