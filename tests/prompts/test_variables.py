"""Tests for variable validation and custom Jinja filters.

This module tests the VariableValidator class and custom Jinja filters
used for LLM prompt processing.
"""

import json
import pytest
from datetime import datetime
from typing import Dict, Any

from kontxt.prompts.types import PromptVariable
from kontxt.prompts.variables.validator import VariableValidator
from kontxt.prompts.variables.filters import (
    get_custom_filters,
    escape_llm_filter,
    format_few_shot_filter,
    truncate_words_filter,
    to_upper_snake_filter
)
from kontxt.core.exceptions import VariableValidationError

from .fixtures import TestData


class TestVariableValidator:
    """Test the VariableValidator class functionality."""
    
    def test_string_validation(self):
        """Test string type validation and coercion."""
        var_def = PromptVariable(name="test_str", type="string", required=True)
        
        # Test valid string
        assert VariableValidator.validate_variable(var_def, "hello") == "hello"
        
        # Test string coercion
        assert VariableValidator.validate_variable(var_def, 123) == "123"
        assert VariableValidator.validate_variable(var_def, True) == "True"
        assert VariableValidator.validate_variable(var_def, 3.14) == "3.14"
    
    def test_integer_validation(self):
        """Test integer type validation and coercion."""
        var_def = PromptVariable(name="test_int", type="integer", required=True)
        
        # Test valid integer
        assert VariableValidator.validate_variable(var_def, 42) == 42
        
        # Test integer coercion
        assert VariableValidator.validate_variable(var_def, "42") == 42
        assert VariableValidator.validate_variable(var_def, 42.0) == 42
        
        # Test invalid coercion
        with pytest.raises(VariableValidationError):
            VariableValidator.validate_variable(var_def, "not_a_number")
    
    def test_float_validation(self):
        """Test float type validation and coercion."""
        var_def = PromptVariable(name="test_float", type="float", required=True)
        
        # Test valid float
        assert VariableValidator.validate_variable(var_def, 3.14) == 3.14
        
        # Test float coercion
        assert VariableValidator.validate_variable(var_def, "3.14") == 3.14
        assert VariableValidator.validate_variable(var_def, 42) == 42.0
        
        # Test invalid coercion
        with pytest.raises(VariableValidationError):
            VariableValidator.validate_variable(var_def, "not_a_float")
    
    def test_boolean_validation(self):
        """Test boolean type validation and coercion."""
        var_def = PromptVariable(name="test_bool", type="boolean", required=True)
        
        # Test valid boolean
        assert VariableValidator.validate_variable(var_def, True) is True
        assert VariableValidator.validate_variable(var_def, False) is False
        
        # Test boolean coercion - truthy values
        assert VariableValidator.validate_variable(var_def, "true") is True
        assert VariableValidator.validate_variable(var_def, "True") is True
        assert VariableValidator.validate_variable(var_def, "1") is True
        assert VariableValidator.validate_variable(var_def, 1) is True
        
        # Test boolean coercion - falsy values
        assert VariableValidator.validate_variable(var_def, "false") is False
        assert VariableValidator.validate_variable(var_def, "False") is False
        assert VariableValidator.validate_variable(var_def, "0") is False
        assert VariableValidator.validate_variable(var_def, 0) is False
        
        # Test other values are falsy
        assert VariableValidator.validate_variable(var_def, "other") is False
    
    def test_list_validation(self):
        """Test list type validation and coercion."""
        var_def = PromptVariable(name="test_list", type="list", required=True)
        
        # Test valid list
        test_list = ["a", "b", "c"]
        assert VariableValidator.validate_variable(var_def, test_list) == test_list
        
        # Test comma-separated string coercion
        result = VariableValidator.validate_variable(var_def, "a,b,c")
        assert result == ["a", "b", "c"]
        
        # Test string with spaces
        result = VariableValidator.validate_variable(var_def, "a, b, c")
        assert result == ["a", "b", "c"]
        
        # Test single item coercion
        assert VariableValidator.validate_variable(var_def, "single") == ["single"]
    
    def test_dict_validation(self):
        """Test dict type validation and coercion."""
        var_def = PromptVariable(name="test_dict", type="dict", required=True)
        
        # Test valid dict
        test_dict = {"key": "value", "num": 42}
        assert VariableValidator.validate_variable(var_def, test_dict) == test_dict
        
        # Test JSON string coercion
        json_str = '{"key": "value", "num": 42}'
        result = VariableValidator.validate_variable(var_def, json_str)
        assert result == {"key": "value", "num": 42}
        
        # Test invalid JSON
        with pytest.raises(VariableValidationError):
            VariableValidator.validate_variable(var_def, "not_valid_json")
        
        # Test non-dict, non-string value
        with pytest.raises(VariableValidationError):
            VariableValidator.validate_variable(var_def, 123)
    
    def test_date_validation(self):
        """Test date type validation and parsing."""
        var_def = PromptVariable(name="test_date", type="date", required=True)
        
        # Test various date formats
        result1 = VariableValidator.validate_variable(var_def, "2024-01-15")
        assert isinstance(result1, datetime)
        assert result1.year == 2024
        
        result2 = VariableValidator.validate_variable(var_def, "2024-01-15 14:30:00")
        assert isinstance(result2, datetime)
        assert result2.hour == 14
        
        result3 = VariableValidator.validate_variable(var_def, "2024/01/15")
        assert isinstance(result3, datetime)
        
        # Test invalid date format
        with pytest.raises(VariableValidationError):
            VariableValidator.validate_variable(var_def, "invalid-date")
        
        # Test existing datetime object
        dt = datetime.now()
        assert VariableValidator.validate_variable(var_def, dt) == dt
    
    def test_enum_validation(self):
        """Test enum type validation with allowed values."""
        var_def = PromptVariable(
            name="test_enum", 
            type="enum",
            values=["option1", "option2", "option3"],
            required=True
        )
        
        # Test valid enum values
        assert VariableValidator.validate_variable(var_def, "option1") == "option1"
        assert VariableValidator.validate_variable(var_def, "option2") == "option2"
        
        # Test invalid enum value
        with pytest.raises(VariableValidationError) as exc_info:
            VariableValidator.validate_variable(var_def, "invalid_option")
        
        assert "test_enum" in str(exc_info.value)
        assert "invalid_option" in str(exc_info.value)
    
    def test_default_values(self):
        """Test handling of default values."""
        var_def = PromptVariable(
            name="test_default",
            type="string",
            default="default_value",
            required=False
        )
        
        # Test None value with default
        assert VariableValidator.validate_variable(var_def, None) == "default_value"
        
        # Test provided value overrides default
        assert VariableValidator.validate_variable(var_def, "custom") == "custom"
    
    def test_required_validation(self):
        """Test required field validation."""
        required_var = PromptVariable(name="required_field", type="string", required=True)
        optional_var = PromptVariable(name="optional_field", type="string", required=False)
        
        # Test required field with None value
        with pytest.raises(VariableValidationError):
            VariableValidator.validate_variable(required_var, None)
        
        # Test optional field with None value
        assert VariableValidator.validate_variable(optional_var, None) is None
    
    def test_validate_all_variables(self):
        """Test validating all variables for a prompt."""
        variables_def = {
            "role": PromptVariable(
                name="role",
                type="enum",
                values=["user", "assistant"],
                default="assistant"
            ),
            "temperature": PromptVariable(
                name="temperature",
                type="float",
                default=0.7,
                required=False
            ),
            "topic": PromptVariable(
                name="topic",
                type="string",
                required=True
            )
        }
        
        input_vars = {
            "role": "user",
            "topic": "AI ethics",
            "extra_param": "should be preserved"  # Extra parameter
        }
        
        result = VariableValidator.validate_all_variables(variables_def, input_vars)
        
        # Check validated variables
        assert result["role"] == "user"
        assert result["topic"] == "AI ethics"
        assert result["temperature"] == 0.7  # Default value used
        assert result["extra_param"] == "should be preserved"  # Extra preserved
    
    def test_validate_all_variables_missing_required(self):
        """Test error when required variable is missing."""
        variables_def = {
            "required_field": PromptVariable(
                name="required_field",
                type="string",
                required=True
            )
        }
        
        input_vars = {}  # Missing required field
        
        with pytest.raises(VariableValidationError):
            VariableValidator.validate_all_variables(variables_def, input_vars)
    
    def test_complex_validation_scenario(self):
        """Test complex validation scenario with multiple types."""
        variables_def = {}
        
        # Create variables from test data
        for name, var_def in TestData.VARIABLES.items():
            variables_def[name] = PromptVariable(
                name=name,
                type=var_def["type"],
                default=var_def.get("default"),
                required=var_def.get("required", True),
                values=var_def.get("values"),
                description=var_def.get("description")
            )
        
        input_vars = {
            "role": "expert",
            "experience_level": "senior", 
            "topic": "machine learning",
            "temperature": "0.8",  # String that needs conversion
            "max_tokens": 1500,
            "verbose": "true"  # String boolean
        }
        
        result = VariableValidator.validate_all_variables(variables_def, input_vars)
        
        assert result["role"] == "expert"
        assert result["temperature"] == 0.8  # Converted to float
        assert result["verbose"] is True  # Converted to boolean
        assert isinstance(result["max_tokens"], int)


class TestCustomJinjaFilters:
    """Test custom Jinja filters for LLM processing."""
    
    def test_get_custom_filters(self):
        """Test that get_custom_filters returns all expected filters."""
        filters = get_custom_filters()
        
        expected_filters = {
            'escape_llm',
            'format_few_shot', 
            'truncate_words',
            'to_upper_snake'
        }
        
        assert set(filters.keys()) == expected_filters
        
        # Test that all filters are callable
        for filter_func in filters.values():
            assert callable(filter_func)
    
    def test_escape_llm_filter(self):
        """Test the escape_llm filter functionality."""
        # Test basic escaping
        result = escape_llm_filter('Hello "world"')
        assert result == 'Hello \\"world\\"'
        
        # Test newline escaping
        result = escape_llm_filter('Line 1\nLine 2')
        assert result == 'Line 1\\nLine 2'
        
        # Test combined escaping
        result = escape_llm_filter('Say "Hello"\nto the world')
        assert result == 'Say \\"Hello\\"\\nto the world'
        
        # Test empty string
        assert escape_llm_filter('') == ''
        
        # Test non-string input (should be converted to string)
        assert escape_llm_filter(123) == '123'
        assert escape_llm_filter(None) == 'None'
    
    def test_format_few_shot_filter(self):
        """Test the format_few_shot filter functionality."""
        examples = [
            {"input": "Hello", "output": "Hi there!", "reasoning": "Friendly greeting"},
            {"input": "Help me", "output": "How can I assist?"},  # No reasoning
            {"input": "Goodbye", "output": "See you later!", "reasoning": "Polite farewell"}
        ]
        
        result = format_few_shot_filter(examples)
        
        # Check that it contains expected structure
        assert "Example 1:" in result
        assert "Example 2:" in result
        assert "Example 3:" in result
        
        # Check content
        assert "Input: Hello" in result
        assert "Output: Hi there!" in result
        assert "Reasoning: Friendly greeting" in result
        
        # Check that missing reasoning is handled
        assert "Input: Help me" in result
        assert "Output: How can I assist?" in result
        # Should not have "Reasoning:" for example 2
        lines = result.split('\n')
        example2_lines = []
        capturing = False
        for line in lines:
            if "Example 2:" in line:
                capturing = True
            elif "Example 3:" in line:
                break
            elif capturing:
                example2_lines.append(line)
        
        # Example 2 should not have reasoning line
        reasoning_lines = [line for line in example2_lines if line.startswith("Reasoning:")]
        assert len(reasoning_lines) == 0
        
        # Test empty examples list
        result_empty = format_few_shot_filter([])
        assert result_empty == ""
    
    def test_truncate_words_filter(self):
        """Test the truncate_words filter functionality."""
        text = "This is a long sentence with many words that should be truncated"
        
        # Test truncation
        result = truncate_words_filter(text, 5)
        assert result == "This is a long sentence..."
        
        # Test no truncation needed
        result = truncate_words_filter("Short text", 5)
        assert result == "Short text"
        
        # Test exact word count
        result = truncate_words_filter("One two three", 3)
        assert result == "One two three"
        
        # Test single word
        result = truncate_words_filter("Hello", 1)
        assert result == "Hello"
        
        # Test zero words (edge case)
        result = truncate_words_filter("Hello world", 0)
        assert result == "..."
        
        # Test non-string input
        result = truncate_words_filter(12345, 2)
        assert result == "12345"  # Single "word"
        
        # Test empty string
        result = truncate_words_filter("", 5)
        assert result == ""
    
    def test_to_upper_snake_filter(self):
        """Test the to_upper_snake filter functionality."""
        # Test basic conversion
        result = to_upper_snake_filter("hello world")
        assert result == "HELLO_WORLD"
        
        # Test already uppercase
        result = to_upper_snake_filter("HELLO WORLD")
        assert result == "HELLO_WORLD"
        
        # Test mixed case
        result = to_upper_snake_filter("Hello World Test")
        assert result == "HELLO_WORLD_TEST"
        
        # Test multiple spaces
        result = to_upper_snake_filter("hello   world")
        assert result == "HELLO___WORLD"  # Preserves multiple spaces as underscores
        
        # Test single word
        result = to_upper_snake_filter("hello")
        assert result == "HELLO"
        
        # Test empty string
        result = to_upper_snake_filter("")
        assert result == ""
        
        # Test non-string input
        result = to_upper_snake_filter(123)
        assert result == "123"
        
        # Test special characters
        result = to_upper_snake_filter("hello-world.test")
        assert result == "HELLO-WORLD.TEST"  # Only spaces converted to underscores


class TestFilterIntegration:
    """Test filters integration with Jinja2 environment."""
    
    def test_filters_in_jinja_env(self):
        """Test that custom filters work in Jinja2 environment."""
        from jinja2 import Environment
        
        env = Environment()
        env.filters.update(get_custom_filters())
        
        # Test escape_llm filter in template
        template = env.from_string('{{ message | escape_llm }}')
        result = template.render(message='Say "Hello"\nWorld')
        assert result == 'Say \\"Hello\\"\\nWorld'
        
        # Test truncate_words filter in template
        template = env.from_string('{{ text | truncate_words(3) }}')
        result = template.render(text="This is a long message")
        assert result == "This is a..."
        
        # Test to_upper_snake filter in template
        template = env.from_string('{{ name | to_upper_snake }}')
        result = template.render(name="my variable name")
        assert result == "MY_VARIABLE_NAME"
    
    def test_complex_filter_combinations(self):
        """Test combining multiple filters in templates."""
        from jinja2 import Environment
        
        env = Environment()
        env.filters.update(get_custom_filters())
        
        # Test chaining filters
        template = env.from_string('{{ text | truncate_words(4) | to_upper_snake }}')
        result = template.render(text="hello world this is a test")
        assert result == "HELLO_WORLD_THIS_IS..."
        
        # Test format_few_shot in complex template
        template = env.from_string('''
Examples:
{{ examples | format_few_shot }}
End of examples.
'''.strip())
        
        examples = [
            {"input": "Hi", "output": "Hello!"},
            {"input": "Thanks", "output": "You're welcome!", "reasoning": "Polite response"}
        ]
        
        result = template.render(examples=examples)
        assert "Example 1:" in result
        assert "Input: Hi" in result
        assert "Reasoning: Polite response" in result
        assert "End of examples." in result


class TestVariableValidationErrorHandling:
    """Test error handling and edge cases in variable validation."""
    
    def test_variable_validation_error_creation(self):
        """Test VariableValidationError contains proper information."""
        var_def = PromptVariable(
            name="test_var",
            type="enum",
            values=["a", "b", "c"],
            required=True
        )
        
        with pytest.raises(VariableValidationError) as exc_info:
            VariableValidator.validate_variable(var_def, "invalid")
        
        error = exc_info.value
        assert error.variable_name == "test_var"
        assert error.expected_type == "enum"
        assert error.actual_value == "invalid"
        assert error.allowed_values == ["a", "b", "c"]
    
    def test_pydantic_schema_validation(self):
        """Test Pydantic schema validation if available."""
        # This test should work whether Pydantic is available or not
        schema = {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "age": {"type": "integer", "minimum": 0}
            }
        }
        
        var_def = PromptVariable(
            name="user_data",
            type="object",
            schema=schema,
            required=True
        )
        
        # Test valid data
        valid_data = {"name": "John", "age": 30}
        result = VariableValidator.validate_variable(var_def, valid_data)
        
        # Should return the data (with or without Pydantic validation)
        assert isinstance(result, dict)
        assert "name" in result
    
    def test_edge_cases(self):
        """Test various edge cases in validation."""
        # Test unknown type (should pass through)
        var_def = PromptVariable(name="unknown", type="unknown_type")
        result = VariableValidator.validate_variable(var_def, "test_value")
        assert result == "test_value"
        
        # Test empty enum values list
        var_def = PromptVariable(name="empty_enum", type="enum", values=[])
        result = VariableValidator.validate_variable(var_def, "anything")
        assert result == "anything"  # Should pass since values is empty
        
        # Test None enum values
        var_def = PromptVariable(name="none_enum", type="enum", values=None)
        result = VariableValidator.validate_variable(var_def, "anything")
        assert result == "anything"  # Should pass since values is None