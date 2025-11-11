"""Tests for new API features: SectionType, State validation, advance_phase."""

from __future__ import annotations

from enum import Enum

import pytest

from kontxt import Context, State, SystemPrompt, ChatMessages, SectionType
from kontxt.exceptions import InvalidPhaseError, InvalidPhaseTransitionError


# Test SectionType functionality
def test_section_type_basic():
    """Test SectionType basic functionality."""
    st = SectionType("custom")
    assert str(st) == "custom"
    assert repr(st) == "SectionType('custom')"


def test_section_type_equality():
    """Test SectionType equality with strings and other SectionTypes."""
    st1 = SectionType("test")
    st2 = SectionType("test")
    st3 = SectionType("other")

    assert st1 == st2
    assert st1 == "test"
    assert "test" == st1
    assert st1 != st3
    assert st1 != "other"


def test_section_type_hashable():
    """Test that SectionType can be used in sets and dicts."""
    st1 = SectionType("test")
    st2 = SectionType("test")

    # Should be hashable
    section_set = {st1, st2}
    assert len(section_set) == 1  # Same hash

    section_dict = {st1: "value"}
    assert section_dict[st2] == "value"


def test_context_add_with_section_type():
    """Test Context.add() accepts SectionType."""
    ctx = Context()

    # Add using built-in SectionType
    ctx.add(SystemPrompt, "You are helpful")
    ctx.add(ChatMessages, {"role": "user", "content": "Hello"})

    # Verify stored correctly (as strings)
    assert "system" in ctx._sections
    assert "messages" in ctx._sections
    assert ctx._sections["system"] == ["You are helpful"]


def test_context_add_with_custom_section_type():
    """Test Context.add() with custom SectionType."""
    ctx = Context()
    PatientData = SectionType("patient")

    ctx.add(PatientData, {"name": "John", "age": 30})

    assert "patient" in ctx._sections
    assert ctx._sections["patient"] == [{"name": "John", "age": 30}]


def test_phase_config_includes_with_section_type():
    """Test phase configuration accepts SectionType in includes."""
    ctx = Context()

    ctx.add(SystemPrompt, "System message")
    ctx.add(ChatMessages, {"role": "user", "content": "Hello"})

    ctx.phase("test").configure(
        instructions="Test instructions",
        includes=[SystemPrompt, ChatMessages],
    )

    # Render and verify sections included
    rendered = ctx.render(phase="test", format="text")
    assert "System message" in rendered
    assert "Hello" in rendered


def test_phase_config_includes_mixed_types():
    """Test phase includes can mix SectionType and strings."""
    ctx = Context()

    ctx.add(SystemPrompt, "System message")
    ctx.add("custom", "Custom data")

    ctx.phase("test").configure(
        includes=[SystemPrompt, "custom"],  # Mix types
    )

    rendered = ctx.render(phase="test", format="text")
    assert "System message" in rendered
    assert "Custom data" in rendered


# Test State phase validation
def test_state_phase_validation_with_enum():
    """Test State validates phases against enum."""

    class TestPhases(str, Enum):
        INITIAL = "initial"
        COMPLETE = "complete"

    state = State(
        initial={"session": {"phase": "initial"}},
        phases=TestPhases,
    )

    # Valid phase
    assert state.phase() == "initial"

    # Valid transition
    state.set_phase(TestPhases.COMPLETE)
    assert state.phase() == "complete"

    # Also accepts string
    state.set_phase("initial")
    assert state.phase() == "initial"


def test_state_phase_validation_invalid_phase():
    """Test State raises error for invalid phase."""

    class TestPhases(str, Enum):
        INITIAL = "initial"
        COMPLETE = "complete"

    state = State(
        initial={"session": {"phase": "initial"}},
        phases=TestPhases,
    )

    with pytest.raises(InvalidPhaseError) as exc_info:
        state.set_phase("invalid_phase")

    assert "Cannot set phase to 'invalid_phase'" in str(exc_info.value)
    assert "initial" in str(exc_info.value)
    assert "complete" in str(exc_info.value)


def test_state_phase_validation_invalid_initial():
    """Test State validates initial phase."""

    class TestPhases(str, Enum):
        INITIAL = "initial"
        COMPLETE = "complete"

    with pytest.raises(InvalidPhaseError) as exc_info:
        State(
            initial={"session": {"phase": "bad_phase"}},
            phases=TestPhases,
        )

    assert "Initial phase 'bad_phase' is not valid" in str(exc_info.value)


def test_state_without_phase_validation():
    """Test State works without phase validation (phases=None)."""
    state = State(initial={"session": {"phase": "anything"}})

    # Any phase is allowed
    state.set_phase("whatever")
    assert state.phase() == "whatever"

    state.set_phase("random")
    assert state.phase() == "random"


# Test Context.add_user_message()
def test_context_add_user_message():
    """Test add_user_message() helper."""
    ctx = Context()
    ctx.add_user_message("Hello!")

    messages = ctx.get_section("messages")
    assert len(messages) == 1
    assert messages[0] == {"role": "user", "content": "Hello!"}


def test_context_add_user_message_chaining():
    """Test add_user_message() supports chaining."""
    ctx = Context()
    result = ctx.add_user_message("Message 1").add_user_message("Message 2")

    assert result is ctx
    messages = ctx.get_section("messages")
    assert len(messages) == 2


# Test Context.advance_phase()
def test_context_advance_phase_basic():
    """Test basic phase advancement with transition validation."""

    class TestPhases(str, Enum):
        INITIAL = "initial"
        PROCESSING = "processing"
        COMPLETE = "complete"

    state = State(
        initial={"session": {"phase": "initial"}},
        phases=TestPhases,
    )
    ctx = Context(state=state)

    # Configure phases with transitions
    ctx.phase("initial").configure(
        instructions="Initial phase",
        transitions_to=["processing"],
    )
    ctx.phase("processing").configure(
        instructions="Processing phase",
        transitions_to=["complete"],
    )

    # Valid transition
    ctx.advance_phase(TestPhases.PROCESSING)
    assert state.phase() == "processing"

    # Another valid transition
    ctx.advance_phase(TestPhases.COMPLETE)
    assert state.phase() == "complete"


def test_context_advance_phase_invalid_transition():
    """Test advance_phase raises error for invalid transition."""

    class TestPhases(str, Enum):
        INITIAL = "initial"
        PROCESSING = "processing"
        COMPLETE = "complete"

    state = State(
        initial={"session": {"phase": "initial"}},
        phases=TestPhases,
    )
    ctx = Context(state=state)

    ctx.phase("initial").configure(
        transitions_to=["processing"],  # Only processing allowed
    )

    # Try to skip to complete (not allowed)
    with pytest.raises(InvalidPhaseTransitionError) as exc_info:
        ctx.advance_phase(TestPhases.COMPLETE)

    assert "Cannot transition from 'initial' to 'complete'" in str(exc_info.value)
    assert "processing" in str(exc_info.value)


def test_context_advance_phase_no_state():
    """Test advance_phase raises error if no State configured."""
    ctx = Context()  # No state

    with pytest.raises(ValueError) as exc_info:
        ctx.advance_phase("some_phase")

    assert "no State configured" in str(exc_info.value)


def test_context_advance_phase_unregistered_current():
    """Test advance_phase raises error if current phase not registered."""

    class TestPhases(str, Enum):
        INITIAL = "initial"
        COMPLETE = "complete"

    state = State(
        initial={"session": {"phase": "initial"}},
        phases=TestPhases,
    )
    ctx = Context(state=state)

    # Don't configure the "initial" phase
    # Try to advance
    with pytest.raises(InvalidPhaseError) as exc_info:
        ctx.advance_phase("complete")

    assert "Current phase 'initial' is not registered" in str(exc_info.value)


def test_context_advance_phase_no_restrictions():
    """Test advance_phase works when transitions_to is None (no restrictions)."""

    class TestPhases(str, Enum):
        INITIAL = "initial"
        COMPLETE = "complete"

    state = State(
        initial={"session": {"phase": "initial"}},
        phases=TestPhases,
    )
    ctx = Context(state=state)

    # Configure without transitions_to (allows any transition)
    ctx.phase("initial").configure(
        instructions="Initial phase",
        # transitions_to=None (default)
    )

    # Should work - no restrictions
    ctx.advance_phase(TestPhases.COMPLETE)
    assert state.phase() == "complete"


def test_context_advance_phase_validates_state_enum():
    """Test advance_phase also validates against State's phases enum."""

    class TestPhases(str, Enum):
        INITIAL = "initial"
        COMPLETE = "complete"

    state = State(
        initial={"session": {"phase": "initial"}},
        phases=TestPhases,  # State has enum validation
    )
    ctx = Context(state=state)

    ctx.phase("initial").configure(
        transitions_to=["complete", "invalid"],  # Context allows invalid
    )

    # Should fail State's validation (not Context's)
    with pytest.raises(InvalidPhaseError) as exc_info:
        ctx.advance_phase("invalid")

    assert "Cannot set phase to 'invalid'" in str(exc_info.value)


def test_full_workflow_with_new_api():
    """Test complete workflow using new API features."""

    class TriagePhases(str, Enum):
        INTAKE = "intake"
        ASSESSMENT = "assessment"
        COMPLETE = "complete"

    # Initialize state with phase validation
    state = State(
        initial={
            "session": {"id": "123", "phase": "intake"},
            "patient": {"name": "John", "age": 30},
        },
        phases=TriagePhases,
    )

    # Initialize context with state
    ctx = Context(state=state)

    # Configure phases with SectionType
    ctx.add(SystemPrompt, "You are a triage assistant")

    ctx.phase(TriagePhases.INTAKE).configure(
        instructions="Gather patient information",
        includes=[SystemPrompt, ChatMessages],
        transitions_to=["assessment"],
        max_history=10,
    )

    ctx.phase(TriagePhases.ASSESSMENT).configure(
        instructions="Assess patient condition",
        includes=[SystemPrompt, ChatMessages],
        transitions_to=["complete"],
        max_history=5,
    )

    # Add user message
    ctx.add_user_message("I have a headache")

    # Render for intake phase
    rendered = ctx.render(phase=state.phase(), format="text")
    assert "triage assistant" in rendered
    assert "headache" in rendered

    # Add response
    ctx.add_response("I'll help assess your headache")

    # Advance to assessment
    ctx.advance_phase(TriagePhases.ASSESSMENT)
    assert state.phase() == "assessment"

    # Add another message
    ctx.add_user_message("It's been hurting for 2 days")

    # Render assessment phase
    rendered = ctx.render(phase=state.phase(), format="text")
    assert "Assess patient condition" in rendered

    # Complete workflow
    ctx.advance_phase(TriagePhases.COMPLETE)
    assert state.phase() == "complete"
