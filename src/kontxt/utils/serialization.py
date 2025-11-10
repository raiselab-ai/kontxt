"""Serialization helpers."""

from __future__ import annotations

from datetime import datetime
from typing import Any


def ensure_serializable(value: Any) -> Any:
    """Best-effort conversion to JSON-serializable objects."""
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, dict):
        return {str(key): ensure_serializable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [ensure_serializable(item) for item in value]
    if callable(value):
        # Do not invoke the callable here—callers control evaluation time.
        return value
    return str(value)


