"""Orchestrate collector runs and persist aggregated + source rows."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

from app.models.aggregated_job import AggregatedJob
from app.models.job_search_profile import JobSearchProfile
from app.models.job_search_run import JobSearchRun
from app.models.job_source import JobSource
from app.services.jobs.canonical_url import canonicalize_apply_url
from app.services.jobs.collectors import CollectedRow, run_collectors_for_profile
from app.services.jobs.dedupe import external_dedupe_key, fingerprint_dedupe_key, url_dedupe_key


def profile_to_collect_params(profile: JobSearchProfile) -> dict[str, Any]:
    return {
        "keywords": profile.keywords,
        "locations": profile.locations,
        "experience_levels": profile.experience_levels,
        "employment_types": profile.employment_types,
        "remote_only": profile.remote_only,
        "selected_portals": profile.selected_portals or [],
    }


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def ingest_collected(session: Session, user_id: int, run_id: int, row: CollectedRow) -> AggregatedJob:
    canon = canonicalize_apply_url(row.apply_url)
    fp_key = fingerprint_dedupe_key(
        title=row.title, company=row.company, location=row.location, posted_at=row.posted_at
    )

    existing: AggregatedJob | None = None
    if canon:
        existing = (
            session.query(AggregatedJob)
            .filter(
                AggregatedJob.user_id == user_id,
                AggregatedJob.canonical_apply_url == canon,
            )
            .first()
        )

    if existing is None and row.external_job_id:
        existing = (
            session.query(AggregatedJob)
            .filter(
                AggregatedJob.user_id == user_id,
                AggregatedJob.portal == row.portal,
                AggregatedJob.external_job_id == row.external_job_id,
            )
            .first()
        )

    if existing is None:
        existing = (
            session.query(AggregatedJob)
            .filter(
                AggregatedJob.user_id == user_id,
                AggregatedJob.dedupe_key == fp_key,
            )
            .first()
        )

    now = _utcnow()

    def _truncate(s: str, n: int) -> str:
        return (s or "")[:n]

    if existing:
        existing.duplicate_count += 1
        existing.last_seen_at = now
        existing.latest_run_id = run_id
        if canon and not existing.canonical_apply_url:
            existing.canonical_apply_url = canon
            existing.apply_url = _truncate(row.apply_url, 2000) or existing.apply_url
        if row.title.strip() and (not existing.title.strip() or len(row.title) > len(existing.title)):
            existing.title = _truncate(row.title, 500)
        if row.company.strip():
            existing.company = _truncate(row.company, 300)
        if row.location.strip():
            existing.location = _truncate(row.location, 300)
        if row.salary_text.strip():
            existing.salary_text = _truncate(row.salary_text, 300)
        if row.posted_at:
            existing.posted_at = row.posted_at[:64]
        if row.description_snippet.strip():
            existing.description_snippet = row.description_snippet
        session.add(existing)
        session.flush()
        job = existing
    else:
        uk = url_dedupe_key(canon)
        ek = external_dedupe_key(row.portal, row.external_job_id)
        primary_key = uk or ek or fp_key
        job = AggregatedJob(
            user_id=user_id,
            latest_run_id=run_id,
            title=_truncate(row.title, 500) or "(no title)",
            company=_truncate(row.company, 300),
            location=_truncate(row.location, 300),
            salary_text=_truncate(row.salary_text, 300),
            posted_at=row.posted_at[:64] if row.posted_at else None,
            description_snippet=row.description_snippet or "",
            apply_url=_truncate(row.apply_url, 2000),
            canonical_apply_url=canon,
            portal=row.portal,
            external_job_id=row.external_job_id,
            dedupe_key=primary_key or fp_key,
            duplicate_count=1,
            first_seen_at=now,
            last_seen_at=now,
        )
        session.add(job)
        session.flush()

    session.add(
        JobSource(
            job_id=job.id,
            run_id=run_id,
            portal=row.portal,
            source_url=_truncate(row.source_url, 2000),
            apply_url=_truncate(row.apply_url, 2000),
            raw_meta=row.raw_meta or {},
        )
    )
    return job


def execute_run(session: Session, run_id: int) -> None:
    run = session.get(JobSearchRun, run_id)
    if run is None:
        return
    profile = session.get(JobSearchProfile, run.search_profile_id)
    if profile is None:
        run.status = "failed"
        run.summary_json = {"error": "search_profile_missing"}
        run.started_at = _utcnow()
        run.finished_at = run.started_at
        session.commit()
        return

    run.status = "running"
    run.started_at = _utcnow()
    session.commit()

    params = profile_to_collect_params(profile)
    rows, portal_outcomes, collector_note = run_collectors_for_profile(params)

    for r in rows:
        ingest_collected(session, run.user_id, run_id, r)

    summary_portals: dict[str, dict[str, Any]] = {
        portal: {"rows": outcome.row_count, "state": outcome.state}
        for portal, outcome in portal_outcomes.items()
    }

    any_unavailable = any(o.state == "unavailable" for o in portal_outcomes.values())
    status = "completed"
    if any_unavailable:
        status = "partial"

    outcome_flag = "no_results" if not rows else "has_results"

    summary_body: dict[str, Any] = {"portals": summary_portals, "outcome": outcome_flag}
    if collector_note:
        summary_body["collector_note"] = collector_note

    run.status = status
    run.finished_at = _utcnow()
    run.summary_json = summary_body
    session.commit()


def run_job_search_task(run_id: int) -> None:
    from app.db.session import SessionLocal

    db = SessionLocal()
    try:
        try:
            execute_run(db, run_id)
        except Exception as exc:  # noqa: BLE001
            db.rollback()
            run = db.get(JobSearchRun, run_id)
            if run is not None:
                run.status = "failed"
                run.finished_at = _utcnow()
                run.started_at = run.started_at or run.finished_at
                summary = dict(run.summary_json or {})
                summary["error"] = type(exc).__name__
                summary["message"] = str(exc)[:500]
                run.summary_json = summary
                db.add(run)
                db.commit()
    finally:
        db.close()
