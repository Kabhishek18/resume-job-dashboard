import json

import httpx
import pytest
import respx
from fastapi.testclient import TestClient

import app.core.config as core_config
from app.main import app
from app.services.tailoring import factory as tailoring_factory


def _tailor_completion_json(include_cover_letter_content: bool) -> dict:
    base = {
        "review": {
            "add": ["LLM highlight Python"],
            "remove": ["Buzzwords"],
            "improve": ["Quantify Kubernetes impact"],
        },
        "tailored_resume": {"summary": "LLM-tailored executive summary.", "bullets": ["B1 outcome", "B2 stack"]},
    }
    if include_cover_letter_content:
        base["cover_letter"] = "Dear Hiring Team,\n\nI bring Python and Docker…\n\nSincerely,\nCandidate"
    else:
        base["cover_letter"] = None
    return base


def _ok_openrouter(inner: dict) -> httpx.Response:
    return httpx.Response(
        200,
        json={"choices": [{"message": {"content": json.dumps(inner)}}]},
    )


def _patch_llm_openrouter(monkeypatch: pytest.MonkeyPatch, fallback_csv: str = "fb/model"):
    """Shared singleton settings mutated in-place like existing stub tests."""
    s = tailoring_factory.settings
    assert s is core_config.settings
    monkeypatch.setattr(s, "tailoring_provider", "llm", raising=False)
    monkeypatch.setattr(s, "openrouter_api_key", "sk-test-secret", raising=False)
    monkeypatch.setattr(s, "openrouter_primary_model", "primary/model", raising=False)
    monkeypatch.setattr(s, "openrouter_fallback_models_csv", fallback_csv, raising=False)
    monkeypatch.setattr(s, "openrouter_base_url", "https://resume-tailor.invalid/api/v1", raising=False)
    monkeypatch.setattr(s, "openrouter_timeout_seconds", 10.0, raising=False)


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


def test_tailor_llm_mode_returns_tailor_apiv1(monkeypatch):
    _patch_llm_openrouter(monkeypatch, fallback_csv="")
    inner = _tailor_completion_json(include_cover_letter_content=False)

    with respx.mock:
        route = respx.post("https://resume-tailor.invalid/api/v1/chat/completions").mock(
            return_value=_ok_openrouter(inner)
        )
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
        assert route.call_count == 1
        body = r.json()
        assert body["version"] == "v1"
        assert body["provider_mode"] == "llm"
        assert body["tailored_resume"]["summary"] == "LLM-tailored executive summary."
        assert body["cover_letter"] is None


def test_tailor_llm_include_cover(monkeypatch):
    _patch_llm_openrouter(monkeypatch, fallback_csv="")
    inner = _tailor_completion_json(include_cover_letter_content=True)

    with respx.mock:
        respx.post("https://resume-tailor.invalid/api/v1/chat/completions").mock(return_value=_ok_openrouter(inner))
        c = TestClient(app)
        r = c.post(
            "/api/resume/tailor",
            json={
                "resume_text": "x",
                "job": {"raw_text": "y"},
                "include_cover_letter": True,
            },
        )
        assert r.status_code == 200
        body = r.json()
        assert body["provider_mode"] == "llm"
        assert body["cover_letter"] and "Dear Hiring Team" in body["cover_letter"]


def test_tailor_llm_accepts_snapshots(monkeypatch):
    _patch_llm_openrouter(monkeypatch, fallback_csv="")
    inner = _tailor_completion_json(include_cover_letter_content=False)

    with respx.mock:
        respx.post("https://resume-tailor.invalid/api/v1/chat/completions").mock(return_value=_ok_openrouter(inner))
        c = TestClient(app)
        r = c.post(
            "/api/resume/tailor",
            json={
                "resume_text": "Python engineer.",
                "job": {"title": "Backend", "raw_text": "Kafka k8s."},
                "include_cover_letter": False,
                "match_snapshot": {
                    "score": 40.0,
                    "skill_match": 40.0,
                    "experience_match": 40.0,
                    "keyword_ats_match": 40.0,
                    "context_fit": 40.0,
                    "missing_skills": ["kafka"],
                    "suggestions": ["add"],
                    "weak_areas": ["x"],
                },
                "match_snapshot_v2": {
                    "version": "v2",
                    "ats_score": 72.5,
                    "job_match_score": 58.3,
                    "missing_hard_skills": ["kafka"],
                    "semantic_matches": ["m"],
                    "strengths": ["s"],
                    "actions": ["a"],
                    "why_this_score": ["w"],
                },
            },
        )
        assert r.status_code == 200
        assert r.json()["provider_mode"] == "llm"


def test_tailor_llm_fallback_on_primary_invalid_json(monkeypatch):
    """Invalid JSON from primary yields fallback model call."""
    _patch_llm_openrouter(monkeypatch, fallback_csv="fallback/model-id")
    inner = _tailor_completion_json(include_cover_letter_content=False)

    with respx.mock:
        route = respx.post("https://resume-tailor.invalid/api/v1/chat/completions").mock(
            side_effect=[
                httpx.Response(200, json={"choices": [{"message": {"content": "oops not json"}}]}),
                _ok_openrouter(inner),
            ]
        )
        c = TestClient(app)
        r = c.post(
            "/api/resume/tailor",
            json={
                "resume_text": "x",
                "job": {"raw_text": "y"},
                "include_cover_letter": False,
            },
        )
        assert r.status_code == 200
        assert route.call_count == 2


def test_tailor_llm_not_configured(monkeypatch):
    s = tailoring_factory.settings
    monkeypatch.setattr(s, "tailoring_provider", "llm", raising=False)
    monkeypatch.setattr(s, "openrouter_api_key", "", raising=False)
    monkeypatch.setattr(s, "openrouter_primary_model", "any/model", raising=False)

    c = TestClient(app)
    r = c.post(
        "/api/resume/tailor",
        json={"resume_text": "x", "job": {"raw_text": "y"}, "include_cover_letter": False},
    )
    assert r.status_code == 503
    assert r.json()["error"]["code"] == "OPENROUTER_NOT_CONFIGURED"


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
