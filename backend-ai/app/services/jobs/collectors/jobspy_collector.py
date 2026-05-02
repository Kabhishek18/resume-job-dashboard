"""Single JobSpy-backed collector for supported job portals."""

from __future__ import annotations

import logging
from typing import Any

import pandas as pd

from app.core.config import settings
from app.services.jobs.collectors.types import CollectedRow, PortalRunOutcome, normalize_portal_id

try:
    from jobspy import scrape_jobs as _scrape_jobs
except ImportError:  # pragma: no cover - dev env without JobSpy / Python < 3.10
    _scrape_jobs = None  # type: ignore[misc, assignment]

logger = logging.getLogger(__name__)

PORTAL_KEYS = frozenset({"linkedin", "indeed", "glassdoor", "naukri"})

# JobSpy returns little or nothing if search_term is missing; keep a harmless default.
_DEFAULT_SEARCH_TERM = "software engineer"


def _jobspy_supported_site_values() -> frozenset[str]:
    """Site names accepted by the installed JobSpy (PyPI builds vary)."""
    if _scrape_jobs is None:
        return frozenset()
    try:
        from jobspy.scrapers import Site

        return frozenset(s.value for s in Site)
    except Exception:  # pragma: no cover
        return frozenset({"linkedin", "indeed", "zip_recruiter"})


def _jobspy_scrape_kw(
    search: str,
    location: str,
    profile: dict[str, Any],
) -> dict[str, Any]:
    kw: dict[str, Any] = {
        "search_term": search,
        "location": location,
        "is_remote": bool(profile.get("remote_only")),
        "results_wanted": max(1, min(settings.jobspy_results_wanted, 200)),
        "country_indeed": settings.jobspy_country_indeed,
    }
    pxy = (settings.jobspy_proxy or "").strip()
    if pxy:
        kw["proxy"] = pxy
    return kw


def _collector_note_for_failures(
    failures: list[tuple[str, str]], any_results: bool
) -> str | None:
    if not failures:
        return None
    parts = [f"{site}: {msg}" for site, msg in failures]
    body = "; ".join(parts)[:380]
    hint = ""
    if any("403" in msg or "429" in msg for _, msg in failures):
        hint = (
            " Boards often block datacenter/residential IPs (403/429). "
            "Try LinkedIn-only, another network, or JOBSPY_PROXY in backend-ai/.env."
        )
    if any_results:
        return f"Some job boards failed (showing results from the rest). {body}.{hint}".strip()
    return f"Job search failed: {body}.{hint}".strip()


def _format_salary(row: pd.Series) -> str:
    parts: list[str] = []
    interval = row.get("interval")
    mi = row.get("min_amount")
    ma = row.get("max_amount")
    cur = row.get("currency")
    if mi is not None or ma is not None:
        if mi is not None and ma is not None:
            parts.append(f"{mi}–{ma}")
        elif mi is not None:
            parts.append(str(mi))
        elif ma is not None:
            parts.append(str(ma))
        if cur:
            parts.append(str(cur))
        if interval:
            parts.append(f"({interval})")
    return " ".join(parts).strip()


def _row_to_collected(row: pd.Series) -> CollectedRow:
    site_raw = row.get("site")
    portal = normalize_portal_id(
        str(site_raw).lower().strip() if site_raw is not None and not pd.isna(site_raw) else ""
    )
    if portal == "other":
        portal = (
            str(site_raw).lower()[:32]
            if site_raw is not None and not pd.isna(site_raw)
            else "unknown"
        )

    direct = row.get("job_url_direct")
    main_url = row.get("job_url")
    apply_url = ""
    if direct is not None and str(direct).strip():
        apply_url = str(direct).strip()
    elif main_url is not None:
        apply_url = str(main_url).strip()

    title = str(row.get("title") or "").strip()
    company = str(row.get("company") or "").strip()
    location = str(row.get("location") or "").strip()

    posted = row.get("date_posted")
    posted_at: str | None = None
    if posted is not None and not pd.isna(posted):
        if hasattr(posted, "isoformat"):
            posted_at = posted.isoformat()[:64]
        else:
            posted_at = str(posted)[:64]

    desc = row.get("description")
    snippet = ""
    if desc is not None and not pd.isna(desc):
        snippet = str(desc).strip()[:2000]

    ext = row.get("id")
    external_job_id: str | None = None
    if ext is not None and not pd.isna(ext):
        s = str(ext).strip()
        if s:
            external_job_id = s[:500]

    source_url = str(main_url or "").strip()[:2000]

    return CollectedRow(
        title=title,
        company=company,
        location=location,
        portal=portal if portal != "other" else str(site_raw or "").lower()[:32],
        apply_url=apply_url[:2000],
        source_url=source_url,
        salary_text=_format_salary(row)[:300],
        posted_at=posted_at,
        description_snippet=snippet,
        external_job_id=external_job_id,
        raw_meta={},
    )


def collect_jobspy(
    profile: dict[str, Any],
) -> tuple[list[CollectedRow], dict[str, PortalRunOutcome], str | None]:
    """Run JobSpy once for all selected portals.

    Third return value is a short user-facing note (install/runtime), or None.
    """
    raw_portals: list[str] = list(profile.get("selected_portals") or [])
    portals: list[str] = []
    for p in raw_portals:
        pid = normalize_portal_id(p)
        if pid != "other" and pid in PORTAL_KEYS:
            portals.append(pid)

    if not portals:
        return [], {}, None

    outcomes: dict[str, PortalRunOutcome] = {p: PortalRunOutcome(row_count=0, state="no_results") for p in portals}

    if _scrape_jobs is None:
        for p in portals:
            outcomes[p] = PortalRunOutcome(row_count=0, state="unavailable")
        note = (
            "Job search needs Python 3.10+ with python-jobspy installed. "
            "Use your conda env (e.g. job-resume-backend) or recreate backend-ai/.venv with Python 3.11+, then pip install -r requirements.txt."
        )
        logger.warning("jobspy: package not importable (Python version or missing install)")
        return [], outcomes, note

    supported = _jobspy_supported_site_values()
    sites_arg = [p for p in portals if p in supported]
    unsupported = [p for p in portals if p not in supported]
    for p in unsupported:
        outcomes[p] = PortalRunOutcome(row_count=0, state="unavailable")

    if not sites_arg:
        joined = ", ".join(sorted(supported)) if supported else "(none)"
        note = (
            f"No selected portals are supported by this JobSpy install ({joined}). "
            "Pick LinkedIn and/or Indeed, or upgrade: pip install -U python-jobspy"
        )
        logger.warning("jobspy: no overlap between selected portals and supported sites %s", supported)
        return [], outcomes, note

    prefix_notes: list[str] = []
    if "indeed" in sites_arg and not settings.jobspy_run_indeed:
        sites_arg = [s for s in sites_arg if s != "indeed"]
    if any(p == "indeed" for p in portals) and "indeed" in supported and not settings.jobspy_run_indeed:
        prefix_notes.append(
            "Indeed is not queried unless JOBSPY_RUN_INDEED=true in backend-ai/.env "
            "(many networks get HTTP 403 from Indeed)."
        )

    if not sites_arg:
        extra = (
            "No boards left to scrape for this profile. "
            "Include LinkedIn, or set JOBSPY_RUN_INDEED=true to try Indeed."
        )
        note = " ".join([*prefix_notes, extra]).strip()[:900] or extra
        logger.warning("jobspy: sites_arg empty after Indeed filter / unsupported portals")
        return [], outcomes, note

    # Prefer LinkedIn first when multiple sites run (often more reliable than Indeed).
    _site_order = {"linkedin": 0, "indeed": 1, "zip_recruiter": 2}
    sites_arg.sort(key=lambda s: (_site_order.get(s, 9), s))

    raw_kw = (profile.get("keywords") or "").strip()
    search = raw_kw or _DEFAULT_SEARCH_TERM
    location = (profile.get("locations") or "").strip()
    scrape_kw = _jobspy_scrape_kw(search, location, profile)

    # One scrape per portal so one board’s error does not abort the others.
    failures: list[tuple[str, str]] = []
    frames: list[pd.DataFrame] = []
    failed_sites: set[str] = set()

    for site in sites_arg:
        try:
            df_site = _scrape_jobs(site_name=[site], **scrape_kw)
        except Exception as exc:
            logger.warning("jobspy scrape_jobs failed for %s", site, exc_info=True)
            failed_sites.add(site)
            msg = str(exc).strip()[:240] or type(exc).__name__
            failures.append((site, msg))
            continue
        if df_site is not None and len(df_site) > 0:
            frames.append(df_site)

    any_results = bool(frames)
    fail_note = _collector_note_for_failures(failures, any_results)
    note_parts = [*prefix_notes]
    if fail_note:
        note_parts.append(fail_note)
    note = " ".join(note_parts).strip()[:900] if note_parts else None

    df = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()

    if df is None or len(df) == 0:
        for p in sites_arg:
            if p in failed_sites:
                outcomes[p] = PortalRunOutcome(row_count=0, state="unavailable")
            else:
                outcomes[p] = PortalRunOutcome(row_count=0, state="no_results")
        return [], outcomes, note

    rows: list[CollectedRow] = []
    for _, series in df.iterrows():
        rows.append(_row_to_collected(series))

    counts: dict[str, int] = {}
    if "site" in df.columns:
        for site_val, cnt in df.groupby(df["site"].astype(str).str.lower()).size().items():
            site_key = str(site_val).lower()
            if normalize_portal_id(site_key) != "other":
                counts[normalize_portal_id(site_key)] = int(cnt)
            else:
                counts[site_key] = int(cnt)

    for p in sites_arg:
        if p in failed_sites:
            outcomes[p] = PortalRunOutcome(row_count=0, state="unavailable")
        else:
            n = int(counts.get(p, 0))
            outcomes[p] = PortalRunOutcome(row_count=n, state="ok" if n > 0 else "no_results")

    return rows, outcomes, note
