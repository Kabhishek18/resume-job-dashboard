"""Single JobSpy-backed collector for supported job portals."""

from __future__ import annotations

import logging
from typing import Any

import pandas as pd

from app.core.config import settings
from app.services.jobs.collectors.linkedin_guest import collect_linkedin_guest
from app.services.jobs.collectors.naukri_html import collect_naukri_html
from app.services.jobs.collectors.types import CollectedRow, PortalRunOutcome, normalize_portal_id

try:
    from jobspy import scrape_jobs as _scrape_jobs
except ImportError:  # pragma: no cover - dev env without JobSpy / Python < 3.10
    _scrape_jobs = None  # type: ignore[misc, assignment]

logger = logging.getLogger(__name__)

PORTAL_KEYS = frozenset({"linkedin", "indeed", "glassdoor", "naukri", "zip_recruiter"})

# JobSpy returns little or nothing if search_term is missing; keep a harmless default.
_DEFAULT_SEARCH_TERM = "software engineer"


def _effective_jobspy_results_wanted(profile: dict[str, Any]) -> int:
    rw = profile.get("results_wanted")
    if isinstance(rw, int):
        return max(1, min(rw, 200))
    return max(1, min(settings.jobspy_results_wanted, 200))


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
        "results_wanted": _effective_jobspy_results_wanted(profile),
        "country_indeed": settings.jobspy_country_indeed,
    }
    pxy = (settings.jobspy_proxy or "").strip()
    if pxy:
        kw["proxy"] = pxy
    return kw


def _looks_like_proxy_failure(exc: Exception, proxy: str) -> bool:
    msg = str(exc).lower()
    proxy_l = proxy.lower()
    proxy_host = proxy_l.split("://", 1)[-1]
    proxy_markers = ("proxy", "127.0.0.1", "localhost")
    failure_markers = (
        "proxyerror",
        "proxy error",
        "cannot connect to proxy",
        "failed to establish a new connection",
        "max retries exceeded",
        "connection refused",
        "connection aborted",
        "connect timeout",
        "timed out",
        "name or service not known",
        "nodename nor servname provided",
    )
    mentions_proxy = any(marker in msg for marker in proxy_markers) or any(
        marker in proxy_host for marker in proxy_markers
    )
    return mentions_proxy and any(marker in msg for marker in failure_markers)


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
            "Try LinkedIn-only, Naukri, another network, or JOBSPY_PROXY in backend-ai/.env. "
            "Indeed and ZipRecruiter often need a working proxy even when JOBSPY_RUN_INDEED / JOBSPY_RUN_ZIP_RECRUITER are true."
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


def _merge_linkedin_guest(
    rows: list[CollectedRow],
    outcomes: dict[str, PortalRunOutcome],
    profile: dict[str, Any],
    note: str | None,
    portals: list[str],
) -> tuple[list[CollectedRow], dict[str, PortalRunOutcome], str | None]:
    """When JobSpy has no usable LinkedIn rows, try lightweight guest /jobs/search HTML parse."""
    if "linkedin" not in portals or not settings.linkedin_guest_enabled:
        return rows, outcomes, note

    li_rows = [r for r in rows if normalize_portal_id(getattr(r, "portal", "") or "") == "linkedin"]
    li_count = len(li_rows)
    st = outcomes.get("linkedin")
    should_try = (
        settings.linkedin_use_guest_instead_of_jobspy
        or li_count == 0
        or (st is not None and st.state == "unavailable")
    )
    if st is not None and st.state == "no_results" and li_count == 0:
        should_try = True
    if not should_try:
        return rows, outcomes, note

    res = collect_linkedin_guest(profile)
    existing_urls = {r.apply_url for r in li_rows if r.apply_url}
    new_li: list[CollectedRow] = []
    for r in res.rows:
        if r.apply_url and r.apply_url in existing_urls:
            continue
        new_li.append(r)
        if r.apply_url:
            existing_urls.add(r.apply_url)

    merged = rows + new_li
    total_li = sum(1 for r in merged if normalize_portal_id(getattr(r, "portal", "") or "") == "linkedin")

    if total_li > 0:
        outcomes["linkedin"] = PortalRunOutcome(row_count=total_li, state="ok")
    elif res.warnings:
        hint = "; ".join(res.warnings)[:220]
        extra = f"LinkedIn guest: {hint}"
        parts = [str(x).strip() for x in (note, extra) if x and str(x).strip()]
        note = " ".join(parts)[:900] if parts else extra

    return merged, outcomes, note


def _finalize_collect(
    rows: list[CollectedRow],
    outcomes: dict[str, PortalRunOutcome],
    profile: dict[str, Any],
    note: str | None,
    portals: list[str],
) -> tuple[list[CollectedRow], dict[str, PortalRunOutcome], str | None]:
    rows, outcomes, note = _merge_linkedin_guest(rows, outcomes, profile, note, portals)
    return _merge_naukri_html(rows, outcomes, profile, note, portals)


def _merge_naukri_html(
    rows: list[CollectedRow],
    outcomes: dict[str, PortalRunOutcome],
    profile: dict[str, Any],
    note: str | None,
    portals: list[str],
) -> tuple[list[CollectedRow], dict[str, PortalRunOutcome], str | None]:
    """Append Naukri HTML/Firecrawl rows and set outcomes['naukri']."""
    if "naukri" not in portals or not settings.naukri_html_enabled:
        return rows, outcomes, note

    n_rows, n_note = collect_naukri_html(profile)
    merged = rows + n_rows
    if n_rows:
        outcomes["naukri"] = PortalRunOutcome(row_count=len(n_rows), state="ok")
    elif n_note and "Naukri discovery failed" in n_note:
        outcomes["naukri"] = PortalRunOutcome(row_count=0, state="unavailable")
    else:
        outcomes["naukri"] = PortalRunOutcome(row_count=0, state="no_results")

    parts = [str(x).strip() for x in (note, n_note) if x and str(x).strip()]
    final_note = " ".join(parts)[:900] if parts else None
    return merged, outcomes, final_note


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
    naukri_wanted = "naukri" in portals and settings.naukri_html_enabled
    linkedin_guest_jobspy_skipped = (
        "linkedin" in portals
        and settings.linkedin_guest_enabled
        and settings.linkedin_use_guest_instead_of_jobspy
    )
    non_jobspy_collect = naukri_wanted or linkedin_guest_jobspy_skipped

    if _scrape_jobs is None:
        for p in portals:
            if p == "naukri" and settings.naukri_html_enabled:
                continue
            outcomes[p] = PortalRunOutcome(row_count=0, state="unavailable")
        inst_note = (
            "Job search needs Python 3.10+ with python-jobspy installed. "
            "Use your conda env (e.g. job-resume-backend) or recreate backend-ai/.venv with Python 3.11+, then pip install -r requirements.txt."
        )
        logger.warning("jobspy: package not importable (Python version or missing install)")
        return _finalize_collect([], outcomes, profile, inst_note, portals)

    supported = _jobspy_supported_site_values()
    sites_arg = [
        p
        for p in portals
        if p in supported
        and p != "naukri"
        and not (p == "linkedin" and linkedin_guest_jobspy_skipped)
    ]

    for p in portals:
        if p == "naukri":
            if not settings.naukri_html_enabled:
                outcomes[p] = PortalRunOutcome(row_count=0, state="unavailable")
            continue
        if p not in supported:
            outcomes[p] = PortalRunOutcome(row_count=0, state="unavailable")

    if not sites_arg and not non_jobspy_collect:
        joined = ", ".join(sorted(supported)) if supported else "(none)"
        note = (
            f"No selected portals are supported by this JobSpy install ({joined}). "
            "Pick LinkedIn, ZipRecruiter, and/or Indeed, or upgrade: pip install -U python-jobspy"
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
    if "zip_recruiter" in sites_arg and not settings.jobspy_run_zip_recruiter:
        sites_arg = [s for s in sites_arg if s != "zip_recruiter"]
    if (
        any(p == "zip_recruiter" for p in portals)
        and "zip_recruiter" in supported
        and not settings.jobspy_run_zip_recruiter
    ):
        prefix_notes.append(
            "ZipRecruiter is not queried unless JOBSPY_RUN_ZIP_RECRUITER=true in backend-ai/.env "
            "(many networks get HTTP 403 from ZipRecruiter)."
        )

    if not sites_arg and not non_jobspy_collect:
        extra = (
            "No boards left to scrape for this profile. "
            "Include LinkedIn or Naukri, or set JOBSPY_RUN_INDEED=true / JOBSPY_RUN_ZIP_RECRUITER=true to try those boards "
            "(often with JOBSPY_PROXY)."
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

    failures: list[tuple[str, str]] = []
    frames: list[pd.DataFrame] = []
    failed_sites: set[str] = set()
    proxy_fallback_used = False

    for site in sites_arg:
        retried_without_proxy = False
        try:
            df_site = _scrape_jobs(site_name=[site], **scrape_kw)
        except Exception as exc:
            proxy = str(scrape_kw.get("proxy") or "").strip()
            if proxy and _looks_like_proxy_failure(exc, proxy):
                retry_kw = dict(scrape_kw)
                retry_kw.pop("proxy", None)
                logger.warning(
                    "jobspy scrape_jobs hit proxy failure for %s; retrying without proxy %s",
                    site,
                    proxy,
                    exc_info=True,
                )
                try:
                    df_site = _scrape_jobs(site_name=[site], **retry_kw)
                    proxy_fallback_used = True
                    retried_without_proxy = True
                except Exception as retry_exc:
                    exc = retry_exc
            if not retried_without_proxy:
                logger.warning("jobspy scrape_jobs failed for %s", site, exc_info=True)
                failed_sites.add(site)
                msg = str(exc).strip()[:240] or type(exc).__name__
                failures.append((site, msg))
                continue
            if df_site is None or len(df_site) == 0:
                continue
        else:
            if df_site is None or len(df_site) == 0:
                continue
        if retried_without_proxy:
            logger.info("jobspy scrape_jobs succeeded for %s after retrying without proxy", site)
        if df_site is not None and len(df_site) > 0:
            frames.append(df_site)

    any_results = bool(frames)
    fail_note = _collector_note_for_failures(failures, any_results)
    note_parts = [*prefix_notes]
    if proxy_fallback_used:
        note_parts.append(
            "Configured JOBSPY_PROXY failed, so this run retried direct connections. "
            "Remove or fix JOBSPY_PROXY in backend-ai/.env if you are not intentionally using a proxy."
        )
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
        return _finalize_collect([], outcomes, profile, note, portals)

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

    return _finalize_collect(rows, outcomes, profile, note, portals)
