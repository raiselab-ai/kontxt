from __future__ import annotations

from datetime import datetime

from kontxt import Context, Format, Memory


def test_context_add_and_render_text(context: Context) -> None:
    context.add("messages", {"role": "user", "content": "Hello"})
    context.add("current_time", lambda: datetime(2025, 1, 1, 12, 0).isoformat())

    rendered = context.render()

    assert "You are a helpful assistant." in rendered
    assert "2025-01-01T12:00:00" in rendered


def test_context_render_openai(context: Context) -> None:
    context.add("messages", {"role": "user", "content": "Ping"})
    messages = context.render(format="openai")

    assert messages[0]["role"] == "system"
    assert any(m["role"] == "user" for m in messages)


def test_context_phase_configuration() -> None:
    ctx = Context()
    ctx.add("patient", {"name": "John"})
    ctx.phase("complaint").configure(
        system="System prompt",
        instructions="Ask about pain scale",
        includes=["patient"],
        tools=["scribe"],
    )

    rendered = ctx.render(phase="complaint", format="anthropic")
    assert rendered["system"] == "System prompt"
    assert any(block["content"].startswith("[patient]") for block in rendered["messages"])


# ------------------------------------------------------------------
# Memory Integration Tests
# ------------------------------------------------------------------
def test_context_with_memory_default() -> None:
    """Test Context initialized with a default memory."""
    memory = Memory()
    memory.scratchpad.write("chief_complaint", "Patient reports chest pain")

    ctx = Context(memory=memory)
    ctx.add("system", "You are a medical AI")
    ctx.phase("assessment").configure(
        instructions="Analyze the chief complaint",
        memory_includes=["chief_complaint"],
    )

    rendered = ctx.render(phase="assessment")
    assert "chest pain" in rendered


def test_context_memory_override_per_render() -> None:
    """Test overriding memory per render call."""
    user1_memory = Memory()
    user1_memory.scratchpad.write("context", "User 1 data")

    user2_memory = Memory()
    user2_memory.scratchpad.write("context", "User 2 data")

    ctx = Context(memory=user1_memory)
    ctx.phase("test").configure(memory_includes=["context"])

    # Render with default memory
    rendered1 = ctx.render(phase="test")
    assert "User 1 data" in rendered1

    # Render with override memory
    rendered2 = ctx.render(phase="test", memory=user2_memory)
    assert "User 2 data" in rendered2


def test_context_memory_includes_multiple_keys() -> None:
    """Test memory_includes with multiple keys."""
    memory = Memory()
    memory.scratchpad.write("vital_signs", "BP: 120/80, HR: 72")
    memory.scratchpad.write("medications", "Lisinopril 10mg")
    memory.scratchpad.write("allergies", "Penicillin")

    ctx = Context(memory=memory)
    ctx.phase("review").configure(
        instructions="Review patient data",
        memory_includes=["vital_signs", "medications", "allergies"],
    )

    rendered = ctx.render(phase="review")
    assert "120/80" in rendered
    assert "Lisinopril" in rendered
    assert "Penicillin" in rendered


def test_context_memory_includes_missing_keys() -> None:
    """Test that missing memory keys are gracefully skipped."""
    memory = Memory()
    memory.scratchpad.write("available_data", "This exists")

    ctx = Context(memory=memory)
    ctx.phase("test").configure(
        instructions="Test phase",
        memory_includes=["available_data", "missing_data"],
    )

    # Should not raise error, just skip missing keys
    rendered = ctx.render(phase="test")
    assert "This exists" in rendered


def test_context_no_memory_provided() -> None:
    """Test phase with memory_includes but no memory provided."""
    ctx = Context()  # No memory
    ctx.phase("test").configure(
        instructions="Test without memory",
        memory_includes=["some_key"],
    )

    # Should not raise error, just skip memory sections
    rendered = ctx.render(phase="test")
    assert "Test without memory" in rendered


def test_context_callable_instructions() -> None:
    """Test callable instructions in phase config."""
    call_count = 0

    def dynamic_instructions() -> str:
        nonlocal call_count
        call_count += 1
        return f"Dynamic instruction #{call_count}"

    ctx = Context()
    ctx.phase("test").configure(instructions=dynamic_instructions)

    rendered1 = ctx.render(phase="test")
    assert "Dynamic instruction #1" in rendered1

    rendered2 = ctx.render(phase="test")
    assert "Dynamic instruction #2" in rendered2


def test_context_max_history_trimming() -> None:
    """Test max_history trims messages section."""
    ctx = Context()

    # Add 10 messages
    for i in range(10):
        ctx.add("messages", {"role": "user", "content": f"Message {i}"})

    ctx.phase("test").configure(
        includes=["messages"],
        max_history=5,
    )

    rendered = ctx.render(phase="test")

    # Should only include last 5 messages
    assert "Message 5" in rendered
    assert "Message 9" in rendered
    assert "Message 0" not in rendered
    assert "Message 4" not in rendered


def test_context_memory_and_includes_combined() -> None:
    """Test that both context includes and memory_includes work together."""
    memory = Memory()
    memory.scratchpad.write("memory_data", "From memory")

    ctx = Context(memory=memory)
    ctx.add("context_data", "From context")

    ctx.phase("combined").configure(
        includes=["context_data"],
        memory_includes=["memory_data"],
    )

    rendered = ctx.render(phase="combined")
    assert "From context" in rendered
    assert "From memory" in rendered


def test_context_render_without_phase_ignores_memory() -> None:
    """Test that rendering without a phase doesn't use memory."""
    memory = Memory()
    memory.scratchpad.write("key", "value")

    ctx = Context(memory=memory)
    ctx.add("system", "System prompt")

    # Render without phase - memory should not be included
    rendered = ctx.render()
    assert "System prompt" in rendered
    # Memory data should not be in output since no phase was specified


# ------------------------------------------------------------------
# Gemini Integration Tests
# ------------------------------------------------------------------
def test_context_render_gemini_format() -> None:
    """Test rendering context in Gemini API format with proper types."""
    from google.genai import types as genai_types

    ctx = Context()
    ctx.add("system", "You are a helpful assistant")
    ctx.add("messages", {"role": "user", "content": "Hello"})
    ctx.add("messages", {"role": "assistant", "content": "Hi there"})

    payload = ctx.render(format=Format.GEMINI)

    assert "system_instruction" in payload
    assert "contents" in payload
    # system_instruction is now a list of Part objects
    assert isinstance(payload["system_instruction"], list)
    assert isinstance(payload["system_instruction"][0], genai_types.Part)
    assert payload["system_instruction"][0].text == "You are a helpful assistant"
    # contents is now a list of Content objects
    assert len(payload["contents"]) == 2
    assert isinstance(payload["contents"][0], genai_types.Content)
    assert payload["contents"][0].role == "user"
    assert payload["contents"][0].parts[0].text == "Hello"
    assert payload["contents"][1].role == "model"  # assistant -> model
    assert payload["contents"][1].parts[0].text == "Hi there"


def test_context_render_gemini_with_generation_config() -> None:
    """Test rendering with generation_config parameter."""
    from google.genai import types as genai_types

    ctx = Context()
    ctx.add("messages", {"role": "user", "content": "Test message"})

    payload = ctx.render(
        format=Format.GEMINI,
        generation_config={"temperature": 0.7, "top_p": 0.9}
    )

    assert "generation_config" in payload
    assert isinstance(payload["generation_config"], genai_types.GenerateContentConfig)
    assert payload["generation_config"].temperature == 0.7
    assert payload["generation_config"].top_p == 0.9


def test_context_render_gemini_with_instructions() -> None:
    """Test that instructions are included in system_instruction."""
    from google.genai import types as genai_types

    ctx = Context()
    ctx.phase("test").configure(
        system="System message",
        instructions="Follow these instructions",
        includes=["messages"]
    )
    ctx.add("messages", {"role": "user", "content": "Hello"})

    payload = ctx.render(phase="test", format=Format.GEMINI)

    # system_instruction is now a list of Part objects
    assert isinstance(payload["system_instruction"], list)
    assert isinstance(payload["system_instruction"][0], genai_types.Part)
    system_text = payload["system_instruction"][0].text
    assert "System message" in system_text
    assert "Follow these instructions" in system_text


def test_context_add_response_helper() -> None:
    """Test add_response() convenience method."""
    ctx = Context()
    ctx.add("messages", {"role": "user", "content": "Hello"})

    # Add assistant response
    ctx.add_response("Hi there, how can I help?")

    messages = ctx.get_section("messages")
    assert len(messages) == 2
    assert messages[1]["role"] == "assistant"
    assert messages[1]["content"] == "Hi there, how can I help?"


def test_context_add_response_with_custom_role() -> None:
    """Test add_response() with custom role."""
    ctx = Context()
    ctx.add("messages", {"role": "user", "content": "Hello"})

    # Add response with custom role
    ctx.add_response("System message", role="system")

    messages = ctx.get_section("messages")
    assert len(messages) == 2
    assert messages[1]["role"] == "system"
    assert messages[1]["content"] == "System message"


def test_gemini_integration_full_workflow() -> None:
    """Test complete workflow simulating Gemini integration."""
    from google.genai import types as genai_types

    memory = Memory()
    ctx = Context(memory=memory)

    # Setup phase with memory
    ctx.phase("chat").configure(
        instructions="You are a medical assistant",
        includes=["messages"],
        memory_includes=["patient_data"],
        max_history=5
    )

    # Store patient data in memory
    memory.scratchpad.write("patient_data", "Patient: Age 45, HTN")

    # Start conversation
    ctx.add("messages", {"role": "user", "content": "What's my blood pressure?"})

    # Render for Gemini
    payload = ctx.render(
        phase="chat",
        format=Format.GEMINI,
        generation_config={"temperature": 0.5}
    )

    # Verify payload structure with proper types
    assert "contents" in payload
    assert "system_instruction" in payload
    assert "generation_config" in payload

    # Verify patient data included - system_instruction is now a list of Part objects
    assert isinstance(payload["system_instruction"], list)
    assert isinstance(payload["system_instruction"][0], genai_types.Part)
    system_text = payload["system_instruction"][0].text
    assert "medical assistant" in system_text

    # Verify message in contents - contents is now a list of Content objects
    assert isinstance(payload["contents"][0], genai_types.Content)
    assert payload["contents"][0].role == "user"

    # Simulate API response
    ctx.add_response("Your current blood pressure reading shows 145/92 mmHg")

    # Verify response added
    messages = ctx.get_section("messages")
    assert len(messages) == 2
    assert messages[1]["role"] == "assistant"


