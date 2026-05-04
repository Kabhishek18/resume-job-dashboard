from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, EmailStr, Field


class ProfileApiV1(BaseModel):
    version: Literal["v1"] = "v1"
    id: int
    email: EmailStr
    name: str
    resume_text: Optional[str] = None
    resume_updated_at: Optional[datetime] = None


class UpdateProfileNameBody(BaseModel):
    name: str = Field(..., min_length=1, max_length=120)


class UpdateResumeBody(BaseModel):
    resume_text: str = Field(..., min_length=1, max_length=500_000)
