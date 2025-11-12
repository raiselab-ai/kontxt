"""Rendering helpers for different LLM providers."""

from __future__ import annotations

from typing import Any, Mapping, Sequence

from ..types import SectionData
from .serialization import ensure_serializable


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
    """Render sections into the Google Gemini API schema.

    Args:
        sections: The context sections to render
        generation_config: Optional generation config (temperature, topP, etc.)

    Returns:
        Dictionary ready to be spread into client.models.generate_content(**payload)
    """
    system_parts: list[str] = []
    contents: list[dict[str, Any]] = []
    instructions_parts: list[str] = []

    for name, items in sections.items():
        if name == "system":
            system_parts.extend(str(ensure_serializable(item)) for item in items)
        elif name == "instructions":
            instructions_parts.extend(str(ensure_serializable(item)) for item in items)
        elif name == "messages":
            for item in items:
                if isinstance(item, dict) and {"role", "content"} <= set(item):
                    # Map OpenAI-style roles to Gemini roles
                    role = item["role"]
                    if role == "assistant":
                        role = "model"
                    elif role == "system":
                        # System messages get prepended to next user message
                        system_parts.append(str(item.get("content", "")))
                        continue

                    contents.append(
                        {
                            "role": role,
                            "parts": [{"text": str(item.get("content", ""))}],
                        }
                    )
                else:
                    contents.append(
                        {
                            "role": "user",
                            "parts": [{"text": str(ensure_serializable(item))}],
                        }
                    )
        else:
            # Other sections get added as user messages
            contents.append(
                {
                    "role": "user",
                    "parts": [{"text": f"[{name}]\n{_stringify_items(items)}"}],
                }
            )

    # Build system instruction
    system_instruction = None
    all_system_parts = system_parts + instructions_parts
    if all_system_parts:
        system_instruction = {"parts": [{"text": "\n\n".join(all_system_parts)}]}

    # Build payload
    payload: dict[str, Any] = {"contents": contents}

    if system_instruction:
        payload["system_instruction"] = system_instruction

    if generation_config:
        payload["generation_config"] = generation_config

    return payload


