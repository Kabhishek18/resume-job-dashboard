from typing import List, Literal, Optional

from pydantic import BaseModel, Field


class ParseResumeRequest(BaseModel):
    raw_text: str = Field(..., min_length=1, description="Resume plain text (MVP; PDF upload not supported)")


class ParsedResume(BaseModel):
    skills: List[str]
    experience_years_est: Optional[float] = None
    education: List[str] = Field(default_factory=list)
    tools: List[str] = Field(default_factory=list)
    keywords: List[str] = Field(default_factory=list)


class ParseResumeResponse(BaseModel):
    parsed: ParsedResume
    cleaned_text_preview: str = Field(..., description="First ~500 chars after cleaning")


class ParseResumeApiV1(ParseResumeResponse):
    version: Literal["v1"] = Field(default="v1", description="API contract version")
