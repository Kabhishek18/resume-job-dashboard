from app.core.errors import AppError
from app.schemas.tailor_contract import TailorApiV1, TailorRequest

from .base import TailoringService


class LLMTailoringService(TailoringService):
    def tailor(self, body: TailorRequest) -> TailorApiV1:
        raise AppError(
            "LLM_TAILOR_NOT_CONFIGURED",
            "LLM tailoring provider is not configured yet.",
            status_code=501,
        )
