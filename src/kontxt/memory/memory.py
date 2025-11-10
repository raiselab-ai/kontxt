"""High-level memory manager."""

from __future__ import annotations

from copy import deepcopy
from typing import Any, Callable, Dict, Iterable, List, Optional

from .backends import FileSystemBackend, InMemoryBackend, MemoryBackend, VectorStoreBackend
from .cache import Cache
from .scratchpad import Scratchpad


CompressionStrategy = Callable[[Any, dict[str, Any]], Any]
CompactionStrategy = Callable[[Any, dict[str, Any]], Any]
PruneStrategy = Callable[[str, Any, dict[str, Any]], bool]


class Memory:
    """Manage information stored outside the immediate LLM context."""

    def __init__(self, backend: MemoryBackend | None = None) -> None:
        self._backend: MemoryBackend = backend or InMemoryBackend()
        self.scratchpad = Scratchpad()
        self.cache = Cache()
        self._compression_strategies: Dict[str, CompressionStrategy] = {}
        self._compaction_strategies: Dict[str, CompactionStrategy] = {}
        self._prune_strategies: Dict[str, PruneStrategy] = {}

    # ------------------------------------------------------------------
    # Backend management
    # ------------------------------------------------------------------
    def configure(self, backend: str, /, **kwargs: Any) -> None:
        """Swap the underlying storage backend."""
        backend = backend.lower()
        if backend == "filesystem":
            self._backend = FileSystemBackend(**kwargs)
        elif backend == "vector":
            self._backend = VectorStoreBackend(**kwargs)
        elif backend == "memory":
            self._backend = InMemoryBackend()
        else:
            raise ValueError(f"Unknown backend '{backend}'.")

    # ------------------------------------------------------------------
    # CRUD
    # ------------------------------------------------------------------
    def store(self, key: str, value: Any, *, meta: Optional[Dict[str, Any]] = None) -> None:
        """Persist *value* under *key* with optional metadata."""
        self._backend.write(key, value, meta or {})

    def retrieve(
        self,
        query: str,
        *,
        filters: Optional[Dict[str, Any]] = None,
        top_k: int = 5,
    ) -> List[Any]:
        """Return a list of relevant memories."""
        return self._backend.retrieve(query, filters=filters, top_k=top_k)

    def get(self, key: str) -> Any | None:
        """Return the exact value stored under *key*."""
        return self._backend.get(key)

    # ------------------------------------------------------------------
    # Extensibility hooks
    # ------------------------------------------------------------------
    def register_compression_strategy(self, name: str, fn: CompressionStrategy) -> None:
        self._compression_strategies[name] = fn

    def register_compaction_strategy(self, name: str, fn: CompactionStrategy) -> None:
        self._compaction_strategies[name] = fn

    def register_prune_strategy(self, name: str, fn: PruneStrategy) -> None:
        self._prune_strategies[name] = fn

    # ------------------------------------------------------------------
    # High level operations
    # ------------------------------------------------------------------
    def compress(
        self,
        key: str,
        *,
        strategy: str,
        target_tokens: Optional[int] = None,
        **kwargs: Any,
    ) -> Any:
        """Apply a registered compression strategy to the stored value."""
        value = self.get(key)
        if value is None:
            return None

        try:
            fn = self._compression_strategies[strategy]
        except KeyError as exc:
            raise KeyError(f"Compression strategy '{strategy}' is not registered.") from exc

        meta = {"target_tokens": target_tokens, **kwargs}
        compressed = fn(value, meta)
        self.store(key, compressed, meta=self._maybe_get_meta(key))
        return compressed

    def compact(self, key: str, *, strategy: str, **kwargs: Any) -> Any:
        """Apply an in-place compaction strategy."""
        value = self.get(key)
        if value is None:
            return None
        try:
            fn = self._compaction_strategies[strategy]
        except KeyError as exc:
            raise KeyError(f"Compaction strategy '{strategy}' is not registered.") from exc
        meta = {"strategy": strategy, **kwargs}
        compacted = fn(value, meta)
        self.store(key, compacted, meta=self._maybe_get_meta(key))
        return compacted

    def prune(
        self,
        *,
        strategy: str,
        keys: Optional[Iterable[str]] = None,
        **kwargs: Any,
    ) -> int:
        """Prune stored memories according to a registered strategy."""
        try:
            fn = self._prune_strategies[strategy]
        except KeyError as exc:
            raise KeyError(f"Prune strategy '{strategy}' is not registered.") from exc

        if not isinstance(self._backend, InMemoryBackend):
            raise NotImplementedError("Custom prune strategies are only supported on InMemoryBackend.")

        removed = 0
        selected_keys = list(keys) if keys is not None else list(self._backend._store.keys())
        for key in selected_keys:
            if key not in self._backend._store:
                continue
            value, meta = self._backend._store[key]
            if fn(key, value, {**meta, **kwargs}):
                del self._backend._store[key]
                removed += 1
        return removed

    # ------------------------------------------------------------------
    # Isolation helpers
    # ------------------------------------------------------------------
    def fork(
        self,
        *,
        include_scratchpad: bool = False,
        include_persistent: Optional[Iterable[str]] = None,
    ) -> "Memory":
        """Create a shallow copy of the memory instance."""
        if not isinstance(self._backend, InMemoryBackend):
            raise NotImplementedError("Forking is currently supported for InMemoryBackend only.")

        backend_copy = InMemoryBackend()
        keys_to_copy = include_persistent or self._backend._store.keys()
        for key in keys_to_copy:
            if key in self._backend._store:
                value, meta = self._backend._store[key]
                backend_copy.write(key, deepcopy(value), deepcopy(meta))

        forked = Memory(backend_copy)
        if include_scratchpad:
            for key, value in self.scratchpad.items():
                forked.scratchpad.write(key, deepcopy(value))
        return forked

    def merge_from(self, other: "Memory", *, keys: Optional[Iterable[str]] = None) -> None:
        """Merge selected items from *other* into this instance."""
        selected_keys = list(keys) if keys is not None else []

        if isinstance(other._backend, InMemoryBackend) and isinstance(self._backend, InMemoryBackend):
            if not selected_keys:
                selected_keys = list(other._backend._store.keys())
            for key in selected_keys:
                if key in other._backend._store:
                    value, meta = other._backend._store[key]
                    self._backend.write(key, deepcopy(value), deepcopy(meta))
        else:
            raise NotImplementedError("merge_from currently supports in-memory backends only.")

        for key in selected_keys or []:
            value = other.scratchpad.read(key)
            if value is not None:
                self.scratchpad.write(key, deepcopy(value))

    # ------------------------------------------------------------------
    def _maybe_get_meta(self, key: str) -> dict[str, Any]:
        if isinstance(self._backend, InMemoryBackend) and key in self._backend._store:
            return deepcopy(self._backend._store[key][1])
        return {}


