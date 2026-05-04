"""OpenRouter chat completions via httpx (sync)."""

from __future__ import annotations

import json
import logging
from typing import Any

import httpx

from app.core.config import Settings
from app.services.llm.classification import LLMFailureClass, classify_http_status
from app.services.llm.contracts import StructuredJsonGenerationSpec, messages_to_openai

_log = logging.getLogger(__name__)


class OpenRouterCompletionError(Exception):
    """Structured failure from one OpenRouter request (before gateway validation)."""

    def __init__(
        self,
        failure_class: LLMFailureClass,
        message: str,
        *,
        http_status: int | None = None,
    ) -> None:
        self.failure_class = failure_class
        self.message = message
        self.http_status = http_status
        super().__init__(message)


def _error_detail_from_body(body_text: str) -> str:
    try:
        data = json.loads(body_text)
    except json.JSONDecodeError:
        return (body_text or "")[:500]
    err = data.get("error")
    if isinstance(err, dict) and isinstance(err.get("message"), str):
        return err["message"]
    if isinstance(err, str):
        return err
    return (body_text or "")[:500]


def complete_chat_openrouter(settings: Settings, model: str, spec: StructuredJsonGenerationSpec) -> str:
    """POST /chat/completions; returns assistant message content string."""
    key = (settings.openrouter_api_key or "").strip()
    if not key:
        raise OpenRouterCompletionError(
            LLMFailureClass.LOCAL_CONFIG_AUTH,
            "OpenRouter API key is missing.",
            http_status=None,
        )

    base = (settings.openrouter_base_url or "").strip().rstrip("/")
    url = f"{base}/chat/completions"

    headers: dict[str, str] = {
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
    }
    referer = (settings.openrouter_http_referer or "").strip()
    if referer:
        headers["HTTP-Referer"] = referer
    title = (settings.openrouter_app_title or "").strip()
    if title:
        headers["X-Title"] = title

    payload: dict[str, Any] = {
        "model": model,
        "messages": messages_to_openai(spec.messages),
    }
    if spec.use_json_object_response_format:
        payload["response_format"] = {"type": "json_object"}

    timeout = httpx.Timeout(settings.openrouter_timeout_seconds)

    try:
        with httpx.Client(timeout=timeout) as client:
            resp = client.post(url, headers=headers, json=payload)
    except httpx.TimeoutException as e:
        raise OpenRouterCompletionError(
            LLMFailureClass.RETRYABLE_UPSTREAM,
            f"OpenRouter request timed out: {e}",
            http_status=None,
        ) from e
    except httpx.RequestError as e:
        raise OpenRouterCompletionError(
            LLMFailureClass.RETRYABLE_UPSTREAM,
            f"OpenRouter connection error: {e}",
            http_status=None,
        ) from e

    body_text = resp.text
    if resp.status_code != 200:
        detail = _error_detail_from_body(body_text)
        msg = detail or resp.reason_phrase or f"HTTP {resp.status_code}"
        fc = classify_http_status(resp.status_code)
        _log.warning(
            "openrouter_http_error status=%s failure_class=%s detail=%s",
            resp.status_code,
            fc.value,
            msg[:300],
        )
        raise OpenRouterCompletionError(fc, msg, http_status=resp.status_code)

    try:
        data = resp.json()
        content = data["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError, json.JSONDecodeError) as e:
        raise OpenRouterCompletionError(
            LLMFailureClass.INVALID_MODEL_OUTPUT,
            f"OpenRouter response missing assistant content: {e}",
            http_status=200,
        ) from e

    if not isinstance(content, str):
        raise OpenRouterCompletionError(
            LLMFailureClass.INVALID_MODEL_OUTPUT,
            "OpenRouter assistant content is not a string.",
            http_status=200,
        )

    return content
