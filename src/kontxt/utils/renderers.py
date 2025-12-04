"""Rendering helpers for different LLM providers."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Mapping, Sequence

from ..types import SectionData
from .serialization import ensure_serializable

if TYPE_CHECKING:
    from google.genai import types as genai_types


def _stringify_items(items: Sequence[Any]) -> str:
    return "\n".join(str(ensure_serializable(item)) for item in items)


def render_text(sections: Mapping[str, SectionData]) -> str:
    """Render sections using XML-like wrappers for lightweight safety."""
    parts: list[str] = []
    for name, items in sections.items():
        parts.append(f"<kontxt:{name}>")
        for item in items:
            parts.append(str(ensure_serializable(item)))
        parts.append(f"</kontxt:{name}>")
    return "\n".join(parts)


def render_openai(sections: Mapping[str, SectionData]) -> list[dict[str, Any]]:
    """Render sections into the OpenAI chat-completions message schema."""
    messages: list[dict[str, Any]] = []
    for name, items in sections.items():
        if name == "messages":
            for item in items:
                if isinstance(item, dict) and {"role", "content"} <= set(item):
                    messages.append(
                        {
                            "role": item["role"],
                            "content": item.get("content"),
                        }
                    )
                else:
                    messages.append({"role": "system", "content": str(ensure_serializable(item))})
        else:
            messages.append({"role": "system", "content": f"[{name}]\n{_stringify_items(items)}"})
    return messages


def render_anthropic(sections: Mapping[str, SectionData]) -> dict[str, Any]:
    """Render sections into the Anthropic Messages API schema."""
    system_parts: list[str] = []
    messages: list[dict[str, Any]] = []
    for name, items in sections.items():
        if name == "system":
            system_parts.extend(str(ensure_serializable(item)) for item in items)
        elif name == "messages":
            for item in items:
                if isinstance(item, dict) and {"role", "content"} <= set(item):
                    messages.append(
                        {
                            "role": item["role"],
                            "content": item.get("content"),
                        }
                    )
                else:
                    messages.append({"role": "user", "content": str(ensure_serializable(item))})
        else:
            messages.append({"role": "assistant", "content": f"[{name}]\n{_stringify_items(items)}"})

    payload: dict[str, Any] = {"messages": messages}
    if system_parts:
        payload["system"] = "\n".join(system_parts)
    return payload


def render_gemini(
    sections: Mapping[str, SectionData],
    generation_config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Render sections into the Google Gemini API schema using proper genai types.

    Optimized for O(n) complexity where n = total items across all sections.
    Uses O(1) dict/set lookups and processes sections in a single pass.

    Args:
        sections: The context sections to render
        generation_config: Optional generation config (temperature, topP, etc.)

    Returns:
        Dictionary with proper google.genai.types objects ready to be spread into
        client.models.generate_content(**payload)
    """
    # Lazy import to avoid hard dependency
    try:
        from google.genai import types
    except ImportError as e:
        raise ImportError(
            "google-genai is required to use render_gemini. "
            "Install it with: pip install 'kontxt[gemini]'"
        ) from e

    # Role mapping lookup - O(1) instead of if/elif
    _ROLE_MAP = {"assistant": "model", "user": "user", "model": "model"}

    # Sections that don't produce contents
    _NON_CONTENT_SECTIONS = frozenset(("system", "instructions", "tools"))

    system_parts: list[str] = []
    contents: list[types.Content] = []
    tools_items: Sequence[Any] = ()

    # Local references for faster method lookup in hot loop
    contents_append = contents.append
    system_parts_append = system_parts.append
    system_parts_extend = system_parts.extend

    # Single pass through sections - O(s) where s = number of sections
    for name, items in sections.items():
        if name == "system":
            system_parts_extend(str(ensure_serializable(item)) for item in items)
        elif name == "instructions":
            system_parts_extend(str(ensure_serializable(item)) for item in items)
        elif name == "tools":
            tools_items = items
        elif name == "messages":
            # Process messages - O(m) where m = number of messages
            for item in items:
                if isinstance(item, dict) and "role" in item and "content" in item:
                    role = item["role"]
                    if role == "system":
                        system_parts_append(str(item.get("content", "")))
                        continue

                    # O(1) role lookup with fallback
                    contents_append(
                        types.Content(
                            role=_ROLE_MAP.get(role, role),
                            parts=[types.Part.from_text(text=str(item.get("content", "")))],
                        )
                    )
                else:
                    contents_append(
                        types.Content(
                            role="user",
                            parts=[types.Part.from_text(text=str(ensure_serializable(item)))],
                        )
                    )
        else:
            # Other sections get added as user messages (preserves order)
            contents_append(
                types.Content(
                    role="user",
                    parts=[types.Part.from_text(text=f"[{name}]\n{_stringify_items(items)}")],
                )
            )

    # Build payload - all O(1) operations
    payload: dict[str, Any] = {"contents": contents}

    if system_parts:
        payload["system_instruction"] = [
            types.Part.from_text(text="\n\n".join(system_parts))
        ]

    if generation_config:
        payload["generation_config"] = types.GenerateContentConfig(**generation_config)

    if tools_items:
        payload["tools"] = list(tools_items)

    return payload

