"""Session state utilities."""

from __future__ import annotations

import json
from copy import deepcopy
from enum import Enum
from typing import Any, Dict, Mapping, MutableMapping, Sequence

from .exceptions import InvalidPhaseError


class State:
    """Lightweight wrapper around a mutable state mapping.

    The default configuration matches the design document and expects the phase
    to live under ``state['session']['phase']``.

    Args:
        initial: Initial state data (other session data)
        current_phase: Starting phase for the workflow (source of truth)
        phase_path: Path to phase value in state dict
        phases: Optional Enum class for phase validation

    Examples:
        >>> from enum import Enum
        >>> class Phases(str, Enum):
        ...     INITIAL = "initial"
        ...     COMPLETE = "complete"
        >>> # Simple usage with current_phase
        >>> state = State(current_phase="initial", phases=Phases)
        >>> # With additional state data
        >>> state = State(
        ...     initial={"user_id": "123"},
        ...     current_phase="initial",
        ...     phases=Phases
        ... )
        >>> state.set_phase(Phases.COMPLETE)  # Valid
        >>> state.set_phase("invalid")  # Raises InvalidPhaseError
    """

    def __init__(
        self,
        initial: Mapping[str, Any] | None = None,
        *,
        current_phase: str | Enum | None = None,
        phase_path: Sequence[str] = ("session", "phase"),
        phases: type[Enum] | None = None,
    ) -> None:
        self._data: Dict[str, Any] = deepcopy(dict(initial)) if initial else {}
        self._phase_path = tuple(phase_path)
        self._phases = phases

        # Set current_phase if provided (source of truth)
        if current_phase is not None:
            phase_str = current_phase.value if isinstance(current_phase, Enum) else current_phase
            # Validate against phases enum if provided
            if self._phases and not self._is_valid_phase(phase_str):
                allowed = [p.value for p in self._phases]
                raise InvalidPhaseError(
                    f"Initial phase '{phase_str}' is not valid. Allowed phases: {allowed}"
                )
            self.set(".".join(self._phase_path), phase_str)
        elif self._phases:
            # Validate existing phase in initial data if phases enum provided
            current = self.phase()
            if current and not self._is_valid_phase(current):
                allowed = [p.value for p in self._phases]
                raise InvalidPhaseError(
                    f"Initial phase '{current}' is not valid. Allowed phases: {allowed}"
                )

    # ------------------------------------------------------------------
    # Basic mapping helpers
    # ------------------------------------------------------------------
    @property
    def data(self) -> Dict[str, Any]:
        """Return a deep copy of the underlying mapping."""
        return deepcopy(self._data)

    def get(self, key: str, default: Any | None = None) -> Any:
        """Retrieve a value using dot notation.

        Args:
            key: Dot-separated path (e.g., "session.id" or "user.profile.name")
            default: Value to return if key not found

        Returns:
            The value at the specified path, or default if not found

        Examples:
            >>> state = State(initial={"session": {"id": "123"}})
            >>> state.get("session.id")
            '123'
            >>> state.get("session.missing", "default")
            'default'
        """
        path = key.split(".")
        current: Any = self._data
        for k in path:
            if isinstance(current, MutableMapping) and k in current:
                current = current[k]
            else:
                return default
        return current

    def set(self, key: str, value: Any) -> None:
        """Set a value using dot notation, creating nested dicts as needed.

        Args:
            key: Dot-separated path (e.g., "session.id" or "user.profile.name")
            value: Value to set

        Examples:
            >>> state = State()
            >>> state.set("session.id", "123")
            >>> state.set("user.profile.name", "Alice")
            >>> state.get("session.id")
            '123'
        """
        path = key.split(".")
        if not path or (len(path) == 1 and not path[0]):
            raise ValueError("key must be a non-empty string")

        current = self._data
        for k in path[:-1]:
            if k not in current or not isinstance(current[k], MutableMapping):
                current[k] = {}
            current = current[k]
        current[path[-1]] = value

    # ------------------------------------------------------------------
    # Phase helpers
    # ------------------------------------------------------------------
    def _is_valid_phase(self, phase: str) -> bool:
        """Check if phase is valid according to enum."""
        if not self._phases:
            return True  # No validation if phases not set
        return phase in [p.value for p in self._phases]

    def phase(self) -> str | None:
        """Return the current phase name, if configured."""
        phase_value = self.get(".".join(self._phase_path))
        if phase_value is None:
            return None
        if not isinstance(phase_value, str):  # pragma: no cover - defensive
            raise TypeError("phase value must be a string")
        return phase_value

    def set_phase(self, phase: str | Enum) -> None:
        """Update the current phase with validation.

        Args:
            phase: New phase (string or Enum member)

        Raises:
            InvalidPhaseError: If phase is not in allowed phases

        Examples:
            >>> state.set_phase("complete")
            >>> state.set_phase(Phases.COMPLETE)  # Also works with enum
        """
        # Convert enum to string
        phase_str = phase.value if isinstance(phase, Enum) else phase

        # Validate if phases enum provided
        if self._phases and not self._is_valid_phase(phase_str):
            allowed = [p.value for p in self._phases]
            raise InvalidPhaseError(
                f"Cannot set phase to '{phase_str}'. Allowed phases: {allowed}"
            )

        self.set(".".join(self._phase_path), phase_str)

    def __str__(self) -> str:
        """Return a human-readable string representation of the state.

        Examples:
            >>> state = State(initial={"user_id": "123"}, current_phase="initial")
            >>> print(state)
            {
              "session": {
                "phase": "initial"
              },
              "user_id": "123"
            }
        """
        return json.dumps(self._data, indent=2, default=str)

    def __repr__(self) -> str:
        """Return a detailed string representation for debugging."""
        phase_info = f", current_phase='{self.phase()}'" if self.phase() else ""
        return f"State(data={self._data!r}{phase_info})"


