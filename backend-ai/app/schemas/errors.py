from typing import Any, List, Optional

from pydantic import BaseModel, Field


class ErrorBody(BaseModel):
    code: str = Field(..., description="Stable machine-readable error code")
    message: str = Field(..., description="Human-readable message")
    details: Optional[List[Any]] = Field(default=None, description="Optional validation or extra context")


class ErrorEnvelope(BaseModel):
    error: ErrorBody
