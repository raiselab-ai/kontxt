"""Storage backends supporting the :mod:`kontxt.memory` module."""

from __future__ import annotations

import json
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Dict, List, Optional


class MemoryBackend(ABC):
    """Abstract interface implemented by storage backends."""

    @abstractmethod
    def write(self, key: str, value: Any, meta: Dict[str, Any]) -> None:
        """Persist a value along with optional metadata."""

    @abstractmethod
    def retrieve(
        self,
        query: str,
        *,
        filters: Optional[Dict[str, Any]] = None,
        top_k: int = 5,
    ) -> List[Any]:
        """Return a ranked list of values for *query*."""

    @abstractmethod
    def get(self, key: str) -> Any | None:
        """Return the stored value for *key*, if any."""


class InMemoryBackend(MemoryBackend):
    """Default backend storing data inside the running process."""

    def __init__(self) -> None:
        self._store: Dict[str, tuple[Any, Dict[str, Any]]] = {}

    def write(self, key: str, value: Any, meta: Dict[str, Any]) -> None:
        self._store[key] = (value, meta or {})

    def retrieve(
        self,
        query: str,
        *,
        filters: Optional[Dict[str, Any]] = None,
        top_k: int = 5,
    ) -> List[Any]:
        results: List[Any] = []
        for value, meta in self._store.values():
            if filters and not all(meta.get(k) == v for k, v in filters.items()):
                continue
            if query.lower() in json.dumps(value).lower():
                results.append(value)
        return results[:top_k]

    def get(self, key: str) -> Any | None:
        item = self._store.get(key)
        return item[0] if item else None


class FileSystemBackend(MemoryBackend):
    """Filesystem backed storage similar to Manus' implementation."""

    def __init__(self, path: str | Path) -> None:
        self.root = Path(path)
        self.root.mkdir(parents=True, exist_ok=True)

    def _path_for(self, key: str) -> Path:
        safe_key = key.replace("/", "_")
        return self.root / f"{safe_key}.json"

    def write(self, key: str, value: Any, meta: Dict[str, Any]) -> None:
        with self._path_for(key).open("w", encoding="utf-8") as fh:
            json.dump({"value": value, "meta": meta or {}}, fh, ensure_ascii=False, indent=2)

    def retrieve(
        self,
        query: str,
        *,
        filters: Optional[Dict[str, Any]] = None,
        top_k: int = 5,
    ) -> List[Any]:
        results: List[Any] = []
        for file_path in self.root.glob("*.json"):
            with file_path.open("r", encoding="utf-8") as fh:
                payload = json.load(fh)
            meta = payload.get("meta", {})
            if filters and not all(meta.get(k) == v for k, v in filters.items()):
                continue
            value = payload.get("value")
            if query.lower() in json.dumps(value).lower():
                results.append(value)
        return results[:top_k]

    def get(self, key: str) -> Any | None:
        path = self._path_for(key)
        if not path.exists():
            return None
        with path.open("r", encoding="utf-8") as fh:
            payload = json.load(fh)
        return payload.get("value")


class VectorStoreBackend(MemoryBackend):
    """Placeholder backend for future vector store integrations."""

    def __init__(self, *, uri: str, api_key: str | None = None) -> None:
        self.uri = uri
        self.api_key = api_key

    def write(self, key: str, value: Any, meta: Dict[str, Any]) -> None:
        raise NotImplementedError("VectorStoreBackend will be implemented in a future release.")

    def retrieve(
        self,
        query: str,
        *,
        filters: Optional[Dict[str, Any]] = None,
        top_k: int = 5,
    ) -> List[Any]:
        raise NotImplementedError("VectorStoreBackend will be implemented in a future release.")

    def get(self, key: str) -> Any | None:
        raise NotImplementedError("VectorStoreBackend will be implemented in a future release.")


