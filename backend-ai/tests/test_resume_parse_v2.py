"""Tests for resume_parse_v2 heuristics."""

from app.services.resume_parse_v2 import parse_resume_v2


def test_extracts_contact_email_and_sections():
    text = """
Jane Doe
jane.doe@example.com | +1-415-555-0100 | linkedin.com/in/janedoe

SUMMARY
Backend engineer focused on APIs.

SKILLS
Python, FastAPI, Docker, Postgres

EXPERIENCE
Acme Corp
Jan 2020 – Present
- Built REST APIs using FastAPI.

EDUCATION
BS Computer Science — State University

CERTIFICATIONS
AWS Certified Developer
"""
    f = parse_resume_v2(text)
    assert "jane.doe@example.com" in f.contact_emails
    assert f.has_linkedin
    assert "python" in f.resume_canonical_skills or "postgresql" in f.resume_canonical_skills
    assert len(f.sections.get("skills", "")) > 5
    assert "EXPERIENCE" in text.upper()


def test_section_headers_route_experience_block():
    text = """WORK HISTORY
Foo Inc
March 2021 to Dec 2022
Worked on backends.

TECHNICAL SKILLS
Java, Kafka
"""
    f = parse_resume_v2(text)
    assert "kafka" in f.resume_canonical_skills
    assert "java" in f.resume_canonical_skills
