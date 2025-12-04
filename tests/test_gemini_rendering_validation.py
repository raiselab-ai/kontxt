"""Validate Gemini rendering format is correct."""

from google.genai import types as genai_types

from kontxt import Context, State, SystemPrompt, ChatMessages, Format


def test_gemini_merges_system_and_instructions():
    """Verify that system + instructions are merged into system_instruction."""
    state = State(current_phase="test")
    ctx = Context(state=state)

    # Add system prompt (global)
    ctx.add(SystemPrompt, "You are a helpful assistant")

    # Configure phase with instructions
    ctx.phase("test").configure(
        instructions="Phase-specific instructions here",
        includes=[SystemPrompt, ChatMessages],
    )

    # Add a message
    ctx.add_user_message("Hello")

    # Render for Gemini
    payload = ctx.render(format=Format.GEMINI)

    # Verify structure
    assert "system_instruction" in payload
    assert "contents" in payload

    # Check system_instruction is a list of Part objects
    assert isinstance(payload["system_instruction"], list)
    assert isinstance(payload["system_instruction"][0], genai_types.Part)
    system_text = payload["system_instruction"][0].text
    assert "helpful assistant" in system_text
    assert "Phase-specific instructions" in system_text
    assert "\n\n" in system_text  # Should be separated

    # Check contents only has messages (not system/instructions)
    assert len(payload["contents"]) == 1
    assert isinstance(payload["contents"][0], genai_types.Content)
    assert payload["contents"][0].role == "user"
    assert payload["contents"][0].parts[0].text == "Hello"


def test_gemini_contents_only_messages():
    """Verify contents section only includes message history."""
    state = State(current_phase="test")
    ctx = Context(state=state)

    ctx.phase("test").configure(
        includes=[ChatMessages],
    )

    # Add conversation
    ctx.add_user_message("First message")
    ctx.add_response("First response")
    ctx.add_user_message("Second message")

    payload = ctx.render(format=Format.GEMINI)

    # Should have exactly 3 messages in contents
    assert len(payload["contents"]) == 3

    # Verify all are Content objects
    for content in payload["contents"]:
        assert isinstance(content, genai_types.Content)

    # Verify roles
    assert payload["contents"][0].role == "user"
    assert payload["contents"][1].role == "model"  # assistant -> model
    assert payload["contents"][2].role == "user"

    # Verify content
    assert "First message" in payload["contents"][0].parts[0].text
    assert "First response" in payload["contents"][1].parts[0].text
    assert "Second message" in payload["contents"][2].parts[0].text


def test_gemini_no_system_in_contents():
    """Verify system/instructions never appear in contents."""
    state = State(current_phase="test")
    ctx = Context(state=state)

    ctx.add(SystemPrompt, "System prompt")
    ctx.phase("test").configure(
        instructions="Instructions",
        includes=[SystemPrompt, ChatMessages],
    )

    ctx.add_user_message("User message")

    payload = ctx.render(format=Format.GEMINI)

    # Contents should only have user message
    assert len(payload["contents"]) == 1
    assert isinstance(payload["contents"][0], genai_types.Content)
    assert payload["contents"][0].role == "user"
    assert payload["contents"][0].parts[0].text == "User message"

    # System/instructions should be in system_instruction as a list of Part objects
    assert isinstance(payload["system_instruction"], list)
    assert isinstance(payload["system_instruction"][0], genai_types.Part)
    system_text = payload["system_instruction"][0].text
    assert "System prompt" in system_text
    assert "Instructions" in system_text


def test_gemini_system_messages_moved_to_instruction():
    """Verify system role messages are moved to system_instruction."""
    state = State(current_phase="test")
    ctx = Context(state=state)

    ctx.phase("test").configure(includes=[ChatMessages])

    # Add system message in messages section
    ctx.add("messages", {"role": "system", "content": "Important context"})
    ctx.add_user_message("Hello")

    payload = ctx.render(format=Format.GEMINI)

    # System message should be in system_instruction as a list of Part objects
    assert isinstance(payload["system_instruction"], list)
    assert isinstance(payload["system_instruction"][0], genai_types.Part)
    assert "Important context" in payload["system_instruction"][0].text

    # Contents should only have user message
    assert len(payload["contents"]) == 1
    assert isinstance(payload["contents"][0], genai_types.Content)
    assert payload["contents"][0].role == "user"


def test_gemini_other_sections_as_user_messages():
    """Verify non-standard sections are added as user messages with labels."""
    state = State(current_phase="test")
    ctx = Context(state=state)

    ctx.add("custom_data", "Some custom data")
    ctx.phase("test").configure(includes=["custom_data", ChatMessages])

    ctx.add_user_message("Hello")

    payload = ctx.render(format=Format.GEMINI)

    # Should have 2 messages in contents
    assert len(payload["contents"]) == 2

    # Verify both are Content objects
    for content in payload["contents"]:
        assert isinstance(content, genai_types.Content)

    # First should be custom_data as user message with label
    assert payload["contents"][0].role == "user"
    assert "[custom_data]" in payload["contents"][0].parts[0].text
    assert "Some custom data" in payload["contents"][0].parts[0].text

    # Second should be user message
    assert payload["contents"][1].role == "user"
    assert payload["contents"][1].parts[0].text == "Hello"


def test_complete_gemini_payload_structure():
    """Validate complete Gemini payload matches API spec with proper types."""
    state = State(current_phase="test")
    ctx = Context(state=state)

    ctx.add(SystemPrompt, "You are helpful")
    ctx.phase("test").configure(
        instructions="Test phase",
        includes=[SystemPrompt, ChatMessages],
    )

    ctx.add_user_message("Hi")
    ctx.add_response("Hello")

    generation_config = {"temperature": 0.7}
    payload = ctx.render(format=Format.GEMINI, generation_config=generation_config)

    # Validate top-level structure
    assert set(payload.keys()) == {"contents", "system_instruction", "generation_config"}

    # Validate system_instruction is a list of Part objects
    assert isinstance(payload["system_instruction"], list)
    assert len(payload["system_instruction"]) == 1
    assert isinstance(payload["system_instruction"][0], genai_types.Part)
    assert payload["system_instruction"][0].text is not None

    # Validate contents structure - should be list of Content objects
    assert isinstance(payload["contents"], list)
    for content in payload["contents"]:
        assert isinstance(content, genai_types.Content)
        assert content.role in ["user", "model"]
        assert isinstance(content.parts, list)
        assert len(content.parts) > 0
        # Parts should have text attribute
        assert content.parts[0].text is not None

    # Validate generation_config is a GenerateContentConfig object
    assert isinstance(payload["generation_config"], genai_types.GenerateContentConfig)
    assert payload["generation_config"].temperature == 0.7


def test_gemini_empty_system_instruction():
    """Verify system_instruction is omitted if no system/instructions."""
    state = State(current_phase="test")
    ctx = Context(state=state)

    ctx.phase("test").configure(includes=[ChatMessages])
    ctx.add_user_message("Hello")

    payload = ctx.render(format=Format.GEMINI)

    # Should not have system_instruction
    assert "system_instruction" not in payload or payload["system_instruction"] is None

    # Should only have contents with proper type
    assert "contents" in payload
    assert len(payload["contents"]) == 1
    assert isinstance(payload["contents"][0], genai_types.Content)
