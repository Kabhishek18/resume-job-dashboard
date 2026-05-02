from typing import Literal

from pydantic import BaseModel, Field

from app.schemas.job import JobDescriptionInput


class MatchRequestV2(BaseModel):
    raw_resume_text: str = Field(..., min_length=1, description="Full resume plain text")
    job: JobDescriptionInput


class BandedBucket(BaseModel):
    score: float = Field(..., ge=0, le=100)
    band: Literal["weak", "needs_work", "strong"]
    reasons: list[str] = Field(default_factory=list)


class MatchApiV2(BaseModel):
    version: Literal["v2"] = "v2"
    ats_compatibility: BandedBucket
    job_match: BandedBucket
    semantic_similarity: float = Field(..., ge=0, le=100)
    exact_skill_overlap: float = Field(..., ge=0, le=100)
    lexical_match: float = Field(..., ge=0, le=100)
    title_alignment: float = Field(..., ge=0, le=100)
    experience_alignment: float = Field(..., ge=0, le=100)
    missing_hard_skills: list[str] = Field(default_factory=list)
    semantic_matches: list[str] = Field(default_factory=list)
    strengths: list[str] = Field(default_factory=list)
    actions: list[str] = Field(default_factory=list)
    why_this_score: list[str] = Field(default_factory=list)


class MatchSnapshotV2(BaseModel):
    version: Literal["v2"] = "v2"
    ats_score: float = Field(..., ge=0, le=100)
    job_match_score: float = Field(..., ge=0, le=100)
    missing_hard_skills: list[str]
    semantic_matches: list[str]
    strengths: list[str]
    actions: list[str]
    why_this_score: list[str]


def snapshot_from_match_api_v2(api: MatchApiV2) -> MatchSnapshotV2:
    return MatchSnapshotV2(
        ats_score=api.ats_compatibility.score,
        job_match_score=api.job_match.score,
        missing_hard_skills=list(api.missing_hard_skills),
        semantic_matches=list(api.semantic_matches),
        strengths=list(api.strengths),
        actions=list(api.actions),
        why_this_score=list(api.why_this_score),
    )


def band_from_score(score: float) -> Literal["weak", "needs_work", "strong"]:
    if score <= 39:
        return "weak"
    if score <= 69:
        return "needs_work"
    return "strong"
