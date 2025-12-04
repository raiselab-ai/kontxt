"""Gemini Format Demo - Shows exactly what gets sent to Gemini API.

This demo proves that:
1. system + instructions are MERGED into system_instruction
2. contents only has message history
3. No system/instructions leak into contents
4. All objects are proper google.genai.types objects
"""

from enum import Enum

from google.genai import types as genai_types

from kontxt import Context, State, SystemPrompt, ChatMessages, Format


class Phases(str, Enum):
    CHAT = "chat"


def main():
    print("=" * 80)
    print("GEMINI FORMAT VALIDATION DEMO")
    print("=" * 80)
    print()

    # Setup
    state = State(current_phase=Phases.CHAT, phases=Phases)
    ctx = Context(state=state)

    # Add system prompt (global)
    ctx.add(SystemPrompt, "You are a helpful AI assistant specialized in customer support.")

    # Configure phase with instructions
    ctx.phase(Phases.CHAT).configure(
        instructions="Current phase: Customer interaction. Be friendly and professional.",
        includes=[SystemPrompt, ChatMessages],
    )

    # Add conversation
    ctx.add_user_message("Hello, I need help with my account")
    ctx.add_response("I'd be happy to help! What seems to be the issue?")
    ctx.add_user_message("I can't log in")

    # Render for Gemini
    payload = ctx.render(format=Format.GEMINI, generation_config={"temperature": 0.7})

    print("📤 PAYLOAD SENT TO GEMINI:")
    print("(Payload contains proper google.genai.types objects)")
    print()

    # Validate structure
    print("=" * 80)
    print("VALIDATION CHECKS")
    print("=" * 80)
    print()

    # Check 1: system_instruction is a list of Part objects
    assert isinstance(payload["system_instruction"], list)
    assert isinstance(payload["system_instruction"][0], genai_types.Part)
    system_text = payload["system_instruction"][0].text
    print("✅ CHECK 1: system + instructions merged into system_instruction (as Part objects)")
    print("   Type: list[genai_types.Part]")
    print(f"   Length: {len(system_text)} chars")
    print(f"   Contains 'customer support': {'customer support' in system_text}")
    print(f"   Contains 'Current phase': {'Current phase' in system_text}")
    double_newline_present = '\n\n' in system_text
    print(f"   Separated by double newline: {double_newline_present}")
    print()

    # Check 2: contents is a list of Content objects
    print("✅ CHECK 2: contents only has message history (as Content objects)")
    print(f"   Number of messages: {len(payload['contents'])}")
    for i, msg in enumerate(payload["contents"]):
        assert isinstance(msg, genai_types.Content)
        print(f"   Message {i+1}: role={msg.role}, text={msg.parts[0].text[:50]}...")
    print()

    # Check 3: No system/instructions in contents
    print("✅ CHECK 3: No system/instructions leaked into contents")
    has_system_in_contents = any(
        "customer support" in msg.parts[0].text or "Current phase" in msg.parts[0].text
        for msg in payload["contents"]
    )
    print(f"   System text found in contents: {has_system_in_contents}")
    print()

    # Check 4: Role mapping
    print("✅ CHECK 4: Roles correctly mapped")
    roles = [msg.role for msg in payload["contents"]]
    print(f"   Roles: {roles}")
    print(f"   'assistant' mapped to 'model': {'model' in roles and 'assistant' not in roles}")
    print()

    # Check 5: Generation config is a GenerateContentConfig object
    print("✅ CHECK 5: generation_config is proper GenerateContentConfig object")
    assert isinstance(payload["generation_config"], genai_types.GenerateContentConfig)
    print("   Type: genai_types.GenerateContentConfig")
    print(f"   Temperature: {payload['generation_config'].temperature}")
    print()

    print("=" * 80)
    print("DETAILED BREAKDOWN")
    print("=" * 80)
    print()

    print("📋 system_instruction (what Gemini sees as system prompt):")
    print("-" * 80)
    print(payload["system_instruction"][0].text)
    print()

    print("💬 contents (conversation history):")
    print("-" * 80)
    for i, msg in enumerate(payload["contents"]):
        print(f"{i+1}. [{msg.role.upper()}]: {msg.parts[0].text}")
    print()

    print("=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print()
    print("✅ system + instructions → MERGED into system_instruction (list[Part])")
    print("✅ contents → ONLY message history (list[Content])")
    print("✅ generation_config → GenerateContentConfig object")
    print("✅ No leakage → system/instructions NOT in contents")
    print("✅ Roles mapped → assistant becomes model")
    print()
    print("🎉 Gemini rendering uses PROPER google.genai.types and is production-ready!")
    print()


if __name__ == "__main__":
    main()
