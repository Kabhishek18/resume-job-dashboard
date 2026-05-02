import uuid

from fastapi.testclient import TestClient

from app.main import app


def _register_and_token() -> tuple[str, str]:
    email = f"prof-{uuid.uuid4().hex[:12]}@example.com"
    c = TestClient(app)
    r = c.post(
        "/api/auth/register",
        json={
            "name": "Prof Test",
            "email": email,
            "password": "securepass123",
            "confirm_password": "securepass123",
        },
    )
    assert r.status_code == 200, r.json()
    return r.json()["access_token"], email


def test_profile_get_requires_auth():
    c = TestClient(app)
    r = c.get("/api/profile")
    assert r.status_code == 401


def test_profile_get_and_resume_update():
    token, _email = _register_and_token()
    c = TestClient(app)

    gp = c.get("/api/profile", headers={"Authorization": f"Bearer {token}"})
    assert gp.status_code == 200
    body = gp.json()
    assert body["resume_text"] is None
    assert body["resume_updated_at"] is None

    txt = "Line one\nSenior engineer Python\n"
    up = c.put(
        "/api/profile/resume",
        headers={"Authorization": f"Bearer {token}"},
        json={"resume_text": txt},
    )
    assert up.status_code == 200
    data = up.json()
    assert data["resume_text"].strip().startswith("Line one")
    assert data["resume_updated_at"] is not None

    gp2 = c.get("/api/profile", headers={"Authorization": f"Bearer {token}"})
    assert gp2.json()["resume_text"].strip().startswith("Line one")


def test_resume_update_validation_empty():
    token, _ = _register_and_token()
    c = TestClient(app)
    bad = c.put(
        "/api/profile/resume",
        headers={"Authorization": f"Bearer {token}"},
        json={"resume_text": ""},
    )
    assert bad.status_code == 400
