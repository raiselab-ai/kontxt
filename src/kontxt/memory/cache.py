"""Simple similarity-based cache for query results."""

from __future__ import annotations

from dataclasses import dataclass
from difflib import SequenceMatcher
from typing import Any, Dict


@dataclass
class CacheEntry:
    """Internal representation of a cached result."""

    query: str
    value: Any


class Cache:
    """Minimal cache used to avoid recomputing repeated LLM calls."""

    def __init__(self) -> None:
        self._store: Dict[str, CacheEntry] = {}

    def get(self, key: str, *, query: str, similarity_threshold: float = 0.8) -> Any | None:
        """Return the cached value when the stored query is similar enough."""
        entry = self._store.get(key)
        if not entry:
            return None
        similarity = SequenceMatcher(None, entry.query, query).ratio()
        if similarity >= similarity_threshold:
            return entry.value
        return None

    def set(self, key: str, *, query: str, value: Any) -> None:
        """Persist a result in the cache."""
        self._store[key] = CacheEntry(query=query, value=value)

    def clear(self) -> None:  # pragma: no cover - trivial
        self._store.clear()


