"""Dedupe keys and merge rules for aggregated jobs."""

from __future__ import annotations

import hashlib

from app.services.jobs.canonical_url import posted_date_bucket


def norm_text(s: str) -> str:
    return " ".join(s.lower().strip().split())


def fingerprint_dedupe_key(
    *,
    title: str,
    company: str,
    location: str,
    posted_at: str | None,
) -> str:
    bucket = posted_date_bucket(posted_at)
    raw = "|".join([norm_text(title), norm_text(company), norm_text(location), bucket])
    h = hashlib.sha256(raw.encode("utf-8")).hexdigest()[:40]
    return f"fp:{h}"


def url_dedupe_key(canonical_url: str) -> str | None:
    c = canonical_url.strip()
    if not c:
        return None
    return f"url:{c}"


def external_dedupe_key(portal: str, external_job_id: str | None) -> str | None:
    if not external_job_id:
        return None
    return f"id:{portal.lower().strip()}:{external_job_id.strip()}"
