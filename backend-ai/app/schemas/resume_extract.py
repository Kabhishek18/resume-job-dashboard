from typing import Literal

from pydantic import BaseModel


class ExtractResumeFileApiV1(BaseModel):
    version: Literal["v1"] = "v1"
    plain_text: str
    warnings: list[str]
