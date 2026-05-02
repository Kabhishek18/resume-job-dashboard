"""Per-observation source row for aggregated job audit trail."""

from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import DateTime, ForeignKey, Integer, String, func
from sqlalchemy.dialects.sqlite import JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.aggregated_job import AggregatedJob


class JobSource(Base):
    __tablename__ = "job_sources"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    job_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("aggregated_jobs.id", ondelete="CASCADE"), index=True
    )
    run_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("job_search_runs.id", ondelete="CASCADE"), index=True
    )

    portal: Mapped[str] = mapped_column(String(32), nullable=False)
    source_url: Mapped[str] = mapped_column(String(2000), default="")
    apply_url: Mapped[str] = mapped_column(String(2000), default="")
    collected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    raw_meta: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)

    job: Mapped["AggregatedJob"] = relationship("AggregatedJob", back_populates="sources")
