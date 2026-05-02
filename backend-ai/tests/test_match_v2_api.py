"""API contract smoke for POST /api/match/v2 (embeddings patched)."""

import hashlib

import numpy as np
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services import embedding_service

client = TestClient(app)


def _deterministic_normalized_vec(text: str, dim: int = 384) -> np.ndarray:
    h = hashlib.sha256(text.encode("utf-8")).digest()
    repeats = bytes((h[i % len(h)] for i in range(dim)))
    buf = np.asarray(list(repeats), dtype=np.float64).copy()
    buf -= buf.mean()
    n = np.linalg.norm(buf)
    return buf / max(1e-9, n)


def _fake_encode_texts(texts):
    return np.stack([_deterministic_normalized_vec(t) for t in texts], axis=0)


@pytest.fixture
def patched_embed(monkeypatch):
    monkeypatch.setattr(embedding_service, "encode_texts", _fake_encode_texts)


def test_match_v2_returns_new_shape_ranges(patched_embed):
    r = client.post(
        "/api/match/v2",
        json={
            "raw_resume_text": "SUMMARY\nEng\nSKILLS\nPython\nEXPERIENCE\nCo • 2021–Present • APIs\n",
            "job": {
                "title": "Backend",
                "raw_text": "Python FastAPI SQL kubernetes microservices SaaS APIs.",
            },
        },
    )
    assert r.status_code == 200
    data = r.json()
    assert data["version"] == "v2"
    assert data["job_match"]["band"] in ("weak", "needs_work", "strong")
    for k in (
        "semantic_similarity",
        "exact_skill_overlap",
        "lexical_match",
        "title_alignment",
        "experience_alignment",
    ):
        assert 0 <= data[k] <= 100
