"""Shared typing utilities for the kontxt package."""

from __future__ import annotations

from enum import Enum
from typing import Any, Callable, MutableMapping, Sequence
from typing import Literal, Protocol, runtime_checkable


class SectionType:
    """Type-safe section identifier for Context sections.

    Provides IDE autocomplete and prevents typos when referencing sections.
    Can be used interchangeably with strings.

    Examples:
        >>> from kontxt.types import SystemPrompt, ChatMessages
        >>> ctx.add(SystemPrompt, "You are helpful")
        >>> # Equivalent to: ctx.add("system", "You are helpful")

        >>> # Create custom section types
        >>> PatientData = SectionType("patient")
        >>> ctx.add(PatientData, {"name": "John", "age": 30})
    """

    def __init__(self, name: str) -> None:
        self.name = name

    def __str__(self) -> str:
        return self.name

    def __repr__(self) -> str:
        return f"SectionType({self.name!r})"

    def __eq__(self, other: object) -> bool:
        if isinstance(other, SectionType):
            return self.name == other.name
        if isinstance(other, str):
            return self.name == other
        return False

    def __hash__(self) -> int:
        return hash(self.name)


# Built-in section types
SystemPrompt = SectionType("system")
ChatMessages = SectionType("messages")
Instructions = SectionType("instructions")
Tools = SectionType("tools")


class Format(str, Enum):
    """Render format options for Context.render().

    Examples:
        >>> from kontxt import Context, Format
        >>> ctx = Context()
        >>> ctx.add("messages", {"role": "user", "content": "Hello"})
        >>> payload = ctx.render(format=Format.GEMINI)
    """

    TEXT = "text"
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    GEMINI = "gemini"


RenderFormat = Literal["text", "openai", "anthropic", "gemini"]
SectionValue = Any
SectionGenerator = Callable[[], SectionValue]
SectionItem = SectionValue | SectionGenerator
SectionData = Sequence[SectionItem]


@runtime_checkable
class SupportsRender(Protocol):
    """Protocol describing renderer callables used by the Context."""

    def __call__(self, sections: MutableMapping[str, SectionData], /) -> Any: ...


