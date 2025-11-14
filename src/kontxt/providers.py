"""Provider abstractions for LLM API integration.

This module defines the Provider protocol that ChatSession uses to interact
with different LLM providers (Gemini, OpenAI, Anthropic, etc.).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Dict, Iterator, Optional, Protocol

if TYPE_CHECKING:
    from .types import Format


@dataclass
class Response:
    """Standardized response from an LLM provider."""

    text: str
    """The generated text response."""

    raw: Any
    """The raw response object from the provider."""

    tool_calls: list[ToolCall] | None = None
    """Any tool/function calls requested by the model."""

    finish_reason: str | None = None
    """Reason the generation stopped (e.g., 'stop', 'length', 'tool_calls')."""


@dataclass
class ToolCall:
    """Represents a tool/function call from the model."""

    name: str
    """Name of the tool/function to call."""

    arguments: Dict[str, Any]
    """Arguments to pass to the tool/function."""

    id: str | None = None
    """Optional tool call ID (used by some providers)."""


@dataclass
class StreamChunk:
    """A chunk from a streaming response."""

    text: str
    """Text content in this chunk."""

    tool_calls: list[ToolCall] | None = None
    """Tool calls in this chunk (if any)."""

    finish_reason: str | None = None
    """Finish reason if this is the final chunk."""

    raw: Any = None
    """Raw chunk from the provider."""


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
