from __future__ import annotations

from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.deps import get_current_user
from app.db.session import get_db
from app.models.aggregated_job import AggregatedJob
from app.models.job_board_entry import JobBoardEntry
from app.models.job_search_profile import JobSearchProfile
from app.models.job_search_run import JobSearchRun
from app.models.job_source import JobSource
from app.models.user import User
from app.schemas.jobs_aggregate import (
    AggregatedJobRowApi,
    BoardEntryApi,
    BoardEntryCreate,
    BoardEntryPatch,
    JobSearchRunApi,
    SearchProfileApi,
    SearchProfileCreate,
    SearchProfilePatch,
)
from app.services.jobs.csv_export import aggregated_jobs_to_csv_rows
from app.services.jobs.job_scheduler import reschedule_all_profiles
from app.services.jobs.jobs_api_payloads import board_entry_to_api, job_search_run_to_api
from app.services.jobs.run_service import run_job_search_task

router = APIRouter(prefix="/jobs", tags=["jobs-aggregator"])

RESULTS_WANTED_MIN = 1
RESULTS_WANTED_MAX = 200


def _validate_results_wanted(v: int | None) -> None:
    if v is None:
        return
    if v < RESULTS_WANTED_MIN or v > RESULTS_WANTED_MAX:
        raise AppError(
            "VALIDATION",
            f"results_wanted must be between {RESULTS_WANTED_MIN} and {RESULTS_WANTED_MAX}",
            status_code=400,
        )


def _profile_api(p: JobSearchProfile) -> SearchProfileApi:
    return SearchProfileApi(
        id=p.id,
        user_id=p.user_id,
        name=p.name,
        keywords=p.keywords,
        locations=p.locations,
        experience_levels=p.experience_levels,
        employment_types=p.employment_types,
        remote_only=p.remote_only,
        selected_portals=list(p.selected_portals or []),
        schedule_enabled=p.schedule_enabled,
        schedule_frequency=p.schedule_frequency,
        schedule_time=p.schedule_time,
        schedule_timezone=p.schedule_timezone,
        results_wanted=p.results_wanted,
        created_at=p.created_at,
        updated_at=p.updated_at,
    )


@router.post("/searches", response_model=SearchProfileApi)
def create_search_profile(
    body: SearchProfileCreate,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
) -> SearchProfileApi:
    _validate_results_wanted(body.results_wanted)
    p = JobSearchProfile(
        user_id=user.id,
        name=body.name.strip(),
        keywords=body.keywords or "",
        locations=body.locations or "",
        experience_levels=body.experience_levels or "",
        employment_types=body.employment_types or "",
        remote_only=body.remote_only,
        selected_portals=body.selected_portals or [],
        schedule_enabled=body.schedule_enabled,
        schedule_frequency=body.schedule_frequency,
        schedule_time=body.schedule_time,
        schedule_timezone=body.schedule_timezone or "UTC",
        results_wanted=body.results_wanted,
    )
    db.add(p)
    db.commit()
    db.refresh(p)
    reschedule_all_profiles()
    return _profile_api(p)


@router.get("/searches", response_model=list[SearchProfileApi])
def list_search_profiles(
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
) -> list[SearchProfileApi]:
    rows = db.query(JobSearchProfile).filter(JobSearchProfile.user_id == user.id).order_by(JobSearchProfile.id.desc())
    return [_profile_api(p) for p in rows]


def _require_profile_owned(db: Session, user_id: int, pid: int) -> JobSearchProfile:
    p = db.get(JobSearchProfile, pid)
    if p is None or p.user_id != user_id:
        raise AppError("NOT_FOUND", "Search profile not found", status_code=404)
    return p


@router.patch("/searches/{search_id}", response_model=SearchProfileApi)
def patch_search_profile(
    search_id: int,
    body: SearchProfilePatch,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
) -> SearchProfileApi:
    p = _require_profile_owned(db, user.id, search_id)
    patch_data = body.model_dump(exclude_unset=True)
    for field in (
        "name",
        "keywords",
        "locations",
        "experience_levels",
        "employment_types",
        "remote_only",
        "selected_portals",
        "schedule_enabled",
        "schedule_frequency",
        "schedule_time",
        "schedule_timezone",
    ):
        if field not in patch_data:
            continue
        v = patch_data[field]
        if field == "name" and isinstance(v, str):
            v = v.strip()
        setattr(p, field, v)
    if "results_wanted" in patch_data:
        rw = patch_data["results_wanted"]
        _validate_results_wanted(rw)
        p.results_wanted = rw
    db.commit()
    db.refresh(p)
    reschedule_all_profiles()
    return _profile_api(p)


@router.delete("/searches/{search_id}")
def delete_search_profile(
    search_id: int,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
) -> dict[str, str]:
    p = _require_profile_owned(db, user.id, search_id)
    db.delete(p)
    db.commit()
    reschedule_all_profiles()
    return {"ok": "deleted"}


@router.post("/searches/{search_id}/run", response_model=JobSearchRunApi)
def run_search_manual(
    search_id: int,
    background_tasks: BackgroundTasks,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
) -> JobSearchRunApi:
    p = _require_profile_owned(db, user.id, search_id)
    run = JobSearchRun(
        user_id=user.id,
        search_profile_id=p.id,
        trigger_mode="manual",
        status="queued",
        summary_json={},
    )
    db.add(run)
    db.commit()
    db.refresh(run)
    background_tasks.add_task(run_job_search_task, run.id)
    return job_search_run_to_api(run)


def _require_run_owned(db: Session, user_id: int, rid: int) -> JobSearchRun:
    run = db.get(JobSearchRun, rid)
    if run is None or run.user_id != user_id:
        raise AppError("NOT_FOUND", "Run not found", status_code=404)
    return run


def _aggregated_jobs_for_run(db: Session, user_id: int, run: JobSearchRun) -> list[AggregatedJob]:
    return (
        db.query(AggregatedJob)
        .join(JobSource, JobSource.job_id == AggregatedJob.id)
        .filter(JobSource.run_id == run.id, AggregatedJob.user_id == user_id)
        .distinct()
        .all()
    )


def _board_entries_by_job_id(
    db: Session, user_id: int, job_ids: list[int]
) -> dict[int, JobBoardEntry]:
    if not job_ids:
        return {}
    rows = (
        db.query(JobBoardEntry)
        .filter(JobBoardEntry.user_id == user_id, JobBoardEntry.job_id.in_(job_ids))
        .all()
    )
    return {e.job_id: e for e in rows}


def _source_counts_for_run(
    db: Session, run_id: int, job_ids: list[int]
) -> dict[int, int]:
    if not job_ids:
        return {}
    q = (
        db.query(JobSource.job_id, func.count(JobSource.id))
        .filter(JobSource.run_id == run_id, JobSource.job_id.in_(job_ids))
        .group_by(JobSource.job_id)
        .all()
    )
    return {int(jid): int(cnt) for jid, cnt in q}


@router.get("/runs/{run_id}", response_model=JobSearchRunApi)
def get_run(
    run_id: int,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
) -> JobSearchRunApi:
    return job_search_run_to_api(_require_run_owned(db, user.id, run_id))


@router.get("/runs/{run_id}/results", response_model=list[AggregatedJobRowApi])
def run_results(
    run_id: int,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
) -> list[AggregatedJobRowApi]:
    run = _require_run_owned(db, user.id, run_id)

    rows = _aggregated_jobs_for_run(db, user.id, run)
    job_ids = [j.id for j in rows]
    board_by_job = _board_entries_by_job_id(db, user.id, job_ids)
    src_counts = _source_counts_for_run(db, run.id, job_ids)

    out: list[AggregatedJobRowApi] = []
    for job in rows:
        board_row = board_by_job.get(job.id)
        src_count = src_counts.get(job.id, 0)
        out.append(
            AggregatedJobRowApi(
                id=job.id,
                portal=job.portal,
                title=job.title,
                company=job.company,
                location=job.location,
                posted_at=job.posted_at,
                salary_text=job.salary_text,
                apply_url=job.apply_url,
                description_snippet=((job.description_snippet or "")[:2000]),
                duplicate_count=job.duplicate_count,
                board_status=board_row.status if board_row else None,
                source_count=max(1, src_count),
            )
        )
    return out


@router.get("/runs/{run_id}/results.csv")
def run_results_csv(
    run_id: int,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
) -> dict[str, str]:
    # Return filename hint via Response headers in caller — use StreamingResponse inline
    from fastapi.responses import Response

    run = _require_run_owned(db, user.id, run_id)

    rows = _aggregated_jobs_for_run(db, user.id, run)
    job_ids = [j.id for j in rows]
    board_by_job = _board_entries_by_job_id(db, user.id, job_ids)
    src_counts = _source_counts_for_run(db, run.id, job_ids)

    payloads: list[dict] = []
    for job in rows:
        board_row = board_by_job.get(job.id)
        src_count = src_counts.get(job.id, 0)
        payloads.append(
            {
                "id": job.id,
                "portal": job.portal,
                "title": job.title,
                "company": job.company,
                "location": job.location,
                "posted_at": job.posted_at or "",
                "salary_text": job.salary_text,
                "apply_url": job.apply_url,
                "description_snippet": (job.description_snippet or "")[:2000],
                "duplicate_count": job.duplicate_count,
                "board_status": board_row.status if board_row else "",
                "source_count": max(1, src_count),
            }
        )

    body = aggregated_jobs_to_csv_rows(payloads)
    return Response(
        content=body,
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="run-{run_id}-results.csv"'},
    )


@router.post("/board", response_model=BoardEntryApi)
def board_add(
    body: BoardEntryCreate,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
) -> BoardEntryApi:
    job = db.get(AggregatedJob, body.job_id)
    if job is None or job.user_id != user.id:
        raise AppError("NOT_FOUND", "Job not found", status_code=404)

    existing = (
        db.query(JobBoardEntry)
        .filter(JobBoardEntry.user_id == user.id, JobBoardEntry.job_id == body.job_id)
        .first()
    )
    if existing is not None:
        return board_entry_to_api(db, existing, job)

    entry = JobBoardEntry(
        user_id=user.id,
        job_id=job.id,
        status="saved",
        notes="",
        follow_up_date=None,
        recruiter_name="",
        recruiter_email="",
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return board_entry_to_api(db, entry, job)


@router.get("/board", response_model=list[BoardEntryApi])
def board_list(
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
) -> list[BoardEntryApi]:
    entries = (
        db.query(JobBoardEntry).filter(JobBoardEntry.user_id == user.id).order_by(JobBoardEntry.updated_at.desc())
    )
    out: list[BoardEntryApi] = []
    for e in entries:
        job = db.get(AggregatedJob, e.job_id)
        if job is None:
            continue
        out.append(board_entry_to_api(db, e, job))
    return out


def _require_board_owned(db: Session, user_id: int, entry_id: int) -> tuple[JobBoardEntry, AggregatedJob]:
    e = db.get(JobBoardEntry, entry_id)
    if e is None or e.user_id != user_id:
        raise AppError("NOT_FOUND", "Board entry not found", status_code=404)
    job = db.get(AggregatedJob, e.job_id)
    if job is None:
        raise AppError("NOT_FOUND", "Job missing", status_code=404)
    return e, job


@router.patch("/board/{entry_id}", response_model=BoardEntryApi)
def board_patch(
    entry_id: int,
    body: BoardEntryPatch,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
) -> BoardEntryApi:
    e, job = _require_board_owned(db, user.id, entry_id)
    if body.status is not None:
        e.status = body.status.strip()
    if body.notes is not None:
        e.notes = body.notes
    if body.follow_up_date is not None:
        e.follow_up_date = body.follow_up_date
    if body.recruiter_name is not None:
        e.recruiter_name = body.recruiter_name.strip()[:200]
    if body.recruiter_email is not None:
        e.recruiter_email = body.recruiter_email.strip()[:255]
    if body.applied_at is not None:
        e.applied_at = body.applied_at
    e.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(e)
    return board_entry_to_api(db, e, job)


@router.delete("/board/{entry_id}")
def board_delete(
    entry_id: int,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
) -> dict[str, str]:
    e, _ = _require_board_owned(db, user.id, entry_id)
    db.delete(e)
    db.commit()
    return {"ok": "deleted"}
