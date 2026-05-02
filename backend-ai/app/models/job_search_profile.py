"""Saved job search configurations per user."""

from datetime import datetime
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.sqlite import JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.job_search_run import JobSearchRun


class JobSearchProfile(Base):
    __tablename__ = "job_search_profiles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"), index=True)

    name: Mapped[str] = mapped_column(String(200), nullable=False)
    keywords: Mapped[str] = mapped_column(Text, default="")
    locations: Mapped[str] = mapped_column(Text, default="")
    experience_levels: Mapped[str] = mapped_column(Text, default="")
    employment_types: Mapped[str] = mapped_column(Text, default="")
    remote_only: Mapped[bool] = mapped_column(Boolean, default=False)

    selected_portals: Mapped[List[str]] = mapped_column(JSON, nullable=False)

    schedule_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    schedule_frequency: Mapped[Optional[str]] = mapped_column(String(16), nullable=True)
    schedule_time: Mapped[Optional[str]] = mapped_column(String(8), nullable=True)
    schedule_timezone: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    runs: Mapped[List["JobSearchRun"]] = relationship(
        "JobSearchRun", back_populates="profile", cascade="all, delete-orphan"
    )
