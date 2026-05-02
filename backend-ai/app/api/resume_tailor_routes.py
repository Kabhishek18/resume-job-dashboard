from fastapi import APIRouter

from app.schemas.tailor_contract import TailorApiV1, TailorRequest
from app.services.tailoring import get_tailoring_service

router = APIRouter(prefix="/resume", tags=["resume"])


@router.post("/tailor", response_model=TailorApiV1)
def tailor_resume(body: TailorRequest) -> TailorApiV1:
    service = get_tailoring_service()
    return service.tailor(body)
