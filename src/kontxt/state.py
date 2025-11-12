"""Session state utilities."""

from __future__ import annotations

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
            self.set_path(self._phase_path, phase_str)
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

    def get_path(self, path: Sequence[str], default: Any | None = None) -> Any:
        """Retrieve a value using a dot-path."""
        current: Any = self._data
        for key in path:
            if isinstance(current, MutableMapping) and key in current:
                current = current[key]
            else:
                return default
        return current

    def set_path(self, path: Sequence[str], value: Any) -> None:
        """Assign a value at the specified path, creating nodes as needed."""
        if not path:
            raise ValueError("path must contain at least one key")

        current = self._data
        for key in path[:-1]:
            if key not in current or not isinstance(current[key], MutableMapping):
                current[key] = {}
            current = current[key]
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
        phase_value = self.get_path(self._phase_path)
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

        self.set_path(self._phase_path, phase_str)


