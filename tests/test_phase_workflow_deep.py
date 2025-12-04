"""Deep integration tests for phase workflow with all render formats.

This test suite validates:
1. Complete phase workflow lifecycle
2. Gemini format rendering with phases
3. Edge cases and error conditions
4. DX patterns and consistency
"""

from __future__ import annotations

from enum import Enum

import pytest
from google.genai import types as genai_types

from kontxt import Context, State, SystemPrompt, ChatMessages, Format
from kontxt.exceptions import InvalidPhaseError, InvalidPhaseTransitionError


class WorkflowPhases(str, Enum):
    """Test phases for workflow."""

    INIT = "init"
    PROCESSING = "processing"
    REVIEW = "review"
    COMPLETE = "complete"


# ============================================================================
# Test 1: Complete Phase Workflow with Gemini Format
# ============================================================================


def test_full_phase_workflow_gemini_format():
    """Test complete phase workflow with Gemini rendering."""
    # Initialize state with enum
    state = State(
        initial={"user_id": "test-123"},
        current_phase=WorkflowPhases.INIT,
        phases=WorkflowPhases,
    )

    ctx = Context(state=state)

    # Add system prompt (applies to all phases)
    ctx.add(SystemPrompt, "You are a helpful AI assistant")

    # Configure phases with Enum transitions
    ctx.phase(WorkflowPhases.INIT).configure(
        instructions="Initial phase: gather requirements",
        includes=[SystemPrompt, ChatMessages],
        transitions_to=[WorkflowPhases.PROCESSING],
        max_history=10,
    )

    ctx.phase(WorkflowPhases.PROCESSING).configure(
        instructions="Processing phase: analyze and process",
        includes=[SystemPrompt, ChatMessages],
        transitions_to=[WorkflowPhases.REVIEW, WorkflowPhases.COMPLETE],
        max_history=5,
    )

    ctx.phase(WorkflowPhases.REVIEW).configure(
        instructions="Review phase: validate results",
        includes=[SystemPrompt, ChatMessages],
        transitions_to=[WorkflowPhases.COMPLETE],
        max_history=3,
    )

    # ======== Phase 1: INIT ========
    assert ctx.current_phase() == "init"

    ctx.add_user_message("I need help with a task")

    # Render with Gemini format
    payload = ctx.render(format=Format.GEMINI)

    # Validate structure
    assert "contents" in payload
    assert "system_instruction" in payload

    # Check system instruction combines system + instructions (now a list of Part objects)
    assert isinstance(payload["system_instruction"], list)
    assert isinstance(payload["system_instruction"][0], genai_types.Part)
    system_text = payload["system_instruction"][0].text
    assert "helpful AI assistant" in system_text
    assert "gather requirements" in system_text

    # Check messages (now Content objects)
    assert len(payload["contents"]) == 1
    assert isinstance(payload["contents"][0], genai_types.Content)
    assert payload["contents"][0].role == "user"
    assert "need help" in payload["contents"][0].parts[0].text

    # Add response
    ctx.add_response("I'll help you. What's the task?")

    # ======== Transition to PROCESSING ========
    ctx.advance_phase(WorkflowPhases.PROCESSING)
    assert ctx.current_phase() == "processing"

    ctx.add_user_message("I need to analyze data")
    payload = ctx.render(format=Format.GEMINI)

    # Verify instructions changed (system_instruction is a list of Part objects)
    assert isinstance(payload["system_instruction"], list)
    system_text = payload["system_instruction"][0].text
    assert "analyze and process" in system_text
    assert "gather requirements" not in system_text

    # Verify messages are preserved
    assert len(payload["contents"]) == 3  # user, model, user

    # ======== Transition to REVIEW ========
    ctx.add_response("Let me analyze that data for you")
    ctx.advance_phase(WorkflowPhases.REVIEW)

    payload = ctx.render(format=Format.GEMINI)
    assert isinstance(payload["system_instruction"], list)
    system_text = payload["system_instruction"][0].text
    assert "validate results" in system_text

    # ======== Complete workflow ========
    ctx.advance_phase(WorkflowPhases.COMPLETE)
    assert ctx.current_phase() == "complete"


# ============================================================================
# Test 2: Edge Cases and Error Handling
# ============================================================================


def test_phase_workflow_error_cases():
    """Test error handling in phase workflow."""

    # Error 1: Render without configuring phase
    state = State(current_phase="init")
    ctx = Context(state=state)

    with pytest.raises(InvalidPhaseError) as exc_info:
        ctx.render()

    assert "Phase 'init' is not registered" in str(exc_info.value)
    assert "ctx.phase('init').configure" in str(exc_info.value)

    # Error 2: Invalid transition
    state = State(current_phase="init", phases=WorkflowPhases)
    ctx = Context(state=state)

    ctx.phase("init").configure(
        transitions_to=[WorkflowPhases.PROCESSING],  # Only PROCESSING allowed
    )

    with pytest.raises(InvalidPhaseTransitionError) as exc_info:
        ctx.advance_phase(WorkflowPhases.COMPLETE)  # Try to skip to COMPLETE

    assert "Cannot transition from 'init' to 'complete'" in str(exc_info.value)
    assert "processing" in str(exc_info.value)

    # Error 3: Advance phase without state
    ctx_no_state = Context()

    with pytest.raises(ValueError) as exc_info:
        ctx_no_state.advance_phase("some_phase")

    assert "no State configured" in str(exc_info.value)

    # Error 4: Invalid phase in State's enum
    state = State(current_phase="init", phases=WorkflowPhases)
    ctx = Context(state=state)

    ctx.phase("init").configure(
        transitions_to=["init", "invalid"],  # Context allows "invalid"
    )

    # State should reject invalid phase
    with pytest.raises(InvalidPhaseError) as exc_info:
        ctx.advance_phase("invalid")

    assert "Cannot set phase to 'invalid'" in str(exc_info.value)


# ============================================================================
# Test 3: Gemini Format Specifics
# ============================================================================


def test_gemini_format_with_generation_config():
    """Test Gemini format with generation_config parameter."""
    state = State(current_phase="init")
    ctx = Context(state=state)

    ctx.add(SystemPrompt, "You are helpful")
    ctx.phase("init").configure(
        instructions="Test instructions",
        includes=[SystemPrompt],
    )

    # Render with generation config (using snake_case as per google.genai)
    generation_config = {
        "temperature": 0.7,
        "top_p": 0.9,
        "max_output_tokens": 1024,
    }

    payload = ctx.render(format=Format.GEMINI, generation_config=generation_config)

    assert "generation_config" in payload
    assert isinstance(payload["generation_config"], genai_types.GenerateContentConfig)
    assert payload["generation_config"].temperature == 0.7
    assert payload["generation_config"].top_p == 0.9
    assert payload["generation_config"].max_output_tokens == 1024


def test_gemini_role_mapping():
    """Test that roles are correctly mapped for Gemini."""
    state = State(current_phase="chat")
    ctx = Context(state=state)

    ctx.phase("chat").configure(includes=[ChatMessages])

    # Add messages with different roles
    ctx.add("messages", {"role": "user", "content": "Hello"})
    ctx.add("messages", {"role": "assistant", "content": "Hi there"})
    ctx.add("messages", {"role": "user", "content": "How are you?"})

    payload = ctx.render(format=Format.GEMINI)

    # Verify role mapping (using Content object attributes)
    for content in payload["contents"]:
        assert isinstance(content, genai_types.Content)
    assert payload["contents"][0].role == "user"
    assert payload["contents"][1].role == "model"  # assistant -> model
    assert payload["contents"][2].role == "user"


def test_gemini_system_in_messages():
    """Test that system messages in messages section are handled correctly."""
    state = State(current_phase="chat")
    ctx = Context(state=state)

    ctx.phase("chat").configure(includes=[ChatMessages])

    # Add system message in messages section
    ctx.add("messages", {"role": "system", "content": "Important context"})
    ctx.add("messages", {"role": "user", "content": "Hello"})

    payload = ctx.render(format=Format.GEMINI)

    # System message should be moved to system_instruction (as a list of Part objects)
    assert isinstance(payload["system_instruction"], list)
    assert isinstance(payload["system_instruction"][0], genai_types.Part)
    assert "Important context" in payload["system_instruction"][0].text

    # Only user message should be in contents (as Content object)
    assert len(payload["contents"]) == 1
    assert isinstance(payload["contents"][0], genai_types.Content)
    assert payload["contents"][0].role == "user"


# ============================================================================
# Test 4: DX and Consistency Checks
# ============================================================================


def test_phase_enum_consistency():
    """Test that Enums work consistently across all phase methods."""
    state = State(current_phase=WorkflowPhases.INIT, phases=WorkflowPhases)
    ctx = Context(state=state)

    # 1. ctx.phase() accepts Enum
    builder = ctx.phase(WorkflowPhases.INIT)
    assert builder is not None

    # 2. transitions_to accepts Enum
    builder.configure(transitions_to=[WorkflowPhases.PROCESSING, WorkflowPhases.COMPLETE])

    # 3. advance_phase accepts Enum
    ctx.advance_phase(WorkflowPhases.PROCESSING)
    assert ctx.current_phase() == "processing"

    # 4. State.set_phase accepts Enum
    state.set_phase(WorkflowPhases.COMPLETE)
    assert state.phase() == "complete"


def test_phase_string_consistency():
    """Test that strings still work everywhere (backward compatibility)."""
    state = State(current_phase="init", phases=WorkflowPhases)
    ctx = Context(state=state)

    # All string-based API should still work
    ctx.phase("init").configure(
        transitions_to=["processing", "complete"],
    )

    ctx.advance_phase("processing")
    assert ctx.current_phase() == "processing"

    state.set_phase("complete")
    assert state.phase() == "complete"


def test_mixed_enum_and_string_usage():
    """Test that Enums and strings can be mixed freely."""
    state = State(current_phase=WorkflowPhases.INIT, phases=WorkflowPhases)
    ctx = Context(state=state)

    # Mix Enum and string in transitions_to
    ctx.phase(WorkflowPhases.INIT).configure(
        transitions_to=[WorkflowPhases.PROCESSING, "complete"],  # Mixed!
    )

    # Use string to advance
    ctx.advance_phase("processing")
    assert ctx.current_phase() == "processing"

    # Reset and use Enum
    state.set_phase(WorkflowPhases.INIT)
    ctx.advance_phase(WorkflowPhases.PROCESSING)
    assert ctx.current_phase() == "processing"


# ============================================================================
# Test 5: Max History with Phases
# ============================================================================


def test_max_history_per_phase():
    """Test that max_history works correctly per phase."""
    # Use init phase from WorkflowPhases enum
    state = State(current_phase=WorkflowPhases.INIT, phases=WorkflowPhases)
    ctx = Context(state=state)

    # Add 10 messages
    for i in range(10):
        ctx.add_user_message(f"Message {i}")
        ctx.add_response(f"Response {i}")

    # Configure phase with max_history=4
    ctx.phase(WorkflowPhases.INIT).configure(
        includes=[ChatMessages],
        max_history=4,
    )

    payload = ctx.render(format=Format.GEMINI)

    # Should only have last 4 messages
    assert len(payload["contents"]) == 4

    # Verify it's the last 4 (using Content object attributes)
    assert isinstance(payload["contents"][-1], genai_types.Content)
    last_msg = payload["contents"][-1].parts[0].text
    assert "Response 9" in last_msg


# ============================================================================
# Test 6: Output Schema with Phases
# ============================================================================


def test_output_schema_with_phases():
    """Test that output schema works with phase rendering."""
    from pydantic import BaseModel

    class OutputSchema(BaseModel):
        result: str
        confidence: float

    state = State(current_phase="process")
    ctx = Context(state=state)

    ctx.phase("process").configure(includes=[SystemPrompt])
    ctx.add(SystemPrompt, "System message")

    # Set output schema
    ctx.set_output_schema(OutputSchema)

    # Render - schema should be included
    payload = ctx.render(format=Format.TEXT)

    assert "output_schema" in payload
    # Note: render_text doesn't process output_schema, but it's in the materialized dict


# ============================================================================
# Test 7: Token Counting with Phases
# ============================================================================


def test_token_count_with_phases():
    """Test token counting respects phases."""
    # Use INIT and PROCESSING from WorkflowPhases
    state = State(current_phase=WorkflowPhases.INIT, phases=WorkflowPhases)
    ctx = Context(state=state)

    ctx.add(SystemPrompt, "Short system message")
    ctx.add("extra_data", "This is a very long section with lots of content that adds many tokens to the total count")

    # INIT phase - only system (small)
    ctx.phase(WorkflowPhases.INIT).configure(includes=[SystemPrompt])

    # PROCESSING phase - system + extra (large)
    ctx.phase(WorkflowPhases.PROCESSING).configure(includes=[SystemPrompt, "extra_data"])

    # Count for current phase (INIT - small)
    small_count = ctx.token_count()

    # Count for PROCESSING phase (large)
    large_count = ctx.token_count(phase="processing")

    assert large_count > small_count


# ============================================================================
# Test 8: Memory Integration with Phases
# ============================================================================


def test_memory_with_phases():
    """Test that memory works correctly with phases."""
    from kontxt import Memory

    memory = Memory()
    memory.scratchpad.write("context_data", "Important context from memory")

    state = State(current_phase="process")
    ctx = Context(state=state, memory=memory)

    ctx.phase("process").configure(
        includes=[SystemPrompt],
        memory_includes=["context_data"],
    )

    ctx.add(SystemPrompt, "System instructions")

    payload = ctx.render(format=Format.TEXT)

    # Should include memory data
    assert "Important context from memory" in payload


# ============================================================================
# Test 9: Callable Instructions
# ============================================================================


def test_callable_instructions_with_phases():
    """Test that callable instructions work with phases."""
    state = State(current_phase="dynamic")
    ctx = Context(state=state)

    call_count = 0

    def dynamic_instructions():
        nonlocal call_count
        call_count += 1
        return f"Dynamic instructions (call #{call_count})"

    ctx.phase("dynamic").configure(
        instructions=dynamic_instructions,
        includes=[SystemPrompt],
    )

    ctx.add(SystemPrompt, "System")

    # First render
    payload1 = ctx.render(format=Format.TEXT)
    assert "call #1" in payload1

    # Second render should call again
    payload2 = ctx.render(format=Format.TEXT)
    assert "call #2" in payload2


# ============================================================================
# Test 10: All Format Consistency
# ============================================================================


def test_all_formats_with_phases():
    """Test that all render formats work correctly with phases."""
    state = State(current_phase="multi")
    ctx = Context(state=state)

    ctx.add(SystemPrompt, "System message")
    ctx.phase("multi").configure(
        instructions="Phase instructions",
        includes=[SystemPrompt, ChatMessages],
    )

    ctx.add_user_message("Hello")
    ctx.add_response("Hi there")

    # Test all formats
    text_output = ctx.render(format=Format.TEXT)
    assert "System message" in text_output
    assert "Phase instructions" in text_output

    openai_output = ctx.render(format=Format.OPENAI)
    assert isinstance(openai_output, list)
    assert len(openai_output) > 0

    anthropic_output = ctx.render(format=Format.ANTHROPIC)
    assert isinstance(anthropic_output, dict)
    assert "messages" in anthropic_output
    assert "system" in anthropic_output

    gemini_output = ctx.render(format=Format.GEMINI)
    assert isinstance(gemini_output, dict)
    assert "contents" in gemini_output
    assert "system_instruction" in gemini_output

    # String format names should also work
    text_str = ctx.render(format="text")
    assert text_str == text_output
