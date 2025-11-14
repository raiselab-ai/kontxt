"""Async ChatSession demonstration with streaming.

This example shows how to use AsyncChatSession for high-performance
async applications with streaming support.

Requirements:
    pip install 'kontxt[gemini]'

Environment:
    export GEMINI_API_KEY='your-api-key'
"""

import asyncio

from kontxt import AsyncChatSession, Context, State
from kontxt.providers import AsyncGeminiProvider


async def main() -> None:
    """Run an async chat session demo with streaming."""
    # Create state and context
    state = State(current_phase="chat")
    ctx = Context(state=state)

    # Add a system prompt
    ctx.add("system", "You are a helpful assistant. Be concise and friendly.")

    # Create async provider and session using context manager
    async with AsyncGeminiProvider() as provider:
        session = AsyncChatSession(ctx, provider)

        print("=" * 60)
        print("Async ChatSession Demo with Streaming")
        print("Type 'exit' to quit")
        print("=" * 60)
        print()

        # Example 1: Non-streaming async
        print("Example 1: Non-streaming\n")
        response = await session.send("What is Python in one sentence?")
        print(f"Assistant: {response.text}\n")

        # Example 2: Streaming async
        print("Example 2: Streaming\n")
        print("Assistant: ", end="", flush=True)

        async for chunk in session.stream("Tell me a short joke about programming"):
            print(chunk.text, end="", flush=True)

        print("\n")

        # Interactive chat loop with streaming
        print("Interactive mode (streaming):\n")
        while True:
            user_input = input("You: ")

            if user_input.lower() in ["exit", "quit", "bye"]:
                print("Goodbye!")
                break

            print("Assistant: ", end="", flush=True)

            # Stream the response
            async for chunk in session.stream(user_input):
                print(chunk.text, end="", flush=True)

            print("\n")

        # Show conversation history
        print("\n" + "=" * 60)
        print("Conversation Summary")
        print("=" * 60)
        messages = ctx.get_messages()
        print(f"Total messages: {len(messages)}")
        print(f"User messages: {len(ctx.get_messages(role='user'))}")
        print(f"Assistant messages: {len(ctx.get_messages(role='assistant'))}")


if __name__ == "__main__":
    # Run the async main function
    asyncio.run(main())
