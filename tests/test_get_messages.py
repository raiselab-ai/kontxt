"""Tests for Context.get_messages() helper method."""

from kontxt import Context


def test_get_messages_all():
    """Test get_messages() returns all messages."""
    ctx = Context()

    ctx.add_user_message("Hello")
    ctx.add_response("Hi there")
    ctx.add_user_message("How are you?")

    messages = ctx.get_messages()

    assert len(messages) == 3
    assert messages[0] == {"role": "user", "content": "Hello"}
    assert messages[1] == {"role": "assistant", "content": "Hi there"}
    assert messages[2] == {"role": "user", "content": "How are you?"}


def test_get_messages_filter_user():
    """Test get_messages(role='user') returns only user messages."""
    ctx = Context()

    ctx.add_user_message("First user message")
    ctx.add_response("Assistant response")
    ctx.add_user_message("Second user message")
    ctx.add_response("Another response")

    user_messages = ctx.get_messages(role="user")

    assert len(user_messages) == 2
    assert user_messages[0] == {"role": "user", "content": "First user message"}
    assert user_messages[1] == {"role": "user", "content": "Second user message"}


def test_get_messages_filter_assistant():
    """Test get_messages(role='assistant') returns only assistant messages."""
    ctx = Context()

    ctx.add_user_message("User message 1")
    ctx.add_response("First response")
    ctx.add_user_message("User message 2")
    ctx.add_response("Second response")

    assistant_messages = ctx.get_messages(role="assistant")

    assert len(assistant_messages) == 2
    assert assistant_messages[0] == {"role": "assistant", "content": "First response"}
    assert assistant_messages[1] == {"role": "assistant", "content": "Second response"}


def test_get_messages_filter_system():
    """Test get_messages(role='system') returns only system messages."""
    ctx = Context()

    ctx.add("messages", {"role": "system", "content": "System context"})
    ctx.add_user_message("User message")
    ctx.add("messages", {"role": "system", "content": "More context"})

    system_messages = ctx.get_messages(role="system")

    assert len(system_messages) == 2
    assert system_messages[0] == {"role": "system", "content": "System context"}
    assert system_messages[1] == {"role": "system", "content": "More context"}


def test_get_messages_empty():
    """Test get_messages() returns empty list when no messages."""
    ctx = Context()

    messages = ctx.get_messages()
    assert messages == []

    # Also test with role filter
    user_messages = ctx.get_messages(role="user")
    assert user_messages == []


def test_get_messages_filters_non_message_items():
    """Test that get_messages() only returns properly formatted messages."""
    ctx = Context()

    # Add proper messages
    ctx.add_user_message("Proper message")

    # Add non-message items (shouldn't be returned)
    ctx.add("messages", "Just a string")  # Not a dict
    ctx.add("messages", {"no_role": "value"})  # Missing role
    ctx.add("messages", {"role": "user"})  # Missing content

    # Add another proper message
    ctx.add_response("Another proper message")

    messages = ctx.get_messages()

    # Should only have the 2 properly formatted messages
    assert len(messages) == 2
    assert messages[0] == {"role": "user", "content": "Proper message"}
    assert messages[1] == {"role": "assistant", "content": "Another proper message"}


def test_get_messages_with_custom_roles():
    """Test get_messages() works with custom roles."""
    ctx = Context()

    ctx.add_user_message("User")
    ctx.add("messages", {"role": "custom", "content": "Custom role"})
    ctx.add_response("Assistant")

    # Get all
    all_messages = ctx.get_messages()
    assert len(all_messages) == 3

    # Filter by custom role
    custom_messages = ctx.get_messages(role="custom")
    assert len(custom_messages) == 1
    assert custom_messages[0] == {"role": "custom", "content": "Custom role"}


def test_get_messages_preserves_extra_fields():
    """Test that get_messages() preserves extra fields in message dicts."""
    ctx = Context()

    # Add message with extra fields
    ctx.add("messages", {
        "role": "user",
        "content": "Hello",
        "timestamp": "2024-01-01",
        "metadata": {"key": "value"}
    })

    messages = ctx.get_messages()

    assert len(messages) == 1
    assert messages[0]["role"] == "user"
    assert messages[0]["content"] == "Hello"
    assert messages[0]["timestamp"] == "2024-01-01"
    assert messages[0]["metadata"] == {"key": "value"}


def test_get_messages_no_role_filter_none():
    """Test that role=None is same as not specifying role."""
    ctx = Context()

    ctx.add_user_message("Message 1")
    ctx.add_response("Message 2")

    messages_no_arg = ctx.get_messages()
    messages_none = ctx.get_messages(role=None)

    assert messages_no_arg == messages_none
    assert len(messages_no_arg) == 2
