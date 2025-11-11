from __future__ import annotations

from kontxt import Context, PhaseConfig, State


def test_phase_builder_customization() -> None:
    ctx = Context()
    ctx.phase("assessment").configure(
        system="Assess the patient",
        instructions="Provide urgency and plan.",
        includes=["patient", "messages"],
        memory_includes=["similar_cases"],
        tools=["draft_prescription"],
        max_history=5,
        transitions_to=["done"],
    )

    phase = ctx._phases["assessment"]
    assert isinstance(phase, PhaseConfig)
    assert phase.tools == ["draft_prescription"]
    assert phase.max_history == 5
    assert phase.transitions_to == ["done"]


def test_state_phase_tracking() -> None:
    """Test that State tracks phase changes (transitions validated by phases, not State)."""
    state = State({"session": {"phase": "complaint"}})

    # State simply tracks current phase
    assert state.phase() == "complaint"

    # State allows any phase transition (validation is phase's responsibility)
    state.set_phase("history")
    assert state.phase() == "history"

    state.set_phase("assessment")
    assert state.phase() == "assessment"

