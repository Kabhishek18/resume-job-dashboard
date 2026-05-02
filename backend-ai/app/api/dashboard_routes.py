from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.dashboard import DashboardSummaryApi
from app.services.dashboard_service import build_dashboard_summary

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/summary", response_model=DashboardSummaryApi)
def dashboard_summary(
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
) -> DashboardSummaryApi:
    return build_dashboard_summary(db, user.id)
