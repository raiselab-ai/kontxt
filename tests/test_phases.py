from __future__ import annotations

import pytest

from kontxt import Context, PhaseConfig, State
from kontxt.exceptions import InvalidPhaseTransitionError


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


def test_state_phase_transitions() -> None:
    state = State({"session": {"phase": "complaint"}})
    state.configure_transitions({"complaint": ["history"], "history": ["assessment"]})
    state.set_phase("history")

    with pytest.raises(InvalidPhaseTransitionError):
        state.set_phase("complaint")

