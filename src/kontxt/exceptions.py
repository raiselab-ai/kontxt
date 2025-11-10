"""Custom exceptions for the kontxt library."""

from __future__ import annotations


class KontxtError(Exception):
    """Base exception for all kontxt errors."""


class BudgetExceededError(KontxtError):
    """Raised when a context render exceeds the configured token budget."""


class UnknownSectionError(KontxtError):
    """Raised when a requested section does not exist in the context."""


class InvalidPhaseError(KontxtError):
    """Raised when a context phase is not registered."""


class InvalidPhaseTransitionError(KontxtError):
    """Raised when a state transition violates the configured phase graph."""


