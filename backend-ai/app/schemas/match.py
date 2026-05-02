from typing import List, Literal

from pydantic import BaseModel, Field

from app.schemas.job import JobDescriptionInput


class MatchRequest(BaseModel):
    """MVP: paste resume as plain text. File upload is not supported."""

    raw_resume_text: str = Field(..., min_length=1, description="Full resume plain text")
    job: JobDescriptionInput


class MatchResult(BaseModel):
    """Core match payload (no API version). Returned scores are deterministic for fixed input."""

    score: float = Field(..., ge=0, le=100)
    skill_match: float = Field(..., ge=0, le=100)
    experience_match: float = Field(..., ge=0, le=100)
    keyword_ats_match: float = Field(..., ge=0, le=100)
    context_fit: float = Field(..., ge=0, le=100)
    missing_skills: List[str]
    suggestions: List[str]
    weak_areas: List[str] = Field(default_factory=list)


class MatchApiV1(MatchResult):
    version: Literal["v1"] = Field(default="v1", description="API contract version")
