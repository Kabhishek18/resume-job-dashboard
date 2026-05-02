import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services.tailoring import factory as tailoring_factory


def test_tailor_stub_shape():
    c = TestClient(app)
    r = c.post(
        "/api/resume/tailor",
        json={
            "resume_text": "Python engineer with FastAPI and Docker.",
            "job": {"title": "Backend", "raw_text": "We need Python, FastAPI, Kubernetes."},
            "include_cover_letter": False,
        },
    )
    assert r.status_code == 200
    body = r.json()
    assert body["version"] == "v1"
    assert body["provider_mode"] == "stub"
    assert set(body["review"].keys()) == {"add", "remove", "improve"}
    assert body["tailored_resume"]["summary"]
    assert isinstance(body["tailored_resume"]["bullets"], list)
    assert len(body["tailored_resume"]["bullets"]) == 3
    assert body["cover_letter"] is None


def test_tailor_stub_with_cover_snapshot():
    c = TestClient(app)
    snap = {
        "score": 55.5,
        "skill_match": 50.0,
        "experience_match": 55.0,
        "keyword_ats_match": 60.0,
        "context_fit": 53.5,
        "missing_skills": ["k8s"],
        "suggestions": ["mirror keywords"],
        "weak_areas": ["depth"],
    }
    r = c.post(
        "/api/resume/tailor",
        json={
            "resume_text": "Python engineer with FastAPI and Docker.",
            "job": {"title": "Backend", "raw_text": "We need Python, FastAPI, Kubernetes."},
            "include_cover_letter": True,
            "match_snapshot": snap,
        },
    )
    assert r.status_code == 200
    body = r.json()
    assert body["cover_letter"]
    assert "ref:" in body["cover_letter"]


def test_tailor_stub_deterministic_snapshot():
    c = TestClient(app)
    payload = {
        "resume_text": "ALPHA resume text deterministic.",
        "job": {"title": "T1", "raw_text": "BETA jd text deterministic."},
        "include_cover_letter": False,
    }
    a = c.post("/api/resume/tailor", json=payload).json()
    b = c.post("/api/resume/tailor", json=payload).json()
    assert a == b


def test_tailor_llm_mode_returns_501(monkeypatch):
    monkeypatch.setattr(tailoring_factory.settings, "tailoring_provider", "llm")

    c = TestClient(app)
    r = c.post(
        "/api/resume/tailor",
        json={
            "resume_text": "x",
            "job": {"raw_text": "y"},
            "include_cover_letter": False,
        },
    )
    assert r.status_code == 501
    err = r.json()["error"]
    assert err["code"] == "LLM_TAILOR_NOT_CONFIGURED"


def test_tailor_stub_accepts_match_snapshot_v2():
    c = TestClient(app)
    r = c.post(
        "/api/resume/tailor",
        json={
            "resume_text": "Python engineer with FastAPI and Docker.",
            "job": {"title": "Backend", "raw_text": "We need Python, FastAPI, Kubernetes."},
            "include_cover_letter": False,
            "match_snapshot_v2": {
                "version": "v2",
                "ats_score": 72.5,
                "job_match_score": 58.3,
                "missing_hard_skills": ["kafka"],
                "semantic_matches": ["JD skill kafka aligns with resume."],
                "strengths": ["overlap"],
                "actions": ["add kafka"],
                "why_this_score": ["blend"],
            },
        },
    )
    assert r.status_code == 200
