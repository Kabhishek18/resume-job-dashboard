"""LLM gateway + OpenRouter client behavior (mocked HTTP)."""

import json

import httpx
import pytest
import respx

from app.core.config import Settings
from app.core.errors import AppError
from app.schemas.tailor_contract import TailorStructuredContent
from app.services.llm.contracts import ChatMessage, StructuredJsonGenerationSpec
from app.services.llm.gateway import generate_structured_json


def _settings(**overrides: object) -> Settings:
    base = dict(
        _env_file=None,
        tailoring_provider="stub",
        openrouter_api_key="test-key",
        openrouter_primary_model="primary/model",
        openrouter_fallback_models_csv="",
        openrouter_base_url="https://mock.openrouter.invalid/api/v1",
        openrouter_timeout_seconds=10.0,
        jwt_secret="a" * 32,
        app_env="development",
    )
    base.update(overrides)
    return Settings(**base)  # type: ignore[arg-type]


def _minimal_tailor_payload(cover_null: bool = True) -> dict:
    d: dict = {
        "review": {"add": ["a"], "remove": ["r"], "improve": ["i"]},
        "tailored_resume": {"summary": "Summary", "bullets": ["B1"]},
    }
    d["cover_letter"] = None if cover_null else "Dear hiring manager..."
    return d


def _ok_response(inner: dict, status_code: int = 200) -> httpx.Response:
    return httpx.Response(
        status_code,
        json={
            "choices": [
                {
                    "message": {
                        "content": json.dumps(inner),
                    }
                }
            ]
        },
    )


def test_gateway_success_first_model():
    inner = _minimal_tailor_payload()
    s = _settings(openrouter_fallback_models_csv="fallback/model")

    with respx.mock:
        route = respx.post("https://mock.openrouter.invalid/api/v1/chat/completions").mock(
            return_value=_ok_response(inner)
        )
        result = generate_structured_json(
            settings=s,
            spec=StructuredJsonGenerationSpec(messages=[ChatMessage(role="user", content="Hi")]),
            response_model=TailorStructuredContent,
        )
        assert result.tailored_resume.summary == "Summary"
        assert route.call_count == 1


def test_gateway_fallback_primary_429_secondary_ok():
    inner = _minimal_tailor_payload()
    s = _settings(openrouter_fallback_models_csv="fb/model")

    with respx.mock:
        route = respx.post("https://mock.openrouter.invalid/api/v1/chat/completions").mock(
            side_effect=[
                httpx.Response(429, json={"error": {"message": "rate limited"}}),
                _ok_response(inner),
            ]
        )
        result = generate_structured_json(
            settings=s,
            spec=StructuredJsonGenerationSpec(messages=[ChatMessage(role="user", content="Hi")]),
            response_model=TailorStructuredContent,
        )
        assert result.review.add == ["a"]
        assert route.call_count == 2


def test_gateway_primary_401_no_fallback():
    s = _settings(openrouter_fallback_models_csv="fb/model")

    with respx.mock:
        route = respx.post("https://mock.openrouter.invalid/api/v1/chat/completions").mock(
            return_value=httpx.Response(401, json={"error": {"message": "Invalid credentials"}}),
        )
        with pytest.raises(AppError) as ei:
            generate_structured_json(
                settings=s,
                spec=StructuredJsonGenerationSpec(messages=[ChatMessage(role="user", content="Hi")]),
                response_model=TailorStructuredContent,
            )
        assert ei.value.code == "OPENROUTER_UNAUTHORIZED"
        assert route.call_count == 1


def test_gateway_timeout_then_fallback_success():
    inner = _minimal_tailor_payload()
    s = _settings(openrouter_fallback_models_csv="fb/model")

    calls = {"n": 0}

    def responder(request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        if calls["n"] == 1:
            raise httpx.TimeoutException("timeout", request=request)
        return _ok_response(inner)

    with respx.mock:
        route = respx.post("https://mock.openrouter.invalid/api/v1/chat/completions").mock(
            side_effect=responder
        )
        result = generate_structured_json(
            settings=s,
            spec=StructuredJsonGenerationSpec(messages=[ChatMessage(role="user", content="Hi")]),
            response_model=TailorStructuredContent,
        )
        assert result.tailored_resume.bullets == ["B1"]
        assert route.call_count == 2


def test_gateway_exhaust_quota():
    s = _settings(openrouter_fallback_models_csv="fb/model")

    with respx.mock:
        route = respx.post("https://mock.openrouter.invalid/api/v1/chat/completions").mock(
            return_value=httpx.Response(429, json={"error": {"message": "rate"}}),
        )
        with pytest.raises(AppError) as ei:
            generate_structured_json(
                settings=s,
                spec=StructuredJsonGenerationSpec(messages=[ChatMessage(role="user", content="Hi")]),
                response_model=TailorStructuredContent,
            )
        assert ei.value.code == "OPENROUTER_QUOTA_EXCEEDED"
        assert route.call_count == 2


def test_gateway_invalid_json_then_fallback():
    s = _settings(openrouter_fallback_models_csv="fb/model")

    with respx.mock:
        route = respx.post("https://mock.openrouter.invalid/api/v1/chat/completions").mock(
            side_effect=[
                httpx.Response(
                    200,
                    json={"choices": [{"message": {"content": "NOT JSON"}}]},
                ),
                _ok_response(_minimal_tailor_payload()),
            ]
        )
        result = generate_structured_json(
            settings=s,
            spec=StructuredJsonGenerationSpec(messages=[ChatMessage(role="user", content="Hi")]),
            response_model=TailorStructuredContent,
        )
        assert isinstance(result.tailored_resume.summary, str)
        assert route.call_count == 2


def test_post_validate_triggers_fallback():
    """Reject first model payload on policy; succeed on second."""

    inner_ok = _minimal_tailor_payload()
    s = _settings(openrouter_fallback_models_csv="fb/model")

    def post_validate(tc: TailorStructuredContent) -> None:
        if tc.tailored_resume.summary == "BAD":
            raise ValueError("policy")

    with respx.mock:
        route = respx.post("https://mock.openrouter.invalid/api/v1/chat/completions").mock(
            side_effect=[
                _ok_response({**inner_ok, "tailored_resume": {"summary": "BAD", "bullets": []}}),
                _ok_response(inner_ok),
            ]
        )
        result = generate_structured_json(
            settings=s,
            spec=StructuredJsonGenerationSpec(messages=[ChatMessage(role="user", content="Hi")]),
            response_model=TailorStructuredContent,
            post_validate=post_validate,
        )
        assert result.tailored_resume.summary == "Summary"
        assert route.call_count == 2
