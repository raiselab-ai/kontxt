"""Minimal RAG-style usage of kontxt."""

from __future__ import annotations

from kontxt import Context


def build_prompt(user_query: str, retrieved_chunks: list[str]) -> str:
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

