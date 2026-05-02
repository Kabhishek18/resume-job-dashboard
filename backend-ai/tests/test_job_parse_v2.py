"""Tests for job_parse_v2 extraction."""

from app.schemas.job import JobDescriptionInput
from app.services.job_parse_v2 import parse_job_v2
from app.services.skill_canonicalization import extract_canonical_skills_from_blob


def test_jd_synonym_maps_container_orchestration_to_canonical_skill():
    blob = """
Senior Backend Engineer
We operate container orchestration at scale plus REST APIs.

Requirements:
Experience with Postgres and kubernetes helpful.
"""
    skills = extract_canonical_skills_from_blob(blob.lower())
    assert "kubernetes" in skills
    assert "postgresql" in skills

    feat = parse_job_v2(
        JobDescriptionInput(
            title="Senior Backend Engineer",
            raw_text=blob,
        )
    )
    assert "kubernetes" in feat.hard_skills


def test_seniority_rank_inferior_intern_title():
    feat = parse_job_v2(
        JobDescriptionInput(
            title="Software Engineer Intern",
            raw_text="Join our internship program building internal tools.",
        )
    )
    assert feat.seniority_rank <= 1
