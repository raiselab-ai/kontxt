"""Test fixtures for prompt testing.

This module provides common fixtures and test data for all prompt tests.
"""

import json
import tempfile
from pathlib import Path
from typing import Any, Dict

import pytest
import yaml

from kontxt.prompts.types import (
    PromptType, 
    PromptMetadata, 
    PromptVariable,
    FewShotExample,
    StructuredPromptContent,
    FreeformPromptContent,
    HybridPromptContent
)


class TestData:
    """Container for common test data."""
    
    # Sample variable definitions
    VARIABLES = {
        "role": {
            "type": "enum",
            "values": ["assistant", "expert", "helper"],
            "default": "assistant",
            "required": True,
            "description": "The role of the AI"
        },
        "experience_level": {
            "type": "enum", 
            "values": ["junior", "senior", "expert"],
            "default": "senior"
        },
        "topic": {
            "type": "string",
            "required": True,
            "description": "The main topic to discuss"
        },
        "temperature": {
            "type": "float",
            "default": 0.7,
            "required": False
        },
        "max_tokens": {
            "type": "integer", 
            "default": 1000
        },
        "verbose": {
            "type": "boolean",
            "default": False
        }
    }
    
    # Sample structured prompt content
    STRUCTURED_PROMPT_DATA = {
        "type": "structured",
        "version": "1.2",
        "metadata": {
            "created_by": "test@example.com",
            "tags": ["sales", "conversation"],
            "performance_score": 0.95,
            "description": "A sales agent prompt for customer interactions"
        },
        "variables": VARIABLES,
        "prompt": {
            "system_role": "You are a {{experience_level}} {{role}} specializing in {{topic}}.",
            "behavior": "Be helpful, professional, and concise. Always maintain a {{experience_level}} level of expertise.",
            "restrictions": "Never share confidential information or make promises beyond your capabilities.",
            "format": "Respond in a structured format with clear reasoning.",
            "few_shots": [
                {
                    "input": "Can you help me with sales strategies?",
                    "output": "I'd be happy to help with sales strategies. What specific area would you like to focus on?",
                    "reasoning": "Open-ended response to gather more specific requirements"
                },
                {
                    "input": "What's the best way to close a deal?",
                    "output": "Successful deal closing involves understanding customer needs, addressing objections, and creating urgency while maintaining trust.",
                    "reasoning": "Comprehensive answer covering key closing principles"
                }
            ],
            "custom_field": "This is a custom section for testing"
        }
    }
    
    # Sample freeform prompt content
    FREEFORM_PROMPT_DATA = {
        "type": "freeform",
        "version": "1.0", 
        "variables": {"topic": {"type": "string"}},
        "prompt": {
            "introduction": "Welcome to our {{topic}} discussion.",
            "main_content": "Let's explore {{topic}} in detail with practical examples.",
            "conclusion": "Thank you for learning about {{topic}} with us."
        }
    }
    
    # Sample hybrid prompt content
    HYBRID_PROMPT_DATA = {
        "type": "hybrid",
        "version": "2.0",
        "variables": {
            "format": {"type": "enum", "values": ["json", "yaml", "text"]},
            "include_metadata": {"type": "boolean", "default": True}
        },
        "prompt": {
            "response_format": "{{format}}",
            "include_metadata": "{{include_metadata}}",
            "instructions": ["Step 1: Analyze the request", "Step 2: Format the response"],
            "nested_config": {
                "timeout": 30,
                "retries": 3,
                "custom_template": "Process in {{format}} format"
            }
        }
    }


@pytest.fixture
def temp_kontxt_dir():
    """Create a temporary .kontxt directory structure for testing."""
    with tempfile.TemporaryDirectory() as temp_dir:
        kontxt_path = Path(temp_dir) / ".kontxt"
        prompts_path = kontxt_path / "prompts"
        logs_path = kontxt_path / "logs"
        
        kontxt_path.mkdir()
        prompts_path.mkdir()
        logs_path.mkdir()
        
        yield kontxt_path


@pytest.fixture
def sample_prompt_files(temp_kontxt_dir):
    """Create sample prompt files for testing."""
    prompts_path = temp_kontxt_dir / "prompts"
    
    # Create sales_agent prompt
    sales_agent_dir = prompts_path / "sales_agent" / "versions"
    sales_agent_dir.mkdir(parents=True)
    
    # Version 1.2
    with open(sales_agent_dir / "1.2.yaml", "w") as f:
        yaml.dump({"sales_agent": TestData.STRUCTURED_PROMPT_DATA}, f)
    
    # Version 1.1 (older)
    older_data = TestData.STRUCTURED_PROMPT_DATA.copy()
    older_data["version"] = "1.1"
    older_data["prompt"]["behavior"] = "Be helpful and professional."  # Different content
    
    with open(sales_agent_dir / "1.1.yaml", "w") as f:
        yaml.dump({"sales_agent": older_data}, f)
    
    # Create freeform_prompt
    freeform_dir = prompts_path / "tutorial_intro" / "versions"
    freeform_dir.mkdir(parents=True)
    
    with open(freeform_dir / "1.0.yaml", "w") as f:
        yaml.dump({"tutorial_intro": TestData.FREEFORM_PROMPT_DATA}, f)
    
    # Create hybrid_prompt  
    hybrid_dir = prompts_path / "api_response" / "versions"
    hybrid_dir.mkdir(parents=True)
    
    with open(hybrid_dir / "2.0.yaml", "w") as f:
        yaml.dump({"api_response": TestData.HYBRID_PROMPT_DATA}, f)
    
    return {
        "sales_agent": sales_agent_dir,
        "tutorial_intro": freeform_dir,
        "api_response": hybrid_dir
    }


@pytest.fixture
def sample_variables():
    """Sample PromptVariable instances for testing."""
    return {
        name: PromptVariable(
            name=name,
            type=var_def["type"],
            default=var_def.get("default"),
            required=var_def.get("required", True),
            values=var_def.get("values"),
            description=var_def.get("description")
        )
        for name, var_def in TestData.VARIABLES.items()
    }


@pytest.fixture
def sample_few_shots():
    """Sample FewShotExample instances for testing."""
    return [
        FewShotExample(
            input="Hello, how can I help?",
            output="Hi there! I'd be happy to assist you today.",
            reasoning="Friendly greeting with offer to help"
        ),
        FewShotExample(
            input="What are your capabilities?",
            output="I can help with analysis, writing, coding, and general questions.",
            reasoning="Clear overview of main capabilities"
        )
    ]


@pytest.fixture
def sample_structured_content():
    """Sample StructuredPromptContent for testing."""
    return StructuredPromptContent(
        system_role="You are a helpful AI assistant",
        behavior="Be concise and accurate",
        restrictions="No harmful content",
        format="Use markdown formatting",
        few_shots=[
            FewShotExample(
                input="Test question",
                output="Test response",
                reasoning="Test reasoning"
            )
        ],
        custom_sections={"priority": "high", "category": "general"}
    )


@pytest.fixture
def sample_freeform_content():
    """Sample FreeformPromptContent for testing."""
    return FreeformPromptContent(
        template="Introduction: {{intro}}\n\nMain content: {{content}}",
        sections={
            "intro": "Welcome message",
            "content": "Main discussion points"
        }
    )


@pytest.fixture 
def sample_hybrid_content():
    """Sample HybridPromptContent for testing."""
    return HybridPromptContent(
        data={
            "format": "json",
            "settings": {"timeout": 30, "retries": 3},
            "template": "Response: {{message}}"
        }
    )


@pytest.fixture
def sample_metadata():
    """Sample PromptMetadata for testing."""
    return PromptMetadata(
        name="test_prompt",
        version="1.0",
        type=PromptType.STRUCTURED,
        created_by="test@example.com",
        tags=["test", "example"],
        performance_score=0.85,
        description="A test prompt for unit testing",
        available_sections={"system_role", "behavior", "restrictions"},
        variable_count=3
    )


@pytest.fixture
def mock_jinja_env():
    """Mock Jinja2 environment for testing."""
    from jinja2 import Environment
    
    env = Environment()
    # Add some test filters
    env.filters.update({
        'test_filter': lambda x: f"filtered_{x}",
        'upper': lambda x: str(x).upper()
    })
    
    return env


@pytest.fixture
def sample_render_variables():
    """Sample variables for rendering tests."""
    return {
        "role": "assistant",
        "experience_level": "expert", 
        "topic": "machine learning",
        "temperature": 0.8,
        "max_tokens": 2000,
        "verbose": True
    }


@pytest.fixture
def invalid_yaml_content():
    """Invalid YAML content for error testing."""
    return """
invalid: yaml: content:
  - missing
    - proper
  indentation
"""


@pytest.fixture
def complex_nested_data():
    """Complex nested data structure for hybrid testing."""
    return {
        "level1": {
            "level2": {
                "level3": {
                    "template": "Deep nesting: {{value}}"
                }
            },
            "array": [
                {"item": "{{item1}}"},
                {"item": "{{item2}}"}
            ]
        },
        "variables": {
            "value": "deep_test",
            "item1": "first",
            "item2": "second"
        }
    }


class MockFileSystem:
    """Mock file system for testing without real files."""
    
    def __init__(self):
        self.files = {}
        self.directories = set()
    
    def add_file(self, path: str, content: str):
        """Add a mock file."""
        self.files[path] = content
        # Add parent directories
        parent = str(Path(path).parent)
        self.directories.add(parent)
    
    def exists(self, path: str) -> bool:
        """Check if mock file exists."""
        return path in self.files or path in self.directories
    
    def read(self, path: str) -> str:
        """Read mock file content."""
        return self.files.get(path, "")
    
    def list_files(self, directory: str) -> list:
        """List files in mock directory."""
        return [f for f in self.files.keys() if f.startswith(directory)]


@pytest.fixture
def mock_filesystem():
    """Mock filesystem for testing."""
    return MockFileSystem()