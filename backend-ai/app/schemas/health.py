from typing import Literal

from pydantic import BaseModel, Field


class HealthApiV1(BaseModel):
    version: Literal["v1"] = Field(default="v1", description="API contract version")
    status: Literal["ok"] = Field(default="ok")
