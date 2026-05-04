"""OpenRouter-related Settings validation."""

import pytest
from pydantic import ValidationError

from app.core.config import JWT_DEV_PLACEHOLDER, Settings


def test_llm_requires_openrouter_key() -> None:
    with pytest.raises(ValidationError) as ei:
        Settings(
            _env_file=None,
            tailoring_provider="llm",
            openrouter_api_key="",
            openrouter_primary_model="openai/gpt-4o-mini",
            jwt_secret="a" * 32,
            app_env="development",
        )
    assert "OPENROUTER_API_KEY" in str(ei.value)


def test_llm_requires_primary_model() -> None:
    with pytest.raises(ValidationError) as ei:
        Settings(
            _env_file=None,
            tailoring_provider="llm",
            openrouter_api_key="sk-test",
            openrouter_primary_model="",
            jwt_secret="a" * 32,
            app_env="development",
        )
    assert "OPENROUTER_PRIMARY_MODEL" in str(ei.value)


def test_stub_ignores_missing_openrouter() -> None:
    s = Settings(
        _env_file=None,
        tailoring_provider="stub",
        openrouter_api_key="",
        openrouter_primary_model="",
        jwt_secret="a" * 32,
        app_env="development",
    )
    assert s.tailoring_provider == "stub"
    assert s.openrouter_model_chain == []


def test_fallback_csv_parsing() -> None:
    s = Settings(
        _env_file=None,
        tailoring_provider="stub",
        openrouter_fallback_models_csv=" a , ,b ",
        jwt_secret="a" * 32,
        app_env="development",
    )
    assert s.openrouter_fallback_models == ["a", "b"]
    assert s.openrouter_model_chain == []


def test_model_chain_primary_and_dedupe() -> None:
    s = Settings(
        _env_file=None,
        tailoring_provider="stub",
        openrouter_primary_model="m1",
        openrouter_fallback_models_csv=" m1 , m2, m3",
        jwt_secret="a" * 32,
        app_env="development",
    )
    assert s.openrouter_model_chain == ["m1", "m2", "m3"]


def test_llm_accept_with_openrouter() -> None:
    s = Settings(
        _env_file=None,
        tailoring_provider="llm",
        openrouter_api_key="secret",
        openrouter_primary_model="google/gemma-7b-it",
        openrouter_fallback_models_csv="x,y",
        jwt_secret="a" * 32,
        app_env="development",
    )
    assert s.tailoring_provider == "llm"
    assert len(s.openrouter_model_chain) == 3


def test_llm_raises_with_placeholder_jwt_in_production() -> None:
    with pytest.raises(ValidationError):
        Settings(
            _env_file=None,
            tailoring_provider="llm",
            openrouter_api_key="k",
            openrouter_primary_model="m",
            app_env="production",
            jwt_secret=JWT_DEV_PLACEHOLDER,
        )
