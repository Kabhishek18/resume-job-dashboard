"""Serialize job aggregation models to API payloads (no FastAPI imports)."""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.aggregated_job import AggregatedJob
from app.models.job_board_entry import JobBoardEntry
from app.models.job_search_run import JobSearchRun
from app.schemas.jobs_aggregate import BoardEntryApi, JobSearchRunApi


def board_entry_to_api(_db: Session, entry: JobBoardEntry, job: AggregatedJob) -> BoardEntryApi:
    _ = _db
    return BoardEntryApi(
        id=entry.id,
        user_id=entry.user_id,
        job_id=entry.job_id,
        status=entry.status,
        notes=entry.notes,
        follow_up_date=entry.follow_up_date,
        recruiter_name=entry.recruiter_name,
        recruiter_email=entry.recruiter_email,
        applied_at=entry.applied_at,
        updated_at=entry.updated_at,
        title=job.title,
        company=job.company,
        portal=job.portal,
        apply_url=job.apply_url,
    )


def job_search_run_to_api(r: JobSearchRun) -> JobSearchRunApi:
    return JobSearchRunApi(
        id=r.id,
        user_id=r.user_id,
        search_profile_id=r.search_profile_id,
        trigger_mode=r.trigger_mode,
        status=r.status,
        started_at=r.started_at,
        finished_at=r.finished_at,
        summary_json=r.summary_json or {},
        scheduled_fire_at=r.scheduled_fire_at,
    )
