"""Simple ChatSession demonstration.

This example shows how to use ChatSession for effortless multi-turn
conversations with automatic context management.

Requirements:
    pip install 'kontxt[gemini]'

Environment:
    export GEMINI_API_KEY='your-api-key'
"""

from kontxt import ChatSession, Context, State
from kontxt.providers import GeminiProvider


def main() -> None:
    """Run a simple chat session demo."""
    # Create state and context
    state = State(current_phase="chat")
    ctx = Context(state=state)

    # Add a system prompt
    ctx.add("system", "You are a helpful assistant. Be concise and friendly.")

    # Create provider and session
    provider = GeminiProvider()
    session = ChatSession(ctx, provider)

    print("=" * 60)
    print("ChatSession Demo - Type 'exit' to quit")
    print("=" * 60)
    print()

    # Chat loop - that's it!
    while True:
        user_input = input("You: ")

        if user_input.lower() in ["exit", "quit", "bye"]:
            print("Goodbye!")
            break

        # Single line to send message and get response
        response = session.send(user_input)
        print(f"Assistant: {response.text}")
        print()

    # Show conversation history
    print("\n" + "=" * 60)
    print("Conversation Summary")
    print("=" * 60)
    messages = ctx.get_messages()
    print(f"Total messages: {len(messages)}")
    print(f"User messages: {len(ctx.get_messages(role='user'))}")
    print(f"Assistant messages: {len(ctx.get_messages(role='assistant'))}")


if __name__ == "__main__":
    main()
