"""Chat session management for multi-turn conversations.

This module provides ChatSession, which bridges Context and Provider to
enable seamless multi-turn conversations with automatic context management.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, AsyncIterator, Iterator

if TYPE_CHECKING:
    from .context import Context
    from .providers import Provider, Response, StreamChunk


class ChatSession:
    """Manages multi-turn conversations with automatic context synchronization.

    ChatSession bridges kontxt's Context (context orchestration) with LLM
    providers (API calls), eliminating boilerplate for common conversation patterns.

    Examples:
        >>> from kontxt import Context, ChatSession
        >>> from kontxt.providers.gemini import GeminiProvider
        >>>
        >>> ctx = Context(state=state)
        >>> ctx.phase("intake").configure(...)
        >>>
        >>> provider = GeminiProvider(client, model="gemini-2.0-flash")
        >>> session = ChatSession(ctx, provider)
        >>>
        >>> # Simple back-and-forth
        >>> response = session.send("Hello!")
        >>> print(response.text)
        >>>
        >>> # Streaming
        >>> for chunk in session.stream("Tell me a story"):
        ...     print(chunk.text, end="")
        >>>
        >>> # Context is automatically kept in sync
        >>> messages = ctx.get_messages()  # Contains full conversation
    """

    def __init__(self, context: "Context", provider: "Provider") -> None:
        """Initialize a chat session.

        Args:
            context: The Context to manage
            provider: The Provider to use for LLM API calls
        """
        self.context = context
        self.provider = provider

    def send(self, message: str) -> "Response":
        """Send a message and get a response.

        This automatically:
        1. Adds the user message to context
        2. Renders the context in the provider's format
        3. Calls the provider's API
        4. Adds the assistant response to context
        5. Returns the response

        Args:
            message: The user's message

        Returns:
            The assistant's response

        Examples:
            >>> response = session.send("What's the weather like?")
            >>> print(response.text)
            "I don't have access to real-time weather data..."
        """
        # Add user message to context
        self.context.add_user_message(message)

        # Render context for provider
        payload = self.context.render(format=self.provider.format)

        # Call provider
        response = self.provider.generate(payload)

        # Add assistant response to context
        if response.text:
            self.context.add_response(response.text)

        return response

    def stream(self, message: str) -> Iterator["StreamChunk"]:
        """Send a message and get a streaming response.

        This automatically:
        1. Adds the user message to context
        2. Renders the context in the provider's format
        3. Calls the provider's streaming API
        4. Yields chunks as they arrive
        5. Adds the complete assistant response to context when done

        Args:
            message: The user's message

        Yields:
            StreamChunk objects as the response is generated

        Examples:
            >>> for chunk in session.stream("Tell me a joke"):
            ...     print(chunk.text, end="")
            ...
            "Why did the chicken cross the road?..."
        """
        # Add user message to context
        self.context.add_user_message(message)

        # Render context for provider
        payload = self.context.render(format=self.provider.format)

        # Collect complete response while streaming
        complete_text = ""

        # Stream from provider
        for chunk in self.provider.stream(payload):
            complete_text += chunk.text
            yield chunk

        # Add complete response to context
        if complete_text:
            self.context.add_response(complete_text)

    def is_phase_complete(self) -> bool:
        """Check if the current phase is complete.

        This is a convenience helper for phase-based workflows.

        Returns:
            True if there are no more allowed transitions from current phase

        Examples:
            >>> while not session.is_phase_complete():
            ...     user_input = input("You: ")
            ...     response = session.send(user_input)
            ...     print(response.text)
        """
        current_phase = self.context.current_phase()
        if current_phase is None:
            return False

        # Check if current phase has any allowed transitions
        phase_config = self.context._phases.get(current_phase)
        if phase_config is None:
            return False

        # If transitions_to is None, any transition is allowed (not complete)
        # If transitions_to is empty list, no transitions allowed (complete)
        return phase_config.transitions_to is not None and len(phase_config.transitions_to) == 0


class AsyncChatSession:
    """Async version of ChatSession for high-performance async applications.

    AsyncChatSession provides the same functionality as ChatSession but with
    async/await support for better performance in async applications.

    Examples:
        >>> from kontxt import Context
        >>> from kontxt.providers import AsyncGeminiProvider
        >>>
        >>> async def main():
        ...     ctx = Context(state=state)
        ...     provider = AsyncGeminiProvider()
        ...     session = AsyncChatSession(ctx, provider)
        ...
        ...     # Simple back-and-forth
        ...     response = await session.send("Hello!")
        ...     print(response.text)
        ...
        ...     # Streaming
        ...     async for chunk in session.stream("Tell me a story"):
        ...         print(chunk.text, end="")
    """

    def __init__(self, context: "Context", provider: "Provider") -> None:
        """Initialize an async chat session.

        Args:
            context: The Context to manage
            provider: The async Provider to use for LLM API calls
        """
        self.context = context
        self.provider = provider

    async def send(self, message: str) -> "Response":
        """Send a message and get a response asynchronously.

        This automatically:
        1. Adds the user message to context
        2. Renders the context in the provider's format
        3. Calls the provider's API asynchronously
        4. Adds the assistant response to context
        5. Returns the response

        Args:
            message: The user's message

        Returns:
            The assistant's response

        Examples:
            >>> response = await session.send("What's the weather like?")
            >>> print(response.text)
        """
        # Add user message to context
        self.context.add_user_message(message)

        # Render context for provider
        payload = self.context.render(format=self.provider.format)

        # Call provider asynchronously
        response = await self.provider.generate(payload)  # type: ignore[misc]

        # Add assistant response to context
        if response.text:
            self.context.add_response(response.text)

        return response

    async def stream(self, message: str) -> AsyncIterator["StreamChunk"]:
        """Send a message and get a streaming response asynchronously.

        This automatically:
        1. Adds the user message to context
        2. Renders the context in the provider's format
        3. Calls the provider's streaming API asynchronously
        4. Yields chunks as they arrive
        5. Adds the complete assistant response to context when done

        Args:
            message: The user's message

        Yields:
            StreamChunk objects as the response is generated

        Examples:
            >>> async for chunk in session.stream("Tell me a joke"):
            ...     print(chunk.text, end="")
        """
        # Add user message to context
        self.context.add_user_message(message)

        # Render context for provider
        payload = self.context.render(format=self.provider.format)

        # Collect complete response while streaming
        complete_text = ""

        # Stream from provider asynchronously
        async for chunk in self.provider.stream(payload):  # type: ignore[attr-defined]
            complete_text += chunk.text
            yield chunk

        # Add complete response to context
        if complete_text:
            self.context.add_response(complete_text)

    def is_phase_complete(self) -> bool:
        """Check if the current phase is complete.

        This is a convenience helper for phase-based workflows.

        Returns:
            True if there are no more allowed transitions from current phase

        Examples:
            >>> while not session.is_phase_complete():
            ...     user_input = input("You: ")
            ...     response = await session.send(user_input)
            ...     print(response.text)
        """
        current_phase = self.context.current_phase()
        if current_phase is None:
            return False

        # Check if current phase has any allowed transitions
        phase_config = self.context._phases.get(current_phase)
        if phase_config is None:
            return False

        # If transitions_to is None, any transition is allowed (not complete)
        # If transitions_to is empty list, no transitions allowed (complete)
        return phase_config.transitions_to is not None and len(phase_config.transitions_to) == 0
