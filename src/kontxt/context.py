"""Core Context primitive."""

from __future__ import annotations

from collections import OrderedDict
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Dict, Iterable, List, MutableMapping, Optional, Sequence

from pydantic import BaseModel

from .exceptions import BudgetExceededError, InvalidPhaseError, InvalidPhaseTransitionError, UnknownSectionError
from .phases import PhaseBuilder, PhaseConfig
from .tokens import HeuristicTokenCounter, TokenCounter
from .types import Format, RenderFormat, SectionItem, SectionType
from .utils import BudgetManager, ensure_serializable, render_anthropic, render_gemini, render_openai, render_text

if TYPE_CHECKING:
    from .memory import Memory
    from .state import State


@dataclass
class BudgetConfig:
    """Configuration describing a global context budget."""

    max_tokens: int
    priority: Sequence[str] | None = None
    strict: bool = False


@dataclass
class SectionBudget:
    """Optional per-section budget configuration."""

    max_tokens: int


class SectionHandle:
    """Fluent API returned by :meth:`Context.section`."""

    def __init__(self, context: "Context", name: str) -> None:
        self._context = context
        self._name = name

    def set_budget(self, *, max_tokens: int) -> "SectionHandle":
        self._context._section_budgets[self._name] = SectionBudget(max_tokens=max_tokens)
        return self


class Context:
    """Container responsible for composing LLM context."""

    def __init__(
        self,
        *,
        token_counter: TokenCounter | None = None,
        memory: "Optional[Memory]" = None,
        state: "Optional[State]" = None,
    ) -> None:
        self._sections: "OrderedDict[str, List[SectionItem]]" = OrderedDict()
        self._phases: Dict[str, PhaseConfig] = {}
        self._budget: BudgetConfig | None = None
        self._section_budgets: Dict[str, SectionBudget] = {}
        self._token_counter = token_counter or HeuristicTokenCounter()
        self._output_schema: type[BaseModel] | None = None
        self._memory = memory
        self._state = state

    # ------------------------------------------------------------------
    # Section management
    # ------------------------------------------------------------------
    def add(self, name: str | SectionType, content: SectionItem | Iterable[SectionItem]) -> "Context":
        """Append *content* to *name*, creating the section if necessary.

        Args:
            name: Section name (string or SectionType)
            content: Content to add to the section

        Examples:
            >>> from kontxt.types import SystemPrompt, ChatMessages
            >>> ctx.add(SystemPrompt, "You are helpful")
            >>> ctx.add("custom_section", "Custom data")
            >>> ctx.add(ChatMessages, {"role": "user", "content": "Hello"})
        """
        # Convert SectionType to string
        section_name = str(name) if isinstance(name, SectionType) else name

        if section_name not in self._sections:
            self._sections[section_name] = []

        items = self._normalize_content(content)
        self._sections[section_name].extend(items)
        return self

    def replace(self, name: str | SectionType, content: SectionItem | Iterable[SectionItem]) -> "Context":
        """Replace *name* with *content*, creating the section if necessary."""
        # Convert SectionType to string
        section_name = str(name) if isinstance(name, SectionType) else name
        self._sections[section_name] = self._normalize_content(content)
        return self

    def get_section(self, name: str) -> List[SectionItem] | None:
        """Return the raw section list, if it exists."""
        return self._sections.get(name)

    def remove(self, name: str) -> "Context":
        """Delete a section if it exists."""
        self._sections.pop(name, None)
        self._section_budgets.pop(name, None)
        return self

    def clear(self) -> "Context":
        """Remove all sections."""
        self._sections.clear()
        self._section_budgets.clear()
        return self

    def section(self, name: str) -> SectionHandle:
        """Return a handle for configuring section-level options."""
        if name not in self._sections:
            raise UnknownSectionError(f"Section '{name}' does not exist.")
        return SectionHandle(self, name)

    def add_user_message(self, content: str) -> "Context":
        """Add a user message to the conversation.

        This is a convenience helper for adding user messages to the messages section.

        Args:
            content: The message content from the user

        Returns:
            Self for method chaining

        Examples:
            >>> ctx.add_user_message("Hello!")
            >>> # Equivalent to: ctx.add("messages", {"role": "user", "content": "Hello!"})
        """
        return self.add("messages", {"role": "user", "content": content})

    def add_response(self, text: str, role: str = "assistant") -> "Context":
        """Add LLM response to messages section.

        This is a convenience helper for adding assistant responses back to the
        conversation history after calling an LLM API.

        Args:
            text: The response text from the LLM
            role: The role of the responder (default: "assistant")

        Returns:
            Self for method chaining

        Examples:
            >>> ctx.add_response("I'm happy to help!")
            >>> # Equivalent to: ctx.add("messages", {"role": "assistant", "content": "I'm happy to help!"})
        """
        return self.add("messages", {"role": role, "content": text})

    # ------------------------------------------------------------------
    # Budget management
    # ------------------------------------------------------------------
    def set_budget(
        self,
        *,
        max_tokens: int,
        priority: Sequence[str] | None = None,
        strict: bool = False,
    ) -> "Context":
        self._budget = BudgetConfig(max_tokens=max_tokens, priority=priority, strict=strict)
        return self

    # ------------------------------------------------------------------
    # Phases
    # ------------------------------------------------------------------
    def phase(self, name: str) -> PhaseBuilder:
        """Return a phase builder, creating the phase if necessary."""
        if name not in self._phases:
            self._phases[name] = PhaseConfig(name=name)
        return PhaseBuilder(self._phases[name])

    def advance_phase(self, next_phase: str) -> "Context":
        """Advance to the next phase with transition validation.

        This method validates that the transition is allowed according to the
        current phase's `transitions_to` configuration, then updates the state.

        Args:
            next_phase: The phase to transition to (string or Enum member)

        Raises:
            ValueError: If no state is configured
            InvalidPhaseError: If current phase is not registered
            InvalidPhaseTransitionError: If transition is not allowed

        Returns:
            Self for method chaining

        Examples:
            >>> from enum import Enum
            >>> class Phases(str, Enum):
            ...     INITIAL = "initial"
            ...     COMPLETE = "complete"
            >>> state = State(initial={"session": {"phase": "initial"}})
            >>> ctx = Context(state=state)
            >>> ctx.phase("initial").configure(transitions_to=["complete"])
            >>> ctx.advance_phase(Phases.COMPLETE)  # Valid transition
        """
        if self._state is None:
            raise ValueError("Cannot advance phase: no State configured in Context")

        # Get current phase from state
        current_phase = self._state.phase()
        if current_phase is None:
            raise InvalidPhaseError("Cannot advance phase: current phase is None")

        # Convert enum to string if needed
        from enum import Enum
        next_phase_str = next_phase.value if isinstance(next_phase, Enum) else next_phase

        # Check if current phase is registered
        if current_phase not in self._phases:
            raise InvalidPhaseError(
                f"Current phase '{current_phase}' is not registered. "
                "Configure it with ctx.phase(name).configure(...)"
            )

        # Get phase config and validate transition
        config = self._phases[current_phase]
        if config.transitions_to is not None:
            if next_phase_str not in config.transitions_to:
                raise InvalidPhaseTransitionError(
                    f"Cannot transition from '{current_phase}' to '{next_phase_str}'. "
                    f"Allowed transitions: {config.transitions_to}"
                )

        # Update state (this also validates against State's phases enum if configured)
        self._state.set_phase(next_phase_str)
        return self

    # ------------------------------------------------------------------
    # Output schema
    # ------------------------------------------------------------------
    def set_output_schema(self, schema: type[BaseModel]) -> "Context":
        self._output_schema = schema
        return self

    # ------------------------------------------------------------------
    # Rendering
    # ------------------------------------------------------------------
    def render(
        self,
        *,
        phase: str | None = None,
        format: RenderFormat | Format = "text",
        max_tokens: int | None = None,
        memory: "Optional[Memory]" = None,
        generation_config: Optional[Dict[str, Any]] = None,
    ) -> Any:
        """Render the context into the requested format.

        Args:
            phase: Named phase to render (uses phase config)
            format: Output format (Format.TEXT, Format.OPENAI, Format.ANTHROPIC, Format.GEMINI)
            max_tokens: Override budget for this render
            memory: Memory instance to pull from (overrides default)
            generation_config: Generation config for Gemini (temperature, topP, etc.)

        Examples:
            >>> from kontxt import Context, Format
            >>> ctx = Context()
            >>> ctx.add("messages", {"role": "user", "content": "Hello"})
            >>> # Use enum (recommended)
            >>> payload = ctx.render(format=Format.GEMINI)
            >>> # Or use string (still supported)
            >>> payload = ctx.render(format="gemini")
        """
        # Use provided memory, fall back to default, or None
        active_memory = memory if memory is not None else self._memory

        sections = self._select_sections(phase, memory=active_memory)
        evaluated = self._evaluate_sections(sections)
        materialized = self._apply_budgets(evaluated, max_tokens=max_tokens)
        if self._output_schema:
            schema_section = self._model_schema(self._output_schema)
            materialized.setdefault("output_schema", []).append(schema_section)

        # Convert Format enum to string value for comparison
        format_str = format.value if isinstance(format, Format) else format

        if format_str == "text":
            return render_text(materialized)
        if format_str == "openai":
            return render_openai(materialized)
        if format_str == "anthropic":
            return render_anthropic(materialized)
        if format_str == "gemini":
            return render_gemini(materialized, generation_config=generation_config)
        raise ValueError(f"Unsupported render format '{format_str}'.")

    def token_count(self) -> int:
        """Return the approximate token count for currently registered sections."""
        evaluated = self._evaluate_sections(self._sections)
        budget_manager = BudgetManager(self._token_counter)
        materialized: MutableMapping[str, List[Any]] = budget_manager.enforce(
            evaluated,
            max_tokens=None,
            priority=None,
        )
        return sum(self._token_counter.estimate(items) for items in materialized.values())

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _select_sections(
        self,
        phase: str | None,
        memory: "Optional[Memory]" = None,
    ) -> "OrderedDict[str, List[SectionItem]]":
        """Select sections based on phase config and pull from memory."""
        if phase is None:
            return OrderedDict(self._sections)

        try:
            config = self._phases[phase]
        except KeyError as exc:
            raise InvalidPhaseError(f"Phase '{phase}' is not registered.") from exc

        ordered: "OrderedDict[str, List[SectionItem]]" = OrderedDict()

        # Add phase-specific sections
        if config.system is not None:
            ordered["system"] = [config.system]

        if config.instructions is not None:
            # Support callable instructions (for dynamic templates)
            instr = config.instructions() if callable(config.instructions) else config.instructions
            ordered["instructions"] = [instr]

        # Add included sections from context
        for name in config.includes:
            # Convert SectionType to string
            section_name = str(name) if isinstance(name, SectionType) else name

            if section_name in self._sections:
                section_data = self._sections[section_name]

                # Apply max_history if this is messages section
                if section_name == "messages" and config.max_history:
                    ordered[section_name] = section_data[-config.max_history :]
                else:
                    ordered[section_name] = section_data

        # Pull from memory if available
        if memory is not None and config.memory_includes:
            for key in config.memory_includes:
                value = memory.scratchpad.read(key)
                if value is not None:
                    ordered[key] = [value]  # Wrap in list for consistency

        # Add tools
        if config.tools:
            ordered["tools"] = list(config.tools)

        return ordered

    def _evaluate_sections(
        self,
        sections: MutableMapping[str, List[SectionItem]],
    ) -> "OrderedDict[str, List[Any]]":
        evaluated: "OrderedDict[str, List[Any]]" = OrderedDict()
        for name, items in sections.items():
            evaluated[name] = []
            for item in items:
                if callable(item):
                    evaluated[name].append(ensure_serializable(item()))
                else:
                    evaluated[name].append(ensure_serializable(item))
        return evaluated

    def _apply_budgets(
        self,
        sections: MutableMapping[str, List[Any]],
        *,
        max_tokens: int | None,
    ) -> MutableMapping[str, List[Any]]:
        limit = max_tokens
        priority: Sequence[str] | None = None
        strict = False
        if self._budget:
            limit = limit or self._budget.max_tokens
            priority = self._budget.priority
            strict = self._budget.strict

        manager = BudgetManager(self._token_counter)
        materialized: MutableMapping[str, List[Any]] = manager.enforce(sections, max_tokens=limit, priority=priority)

        if limit is not None and strict:
            total_tokens = sum(self._token_counter.estimate(items) for items in materialized.values())
            if total_tokens > limit:
                raise BudgetExceededError(
                    f"Rendering exceeded strict budget of {limit} tokens (estimated {total_tokens})."
                )
        return materialized

    @staticmethod
    def _normalize_content(content: SectionItem | Iterable[SectionItem]) -> List[SectionItem]:
        if isinstance(content, (list, tuple)):
            return list(content)
        return [content]

    @staticmethod
    def _model_schema(model: type[BaseModel]) -> dict[str, Any]:
        try:
            return model.model_json_schema()
        except AttributeError:  # pragma: no cover - compatibility
            return model.schema()


