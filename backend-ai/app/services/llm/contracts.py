"""Provider-agnostic shapes for structured LLM generation."""

from dataclasses import dataclass
from typing import Any, TypedDict


class ChatMessage(TypedDict):
    role: str
    content: str


@dataclass(frozen=True)
class StructuredJsonGenerationSpec:
    """What the gateway asks the provider to return (validated server-side)."""

    messages: list[ChatMessage]
    use_json_object_response_format: bool = True


def messages_to_openai(messages: list[ChatMessage]) -> list[dict[str, Any]]:
    return [{"role": m["role"], "content": m["content"]} for m in messages]
