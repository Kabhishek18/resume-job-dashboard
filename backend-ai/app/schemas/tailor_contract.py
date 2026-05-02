from typing import List, Literal, Optional

from pydantic import BaseModel, Field

from app.schemas.job import JobDescriptionInput
from app.schemas.match import MatchResult
from app.schemas.match_v2 import MatchSnapshotV2


class TailorRequest(BaseModel):
    resume_text: str = Field(..., min_length=1, max_length=500_000)
    job: JobDescriptionInput
    include_cover_letter: bool = False
    match_snapshot: Optional[MatchResult] = None
    match_snapshot_v2: Optional[MatchSnapshotV2] = None


class TailorReview(BaseModel):
    add: List[str]
    remove: List[str]
    improve: List[str]


class TailoredResumeOut(BaseModel):
    summary: str
    bullets: List[str]


class TailorApiV1(BaseModel):
    version: Literal["v1"] = "v1"
    provider_mode: Literal["stub", "llm"]
    review: TailorReview
    tailored_resume: TailoredResumeOut
    cover_letter: Optional[str] = None
