"""Base provider types and protocols."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional


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
