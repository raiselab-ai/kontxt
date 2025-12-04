"""Integration tests for GeminiProvider with full payload handling."""

from google.genai import types as genai_types

from kontxt import Context, State
from kontxt.providers import GeminiProvider
from kontxt.types import Format


def test_gemini_payload_with_system_instruction():
    """Test that system_instruction is properly extracted from rendered payload."""
    ctx = Context()
    ctx.add("system", "You are a helpful assistant.")
    ctx.add("instructions", "Be concise and direct.")
    ctx.add("messages", {"role": "user", "content": "Hello!"})

    payload = ctx.render(format=Format.GEMINI)

    # Verify structure
    assert "contents" in payload
    assert "system_instruction" in payload
    assert "system_instruction" not in payload["contents"]

    # Verify system_instruction is a list of Part objects
    assert isinstance(payload["system_instruction"], list)
    assert isinstance(payload["system_instruction"][0], genai_types.Part)
    system_text = payload["system_instruction"][0].text
    assert "You are a helpful assistant." in system_text
    assert "Be concise and direct." in system_text

    # Verify contents only has messages (as Content objects)
    assert len(payload["contents"]) == 1
    assert isinstance(payload["contents"][0], genai_types.Content)
    assert payload["contents"][0].role == "user"
    assert payload["contents"][0].parts[0].text == "Hello!"


def test_gemini_payload_with_tools():
    """Test that tools are properly extracted and passed separately."""

    # Mock tool declaration (what users would actually pass)
    advance_phase_tool = {
        "function_declarations": [{
            "name": "advance_phase",
            "description": "Advance to next phase",
            "parameters": {
                "type": "object",
                "properties": {
                    "phase": {"type": "string"}
                }
            }
        }]
    }

    ctx = Context()
    ctx.add("system", "You are a phase manager.")
    ctx.add("tools", advance_phase_tool)
    ctx.add("messages", {"role": "user", "content": "Move to next phase"})

    payload = ctx.render(format=Format.GEMINI)

    # Verify structure
    assert "contents" in payload
    assert "system_instruction" in payload
    assert "tools" in payload
    assert "generation_config" not in payload

    # Verify tools are separate from contents
    assert payload["tools"] == [advance_phase_tool]

    # Verify tools don't appear as text in contents (now using Content objects)
    for content in payload["contents"]:
        assert isinstance(content, genai_types.Content)
        text = content.parts[0].text
        assert "[tools]" not in text
        assert "advance_phase" not in text


def test_gemini_payload_with_phase_tools():
    """Test that tools configured via phase are properly rendered."""

    tool1 = {"name": "search"}
    tool2 = {"name": "calculate"}

    state = State(initial={"session": {"phase": "active"}})
    ctx = Context(state=state)

    # Configure phase with tools
    ctx.phase("active").configure(
        system="You are an assistant with tools.",
        tools=[tool1, tool2],
        includes=["messages"]
    )

    ctx.add("messages", {"role": "user", "content": "Help me"})

    payload = ctx.render(format=Format.GEMINI)

    # Verify tools are included at the top level
    assert "tools" in payload
    assert payload["tools"] == [tool1, tool2]


def test_gemini_payload_with_generation_config_and_tools():
    """Test that generation_config and tools are emitted separately."""

    tool = {"name": "test_tool"}
    gen_config = {"temperature": 0.7, "top_p": 0.9}

    ctx = Context()
    ctx.add("system", "Test system")
    ctx.add("tools", tool)
    ctx.add("messages", {"role": "user", "content": "Test"})

    payload = ctx.render(format=Format.GEMINI, generation_config=gen_config)

    # Verify both generation_config (as GenerateContentConfig) and tools are present
    assert "generation_config" in payload
    assert isinstance(payload["generation_config"], genai_types.GenerateContentConfig)
    assert payload["generation_config"].temperature == 0.7
    assert payload["generation_config"].top_p == 0.9
    assert payload["tools"] == [tool]


def test_gemini_payload_complete_workflow():
    """Test complete workflow with system, instructions, messages, and tools."""

    tool = {
        "function_declarations": [{
            "name": "get_weather",
            "description": "Get weather for a location"
        }]
    }

    state = State(initial={"session": {"phase": "query"}})
    ctx = Context(state=state)

    ctx.phase("query").configure(
        system="You are a weather assistant.",
        instructions="Always use the get_weather tool.",
        tools=[tool],
        includes=["messages"]
    )

    ctx.add_user_message("What's the weather in SF?")

    payload = ctx.render(format=Format.GEMINI)

    # Verify complete structure
    assert "contents" in payload
    assert "system_instruction" in payload
    assert "tools" in payload

    # Verify system_instruction is a list of Part objects
    assert isinstance(payload["system_instruction"], list)
    assert isinstance(payload["system_instruction"][0], genai_types.Part)
    system_text = payload["system_instruction"][0].text
    assert "You are a weather assistant." in system_text
    assert "Always use the get_weather tool." in system_text

    # Verify tools at the top level
    assert payload["tools"] == [tool]

    # Verify contents only has the message (as Content object)
    assert len(payload["contents"]) == 1
    assert isinstance(payload["contents"][0], genai_types.Content)
    assert payload["contents"][0].role == "user"


def test_gemini_payload_without_tools():
    """Test that generation_config is omitted when no tools and no config."""
    ctx = Context()
    ctx.add("system", "Test")
    ctx.add("messages", {"role": "user", "content": "Hi"})

    payload = ctx.render(format=Format.GEMINI)

    # No generation_config should be present
    assert "generation_config" not in payload
    assert "contents" in payload
    assert "system_instruction" in payload


def test_gemini_payload_with_only_generation_config():
    """Test generation_config without tools."""
    ctx = Context()
    ctx.add("messages", {"role": "user", "content": "Hi"})

    gen_config = {"temperature": 0.5}
    payload = ctx.render(format=Format.GEMINI, generation_config=gen_config)

    # Should have generation_config (as GenerateContentConfig) but no tools
    assert "generation_config" in payload
    assert isinstance(payload["generation_config"], genai_types.GenerateContentConfig)
    assert payload["generation_config"].temperature == 0.5
    assert "tools" not in payload


def test_gemini_payload_messages_only():
    """Test minimal payload with just messages."""
    ctx = Context()
    ctx.add_user_message("Hello")
    ctx.add_response("Hi there!")
    ctx.add_user_message("How are you?")

    payload = ctx.render(format=Format.GEMINI)

    # Verify structure - contents should be list of Content objects
    assert "contents" in payload
    assert len(payload["contents"]) == 3

    # Verify role mapping (using Content object attributes)
    for content in payload["contents"]:
        assert isinstance(content, genai_types.Content)
    assert payload["contents"][0].role == "user"
    assert payload["contents"][1].role == "model"  # assistant -> model
    assert payload["contents"][2].role == "user"

    # No system_instruction or generation_config
    assert "system_instruction" not in payload
    assert "generation_config" not in payload


class _DummyResponse:
    def __init__(self) -> None:
        self.candidates: list[object] = []


class _DummyChunk(_DummyResponse):
    pass


class _DummyModels:
    def __init__(self) -> None:
        self.generate_kwargs: dict[str, object] | None = None
        self.stream_kwargs: dict[str, object] | None = None

    def generate_content(self, **kwargs: object) -> _DummyResponse:
        self.generate_kwargs = kwargs
        return _DummyResponse()

    def generate_content_stream(self, **kwargs: object):
        self.stream_kwargs = kwargs
        yield _DummyChunk()


class _DummyClient:
    def __init__(self) -> None:
        self.models = _DummyModels()


def test_gemini_provider_passes_generation_config_and_tools():
    """Ensure provider forwards generation config defaults and ad-hoc overrides."""
    client = _DummyClient()
    provider = GeminiProvider(client=client, model="dummy-model", config={"temperature": 0.1})

    payload = {
        "contents": [{"role": "user", "parts": [{"text": "Hello"}]}],
        "system_instruction": {"parts": [{"text": "Be nice"}]},
        "generation_config": {"topP": 0.9},
        "tools": [{"name": "test_tool"}],
    }

    provider.generate(payload)

    assert client.models.generate_kwargs is not None
    kwargs = client.models.generate_kwargs
    assert kwargs["model"] == "dummy-model"
    assert kwargs["contents"] == payload["contents"]
    # system_instruction should be inside config, not separate
    assert "system_instruction" not in kwargs
    assert kwargs["config"]["system_instruction"] == payload["system_instruction"]
    # Default config merged with render-time config
    assert kwargs["config"]["temperature"] == 0.1
    assert kwargs["config"]["topP"] == 0.9
    assert kwargs["tools"] == payload["tools"]


def test_gemini_provider_streams_forward_tools_and_config():
    client = _DummyClient()
    provider = GeminiProvider(client=client, model="dummy-model")

    payload = {
        "contents": [{"role": "user", "parts": [{"text": "Stream?"}]}],
        "tools": [{"name": "stream_tool"}],
    }

    chunks = list(provider.stream(payload))
    assert len(chunks) == 1  # streaming stub yields one chunk

    assert client.models.stream_kwargs is not None
    kwargs = client.models.stream_kwargs
    assert kwargs["tools"] == payload["tools"]
    assert kwargs["contents"] == payload["contents"]
