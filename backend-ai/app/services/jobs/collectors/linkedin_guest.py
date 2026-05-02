"""HTTP-based LinkedIn jobs guest search; best-effort parse (no JobSpy, no JOBSPY_PROXY)."""

from __future__ import annotations

import re
from typing import Any

import httpx
from bs4 import BeautifulSoup

from app.services.jobs.collectors.types import CollectedRow, CollectorResult

USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)


def collect_linkedin_guest(profile: dict[str, Any]) -> CollectorResult:
    """
    Lightweight guest fetch to https://www.linkedin.com/jobs/search.
    LinkedIn may return auth walls or empty HTML; we parse common list-card markup when present.
    """
    warnings: list[str] = []
    keywords = str(profile.get("keywords") or profile.get("q") or "software engineer")
    params = {"keywords": keywords, "location": profile.get("locations") or ""}
    url = "https://www.linkedin.com/jobs/search"
    try:
        with httpx.Client(timeout=20.0, headers={"User-Agent": USER_AGENT}, follow_redirects=True) as c:
            r = c.get(url, params=params)
        if r.status_code != 200:
            warnings.append(f"linkedin_http_{r.status_code}")
            return CollectorResult(rows=[], warnings=warnings)

        if "sign in" in r.text.lower() and r.status_code == 200:
            warnings.append("linkedin_guest_page_may_require_auth")
        rows = _parse_cards_or_fixture_html(r.text)
        if not rows:
            warnings.append("linkedin_empty_results_or_selectors_miss")
        return CollectorResult(rows=rows, warnings=warnings)
    except Exception as fc:  # noqa: BLE001
        warnings.append(f"linkedin_request_error:{type(fc).__name__}")
        return CollectorResult(rows=[], warnings=warnings)


def _parse_cards_or_fixture_html(html: str) -> list[CollectedRow]:
    soup = BeautifulSoup(html, "html.parser")
    out: list[CollectedRow] = []
    cards = soup.select("div.base-card") or soup.select("div.job-search-card")
    for card in cards:
        title_el = card.select_one(".base-search-card__title") or card.select_one("h3")
        company_el = card.select_one(".base-search-card__subtitle") or card.select_one("h4")
        loc_el = card.select_one(".job-search-card__location") or card.select_one(
            ".base-search-card__metadata"
        )
        link_el = card.select_one("a[href*=job]")
        title = title_el.get_text(strip=True) if title_el else ""
        company = company_el.get_text(strip=True) if company_el else ""
        location = loc_el.get_text(strip=True) if loc_el else ""
        href = ""
        if link_el and link_el.has_attr("href"):
            href = str(link_el["href"])
            if href.startswith("/"):
                href = f"https://www.linkedin.com{href}"
        if not title:
            continue
        out.append(
            CollectedRow(
                title=title,
                company=company,
                location=location,
                portal="linkedin",
                apply_url=href or "",
                source_url=href or "",
                external_job_id=_extract_li_job_id(href),
                raw_meta={"source": "linkedin_guest"},
            )
        )
    return out


def _extract_li_job_id(url: str) -> str | None:
    if not url:
        return None
    m = re.search(r"(?:jobs/view/|currentJobId=)(\d+)", url)
    return m.group(1) if m else None
