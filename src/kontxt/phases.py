"""Phase configuration utilities."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Callable, List, Optional, Sequence, Union

if TYPE_CHECKING:
    from .types import SectionType


@dataclass
class PhaseConfig:
    """Serializable configuration that describes a named phase."""

    name: str
    system: Optional[str] = None
    instructions: Optional[Union[str, Callable[[], str]]] = None
    includes: List[str] = field(default_factory=list)
    memory_includes: List[str] = field(default_factory=list)
    tools: List[str] = field(default_factory=list)
    max_history: int = 10
    transitions_to: Optional[List[str]] = None


class PhaseBuilder:
    """Fluent builder used by :class:`kontxt.context.Context`."""

    def __init__(self, config: PhaseConfig) -> None:
        self._config = config

    @property
    def config(self) -> PhaseConfig:
        return self._config

    def configure(
        self,
        *,
        system: Optional[str] = None,
        instructions: Optional[Union[str, Callable[[], str]]] = None,
        includes: Optional[Sequence[Union[str, "SectionType"]]] = None,
        memory_includes: Optional[Sequence[str]] = None,
        tools: Optional[Sequence[str]] = None,
        max_history: Optional[int] = None,
        transitions_to: Optional[Sequence[str]] = None,
    ) -> "PhaseBuilder":
        if system is not None:
            self._config.system = system
        if instructions is not None:
            self._config.instructions = instructions
        if includes is not None:
            # Convert SectionType to strings
            self._config.includes = [str(item) for item in includes]
        if memory_includes is not None:
            self._config.memory_includes = list(memory_includes)
        if tools is not None:
            self._config.tools = list(tools)
        if max_history is not None:
            self._config.max_history = max_history
        if transitions_to is not None:
            self._config.transitions_to = list(transitions_to)
        return self


