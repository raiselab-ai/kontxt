"""Base provider types and protocols."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Dict, Iterator, List, Optional, Protocol

if TYPE_CHECKING:
    from ..types import Format


@dataclass
class ToolCall:
    """Represents a tool/function call from the model."""

    name: str
    """Name of the tool/function to call."""

    arguments: Dict[str, Any]
    """Arguments to pass to the tool/function."""

    id: Optional[str] = None
    """Optional tool call ID (used by some providers)."""


@dataclass
class Response:
    """Standardized response from an LLM provider."""

    text: str
    """The generated text response."""

    raw: Any
    """The raw response object from the provider."""

    tool_calls: Optional[List[ToolCall]] = None
    """Any tool/function calls requested by the model."""

    finish_reason: Optional[str] = None
    """Reason the generation stopped (e.g., 'stop', 'length', 'tool_calls')."""


@dataclass
class StreamChunk:
    """A chunk from a streaming response."""

    text: str
    """Text content in this chunk."""

    tool_calls: Optional[List[ToolCall]] = None
    """Tool calls in this chunk (if any)."""

    finish_reason: Optional[str] = None
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
        """
        ...

    def stream(self, payload: Dict[str, Any]) -> Iterator[StreamChunk]:
        """Generate a streaming response from the LLM.

        Args:
            payload: The rendered context payload from Context.render()

        Yields:
            StreamChunk objects as the response is generated
        """
        ...
