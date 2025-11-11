"""Multi-phase workflow example with state management and type-safe API.

This example demonstrates building production-ready multi-phase workflows:
- Type-safe section references (SystemPrompt, ChatMessages)
- State initialization with phase validation
- Phase configuration with transition rules
- Context.advance_phase() with automatic validation
- Workflow coordination for complex agent systems

Use case: Medical triage assistant with intake → assessment → completion workflow.
"""

from enum import Enum

from kontxt import Context, State, SystemPrompt, ChatMessages, Format


# Define phases as enum for type safety
class TriagePhases(str, Enum):
    INTAKE = "intake"
    ASSESSMENT = "assessment"
    COMPLETE = "complete"


def main():
    print("=" * 80)
    print("KONTXT NEW API DEMO")
    print("=" * 80)
    print()

    # Initialize state with phase validation
    state = State(
        initial={
            "session": {
                "id": "demo-001",
                "phase": TriagePhases.INTAKE,
            },
            "patient": {
                "name": "Alice",
                "age": 28,
                "locale": "en-US",
            },
        },
        phases=TriagePhases,  # Validates phase values
    )

    print(f"Session ID: {state.get_path(['session', 'id'])}")
    print(f"Initial Phase: {state.phase()}")
    print(f"Patient: {state.get_path(['patient', 'name'])}, {state.get_path(['patient', 'age'])}")
    print()

    # Initialize context with state
    ctx = Context(state=state)

    # Add system prompt using type-safe constant
    ctx.add(SystemPrompt, "You are a helpful medical triage assistant.")

    # Configure phases with type-safe section references
    ctx.phase(TriagePhases.INTAKE).configure(
        instructions="Gather the patient's chief complaint and basic information.",
        includes=[SystemPrompt, ChatMessages],  # Type-safe!
        transitions_to=["assessment"],  # Only assessment allowed from intake
        max_history=10,
    )

    ctx.phase(TriagePhases.ASSESSMENT).configure(
        instructions="Assess the patient's condition based on gathered information.",
        includes=[SystemPrompt, ChatMessages],
        transitions_to=["complete"],
        max_history=5,
    )

    # ----------------------------------------------------------------
    # Phase 1: Intake
    # ----------------------------------------------------------------
    print("-" * 80)
    print(f"PHASE: {state.phase().upper()}")
    print("-" * 80)

    # Add user message using helper
    ctx.add_user_message("I've been experiencing headaches for the past week.")
    print(f"User: I've been experiencing headaches for the past week.")
    print()

    # Render for current phase
    rendered = ctx.render(phase=state.phase(), format=Format.TEXT)
    print("Rendered prompt preview:")
    print(rendered[:200] + "..." if len(rendered) > 200 else rendered)
    print()

    # Simulate assistant response
    assistant_msg = "I understand you've had headaches for a week. Can you describe the pain?"
    ctx.add_response(assistant_msg)
    print(f"Assistant: {assistant_msg}")
    print()

    # Advance to assessment phase (validated)
    print(f"✓ Advancing from '{state.phase()}' to 'assessment'...")
    ctx.advance_phase(TriagePhases.ASSESSMENT)
    print(f"✓ Current phase: {state.phase()}")
    print()

    # ----------------------------------------------------------------
    # Phase 2: Assessment
    # ----------------------------------------------------------------
    print("-" * 80)
    print(f"PHASE: {state.phase().upper()}")
    print("-" * 80)

    # Continue conversation
    ctx.add_user_message("It's a throbbing pain, usually on the right side.")
    print(f"User: It's a throbbing pain, usually on the right side.")
    print()

    # Render assessment phase
    rendered = ctx.render(phase=state.phase(), format=Format.TEXT)
    print("Rendered prompt preview:")
    print(rendered[:200] + "..." if len(rendered) > 200 else rendered)
    print()

    # Simulate assessment completion
    ctx.add_response("Based on your symptoms, this appears to be a migraine.")
    print(f"Assistant: Based on your symptoms, this appears to be a migraine.")
    print()

    # Complete workflow
    print(f"✓ Advancing from '{state.phase()}' to 'complete'...")
    ctx.advance_phase(TriagePhases.COMPLETE)
    print(f"✓ Current phase: {state.phase()}")
    print()

    # ----------------------------------------------------------------
    # Demo transition validation
    # ----------------------------------------------------------------
    print("=" * 80)
    print("TRANSITION VALIDATION DEMO")
    print("=" * 80)
    print()

    # Create new session to demo validation
    state2 = State(
        initial={"session": {"phase": "intake"}},
        phases=TriagePhases,
    )
    ctx2 = Context(state=state2)

    ctx2.phase(TriagePhases.INTAKE).configure(
        instructions="Intake phase",
        transitions_to=["assessment"],  # Only assessment allowed
    )

    print(f"Current phase: {state2.phase()}")
    print(f"Allowed transitions: ['assessment']")
    print()

    # Try invalid transition (would raise InvalidPhaseTransitionError)
    print("❌ Trying to transition directly to 'complete' (not allowed)...")
    print("   This would raise: InvalidPhaseTransitionError")
    print(f"   'Cannot transition from intake to complete'")
    print()

    print("✅ Transitioning to 'assessment' (allowed)...")
    ctx2.advance_phase(TriagePhases.ASSESSMENT)
    print(f"   Success! Current phase: {state2.phase()}")
    print()

    # ----------------------------------------------------------------
    # Summary
    # ----------------------------------------------------------------
    print("=" * 80)
    print("NEW API FEATURES DEMONSTRATED")
    print("=" * 80)
    print()
    print("✅ Type-Safe Section References:")
    print("   - ctx.add(SystemPrompt, ...) instead of ctx.add('system', ...)")
    print("   - IDE autocomplete and prevents typos")
    print()
    print("✅ State Phase Validation:")
    print("   - State(phases=TriagePhases) validates phase values")
    print("   - Catches invalid phases at runtime")
    print()
    print("✅ Transition Validation:")
    print("   - ctx.advance_phase() validates allowed transitions")
    print("   - Prevents invalid workflow states")
    print()
    print("✅ Convenience Helpers:")
    print("   - ctx.add_user_message(content) for cleaner code")
    print("   - ctx.add_response(text) for assistant responses")
    print()
    print("✅ Enum Support:")
    print("   - Works with Enum phases for type safety")
    print("   - Also accepts strings for flexibility")
    print()


if __name__ == "__main__":
    main()
