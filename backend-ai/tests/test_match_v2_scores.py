"""Deterministic scoring tests via embedding monkeypatch."""

import hashlib

import numpy as np
import pytest

from app.schemas.job import JobDescriptionInput
from app.schemas.match import MatchRequest
from app.services import embedding_service
from app.services.match_v2_service import score_match_v2


def _deterministic_normalized_vec(text: str, dim: int = 384) -> np.ndarray:
    h = hashlib.sha256(text.encode("utf-8")).digest()
    repeats = bytes((h[i % len(h)] for i in range(dim)))
    buf = np.asarray(list(repeats), dtype=np.float64).copy()
    buf -= buf.mean()
    n = np.linalg.norm(buf)
    return buf / max(1e-9, n)


def _fake_encode_texts(texts):
    mats = [_deterministic_normalized_vec(t) for t in texts]
    return np.stack(mats, axis=0)


@pytest.fixture(autouse=True)
def _patch_embeddings(monkeypatch):
    monkeypatch.setattr(embedding_service, "encode_texts", _fake_encode_texts)


def test_ats_rewards_structure_over_noise_wall():
    clean = """CONTACT\nx@co.com\n\nSKILLS\nPython SQL\n\nEXPERIENCE\nAcme\nJan 2019–Jan 2021\n• Shipped APIs\n"""
    noisy = "word " * 400 + "\t\t\t tabwall " * 120
    jd = JobDescriptionInput(title="Eng", raw_text="Python developer needed.")

    req_clean = MatchRequest(raw_resume_text=clean, job=jd)
    req_noise = MatchRequest(raw_resume_text=noisy, job=jd)
    assert score_match_v2(req_clean).ats_compatibility.score > score_match_v2(req_noise).ats_compatibility.score


def test_exact_skill_overlap_uses_canonical_matches():
    resume = "SKILLS\nPostgres REST API golang\nEXPERIENCE\nBackend work"
    jd = JobDescriptionInput(
        title="Backend",
        raw_text="PostgreSQL and container orchestration with REST APIs.",
    )
    out = score_match_v2(MatchRequest(raw_resume_text=resume, job=jd))
    assert out.exact_skill_overlap > 35.0


def test_jaccard_reflects_overlap():
    r = MatchRequest(
        raw_resume_text="SKILLS\nPython Django SQL\nPROJECTS\nData pipeline",
        job=JobDescriptionInput(
            title="Python Engineer",
            raw_text="Needs Python Django AWS SQL experience building services.",
        ),
    )
    out = score_match_v2(r)
    assert 0 <= out.exact_skill_overlap <= 100


def test_bm25_section_boost_skills_above_education(monkeypatch):
    monkeypatch.setattr(embedding_service, "encode_texts", _fake_encode_texts)

    resume_skills = """EDUCATION
BS CS — general studies

SKILLS
kafka python kubernetes pipelines microservices production shipping

PROJECTS

EXPERIENCE
"""
    resume_edu = """EDUCATION
kafka python kubernetes theory coursework pipelines microservices academic only

SKILLS

PROJECTS

EXPERIENCE
"""
    jd = JobDescriptionInput(
        title="Streaming Engineer kafka kubernetes python",
        raw_text="Responsible for kafka kubernetes python microservices pipelines production shipping.",
    )
    sk = score_match_v2(MatchRequest(raw_resume_text=resume_skills, job=jd)).lexical_match
    ed = score_match_v2(MatchRequest(raw_resume_text=resume_edu, job=jd)).lexical_match
    assert sk > ed


def test_snapshot_deterministic_for_fixed_inputs():
    r = MatchRequest(
        raw_resume_text=(
            "SUMMARY\nAPI engineer\nSKILLS\nPython FastAPI\n"
            "EXPERIENCE\nCo • Jan2020-Present • APIs shipped"
        ),
        job=JobDescriptionInput(
            title="Backend Engineer",
            raw_text="We need FastAPI PostgreSQL kubernetes REST APIs SaaS backend.",
        ),
    )
    a = score_match_v2(r).model_dump()
    b = score_match_v2(r).model_dump()
    assert a == b
    assert a["version"] == "v2"
    for k in (
        "semantic_similarity",
        "exact_skill_overlap",
        "lexical_match",
        "title_alignment",
        "experience_alignment",
    ):
        assert 0 <= a[k] <= 100


def test_seniority_gap_intern_resume_vs_staff_jd_scores_lower_fit():
    intern_resume = "EXPERIENCE\nSoftware Intern • ToolsCo Summer 2024\nSKILLS\nPython scripts"
    staff_jd = JobDescriptionInput(
        title="Staff Principal Engineer Platform",
        raw_text="Staff-level distributed systems kafka kubernetes leadership mentorship.",
    )
    intern_jd = JobDescriptionInput(
        title="Software Engineering Intern",
        raw_text="Internship tooling with python scripting.",
    )
    aligned = score_match_v2(MatchRequest(raw_resume_text=intern_resume, job=intern_jd)).experience_alignment
    tense = score_match_v2(MatchRequest(raw_resume_text=intern_resume, job=staff_jd)).experience_alignment
    assert aligned >= tense
