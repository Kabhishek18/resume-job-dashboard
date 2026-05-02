"""User tracking row for jobs added to board."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.aggregated_job import AggregatedJob


class JobBoardEntry(Base):
    __tablename__ = "job_board_entries"
    __table_args__ = (UniqueConstraint("user_id", "job_id", name="uq_job_board_user_job"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"), index=True)
    job_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("aggregated_jobs.id", ondelete="CASCADE"), index=True
    )

    status: Mapped[str] = mapped_column(String(24), nullable=False, default="new")
    notes: Mapped[str] = mapped_column(Text, default="")
    follow_up_date: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    recruiter_name: Mapped[str] = mapped_column(String(200), default="")
    recruiter_email: Mapped[str] = mapped_column(String(255), default="")
    applied_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    job: Mapped["AggregatedJob"] = relationship("AggregatedJob", back_populates="board_entries")
