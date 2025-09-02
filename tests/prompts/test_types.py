"""Tests for prompt types and dataclasses.

This module tests all the core types: PromptType, PromptVariable, PromptMetadata,
FewShotExample, and the three content types (Structured, Freeform, Hybrid).
"""

import pytest
from typing import Dict, Any

from kontxt.prompts.types import (
    PromptType,
    PromptVariable, 
    PromptMetadata,
    FewShotExample,
    StructuredPromptContent,
    FreeformPromptContent,
    HybridPromptContent
)

from .fixtures import TestData


class TestPromptType:
    """Test PromptType enum functionality."""
    
    def test_prompt_type_values(self):
        """Test that PromptType has correct values."""
        assert PromptType.STRUCTURED.value == "structured"
        assert PromptType.FREEFORM.value == "freeform"  
        assert PromptType.HYBRID.value == "hybrid"
    
    def test_prompt_type_from_string(self):
        """Test creating PromptType from string values."""
        assert PromptType("structured") == PromptType.STRUCTURED
        assert PromptType("freeform") == PromptType.FREEFORM
        assert PromptType("hybrid") == PromptType.HYBRID
    
    def test_invalid_prompt_type(self):
        """Test that invalid prompt type raises ValueError."""
        with pytest.raises(ValueError):
            PromptType("invalid_type")


class TestPromptVariable:
    """Test PromptVariable dataclass functionality."""
    
    def test_basic_variable_creation(self):
        """Test creating a basic PromptVariable."""
        var = PromptVariable(
            name="test_var",
            type="string",
            default="default_value",
            required=True,
            description="A test variable"
        )
        
        assert var.name == "test_var"
        assert var.type == "string"
        assert var.default == "default_value"
        assert var.required is True
        assert var.description == "A test variable"
        assert var.values is None
        assert var.schema is None
    
    def test_enum_variable_creation(self):
        """Test creating an enum type PromptVariable."""
        var = PromptVariable(
            name="role",
            type="enum",
            values=["user", "assistant", "system"],
            default="assistant",
            required=False
        )
        
        assert var.type == "enum"
        assert var.values == ["user", "assistant", "system"]
        assert var.default == "assistant"
        assert var.required is False
    
    def test_variable_with_schema(self):
        """Test PromptVariable with complex schema."""
        schema = {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "age": {"type": "integer", "minimum": 0}
            },
            "required": ["name"]
        }
        
        var = PromptVariable(
            name="user_info",
            type="object",
            schema=schema,
            required=True
        )
        
        assert var.schema == schema
        assert var.type == "object"
    
    def test_minimal_variable(self):
        """Test creating minimal PromptVariable with defaults."""
        var = PromptVariable(name="simple", type="string")
        
        assert var.name == "simple"
        assert var.type == "string"
        assert var.default is None
        assert var.required is True
        assert var.values is None
        assert var.description is None
        assert var.schema is None


class TestPromptMetadata:
    """Test PromptMetadata dataclass functionality."""
    
    def test_basic_metadata_creation(self):
        """Test creating basic PromptMetadata."""
        metadata = PromptMetadata(
            name="test_prompt",
            version="1.0",
            type=PromptType.STRUCTURED
        )
        
        assert metadata.name == "test_prompt"
        assert metadata.version == "1.0"
        assert metadata.type == PromptType.STRUCTURED
        assert metadata.tags == []  # Default empty list
        assert metadata.variable_count == 0  # Default
        assert metadata.available_sections == set()  # Default empty set
    
    def test_full_metadata_creation(self):
        """Test creating PromptMetadata with all fields."""
        sections = {"system", "behavior", "restrictions"}
        tags = ["sales", "conversation"]
        
        metadata = PromptMetadata(
            name="sales_agent",
            version="1.2",
            type=PromptType.STRUCTURED,
            created_by="test@example.com",
            created_at="2024-01-01T00:00:00Z",
            updated_at="2024-01-02T00:00:00Z",
            tags=tags,
            performance_score=0.95,
            description="Sales conversation prompt",
            available_sections=sections,
            variable_count=5
        )
        
        assert metadata.created_by == "test@example.com"
        assert metadata.tags == tags
        assert metadata.performance_score == 0.95
        assert metadata.description == "Sales conversation prompt"
        assert metadata.available_sections == sections
        assert metadata.variable_count == 5
    
    def test_metadata_type_conversion(self):
        """Test that string type gets converted to PromptType enum."""
        metadata = PromptMetadata(
            name="test",
            version="1.0",
            type="structured"  # String instead of enum
        )
        
        # Should be converted to enum in __post_init__
        assert isinstance(metadata.type, PromptType)
        assert metadata.type == PromptType.STRUCTURED
    
    def test_metadata_defaults(self):
        """Test that metadata defaults are properly set."""
        metadata = PromptMetadata(
            name="test",
            version="1.0", 
            type=PromptType.FREEFORM
        )
        
        assert metadata.created_by is None
        assert metadata.created_at is None
        assert metadata.updated_at is None
        assert metadata.tags == []
        assert metadata.performance_score is None
        assert metadata.description is None
        assert metadata.available_sections == set()
        assert metadata.variable_count == 0


class TestFewShotExample:
    """Test FewShotExample dataclass functionality."""
    
    def test_basic_few_shot_example(self):
        """Test creating basic FewShotExample."""
        example = FewShotExample(
            input="What is AI?",
            output="AI stands for Artificial Intelligence.",
            reasoning="Direct factual response"
        )
        
        assert example.input == "What is AI?"
        assert example.output == "AI stands for Artificial Intelligence."
        assert example.reasoning == "Direct factual response"
        assert example.metadata == {}  # Default empty dict
    
    def test_few_shot_with_metadata(self):
        """Test FewShotExample with additional metadata."""
        metadata = {"difficulty": "easy", "category": "factual"}
        
        example = FewShotExample(
            input="Hello",
            output="Hi there!",
            metadata=metadata
        )
        
        assert example.metadata == metadata
        assert example.reasoning is None  # Not provided
    
    def test_multi_turn_few_shot(self):
        """Test FewShotExample with multi-turn conversation."""
        multi_turn_input = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi! How can I help?"},
            {"role": "user", "content": "What's the weather?"}
        ]
        
        multi_turn_output = [
            {"role": "assistant", "content": "I don't have access to current weather data."}
        ]
        
        example = FewShotExample(
            input=multi_turn_input,
            output=multi_turn_output,
            reasoning="Multi-turn conversation example"
        )
        
        assert example.input == multi_turn_input
        assert example.output == multi_turn_output
        assert isinstance(example.input, list)
        assert isinstance(example.output, list)


class TestStructuredPromptContent:
    """Test StructuredPromptContent dataclass functionality."""
    
    def test_basic_structured_content(self):
        """Test creating basic StructuredPromptContent."""
        content = StructuredPromptContent(
            system_role="You are a helpful assistant",
            behavior="Be concise and accurate"
        )
        
        assert content.system_role == "You are a helpful assistant"
        assert content.behavior == "Be concise and accurate"
        assert content.restrictions is None
        assert content.few_shots == []
        assert content.custom_sections == {}
    
    def test_structured_content_with_few_shots(self):
        """Test StructuredPromptContent with few-shot examples."""
        few_shots = [
            FewShotExample("Hi", "Hello!", "Friendly greeting"),
            FewShotExample("Help", "How can I assist?", "Offer assistance")
        ]
        
        content = StructuredPromptContent(
            system_role="Assistant",
            few_shots=few_shots
        )
        
        assert len(content.few_shots) == 2
        assert content.few_shots[0].input == "Hi"
        assert content.few_shots[1].reasoning == "Offer assistance"
    
    def test_backward_compatibility_aliases(self):
        """Test backward compatibility role/system aliases."""
        content = StructuredPromptContent()
        
        # Test setter
        content.role = "Test role"
        assert content.system_role == "Test role"
        assert content.role == "Test role"
        assert content.system == "Test role"
        
        # Test system setter  
        content.system = "Test system"
        assert content.system_role == "Test system"
        assert content.role == "Test system"
        assert content.system == "Test system"
    
    def test_from_dict_basic(self):
        """Test creating StructuredPromptContent from dictionary."""
        data = {
            "role": "You are helpful",
            "behavior": "Be kind",
            "restrictions": "No harmful content",
            "user": "Sample user message"
        }
        
        content = StructuredPromptContent.from_dict(data)
        
        assert content.system_role == "You are helpful"
        assert content.behavior == "Be kind"
        assert content.restrictions == "No harmful content"
        assert content.user == "Sample user message"
    
    def test_from_dict_with_few_shots(self):
        """Test creating StructuredPromptContent with few-shot examples."""
        data = {
            "system": "Assistant",
            "few_shots": [
                {"input": "Hello", "output": "Hi there!", "reasoning": "Greeting"},
                {"input": "Help", "output": "How can I help?"}
            ]
        }
        
        content = StructuredPromptContent.from_dict(data)
        
        assert content.system_role == "Assistant"
        assert len(content.few_shots) == 2
        assert content.few_shots[0].reasoning == "Greeting"
        assert content.few_shots[1].reasoning is None
    
    def test_from_dict_with_aliases(self):
        """Test from_dict with human/ai aliases."""
        data = {
            "system_role": "Main role",
            "human": "Human message",
            "ai": "AI response"
        }
        
        content = StructuredPromptContent.from_dict(data)
        
        assert content.system_role == "Main role"
        assert content.user == "Human message"
        assert content.assistant == "AI response"
    
    def test_from_dict_custom_sections(self):
        """Test from_dict extracts custom sections."""
        data = {
            "system_role": "Assistant",
            "behavior": "Be helpful",
            "custom_field1": "Custom value 1",
            "custom_field2": "Custom value 2",
            "priority": "high"
        }
        
        content = StructuredPromptContent.from_dict(data)
        
        assert content.system_role == "Assistant"
        assert content.behavior == "Be helpful"
        assert content.custom_sections["custom_field1"] == "Custom value 1"
        assert content.custom_sections["custom_field2"] == "Custom value 2"
        assert content.custom_sections["priority"] == "high"
    
    def test_get_available_sections(self):
        """Test getting available sections from structured content."""
        content = StructuredPromptContent(
            system_role="Role",
            behavior="Behavior", 
            format="Format",
            few_shots=[FewShotExample("in", "out")],
            custom_sections={"custom1": "value1", "custom2": "value2"}
        )
        
        sections = content.get_available_sections()
        expected_sections = {
            "system_role", "behavior", "format", "few_shots", "custom1", "custom2"
        }
        
        assert sections == expected_sections
    
    def test_empty_structured_content_sections(self):
        """Test available sections for empty content."""
        content = StructuredPromptContent()
        sections = content.get_available_sections()
        
        assert sections == set()


class TestFreeformPromptContent:
    """Test FreeformPromptContent dataclass functionality."""
    
    def test_basic_freeform_content(self):
        """Test creating basic FreeformPromptContent."""
        content = FreeformPromptContent(
            template="Hello {{name}}, welcome to {{topic}}!",
            sections={"greeting": "Hello {{name}}", "welcome": "welcome to {{topic}}!"}
        )
        
        assert content.template == "Hello {{name}}, welcome to {{topic}}!"
        assert len(content.sections) == 2
        assert content.sections["greeting"] == "Hello {{name}}"
    
    def test_from_dict_freeform(self):
        """Test creating FreeformPromptContent from dictionary."""
        data = {
            "intro": "Welcome to our service",
            "main": "Here are the main points: {{points}}",
            "outro": "Thank you for your time"
        }
        
        content = FreeformPromptContent.from_dict(data)
        
        # Should combine all sections into template
        expected_template = "Welcome to our service\n\nHere are the main points: {{points}}\n\nThank you for your time"
        assert content.template == expected_template
        
        # Should preserve individual sections
        assert content.sections["intro"] == "Welcome to our service"
        assert content.sections["main"] == "Here are the main points: {{points}}"
        assert content.sections["outro"] == "Thank you for your time"
    
    def test_get_available_sections_freeform(self):
        """Test getting available sections from freeform content."""
        content = FreeformPromptContent(
            template="Test",
            sections={"intro": "Introduction", "body": "Main content", "conclusion": "End"}
        )
        
        sections = content.get_available_sections()
        expected_sections = {"intro", "body", "conclusion"}
        
        assert sections == expected_sections
    
    def test_empty_freeform_sections(self):
        """Test freeform content with no sections."""
        content = FreeformPromptContent(template="Simple template")
        sections = content.get_available_sections()
        
        assert sections == set()


class TestHybridPromptContent:
    """Test HybridPromptContent dataclass functionality."""
    
    def test_basic_hybrid_content(self):
        """Test creating basic HybridPromptContent."""
        data = {
            "format": "json",
            "timeout": 30,
            "template": "Process {{data}} as {{format}}"
        }
        
        content = HybridPromptContent(data=data)
        
        assert content.data == data
        assert content.data["format"] == "json"
        assert content.data["timeout"] == 30
    
    def test_from_dict_hybrid(self):
        """Test creating HybridPromptContent from dictionary."""
        data = {
            "response_format": "{{format}}",
            "settings": {"timeout": 30, "retries": 3},
            "template": "{{message}}"
        }
        
        content = HybridPromptContent.from_dict(data)
        
        assert content.data == data
        # Should have inferred types
        assert len(content._typed_fields) == 3
        assert content._typed_fields["response_format"] == str
        assert content._typed_fields["settings"] == dict
    
    def test_get_available_sections_hybrid(self):
        """Test getting available sections from hybrid content."""
        data = {
            "section1": "value1",
            "section2": {"nested": "value2"},  
            "section3": ["list", "value"]
        }
        
        content = HybridPromptContent(data=data)
        sections = content.get_available_sections()
        expected_sections = {"section1", "section2", "section3"}
        
        assert sections == expected_sections
    
    def test_get_typed_value(self):
        """Test getting typed values from hybrid content."""
        data = {
            "string_val": "test",
            "int_val": "42",  # String that can be converted to int
            "bool_val": "true",  # String that can be converted to bool
            "invalid_int": "not_a_number"
        }
        
        content = HybridPromptContent.from_dict(data)
        
        # Test direct value access
        assert content.get_typed_value("string_val") == "test"
        
        # Test type conversion
        assert content.get_typed_value("int_val", int) == 42
        assert isinstance(content.get_typed_value("int_val", int), int)
        
        # Test invalid conversion (should return original value and log warning)
        result = content.get_typed_value("invalid_int", int)
        assert result == "not_a_number"  # Original string value
        
        # Test missing key
        assert content.get_typed_value("missing_key") is None
    
    def test_type_inference(self):
        """Test that _infer_types works correctly."""
        data = {
            "string": "test",
            "integer": 42,
            "float": 3.14,
            "boolean": True,
            "list": [1, 2, 3],
            "dict": {"nested": "value"}
        }
        
        content = HybridPromptContent.from_dict(data)
        
        assert content._typed_fields["string"] == str
        assert content._typed_fields["integer"] == int
        assert content._typed_fields["float"] == float
        assert content._typed_fields["boolean"] == bool
        assert content._typed_fields["list"] == list
        assert content._typed_fields["dict"] == dict


# Integration tests for complex data structures
class TestComplexDataStructures:
    """Test complex interactions between different types."""
    
    def test_structured_with_complex_few_shots(self):
        """Test structured content with complex few-shot examples."""
        data = TestData.STRUCTURED_PROMPT_DATA["prompt"]
        content = StructuredPromptContent.from_dict(data)
        
        assert len(content.few_shots) == 2
        assert content.few_shots[0].input == "Can you help me with sales strategies?"
        assert content.few_shots[1].reasoning == "Comprehensive answer covering key closing principles"
        
        # Test that custom sections are preserved
        assert "custom_field" in content.custom_sections
    
    def test_metadata_with_real_data(self):
        """Test metadata creation with realistic test data."""
        metadata_data = TestData.STRUCTURED_PROMPT_DATA["metadata"]
        
        metadata = PromptMetadata(
            name="sales_agent",
            version="1.2",
            type=PromptType.STRUCTURED,
            **metadata_data
        )
        
        assert metadata.created_by == "test@example.com"
        assert "sales" in metadata.tags
        assert metadata.performance_score == 0.95
    
    def test_variable_definitions_from_test_data(self):
        """Test creating variables from realistic test data."""
        variables_data = TestData.VARIABLES
        
        variables = {}
        for name, var_def in variables_data.items():
            variables[name] = PromptVariable(
                name=name,
                type=var_def["type"],
                default=var_def.get("default"),
                required=var_def.get("required", True),
                values=var_def.get("values"),
                description=var_def.get("description")
            )
        
        # Test role variable (enum type)
        role_var = variables["role"]
        assert role_var.type == "enum"
        assert "assistant" in role_var.values
        assert role_var.default == "assistant"
        
        # Test topic variable (required string)
        topic_var = variables["topic"]
        assert topic_var.type == "string"
        assert topic_var.required is True
        assert topic_var.description == "The main topic to discuss"
        
        # Test temperature variable (optional float)
        temp_var = variables["temperature"] 
        assert temp_var.type == "float"
        assert temp_var.default == 0.7
        assert temp_var.required is False