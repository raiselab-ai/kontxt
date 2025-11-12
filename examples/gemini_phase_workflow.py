"""Gemini Phase Workflow Example - Production-Ready Pattern.

This example demonstrates the complete phase workflow designed for Google Gemini:
- Type-safe Enum phases
- Proper Gemini format rendering
- Phase transitions with validation
- System instructions + phase-specific instructions
- Generation config support

Real-world use case: Customer support escalation workflow
"""

from enum import Enum

from kontxt import Context, State, SystemPrompt, ChatMessages, Format


class SupportPhases(str, Enum):
    """Support ticket escalation workflow phases."""

    TRIAGE = "triage"
    INVESTIGATION = "investigation"
    RESOLUTION = "resolution"
    CLOSED = "closed"


def main():
    print("=" * 80)
    print("GEMINI PHASE WORKFLOW EXAMPLE")
    print("Customer Support Escalation System")
    print("=" * 80)
    print()

    # ========================================================================
    # Setup: Initialize State and Context
    # ========================================================================
    state = State(
        initial={
            "ticket": {"id": "CS-2024-001", "priority": "high"},
            "customer": {"name": "Alice Johnson", "tier": "enterprise"},
        },
        current_phase=SupportPhases.TRIAGE,
        phases=SupportPhases,
    )

    ctx = Context(state=state)

    # Global system prompt (applies to all phases)
    ctx.add(
        SystemPrompt,
        "You are an expert customer support AI assistant. "
        "You provide clear, professional, and helpful responses.",
    )

    # ========================================================================
    # Configure Phases with Type-Safe Enums
    # ========================================================================

    ctx.phase(SupportPhases.TRIAGE).configure(
        instructions=(
            "TRIAGE PHASE: Gather initial information about the issue.\n"
            "- Ask clarifying questions\n"
            "- Identify issue category\n"
            "- Determine severity"
        ),
        includes=[SystemPrompt, ChatMessages],
        transitions_to=[SupportPhases.INVESTIGATION, SupportPhases.CLOSED],
        max_history=10,
    )

    ctx.phase(SupportPhases.INVESTIGATION).configure(
        instructions=(
            "INVESTIGATION PHASE: Deep dive into the technical issue.\n"
            "- Analyze logs and data\n"
            "- Reproduce the problem\n"
            "- Identify root cause"
        ),
        includes=[SystemPrompt, ChatMessages],
        transitions_to=[SupportPhases.RESOLUTION, SupportPhases.TRIAGE],
        max_history=8,
    )

    ctx.phase(SupportPhases.RESOLUTION).configure(
        instructions=(
            "RESOLUTION PHASE: Provide solution and verify fix.\n"
            "- Explain the solution clearly\n"
            "- Provide step-by-step instructions\n"
            "- Confirm issue is resolved"
        ),
        includes=[SystemPrompt, ChatMessages],
        transitions_to=[SupportPhases.CLOSED, SupportPhases.INVESTIGATION],
        max_history=5,
    )

    # ========================================================================
    # Phase 1: TRIAGE
    # ========================================================================
    print("📋 PHASE:", state.phase().upper())
    print("-" * 80)
    print()

    # Customer's initial message
    customer_msg = "Our production API is returning 500 errors for the past hour!"
    ctx.add_user_message(customer_msg)
    print(f"Customer: {customer_msg}")
    print()

    # Render for Gemini with generation config
    generation_config = {
        "temperature": 0.7,
        "topP": 0.9,
        "maxOutputTokens": 2048,
    }

    payload = ctx.render(format=Format.GEMINI, generation_config=generation_config)

    print("🔍 Gemini Payload Structure:")
    print(f"  - system_instruction: {len(payload['system_instruction']['parts'][0]['text'])} chars")
    print(f"  - contents: {len(payload['contents'])} messages")
    print(f"  - generation_config: {payload['generation_config']}")
    print()

    # Show what Gemini sees
    print("📤 System Instruction sent to Gemini:")
    print(payload["system_instruction"]["parts"][0]["text"][:200] + "...")
    print()

    # Simulate AI response
    ai_response = (
        "I understand this is urgent. Let me help you diagnose the issue. "
        "Can you tell me:\n"
        "1. Which endpoints are affected?\n"
        "2. What's the error message in the logs?\n"
        "3. Were there any recent deployments?"
    )
    ctx.add_response(ai_response)
    print(f"AI: {ai_response}")
    print()

    # ========================================================================
    # Phase 2: INVESTIGATION
    # ========================================================================
    print("✅ Advancing to INVESTIGATION phase...")
    ctx.advance_phase(SupportPhases.INVESTIGATION)
    print(f"📋 PHASE: {state.phase().upper()}")
    print("-" * 80)
    print()

    # Customer provides details
    customer_msg = "It's the /api/v1/payments endpoint. Error logs show 'Database connection timeout'."
    ctx.add_user_message(customer_msg)
    print(f"Customer: {customer_msg}")
    print()

    # Re-render for new phase
    payload = ctx.render(format=Format.GEMINI, generation_config=generation_config)

    print("🔍 New Gemini Payload (Investigation Phase):")
    print(f"  - system_instruction: {len(payload['system_instruction']['parts'][0]['text'])} chars")
    print(f"  - contents: {len(payload['contents'])} messages")
    print()

    # Verify instructions changed
    system_text = payload["system_instruction"]["parts"][0]["text"]
    assert "INVESTIGATION PHASE" in system_text
    assert "TRIAGE PHASE" not in system_text

    print("📤 New System Instruction (showing phase change):")
    investigation_line = [line for line in system_text.split("\n") if "INVESTIGATION" in line][0]
    print(f"  {investigation_line}")
    print()

    ai_response = (
        "I see the issue - database connection timeouts. "
        "This could be due to connection pool exhaustion. "
        "Let me check your database configuration."
    )
    ctx.add_response(ai_response)
    print(f"AI: {ai_response}")
    print()

    # ========================================================================
    # Phase 3: RESOLUTION
    # ========================================================================
    print("✅ Advancing to RESOLUTION phase...")
    ctx.advance_phase(SupportPhases.RESOLUTION)
    print(f"📋 PHASE: {state.phase().upper()}")
    print("-" * 80)
    print()

    customer_msg = "What's the fix?"
    ctx.add_user_message(customer_msg)
    print(f"Customer: {customer_msg}")
    print()

    payload = ctx.render(format=Format.GEMINI, generation_config=generation_config)

    ai_response = (
        "Here's the solution:\n\n"
        "1. Increase database connection pool from 10 to 50\n"
        "2. Add connection timeout of 30 seconds\n"
        "3. Restart the API service\n\n"
        "This should resolve the 500 errors immediately."
    )
    ctx.add_response(ai_response)
    print(f"AI: {ai_response}")
    print()

    # ========================================================================
    # Phase 4: CLOSED
    # ========================================================================
    print("✅ Advancing to CLOSED phase...")
    ctx.advance_phase(SupportPhases.CLOSED)
    print(f"📋 PHASE: {state.phase().upper()}")
    print()

    # ========================================================================
    # Summary
    # ========================================================================
    print("=" * 80)
    print("SUMMARY - What Makes This Production-Ready")
    print("=" * 80)
    print()
    print("✅ Type Safety:")
    print("   - Enum phases prevent typos")
    print("   - IDE autocomplete for all phase transitions")
    print("   - Compile-time checking for phase names")
    print()
    print("✅ Gemini-Specific Features:")
    print("   - Correct system_instruction format")
    print("   - Proper role mapping (assistant → model)")
    print("   - Generation config support")
    print("   - Instructions separate from system prompt")
    print()
    print("✅ Phase Management:")
    print("   - Automatic current phase tracking")
    print("   - Validated transitions")
    print("   - Phase-specific instructions")
    print("   - Per-phase max_history control")
    print()
    print("✅ Developer Experience:")
    print("   - ctx.render() auto-uses current phase")
    print("   - ctx.advance_phase() validates transitions")
    print("   - Clear error messages")
    print("   - No manual phase tracking needed")
    print()
    print("📊 Workflow Statistics:")
    print(f"   - Total phases: {len(SupportPhases)}")
    print(f"   - Messages exchanged: {len(ctx.get_section('messages') or [])}")
    print(f"   - Final state: {state.data}")
    print()


if __name__ == "__main__":
    main()
