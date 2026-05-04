"""Settings validation for production deployment."""

import pytest
from pydantic import ValidationError

from app.core.config import JWT_DEV_PLACEHOLDER, Settings


def test_production_rejects_placeholder_jwt(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("JWT_SECRET", JWT_DEV_PLACEHOLDER)
    with pytest.raises(ValidationError):
        Settings()


def test_production_rejects_short_jwt(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("JWT_SECRET", "x" * 31)
    with pytest.raises(ValidationError):
        Settings()


def test_production_accepts_long_random_jwt(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("APP_ENV", "production")
    secret = "a" * 32
    monkeypatch.setenv("JWT_SECRET", secret)
    s = Settings()
    assert s.jwt_secret == secret
    assert s.app_env == "production"


def test_development_allows_default_jwt(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("APP_ENV", "development")
    monkeypatch.setenv("JWT_SECRET", JWT_DEV_PLACEHOLDER)
    s = Settings()
    assert s.jwt_secret == JWT_DEV_PLACEHOLDER
