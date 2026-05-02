"""One execution of a job search profile."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Any, Dict, Optional

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.sqlite import JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.job_search_profile import JobSearchProfile


class JobSearchRun(Base):
    __tablename__ = "job_search_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"), index=True)
    search_profile_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("job_search_profiles.id", ondelete="CASCADE"), index=True
    )

    trigger_mode: Mapped[str] = mapped_column(String(16), nullable=False)  # manual|scheduled
    status: Mapped[str] = mapped_column(String(24), nullable=False, default="queued")

    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    summary_json: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict)

    scheduled_fire_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True, index=True
    )

    profile: Mapped["JobSearchProfile"] = relationship("JobSearchProfile", back_populates="runs")
