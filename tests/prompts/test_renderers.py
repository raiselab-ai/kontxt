"""Tests for prompt renderers.

This module tests all prompt renderers: StructuredRenderer, FreeformRenderer,
and HybridRenderer, along with the renderer factory function.
"""

import pytest
from unittest.mock import Mock, MagicMock
from typing import Dict, List, Any

from jinja2 import Environment, TemplateError

from kontxt.prompts.renderers import (
    get_renderer,
    PromptRenderer,
    StructuredRenderer,
    FreeformRenderer, 
    HybridRenderer
)
from kontxt.prompts.types import (
    PromptType,
    FewShotExample,
    StructuredPromptContent,
    FreeformPromptContent,
    HybridPromptContent
)
from kontxt.core.exceptions import TemplateRenderError

from .fixtures import TestData


class TestRendererFactory:
    """Test the renderer factory function."""
    
    def test_get_structured_renderer(self):
        """Test getting StructuredRenderer."""
        jinja_env = Environment()
        renderer = get_renderer(PromptType.STRUCTURED, jinja_env)
        
        assert isinstance(renderer, StructuredRenderer)
        assert renderer.jinja_env == jinja_env
    
    def test_get_freeform_renderer(self):
        """Test getting FreeformRenderer."""
        jinja_env = Environment()
        renderer = get_renderer(PromptType.FREEFORM, jinja_env)
        
        assert isinstance(renderer, FreeformRenderer)
        assert renderer.jinja_env == jinja_env
    
    def test_get_hybrid_renderer(self):
        """Test getting HybridRenderer."""
        jinja_env = Environment()
        renderer = get_renderer(PromptType.HYBRID, jinja_env)
        
        assert isinstance(renderer, HybridRenderer)
        assert renderer.jinja_env == jinja_env
    
    def test_get_hybrid_renderer_with_recursion_depth(self):
        """Test getting HybridRenderer with custom recursion depth."""
        jinja_env = Environment()
        renderer = get_renderer(PromptType.HYBRID, jinja_env, max_recursion_depth=100)
        
        assert isinstance(renderer, HybridRenderer)
        assert renderer.max_recursion_depth == 100
    
    def test_get_renderer_invalid_type(self):
        """Test that invalid prompt type raises ValueError."""
        jinja_env = Environment()
        
        with pytest.raises(ValueError, match="Unknown prompt type"):
            get_renderer("invalid_type", jinja_env)


class TestStructuredRenderer:
    """Test StructuredRenderer functionality."""
    
    @pytest.fixture
    def structured_renderer(self):
        """Create StructuredRenderer for testing."""
        jinja_env = Environment()
        return StructuredRenderer(jinja_env)
    
    @pytest.fixture
    def sample_content(self):
        """Sample structured content for testing."""
        return StructuredPromptContent(
            system_role="You are a {{role}} assistant",
            behavior="Be {{style}} and helpful",
            restrictions="Never share {{restricted_info}}",
            format="Use {{output_format}} format",
            user="Please help with {{task}}",
            assistant="I'll help you with {{task}}",
            few_shots=[
                FewShotExample(
                    input="Hello {{name}}",
                    output="Hi {{name}}! How can I help?",
                    reasoning="Friendly greeting"
                ),
                FewShotExample(
                    input="Thanks",
                    output="You're welcome!",
                    reasoning="Polite response"
                )
            ],
            custom_sections={
                "priority": "This is {{priority}} priority",
                "category": "{{category}} assistance"
            }
        )
    
    def test_basic_structured_rendering(self, structured_renderer, sample_content):
        """Test basic structured prompt rendering."""
        variables = {
            "role": "helpful",
            "style": "professional", 
            "restricted_info": "passwords",
            "output_format": "markdown",
            "task": "coding",
            "name": "John",
            "priority": "high",
            "category": "technical"
        }
        
        result = structured_renderer.render(sample_content, variables)
        
        # Should return list of message dictionaries
        assert isinstance(result, list)
        assert len(result) > 0
        
        # Check system message (first message)
        system_msg = result[0]
        assert system_msg["role"] == "system"
        system_content = system_msg["content"]
        
        # Check that variables were rendered
        assert "helpful assistant" in system_content
        assert "professional and helpful" in system_content
        assert "Never share passwords" in system_content
        assert "Use markdown format" in system_content
        
        # Find few-shot examples (should be user/assistant pairs)
        user_messages = [msg for msg in result if msg["role"] == "user"]
        assistant_messages = [msg for msg in result if msg["role"] == "assistant"]
        
        # Should have user/assistant messages from few-shots plus explicit user/assistant
        assert len(user_messages) >= 2  # At least 2 from few-shots
        assert len(assistant_messages) >= 2  # At least 2 from few-shots
        
        # Check that variables were rendered in few-shots
        hello_msg = next((msg for msg in user_messages if "Hello John" in msg["content"]), None)
        assert hello_msg is not None
        
        # Check custom sections
        custom_system_msgs = [msg for msg in result 
                             if msg["role"] == "system" and ("PRIORITY:" in msg["content"] or "CATEGORY:" in msg["content"])]
        assert len(custom_system_msgs) >= 2  # Should have priority and category
    
    def test_selective_section_rendering(self, structured_renderer, sample_content):
        """Test rendering only specific sections."""
        variables = {"role": "assistant", "style": "friendly"}
        sections = ["system_role", "behavior"]
        
        result = structured_renderer.render(sample_content, variables, sections)
        
        # Should only have system message with role and behavior
        assert len(result) == 1
        assert result[0]["role"] == "system"
        
        content = result[0]["content"]
        assert "assistant" in content
        assert "friendly" in content
        assert "Never share" not in content  # restrictions not included
        assert "Use" not in content  # format not included
    
    def test_few_shots_only_rendering(self, structured_renderer, sample_content):
        """Test rendering only few-shot examples."""
        variables = {"name": "Alice"}
        sections = ["few_shots"]
        
        result = structured_renderer.render(sample_content, variables, sections)
        
        # Should have 4 messages: 2 user + 2 assistant from few-shots
        assert len(result) == 4
        
        # Check alternating pattern: user, assistant, user, assistant
        assert result[0]["role"] == "user"
        assert result[1]["role"] == "assistant"
        assert result[2]["role"] == "user" 
        assert result[3]["role"] == "assistant"
        
        # Check content
        assert "Hello Alice" in result[0]["content"]
        assert "Hi Alice" in result[1]["content"]
        assert "Thanks" in result[2]["content"]
        assert "You're welcome" in result[3]["content"]
    
    def test_multi_turn_few_shots(self, structured_renderer):
        """Test multi-turn few-shot examples."""
        multi_turn_content = StructuredPromptContent(
            system_role="Assistant",
            few_shots=[
                FewShotExample(
                    input=[
                        {"role": "user", "content": "Hi there"},
                        {"role": "assistant", "content": "Hello! How can I help?"},
                        {"role": "user", "content": "I need help with {{task}}"}
                    ],
                    output=[
                        {"role": "assistant", "content": "I'd be happy to help with {{task}}"}
                    ]
                )
            ]
        )
        
        variables = {"task": "coding"}
        result = structured_renderer.render(multi_turn_content, variables)
        
        # Should have system + multi-turn conversation
        assert len(result) >= 5  # System + 4 conversation turns
        
        # Find the multi-turn conversation
        conversation_msgs = [msg for msg in result if msg["role"] in ["user", "assistant"]]
        assert len(conversation_msgs) == 4
        
        # Check that variables were rendered
        help_msg = next((msg for msg in conversation_msgs if "coding" in msg["content"]), None)
        assert help_msg is not None
    
    def test_custom_sections_only(self, structured_renderer, sample_content):
        """Test rendering only custom sections."""
        variables = {"priority": "urgent", "category": "support"}
        sections = ["priority", "category"]
        
        result = structured_renderer.render(sample_content, variables, sections)
        
        # Should have 2 system messages for custom sections
        assert len(result) == 2
        assert all(msg["role"] == "system" for msg in result)
        
        # Check content
        priority_msg = next((msg for msg in result if "PRIORITY:" in msg["content"]), None)
        category_msg = next((msg for msg in result if "CATEGORY:" in msg["content"]), None)
        
        assert priority_msg is not None
        assert category_msg is not None
        assert "urgent priority" in priority_msg["content"]
        assert "support assistance" in category_msg["content"]
    
    def test_empty_content_rendering(self, structured_renderer):
        """Test rendering empty structured content."""
        empty_content = StructuredPromptContent()
        result = structured_renderer.render(empty_content, {})
        
        # Should return empty list
        assert result == []
    
    def test_template_error_handling(self, structured_renderer):
        """Test handling of template rendering errors."""
        content = StructuredPromptContent(
            system_role="You are a {{undefined_variable}} assistant"
        )
        
        with pytest.raises(TemplateRenderError) as exc_info:
            structured_renderer.render(content, {})
        
        error = exc_info.value
        assert "undefined_variable" in str(error)
    
    def test_template_caching(self, structured_renderer, sample_content):
        """Test that template rendering uses caching."""
        variables = {"role": "assistant"}
        
        # Render same content multiple times
        result1 = structured_renderer.render(sample_content, variables, ["system_role"])
        result2 = structured_renderer.render(sample_content, variables, ["system_role"])
        
        # Results should be identical
        assert result1 == result2
        
        # Cache info should show hits (if accessible)
        cache_info = structured_renderer._render_template.cache_info()
        assert cache_info.hits > 0


class TestFreeformRenderer:
    """Test FreeformRenderer functionality."""
    
    @pytest.fixture
    def freeform_renderer(self):
        """Create FreeformRenderer for testing."""
        jinja_env = Environment()
        return FreeformRenderer(jinja_env)
    
    @pytest.fixture
    def sample_freeform_content(self):
        """Sample freeform content for testing."""
        return FreeformPromptContent(
            template="Welcome {{name}} to our {{service}}.\n\nHere are the {{details}}.\n\nThank you!",
            sections={
                "greeting": "Welcome {{name}} to our {{service}}",
                "details": "Here are the {{details}}",
                "closing": "Thank you!"
            }
        )
    
    def test_basic_freeform_rendering(self, freeform_renderer, sample_freeform_content):
        """Test basic freeform prompt rendering."""
        variables = {
            "name": "John",
            "service": "AI platform",
            "details": "important features"
        }
        
        result = freeform_renderer.render(sample_freeform_content, variables)
        
        # Should return string
        assert isinstance(result, str)
        
        # Check that variables were rendered
        assert "Welcome John to our AI platform" in result
        assert "Here are the important features" in result
        assert "Thank you!" in result
    
    def test_selective_section_rendering(self, freeform_renderer, sample_freeform_content):
        """Test rendering only specific sections."""
        variables = {"name": "Alice", "service": "platform"}
        sections = ["greeting", "closing"]
        
        result = freeform_renderer.render(sample_freeform_content, variables, sections)
        
        # Should only have greeting and closing
        assert "Welcome Alice to our platform" in result
        assert "Thank you!" in result
        assert "Here are the" not in result  # details section excluded
    
    def test_single_section_rendering(self, freeform_renderer, sample_freeform_content):
        """Test rendering single section."""
        variables = {"name": "Bob", "service": "API"}
        sections = ["greeting"]
        
        result = freeform_renderer.render(sample_freeform_content, variables, sections)
        
        # Should only have greeting
        assert result == "Welcome Bob to our API"
    
    def test_empty_sections_list(self, freeform_renderer, sample_freeform_content):
        """Test rendering with empty sections list."""
        variables = {"name": "Charlie", "service": "system", "details": "info"}
        sections = []
        
        result = freeform_renderer.render(sample_freeform_content, variables, sections)
        
        # Should render nothing
        assert result == ""
    
    def test_nonexistent_sections(self, freeform_renderer, sample_freeform_content):
        """Test rendering with nonexistent sections."""
        variables = {"name": "Dave"}
        sections = ["nonexistent1", "nonexistent2"]
        
        result = freeform_renderer.render(sample_freeform_content, variables, sections)
        
        # Should render nothing
        assert result == ""
    
    def test_template_error_handling(self, freeform_renderer):
        """Test handling of template rendering errors."""
        content = FreeformPromptContent(
            template="Hello {{undefined_variable}}!",
            sections={"greeting": "Hello {{undefined_variable}}!"}
        )
        
        with pytest.raises(TemplateRenderError):
            freeform_renderer.render(content, {})


class TestHybridRenderer:
    """Test HybridRenderer functionality."""
    
    @pytest.fixture
    def hybrid_renderer(self):
        """Create HybridRenderer for testing."""
        jinja_env = Environment()
        return HybridRenderer(jinja_env, max_recursion_depth=10)
    
    @pytest.fixture
    def sample_hybrid_content(self):
        """Sample hybrid content for testing."""
        return HybridPromptContent(
            data={
                "format": "{{output_format}}",
                "settings": {
                    "temperature": "{{temperature}}",
                    "max_tokens": "{{max_tokens}}"
                },
                "instructions": [
                    "Step 1: {{step1}}",
                    "Step 2: {{step2}}"
                ],
                "nested": {
                    "deep": {
                        "template": "Deep value: {{deep_value}}"
                    }
                },
                "static_value": "This is static"
            }
        )
    
    def test_basic_hybrid_rendering(self, hybrid_renderer, sample_hybrid_content):
        """Test basic hybrid prompt rendering."""
        variables = {
            "output_format": "json",
            "temperature": "0.8",
            "max_tokens": "2000", 
            "step1": "analyze input",
            "step2": "generate response",
            "deep_value": "nested template"
        }
        
        result = hybrid_renderer.render(sample_hybrid_content, variables)
        
        # Should return dictionary
        assert isinstance(result, dict)
        
        # Check rendered values
        assert result["format"] == "json"
        assert result["settings"]["temperature"] == "0.8"
        assert result["settings"]["max_tokens"] == "2000"
        assert result["instructions"][0] == "Step 1: analyze input"
        assert result["instructions"][1] == "Step 2: generate response"
        assert result["nested"]["deep"]["template"] == "Deep value: nested template"
        assert result["static_value"] == "This is static"  # Unchanged
    
    def test_selective_section_rendering(self, hybrid_renderer, sample_hybrid_content):
        """Test rendering only specific sections."""
        variables = {"output_format": "yaml", "temperature": "0.5"}
        sections = ["format", "settings"]
        
        result = hybrid_renderer.render(sample_hybrid_content, variables, sections)
        
        # Should only have format and settings
        assert "format" in result
        assert "settings" in result
        assert "instructions" not in result
        assert "nested" not in result
        assert "static_value" not in result
        
        assert result["format"] == "yaml"
        assert result["settings"]["temperature"] == "0.5"
    
    def test_deep_nesting_rendering(self, hybrid_renderer):
        """Test rendering deeply nested structures."""
        content = HybridPromptContent(
            data={
                "level1": {
                    "level2": {
                        "level3": {
                            "template": "L3: {{value}}",
                            "array": ["{{item1}}", "{{item2}}"]
                        }
                    }
                }
            }
        )
        
        variables = {"value": "deep", "item1": "first", "item2": "second"}
        result = hybrid_renderer.render(content, variables)
        
        # Check deep nesting was rendered
        assert result["level1"]["level2"]["level3"]["template"] == "L3: deep"
        assert result["level1"]["level2"]["level3"]["array"] == ["first", "second"]
    
    def test_recursion_depth_limit(self, hybrid_renderer):
        """Test recursion depth limiting."""
        # Create very deeply nested structure
        nested_data = {"value": "{{var}}"}
        current = nested_data
        
        # Create nesting deeper than limit (15 levels)
        for i in range(15):
            new_level = {"nested": current}
            current = new_level
        
        content = HybridPromptContent(data=current)
        variables = {"var": "test"}
        
        # Should not crash due to recursion limit
        result = hybrid_renderer.render(content, variables)
        assert isinstance(result, dict)
    
    def test_mixed_types_rendering(self, hybrid_renderer):
        """Test rendering mixed data types."""
        content = HybridPromptContent(
            data={
                "string": "{{name}}",
                "number": 42,
                "boolean": True,
                "null_value": None,
                "list": ["{{item}}", 123, True],
                "dict": {"key": "{{value}}"}
            }
        )
        
        variables = {"name": "test", "item": "rendered", "value": "dict_value"}
        result = hybrid_renderer.render(content, variables)
        
        # Check types are preserved for non-string values
        assert result["string"] == "test"
        assert result["number"] == 42  # Unchanged
        assert result["boolean"] is True  # Unchanged
        assert result["null_value"] is None  # Unchanged
        assert result["list"] == ["rendered", 123, True]
        assert result["dict"]["key"] == "dict_value"
    
    def test_template_error_in_nested_structure(self, hybrid_renderer):
        """Test handling template errors in nested structures."""
        content = HybridPromptContent(
            data={
                "valid": "{{valid_var}}",
                "nested": {
                    "invalid": "{{undefined_variable}}"
                }
            }
        )
        
        variables = {"valid_var": "ok"}
        
        with pytest.raises(TemplateRenderError):
            hybrid_renderer.render(content, variables)
    
    def test_empty_hybrid_content(self, hybrid_renderer):
        """Test rendering empty hybrid content."""
        content = HybridPromptContent(data={})
        result = hybrid_renderer.render(content, {})
        
        assert result == {}
    
    def test_array_template_rendering(self, hybrid_renderer):
        """Test rendering templates within arrays."""
        content = HybridPromptContent(
            data={
                "steps": [
                    "First: {{step1}}",
                    "Second: {{step2}}",
                    {"nested_in_array": "{{nested}}"}
                ]
            }
        )
        
        variables = {"step1": "initialize", "step2": "execute", "nested": "array_nested"}
        result = hybrid_renderer.render(content, variables)
        
        assert result["steps"][0] == "First: initialize"
        assert result["steps"][1] == "Second: execute"
        assert result["steps"][2]["nested_in_array"] == "array_nested"


class TestRendererIntegration:
    """Test integration between different renderers."""
    
    def test_all_renderers_with_same_variables(self):
        """Test that all renderers work with the same variable set."""
        jinja_env = Environment()
        variables = {"name": "Alice", "role": "assistant", "task": "help"}
        
        # Test structured renderer
        structured_renderer = StructuredRenderer(jinja_env)
        structured_content = StructuredPromptContent(
            system_role="You are {{role}} named {{name}}"
        )
        structured_result = structured_renderer.render(structured_content, variables)
        assert isinstance(structured_result, list)
        assert "assistant named Alice" in structured_result[0]["content"]
        
        # Test freeform renderer
        freeform_renderer = FreeformRenderer(jinja_env)
        freeform_content = FreeformPromptContent(
            template="Hello {{name}}, I'm your {{role}} to {{task}}"
        )
        freeform_result = freeform_renderer.render(freeform_content, variables)
        assert isinstance(freeform_result, str)
        assert "Hello Alice, I'm your assistant to help" == freeform_result
        
        # Test hybrid renderer
        hybrid_renderer = HybridRenderer(jinja_env)
        hybrid_content = HybridPromptContent(
            data={
                "greeting": "Hello {{name}}",
                "role": "{{role}}",
                "purpose": "to {{task}}"
            }
        )
        hybrid_result = hybrid_renderer.render(hybrid_content, variables)
        assert isinstance(hybrid_result, dict)
        assert hybrid_result["greeting"] == "Hello Alice"
        assert hybrid_result["role"] == "assistant"
        assert hybrid_result["purpose"] == "to help"
    
    def test_renderer_error_consistency(self):
        """Test that all renderers handle errors consistently."""
        jinja_env = Environment()
        variables = {}  # Missing required variables
        
        renderers_and_content = [
            (StructuredRenderer(jinja_env), StructuredPromptContent(system_role="{{missing}}")),
            (FreeformRenderer(jinja_env), FreeformPromptContent(template="{{missing}}")),
            (HybridRenderer(jinja_env), HybridPromptContent(data={"key": "{{missing}}"}))
        ]
        
        for renderer, content in renderers_and_content:
            with pytest.raises(TemplateRenderError) as exc_info:
                renderer.render(content, variables)
            
            # All should raise TemplateRenderError with missing variable info
            assert "missing" in str(exc_info.value).lower()


class TestRendererPerformance:
    """Test renderer performance characteristics."""
    
    def test_structured_renderer_caching(self):
        """Test that structured renderer caching works."""
        jinja_env = Environment()
        renderer = StructuredRenderer(jinja_env)
        
        # Clear cache
        renderer._render_template.cache_clear()
        
        content = StructuredPromptContent(
            system_role="You are {{role}}",
            behavior="Be {{style}}"
        )
        
        variables = {"role": "assistant", "style": "helpful"}
        
        # First render
        result1 = renderer.render(content, variables)
        cache_info1 = renderer._render_template.cache_info()
        
        # Second render with same variables (should hit cache)
        result2 = renderer.render(content, variables) 
        cache_info2 = renderer._render_template.cache_info()
        
        # Results should be identical
        assert result1 == result2
        
        # Should have cache hits
        assert cache_info2.hits > cache_info1.hits
    
    def test_large_content_rendering(self):
        """Test rendering large content structures."""
        jinja_env = Environment()
        
        # Create large structured content
        large_content = StructuredPromptContent(
            system_role="System: {{role}}",
            behavior="Behavior: {{style}}",
            few_shots=[
                FewShotExample(
                    input=f"Input {i}: {{var{i}}}",
                    output=f"Output {i}: Response to {{var{i}}}"
                )
                for i in range(100)  # 100 few-shot examples
            ]
        )
        
        variables = {f"var{i}": f"value{i}" for i in range(100)}
        variables.update({"role": "assistant", "style": "professional"})
        
        renderer = StructuredRenderer(jinja_env)
        
        # Should handle large content without issues
        result = renderer.render(large_content, variables)
        
        # Should have system message + 200 few-shot messages (100 pairs)
        assert len(result) == 201
        assert result[0]["role"] == "system"
        
        # Check some few-shot examples were rendered correctly
        user_msgs = [msg for msg in result if msg["role"] == "user"]
        assert len(user_msgs) == 100
        assert "Input 0: value0" in user_msgs[0]["content"]