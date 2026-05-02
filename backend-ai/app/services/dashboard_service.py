"""Build dashboard summary for the authenticated user."""

from __future__ import annotations

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.services.jobs.jobs_api_payloads import board_entry_to_api, job_search_run_to_api
from app.models.aggregated_job import AggregatedJob
from app.models.job_board_entry import JobBoardEntry
from app.models.job_search_run import JobSearchRun
from app.schemas.dashboard import DashboardSummaryApi


def build_dashboard_summary(db: Session, user_id: int) -> DashboardSummaryApi:
    counts_rows = (
        db.query(JobBoardEntry.status, func.count(JobBoardEntry.id))
        .filter(JobBoardEntry.user_id == user_id)
        .group_by(JobBoardEntry.status)
        .all()
    )
    board_counts = {str(status): int(n) for status, n in counts_rows}

    total_tracked = (
        db.query(func.count(JobBoardEntry.id)).filter(JobBoardEntry.user_id == user_id).scalar() or 0
    )

    entries = (
        db.query(JobBoardEntry)
        .filter(JobBoardEntry.user_id == user_id)
        .order_by(JobBoardEntry.updated_at.desc())
        .limit(12)
        .all()
    )

    recent = []
    for e in entries:
        job = db.get(AggregatedJob, e.job_id)
        if job is None:
            continue
        recent.append(board_entry_to_api(db, e, job))

    run_row = (
        db.query(JobSearchRun)
        .filter(JobSearchRun.user_id == user_id)
        .order_by(JobSearchRun.id.desc())
        .first()
    )
    most_recent = job_search_run_to_api(run_row) if run_row is not None else None

    return DashboardSummaryApi(
        board_counts_by_status=board_counts,
        total_tracked_jobs=int(total_tracked),
        recent_board_entries=recent,
        most_recent_run=most_recent,
    )
