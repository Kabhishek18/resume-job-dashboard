"""APScheduler bootstrap for saved job searches."""

from __future__ import annotations

import logging
import os
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from app.services.jobs.run_service import run_job_search_task

logger = logging.getLogger(__name__)
_scheduler: BackgroundScheduler | None = None


def is_scheduler_disabled() -> bool:
    return os.environ.get("JOBS_SCHEDULER_DISABLED", "").lower() in ("1", "true", "yes")


def shutdown_scheduler() -> None:
    global _scheduler
    if _scheduler is not None:
        try:
            _scheduler.shutdown(wait=False)
        except Exception as exc:  # noqa: BLE001
            logger.warning("scheduler_shutdown %s", exc)
        _scheduler = None


def scheduled_search_fire(profile_id: int) -> None:
    """Create idempotent scheduled run + background execute."""
    from app.db.session import SessionLocal
    from app.models.job_search_profile import JobSearchProfile
    from app.models.job_search_run import JobSearchRun

    fire_at = datetime.now(timezone.utc).replace(second=0, microsecond=0)

    db = SessionLocal()
    try:
        prof = db.get(JobSearchProfile, profile_id)
        if prof is None or not prof.schedule_enabled:
            return
        existing = (
            db.query(JobSearchRun)
            .filter(
                JobSearchRun.search_profile_id == profile_id,
                JobSearchRun.scheduled_fire_at == fire_at,
                JobSearchRun.trigger_mode == "scheduled",
            )
            .first()
        )
        if existing is not None:
            return

        run = JobSearchRun(
            user_id=prof.user_id,
            search_profile_id=prof.id,
            trigger_mode="scheduled",
            status="queued",
            summary_json={},
            scheduled_fire_at=fire_at,
        )
        db.add(run)
        db.commit()
        db.refresh(run)
        rid = run.id
    finally:
        db.close()

    run_job_search_task(rid)


def reschedule_all_profiles() -> None:
    """Reload cron jobs from DB."""
    global _scheduler
    if _scheduler is None or is_scheduler_disabled():
        return

    _scheduler.remove_all_jobs()

    from app.db.session import SessionLocal
    from app.models.job_search_profile import JobSearchProfile

    db = SessionLocal()
    try:
        profiles = db.query(JobSearchProfile).filter(JobSearchProfile.schedule_enabled.is_(True)).all()
        for prof in profiles:
            if prof.schedule_frequency not in ("daily", "weekly"):
                continue
            tzname = prof.schedule_timezone or "UTC"
            try:
                tz = ZoneInfo(tzname)
            except Exception:  # noqa: BLE001
                tz = ZoneInfo("UTC")
            hm = prof.schedule_time or "09:00"
            parts = hm.split(":")
            hour = int(parts[0]) if parts else 9
            minute = int(parts[1]) if len(parts) > 1 else 0

            if prof.schedule_frequency == "daily":
                trigger = CronTrigger(hour=hour, minute=minute, timezone=tz)
            else:
                trigger = CronTrigger(day_of_week="mon", hour=hour, minute=minute, timezone=tz)

            _scheduler.add_job(
                scheduled_search_fire,
                trigger,
                id=f"saved_search_{prof.id}",
                replace_existing=True,
                kwargs={"profile_id": prof.id},
            )
    finally:
        db.close()


def start_scheduler() -> None:
    global _scheduler
    if is_scheduler_disabled():
        logger.info("job scheduler disabled (JOBS_SCHEDULER_DISABLED)")
        return
    shutdown_scheduler()
    _scheduler = BackgroundScheduler()
    reschedule_all_profiles()
    _scheduler.start()
    logger.info("job scheduler started jobs=%s", len(_scheduler.get_jobs()))
