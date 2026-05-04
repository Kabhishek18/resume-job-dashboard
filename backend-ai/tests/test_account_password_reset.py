import io
import uuid
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient
from sqlalchemy import func, select

from app.db.session import SessionLocal
from app.main import app
from app.models.password_reset_token import PasswordResetToken
from app.models.user import User
from app.services.password_reset import FORGOT_PASSWORD_PUBLIC_MESSAGE_V1


def _register(name: str = "Acct Test") -> tuple[str, str, str]:
    email = f"acct-{uuid.uuid4().hex[:12]}@example.com"
    c = TestClient(app)
    r = c.post(
        "/api/auth/register",
        json={
            "name": name,
            "email": email,
            "password": "oldpass123",
            "confirm_password": "oldpass123",
        },
    )
    assert r.status_code == 200, r.json()
    return r.json()["access_token"], email, "oldpass123"


def test_patch_profile_name_requires_auth():
    c = TestClient(app)
    r = c.patch("/api/profile", json={"name": "N"})
    assert r.status_code == 401


def test_patch_profile_name_success():
    token, _email, _pw = _register("Before")
    c = TestClient(app)
    r = c.patch(
        "/api/profile",
        headers={"Authorization": f"Bearer {token}"},
        json={"name": "  After Name  "},
    )
    assert r.status_code == 200
    assert r.json()["name"] == "After Name"


def test_change_password_requires_auth():
    c = TestClient(app)
    r = c.post(
        "/api/auth/change-password",
        json={
            "current_password": "x",
            "new_password": "newpass123",
            "confirm_password": "newpass123",
        },
    )
    assert r.status_code == 401


def test_change_password_wrong_current():
    token, _, _ = _register()
    c = TestClient(app)
    r = c.post(
        "/api/auth/change-password",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "current_password": "wrongpassword",
            "new_password": "newpass123",
            "confirm_password": "newpass123",
        },
    )
    assert r.status_code == 400
    assert r.json()["error"]["code"] == "WRONG_CURRENT_PASSWORD"


def test_change_password_mismatch_new():
    token, _, _ = _register()
    c = TestClient(app)
    r = c.post(
        "/api/auth/change-password",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "current_password": "oldpass123",
            "new_password": "newpass123",
            "confirm_password": "newpass124",
        },
    )
    assert r.status_code == 400
    assert r.json()["error"]["code"] == "VALIDATION_ERROR"


def test_change_password_weak_new():
    token, _, _ = _register()
    c = TestClient(app)
    r = c.post(
        "/api/auth/change-password",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "current_password": "oldpass123",
            "new_password": "short",
            "confirm_password": "short",
        },
    )
    assert r.status_code == 400


def test_change_password_login_roundtrip():
    token, email, old_pw = _register()
    c = TestClient(app)
    ch = c.post(
        "/api/auth/change-password",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "current_password": old_pw,
            "new_password": "brandnewpass123",
            "confirm_password": "brandnewpass123",
        },
    )
    assert ch.status_code == 200

    bad = c.post("/api/auth/login", json={"email": email, "password": old_pw})
    assert bad.status_code == 401

    ok = c.post("/api/auth/login", json={"email": email, "password": "brandnewpass123"})
    assert ok.status_code == 200


def test_forgot_password_same_shape_unknown_email():
    c = TestClient(app)
    r = c.post("/api/auth/forgot-password", json={"email": f"nope-{uuid.uuid4().hex}@example.com"})
    assert r.status_code == 200
    body = r.json()
    assert body["version"] == "v1"
    assert body["message"] == FORGOT_PASSWORD_PUBLIC_MESSAGE_V1


def _unique_reset_raw() -> str:
    return f"raw-{uuid.uuid4().hex}-{uuid.uuid4().hex}"


@patch("app.services.password_reset.get_mail_sender", return_value=MagicMock())
def test_forgot_password_same_shape_known_email(_mock: MagicMock):
    _t, email, _ = _register()
    ur = _unique_reset_raw()
    with patch("app.services.password_reset.generate_password_reset_raw_token", return_value=ur):
        c = TestClient(app)
        r = c.post("/api/auth/forgot-password", json={"email": email})
    assert r.status_code == 200
    assert r.json() == {"version": "v1", "message": FORGOT_PASSWORD_PUBLIC_MESSAGE_V1}


@patch("app.services.password_reset.get_mail_sender")
def test_forgot_password_creates_token_and_sends_mail(mock_get_sender: MagicMock):
    token, email, _ = _register()
    mock_get_sender.return_value = MagicMock()

    ur = _unique_reset_raw()
    with patch("app.services.password_reset.generate_password_reset_raw_token", return_value=ur):
        c = TestClient(app)
        r = c.post("/api/auth/forgot-password", json={"email": email})
    assert r.status_code == 200
    assert r.json()["message"] == FORGOT_PASSWORD_PUBLIC_MESSAGE_V1

    with SessionLocal() as db:
        uid = db.scalar(select(User.id).where(User.email == email))
        assert uid is not None
        n = db.scalar(
            select(func.count()).select_from(PasswordResetToken).where(PasswordResetToken.user_id == uid)
        )
        assert n == 1

    mock_get_sender.return_value.send.assert_called_once()
    args, _kwargs = mock_get_sender.return_value.send.call_args
    assert args[0] == email
    body = f"{args[2]}\n{args[3] or ''}"
    assert "reset-password?token=" in body


def _forgot_with_raw(email: str, raw: str) -> None:
    mock_sender = MagicMock()
    with patch("app.services.password_reset.get_mail_sender", return_value=mock_sender):
        with patch("app.services.password_reset.generate_password_reset_raw_token", return_value=raw):
            c = TestClient(app)
            r = c.post("/api/auth/forgot-password", json={"email": email})
            assert r.status_code == 200


def test_reset_password_success_and_single_use():
    _tok, email, _ = _register()
    raw = _unique_reset_raw()
    _forgot_with_raw(email, raw)

    c = TestClient(app)
    res = c.post(
        "/api/auth/reset-password",
        json={
            "token": raw,
            "new_password": "freshpass456",
            "confirm_password": "freshpass456",
        },
    )
    assert res.status_code == 200
    assert res.json()["version"] == "v1"

    bad2 = c.post(
        "/api/auth/reset-password",
        json={
            "token": raw,
            "new_password": "otherpass678",
            "confirm_password": "otherpass678",
        },
    )
    assert bad2.status_code == 400
    assert bad2.json()["error"]["code"] == "RESET_TOKEN_INVALID"

    login_ok = c.post("/api/auth/login", json={"email": email, "password": "freshpass456"})
    assert login_ok.status_code == 200


def test_reset_password_invalid_token():
    c = TestClient(app)
    r = c.post(
        "/api/auth/reset-password",
        json={
            "token": "not-a-real-token-at-all-xxxxxxxx",
            "new_password": "freshpass456",
            "confirm_password": "freshpass456",
        },
    )
    assert r.status_code == 400
    assert r.json()["error"]["code"] == "RESET_TOKEN_INVALID"


def test_reset_password_expired_token():
    _tok, email, _ = _register()
    raw = _unique_reset_raw()
    _forgot_with_raw(email, raw)

    with SessionLocal() as db:
        row = db.scalar(select(PasswordResetToken).order_by(PasswordResetToken.id.desc()))
        assert row is not None
        from datetime import datetime, timedelta, timezone

        row.expires_at = datetime.now(timezone.utc) - timedelta(seconds=30)
        db.add(row)
        db.commit()

    c = TestClient(app)
    r = c.post(
        "/api/auth/reset-password",
        json={
            "token": raw,
            "new_password": "freshpass456",
            "confirm_password": "freshpass456",
        },
    )
    assert r.status_code == 400
    assert r.json()["error"]["code"] == "RESET_TOKEN_INVALID"


def test_resume_upload_then_put_updates_profile_resume():
    token, _, _ = _register()
    c = TestClient(app)
    files = {"file": ("resume.txt", io.BytesIO(b"Uploaded line one\nUploaded line two\n"), "text/plain")}
    ex = c.post("/api/profile/resume-upload", headers={"Authorization": f"Bearer {token}"}, files=files)
    assert ex.status_code == 200
    text = ex.json()["plain_text"]
    put = c.put(
        "/api/profile/resume",
        headers={"Authorization": f"Bearer {token}"},
        json={"resume_text": text},
    )
    assert put.status_code == 200
    gp = c.get("/api/profile", headers={"Authorization": f"Bearer {token}"})
    assert "Uploaded line one" in (gp.json().get("resume_text") or "")
