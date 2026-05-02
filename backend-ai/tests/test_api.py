import uuid

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_match_endpoint_v1_shape():
    r = client.post(
        "/api/match",
        json={
            "raw_resume_text": "python fastapi engineer with docker experience",
            "job": {
                "title": "Backend Engineer",
                "company": "Acme",
                "raw_text": "We need Python FastAPI SQL AWS backend development.",
            },
        },
    )
    assert r.status_code == 200
    data = r.json()
    assert data["version"] == "v1"
    assert "score" in data
    assert 0 <= data["score"] <= 100


def test_match_accepts_optional_job_url():
    r = client.post(
        "/api/match",
        json={
            "raw_resume_text": "python fastapi engineer",
            "job": {
                "title": "Backend Engineer",
                "company": "Acme",
                "raw_text": "We need Python FastAPI SQL backend development.",
                "url": "https://jobs.example.invalid/123",
            },
        },
    )
    assert r.status_code == 200
    assert r.json()["version"] == "v1"


def test_match_rejects_empty_job_description():
    r = client.post(
        "/api/match",
        json={
            "raw_resume_text": "senior engineer python",
            "job": {"title": "Backend", "raw_text": ""},
        },
    )
    assert r.status_code == 400


def test_match_validation_error_envelope():
    r = client.post(
        "/api/match",
        json={
            "raw_resume_text": "",
            "job": {"raw_text": "Python developer"},
        },
    )
    assert r.status_code == 400
    body = r.json()
    assert body["error"]["code"] == "VALIDATION_ERROR"


def test_health_v1():
    r = client.get("/api/health")
    assert r.status_code == 200
    assert r.json() == {"version": "v1", "status": "ok"}


def test_auth_register_login_me_flow():
    email = f"auth-{uuid.uuid4().hex[:12]}@example.com"
    r = client.post(
        "/api/auth/register",
        json={
            "name": "Flow Test",
            "email": email,
            "password": "securepass123",
            "confirm_password": "securepass123",
        },
    )
    assert r.status_code == 200
    body = r.json()
    assert "access_token" in body
    assert body["user"]["email"] == email

    token = body["access_token"]
    me = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 200
    assert me.json()["name"] == "Flow Test"

    login = client.post(
        "/api/auth/login",
        json={"email": email, "password": "securepass123"},
    )
    assert login.status_code == 200
    assert login.json()["user"]["email"] == email
