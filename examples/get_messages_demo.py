"""Demo of the get_messages() convenience method.

Shows how to retrieve conversation history with optional role filtering.
"""

from kontxt import Context


def main():
    print("=" * 80)
    print("GET_MESSAGES() METHOD DEMO")
    print("=" * 80)
    print()

    ctx = Context()

    # Build a conversation
    ctx.add_user_message("Hello! I need help with Python")
    ctx.add_response("I'd be happy to help! What would you like to know?")
    ctx.add_user_message("How do I read a file?")
    ctx.add_response("You can use open() with a context manager: with open('file.txt') as f: ...")
    ctx.add_user_message("Thanks! That's helpful")

    # ========================================================================
    # Example 1: Get all messages
    # ========================================================================
    print("📋 Example 1: Get ALL messages")
    print("-" * 80)

    all_messages = ctx.get_messages()
    print(f"Total messages: {len(all_messages)}")
    print()

    for i, msg in enumerate(all_messages, 1):
        role = msg["role"].upper()
        content = msg["content"]
        print(f"{i}. [{role}]: {content}")
    print()

    # ========================================================================
    # Example 2: Get only user messages
    # ========================================================================
    print("👤 Example 2: Get ONLY user messages")
    print("-" * 80)

    user_messages = ctx.get_messages(role="user")
    print(f"User messages: {len(user_messages)}")
    print()

    for i, msg in enumerate(user_messages, 1):
        print(f"{i}. {msg['content']}")
    print()

    # ========================================================================
    # Example 3: Get only assistant messages
    # ========================================================================
    print("🤖 Example 3: Get ONLY assistant messages")
    print("-" * 80)

    assistant_messages = ctx.get_messages(role="assistant")
    print(f"Assistant messages: {len(assistant_messages)}")
    print()

    for i, msg in enumerate(assistant_messages, 1):
        print(f"{i}. {msg['content']}")
    print()

    # ========================================================================
    # Use Case: Analytics
    # ========================================================================
    print("=" * 80)
    print("USE CASE: Conversation Analytics")
    print("=" * 80)
    print()

    all_msgs = ctx.get_messages()
    user_msgs = ctx.get_messages(role="user")
    assistant_msgs = ctx.get_messages(role="assistant")

    print("📊 Conversation Statistics:")
    print(f"  - Total turns: {len(all_msgs)}")
    print(f"  - User messages: {len(user_msgs)}")
    print(f"  - Assistant messages: {len(assistant_msgs)}")
    print()

    # Calculate average message lengths
    user_avg_len = sum(len(msg["content"]) for msg in user_msgs) / len(user_msgs)
    assistant_avg_len = sum(len(msg["content"]) for msg in assistant_msgs) / len(assistant_msgs)

    print("📏 Average Message Lengths:")
    print(f"  - User: {user_avg_len:.1f} chars")
    print(f"  - Assistant: {assistant_avg_len:.1f} chars")
    print()

    # ========================================================================
    # Use Case: Last N messages by role
    # ========================================================================
    print("=" * 80)
    print("USE CASE: Get Last N User Messages")
    print("=" * 80)
    print()

    last_2_user_msgs = ctx.get_messages(role="user")[-2:]

    print("Last 2 user messages:")
    for msg in last_2_user_msgs:
        print(f"  - {msg['content']}")
    print()

    # ========================================================================
    # Use Case: Filter and process
    # ========================================================================
    print("=" * 80)
    print("USE CASE: Extract User Questions")
    print("=" * 80)
    print()

    user_questions = [
        msg["content"]
        for msg in ctx.get_messages(role="user")
        if "?" in msg["content"]
    ]

    print(f"Found {len(user_questions)} questions:")
    for q in user_questions:
        print(f"  - {q}")
    print()

    # ========================================================================
    # Summary
    # ========================================================================
    print("=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print()
    print("✅ get_messages() - Get all messages")
    print("✅ get_messages(role='user') - Get only user messages")
    print("✅ get_messages(role='assistant') - Get only assistant messages")
    print("✅ get_messages(role='system') - Get only system messages")
    print()
    print("💡 Use cases:")
    print("   - Analytics and statistics")
    print("   - Extracting user questions")
    print("   - Getting conversation context")
    print("   - Filtering by role for processing")
    print()


if __name__ == "__main__":
    main()
