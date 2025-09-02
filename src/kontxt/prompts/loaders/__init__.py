"""Loaders module for prompt file loading and discovery.

This module provides functionality for discovering .kontxt directories
and loading prompt files with optional compression support.
"""

from .discovery import KontxtDiscovery
from .file_loader import PromptFileLoader

__all__ = [
    "KontxtDiscovery",
    "PromptFileLoader"
]
