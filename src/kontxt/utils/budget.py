"""Token budget management helpers."""

from __future__ import annotations

from typing import Any, Dict, List, MutableMapping, Sequence

from ..exceptions import BudgetExceededError
from ..tokens import TokenCounter


class BudgetManager:
    """Apply soft token budgets across context sections."""

    def __init__(self, counter: TokenCounter) -> None:
        self._counter = counter

    def enforce(
        self,
        sections: MutableMapping[str, List[Any]],
        *,
        max_tokens: int | None = None,
        priority: Sequence[str] | None = None,
    ) -> MutableMapping[str, List[Any]]:
        """Trim sections until they fit within *max_tokens*.

        Sections appearing earlier in *priority* are preserved preferentially.
        """
        if max_tokens is None:
            return sections

        materialized: Dict[str, List[Any]] = {
            name: list(items) for name, items in sections.items()
        }

        def section_tokens(name: str) -> int:
            return self._counter.estimate(materialized[name])

        def total_tokens() -> int:
            return sum(section_tokens(name) for name in materialized)

        if total_tokens() <= max_tokens:
            return materialized

        priority_order = list(priority or ())
        ordering = sorted(
            materialized.keys(),
            key=lambda name: priority_order.index(name) if name in priority_order else len(priority_order),
        )

        for name in ordering[::-1]:  # trim lowest priority first
            while materialized[name] and total_tokens() > max_tokens:
                materialized[name].pop()
            if total_tokens() <= max_tokens:
                return materialized

        if total_tokens() > max_tokens:
            raise BudgetExceededError(
                f"Unable to enforce token budget of {max_tokens} tokens; "
                f"consider increasing the limit or providing trimming callbacks."
            )

        return materialized


