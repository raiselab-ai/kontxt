"""Shared typing utilities for the kontxt package."""

from __future__ import annotations

from enum import Enum
from typing import Any, Callable, MutableMapping, Sequence
from typing import Literal, Protocol, runtime_checkable


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


