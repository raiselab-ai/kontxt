"""Minimal RAG-style usage of kontxt.

This example demonstrates basic Context usage with string-based section names.

For type-safe section references (optional), you can use:
    from kontxt import SystemPrompt, Instructions
    context.add(SystemPrompt, "You answer questions...")
    context.add(Instructions, "Cite the chunk ids...")
"""

from __future__ import annotations

from kontxt import Context


def build_prompt(user_query: str, retrieved_chunks: list[str]) -> str:
    """Build a RAG prompt using kontxt.

    Args:
        user_query: The user's question
        retrieved_chunks: List of relevant documentation chunks

    Returns:
        Formatted prompt string
    """
    context = Context()
    context.add("system", "You answer questions using the supplied documentation.")
    context.add("instructions", "Cite the chunk ids you relied on.")
    context.add("documentation", retrieved_chunks)
    context.add("question", user_query)
    return context.render()


if __name__ == "__main__":  # pragma: no cover - example script
    docs = [
        "Chunk A: Authentication uses API tokens.",
        "Chunk B: Refresh tokens last 24 hours.",
    ]
    prompt = build_prompt("How do I authenticate?", docs)
    print(prompt)

