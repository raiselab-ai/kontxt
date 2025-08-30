"""Kontxt — framework-agnostic context management for AI apps."""

__version__ = "0.1.0"  # keep in sync with pyproject if not using dynamic version
__status__ = "alpha"

# Public API (fill these as you implement modules)
try:
    from .registry.prompt_registry import PromptRegistry  # noqa: F401
except Exception:  # modules are stubs right now
    class PromptRegistry:  # type: ignore
        pass

try:
    from .store.context_store import Context  # noqa: F401
except Exception:
    class Context:  # type: ignore
        pass

try:
    from .memory.memory_manager import MemoryManager  # noqa: F401
except Exception:
    class MemoryManager:  # type: ignore
        pass

def main() -> None:
    """Entry point for `kontxt` console script."""
    from .cli import app
    app()
