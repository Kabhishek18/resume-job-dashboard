from typing import Any, Optional, Union

from pydantic import BaseModel, Field, HttpUrl, field_validator


class JobDescriptionInput(BaseModel):
    title: Optional[str] = Field(default=None, description="Job title if known")
    company: Optional[str] = Field(default=None)
    raw_text: str = Field(..., min_length=1, description="Full job description text")
    url: Optional[HttpUrl] = Field(default=None, description="Source job posting URL")

    @field_validator("url", mode="before")
    @classmethod
    def coerce_empty_url(cls, v: Any) -> Union[str, None]:
        if v is None:
            return None
        if isinstance(v, str) and not v.strip():
            return None
        return v
