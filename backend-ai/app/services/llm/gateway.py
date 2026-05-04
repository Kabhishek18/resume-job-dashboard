"""Chain OpenRouter models; validate JSON against a Pydantic model."""

from __future__ import annotations

import json
import logging
import time
from collections.abc import Callable
from typing import Type, TypeVar

from pydantic import BaseModel, ValidationError

from app.core.config import Settings
from app.core.errors import AppError
from app.services.llm.classification import LLMFailureClass
from app.services.llm.contracts import StructuredJsonGenerationSpec
from app.services.llm.json_extract import parse_json_object_strict
from app.services.llm.openrouter import OpenRouterCompletionError, complete_chat_openrouter

_log = logging.getLogger(__name__)

TModel = TypeVar("TModel", bound=BaseModel)


def generate_structured_json(
    *,
    settings: Settings,
    spec: StructuredJsonGenerationSpec,
    response_model: Type[TModel],
    log: logging.Logger | None = None,
    post_validate: Callable[[TModel], None] | None = None,
) -> TModel:
    """
    Try each model in openrouter_model_chain until one returns valid JSON for response_model.

    Raises AppError when the caller must surface a stable error (auth, exhaustion).
    """
    logger = log or _log
    chain = settings.openrouter_model_chain
    if not chain:
        raise AppError(
            "OPENROUTER_NOT_CONFIGURED",
            "No OpenRouter models configured (set OPENROUTER_PRIMARY_MODEL).",
            status_code=503,
        )

    if not (settings.openrouter_api_key or "").strip():
        raise AppError(
            "OPENROUTER_NOT_CONFIGURED",
            "OpenRouter API key is missing (OPENROUTER_API_KEY).",
            status_code=503,
        )

    saw_429 = False
    saw_invalid_output = False
    saw_retryable_http = False
    last_detail = ""

    for fallback_index, model in enumerate(chain):
        t0 = time.perf_counter()
        latency_ms = 0.0
        fallback_occurred = fallback_index > 0

        try:
            raw = complete_chat_openrouter(settings, model, spec)
            latency_ms = (time.perf_counter() - t0) * 1000.0

            parsed = parse_json_object_strict(raw)
            validated = response_model.model_validate(parsed)
            if post_validate is not None:
                try:
                    post_validate(validated)
                except ValueError as ve:
                    saw_invalid_output = True
                    last_detail = str(ve)
                    logger.warning(
                        "llm_attempt provider=openrouter model=%s latency_ms=%.1f outcome=post_validation_failed "
                        "failure_class=invalid_model_output fallback_index=%s fallback_occurred=%s detail=%s",
                        model,
                        latency_ms,
                        fallback_index,
                        fallback_occurred,
                        str(ve)[:200],
                    )
                    continue

            logger.info(
                "llm_attempt provider=openrouter model=%s latency_ms=%.1f outcome=success fallback_index=%s fallback_occurred=%s",
                model,
                latency_ms,
                fallback_index,
                fallback_occurred,
            )
            return validated

        except OpenRouterCompletionError as e:
            latency_ms = (time.perf_counter() - t0) * 1000.0
            last_detail = e.message

            if e.failure_class == LLMFailureClass.LOCAL_CONFIG_AUTH:
                logger.warning(
                    "llm_attempt provider=openrouter model=%s latency_ms=%.1f outcome=auth_failure failure_class=%s fallback_index=%s",
                    model,
                    latency_ms,
                    e.failure_class.value,
                    fallback_index,
                )
                raise AppError(
                    "OPENROUTER_UNAUTHORIZED",
                    e.message or "OpenRouter rejected the API key or account.",
                    status_code=401,
                )

            if e.failure_class == LLMFailureClass.RETRYABLE_UPSTREAM:
                if e.http_status == 429:
                    saw_429 = True
                elif e.http_status is not None and e.http_status >= 400:
                    saw_retryable_http = True
                else:
                    saw_retryable_http = True
                logger.warning(
                    "llm_attempt provider=openrouter model=%s latency_ms=%.1f outcome=upstream_error "
                    "failure_class=%s http_status=%s fallback_index=%s fallback_occurred=%s detail=%s",
                    model,
                    latency_ms,
                    e.failure_class.value,
                    e.http_status,
                    fallback_index,
                    fallback_occurred,
                    (e.message or "")[:200],
                )
                continue

            if e.failure_class == LLMFailureClass.INVALID_MODEL_OUTPUT:
                saw_invalid_output = True
                logger.warning(
                    "llm_attempt provider=openrouter model=%s latency_ms=%.1f outcome=invalid_upstream_shape "
                    "failure_class=%s fallback_index=%s fallback_occurred=%s",
                    model,
                    latency_ms,
                    e.failure_class.value,
                    fallback_index,
                    fallback_occurred,
                )
                continue

        except (json.JSONDecodeError, ValueError, TypeError) as e:
            latency_ms = (time.perf_counter() - t0) * 1000.0
            saw_invalid_output = True
            last_detail = str(e)
            logger.warning(
                "llm_attempt provider=openrouter model=%s latency_ms=%.1f outcome=invalid_json "
                "failure_class=invalid_model_output fallback_index=%s fallback_occurred=%s detail=%s",
                model,
                latency_ms,
                fallback_index,
                fallback_occurred,
                str(e)[:200],
            )
            continue

        except ValidationError as e:
            latency_ms = (time.perf_counter() - t0) * 1000.0
            saw_invalid_output = True
            last_detail = str(e)
            logger.warning(
                "llm_attempt provider=openrouter model=%s latency_ms=%.1f outcome=schema_validation_failed "
                "failure_class=invalid_model_output fallback_index=%s fallback_occurred=%s",
                model,
                latency_ms,
                fallback_index,
                fallback_occurred,
            )
            continue

    suffix = (last_detail[:400] + "…") if len(last_detail) > 400 else last_detail
    suffix = f" ({suffix})" if suffix else ""

    if saw_invalid_output and not saw_429 and not saw_retryable_http:
        raise AppError(
            "LLM_TAILOR_INVALID_OUTPUT",
            "The model returned JSON that did not match the expected schema after all fallback models." + suffix,
            status_code=502,
        )

    if saw_429:
        raise AppError(
            "OPENROUTER_QUOTA_EXCEEDED",
            "OpenRouter rate limit or quota was hit for every model in the fallback chain.",
            status_code=429,
        )

    raise AppError(
        "OPENROUTER_UPSTREAM_UNAVAILABLE",
        "OpenRouter was unreachable or repeatedly errored after trying every model in the fallback chain.",
        status_code=502,
    )


__all__ = ["generate_structured_json"]
