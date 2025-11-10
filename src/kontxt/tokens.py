"""Token counting utilities."""

from __future__ import annotations

from typing import Any


class TokenCounter:
    """Base interface for token counting helpers."""

    def count(self, text: str, /) -> int:
        """Return the number of tokens contained in *text*."""
        raise NotImplementedError

    def estimate(self, obj: Any, /) -> int:
        """Estimate the token count for arbitrary Python objects."""
        if isinstance(obj, str):
            return self.count(obj)
        if isinstance(obj, bytes):
            return self.count(obj.decode("utf-8", errors="ignore"))
        if isinstance(obj, dict):
            return self.count(str(obj))
        if isinstance(obj, (list, tuple, set)):
            return sum(self.estimate(item) for item in obj)
        return self.count(str(obj))


class HeuristicTokenCounter(TokenCounter):
    """Fast, model-agnostic token estimator.

    This counter uses a simple heuristic based on average English word length.
    It slightly overestimates on purpose to give conservative budget checks.
    """

    AVERAGE_CHARS_PER_TOKEN = 4

    def count(self, text: str, /) -> int:
        cleaned = text.strip()
        if not cleaned:
            return 0
        approx = max(1, len(cleaned) // self.AVERAGE_CHARS_PER_TOKEN)
        return approx


class TiktokenTokenCounter(TokenCounter):
    """Accurate counter that leverages the tiktoken library when available."""

    def __init__(self, model: str = "gpt-4o") -> None:
        try:
            import tiktoken
        except ImportError as exc:  # pragma: no cover - defensive
            raise RuntimeError(
                "tiktoken is required to use TiktokenTokenCounter. "
                "Install the optional 'docs' dependency group or add tiktoken "
                "to your environment."
            ) from exc

        self._model = model
        self._encoding = tiktoken.encoding_for_model(model)

    @property
    def model(self) -> str:
        """Return the model this counter targets."""
        return self._model

    def count(self, text: str, /) -> int:
        return len(self._encoding.encode(text))

