"""Session state utilities."""

from __future__ import annotations

from collections import abc
from copy import deepcopy
from typing import Any, Dict, Iterable, Mapping, MutableMapping, Sequence

from .exceptions import InvalidPhaseTransitionError


class State:
    """Lightweight wrapper around a mutable state mapping.

    The default configuration matches the design document and expects the phase
    to live under ``state['session']['phase']``.
    """

    def __init__(
        self,
        initial: Mapping[str, Any] | None = None,
        *,
        phase_path: Sequence[str] = ("session", "phase"),
        transitions: Mapping[str, Iterable[str]] | None = None,
    ) -> None:
        self._data: Dict[str, Any] = deepcopy(initial) if initial else {}
        self._phase_path = tuple(phase_path)
        self._transitions: Dict[str, set[str]] = {
            phase: set(targets) for phase, targets in (transitions or {}).items()
        }

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
    def phase(self) -> str | None:
        """Return the current phase name, if configured."""
        phase_value = self.get_path(self._phase_path)
        if phase_value is None:
            return None
        if not isinstance(phase_value, str):  # pragma: no cover - defensive
            raise TypeError("phase value must be a string")
        return phase_value

    def set_phase(self, phase: str) -> None:
        """Update the current phase while validating transition rules."""
        current = self.phase()
        if current is not None and current in self._transitions:
            allowed = self._transitions[current]
            if allowed and phase not in allowed:
                raise InvalidPhaseTransitionError(
                    f"Cannot transition from '{current}' to '{phase}'. "
                    f"Allowed: {sorted(allowed)}"
                )
        self.set_path(self._phase_path, phase)

    def configure_transitions(self, transitions: Mapping[str, Iterable[str]]) -> None:
        """Update the phase transition mapping."""
        self._transitions = {phase: set(targets) for phase, targets in transitions.items()}


