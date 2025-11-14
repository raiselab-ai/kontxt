"""Provider abstractions for LLM API integration.

This module defines the Provider protocol that ChatSession uses to interact
with different LLM providers (Gemini, OpenAI, Anthropic, etc.).

Note: Response, StreamChunk, and ToolCall are now defined in providers/base.py
and re-exported from providers/__init__.py for convenience.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Dict, Iterator, Protocol

if TYPE_CHECKING:
    from .types import Format

# Import and re-export base types
from .providers import Response, StreamChunk, ToolCall

__all__ = ['Response', 'StreamChunk', 'ToolCall', 'Provider']


class Provider(Protocol):
    """Protocol that all LLM providers must implement.

    This defines the minimal interface that ChatSession needs to interact
    with different LLM APIs.
    """

    @property
    def format(self) -> "Format":
        """The render format this provider expects (e.g., Format.GEMINI)."""
        ...

    def generate(self, payload: Dict[str, Any]) -> Response:
        """Generate a response from the LLM.

        Args:
            payload: The rendered context payload from Context.render()

        Returns:
            A standardized Response object

        Examples:
            >>> provider = GeminiProvider(client, model="gemini-2.0-flash")
            >>> payload = ctx.render(format=provider.format)
            >>> response = provider.generate(payload)
            >>> print(response.text)
        """
        ...

    def stream(self, payload: Dict[str, Any]) -> Iterator[StreamChunk]:
        """Generate a streaming response from the LLM.

        Args:
            payload: The rendered context payload from Context.render()

        Yields:
            StreamChunk objects as the response is generated

        Examples:
            >>> for chunk in provider.stream(payload):
            ...     print(chunk.text, end="")
        """
        ...
