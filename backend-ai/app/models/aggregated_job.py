"""Deduped aggregated job row per user."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.job_board_entry import JobBoardEntry
    from app.models.job_search_run import JobSearchRun
    from app.models.job_source import JobSource


class AggregatedJob(Base):
    __tablename__ = "aggregated_jobs"
    __table_args__ = (UniqueConstraint("user_id", "dedupe_key", name="uq_aggregated_jobs_user_dedupe"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"), index=True)
    latest_run_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("job_search_runs.id", ondelete="SET NULL"), nullable=True
    )

    title: Mapped[str] = mapped_column(String(500), nullable=False, default="")
    company: Mapped[str] = mapped_column(String(300), nullable=False, default="")
    location: Mapped[str] = mapped_column(String(300), nullable=False, default="")
    salary_text: Mapped[str] = mapped_column(String(300), nullable=False, default="")
    posted_at: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    description_snippet: Mapped[str] = mapped_column(Text, default="")

    apply_url: Mapped[str] = mapped_column(String(2000), nullable=False, default="")
    canonical_apply_url: Mapped[str] = mapped_column(String(2000), nullable=False, default="", index=True)
    portal: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    external_job_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    dedupe_key: Mapped[str] = mapped_column(String(512), nullable=False, index=True)
    duplicate_count: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    first_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    latest_run_rel: Mapped[Optional["JobSearchRun"]] = relationship(
        "JobSearchRun", foreign_keys=[latest_run_id]
    )
    sources: Mapped[List["JobSource"]] = relationship(
        "JobSource", back_populates="job", cascade="all, delete-orphan"
    )
    board_entries: Mapped[List["JobBoardEntry"]] = relationship(
        "JobBoardEntry", back_populates="job", cascade="all, delete-orphan"
    )
