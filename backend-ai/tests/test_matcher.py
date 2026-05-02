from app.schemas.job import JobDescriptionInput
from app.schemas.match import MatchRequest
from app.services.matcher import score_match


def test_score_match_deterministic_snapshot():
    req = MatchRequest(
        raw_resume_text="python fastapi sql engineer",
        job=JobDescriptionInput(
            title="Backend Engineer",
            company="Acme",
            raw_text="We need Python FastAPI and PostgreSQL for our API platform.",
        ),
    )
    result = score_match(req)
    assert result.model_dump() == {
        "score": 44.9,
        "skill_match": 55.4,
        "experience_match": 49.0,
        "keyword_ats_match": 23.1,
        "context_fit": 39.2,
        "missing_skills": [
            "acme",
            "and",
            "api",
            "backend",
            "for",
            "need",
            "our",
            "platform",
            "postgresql",
        ],
        "suggestions": [
            "Surface more matching skills from your experience in the resume.",
            "Mirror important phrases from the job description (honestly) in your summary or bullets.",
        ],
        "weak_areas": ["Experience depth vs role"],
    }
