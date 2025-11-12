"""In-session scratchpad storage."""

from __future__ import annotations

from typing import Any, Dict, Iterable


class Scratchpad:
    """Ephemeral key-value store scoped to a session."""

    def __init__(self) -> None:
        self._data: Dict[str, Any] = {}

    def write(self, key: str, value: Any) -> None:
        """Store a value under *key*."""
        self._data[key] = value

    def read(self, key: str) -> Any | None:
        """Return the value for *key*, if present."""
        return self._data.get(key)

    def delete(self, key: str) -> None:
        """Remove *key* from the scratchpad if it exists."""
        self._data.pop(key, None)

    def clear(self) -> None:
        """Remove all entries from the scratchpad."""
        self._data.clear()

    def items(self) -> Iterable[tuple[str, Any]]:
        """Return an iterable over scratchpad items."""
        return self._data.items()

    def __contains__(self, key: object) -> bool:  # pragma: no cover - trivial
        return key in self._data

    def __len__(self) -> int:  # pragma: no cover - trivial
        return len(self._data)


