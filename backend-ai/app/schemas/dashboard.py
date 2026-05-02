"""Dashboard API response models."""

from __future__ import annotations

from typing import Dict, List, Optional

from pydantic import BaseModel, Field

from app.schemas.jobs_aggregate import BoardEntryApi, JobSearchRunApi


class DashboardSummaryApi(BaseModel):
    board_counts_by_status: Dict[str, int] = Field(default_factory=dict)
    total_tracked_jobs: int = 0
    recent_board_entries: List[BoardEntryApi] = Field(default_factory=list)
    most_recent_run: Optional[JobSearchRunApi] = None
