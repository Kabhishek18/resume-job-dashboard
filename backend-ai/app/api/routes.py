from fastapi import APIRouter

from app.api import (
    auth_routes,
    dashboard_routes,
    job_routes,
    jobs_aggregate_routes,
    profile_routes,
    resume_tailor_routes,
)
from app.schemas.health import HealthApiV1
from app.schemas.match import MatchApiV1, MatchRequest
from app.schemas.match_v2 import MatchApiV2
from app.schemas.resume import ParseResumeApiV1, ParseResumeRequest
from app.services import matcher, match_v2_service, parser

router = APIRouter()

router.include_router(auth_routes.router, prefix="/auth")
router.include_router(profile_routes.router)
router.include_router(dashboard_routes.router)
router.include_router(job_routes.router)
router.include_router(jobs_aggregate_routes.router)
router.include_router(resume_tailor_routes.router)


@router.get("/health", response_model=HealthApiV1)
def health() -> HealthApiV1:
    return HealthApiV1()


@router.post("/parse", response_model=ParseResumeApiV1)
def parse(body: ParseResumeRequest) -> ParseResumeApiV1:
    result = parser.parse_resume(body)
    return ParseResumeApiV1(**result.model_dump())


@router.post("/match", response_model=MatchApiV1)
def match(body: MatchRequest) -> MatchApiV1:
    result = matcher.score_match(body)
    return MatchApiV1(**result.model_dump())


@router.post("/match/v2", response_model=MatchApiV2)
def match_v2(body: MatchRequest) -> MatchApiV2:
    return match_v2_service.score_match_v2(body)
