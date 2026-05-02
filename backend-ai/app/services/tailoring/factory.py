from app.core.config import settings

from .base import TailoringService
from .llm import LLMTailoringService
from .stub import StubTailoringService


def get_tailoring_service() -> TailoringService:
    if settings.tailoring_provider == "llm":
        return LLMTailoringService()
    return StubTailoringService()
