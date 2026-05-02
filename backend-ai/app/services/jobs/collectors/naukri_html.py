"""Naukri job listing discovery via HTML + optional Firecrawl (not python-jobspy).

Best-effort; site HTML/anti-bot changes can break this path without warning.
"""

from __future__ import annotations

import asyncio
import logging
import re
from dataclasses import dataclass
from typing import Any
from urllib.parse import quote_plus, urljoin, urlparse

import httpx
from bs4 import BeautifulSoup

from app.core.config import settings
from app.services.jobs.collectors.types import CollectedRow
from app.services.jobs.firecrawl_client import firecrawl_configured, scrape_url_to_markdown

_log = logging.getLogger(__name__)

NAUKRI_BASE = "https://www.naukri.com"

_DEFAULT_NAUKRI_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)


def _slug_part(s: str) -> str:
    s = (s or "").strip().lower()
    s = re.sub(r"[^a-z0-9]+", "-", s)
    return s.strip("-") or "all"


def stable_key_from_url(url: str) -> str:
    try:
        p = urlparse(url)
        key = (p.netloc + p.path).lower()
        return key[:500]
    except Exception:
        return url[:500]


def _absolutize(base: str, href: str) -> str:
    return urljoin(base, href)


def naukri_http_headers() -> dict[str, str]:
    ua = (settings.naukri_http_user_agent or "").strip() or _DEFAULT_NAUKRI_UA
    return {
        "User-Agent": ua,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
    }


def _href_looks_like_naukri_job(href: str) -> bool:
    h = href.lower()
    if "naukri.com" not in h and not h.startswith("/"):
        return False
    return (
        "job-listings" in h
        or "/job/" in h
        or "jobs/vacancy" in h
        or re.search(r"/jobs/[^/?#]+-\d+", h) is not None
    )


def _extract_job_links_from_markdown(md: str) -> list[tuple[str, str]]:
    if not md or len(md) < 50:
        return []
    out: list[tuple[str, str]] = []
    seen: set[str] = set()
    for m in re.finditer(r"\[([^\]]{2,400})\]\((https://www\.naukri\.com[^)]+)\)", md, re.I):
        title, raw_u = m.group(1).strip(), m.group(2).strip()
        u = raw_u.split("?")[0].split("#")[0]
        if not _href_looks_like_naukri_job(u):
            continue
        k = stable_key_from_url(_absolutize(NAUKRI_BASE, u))
        if k in seen:
            continue
        seen.add(k)
        out.append((title, _absolutize(NAUKRI_BASE, u)))
    for m in re.finditer(r"https://www\.naukri\.com[/\w.-]*job-listings[/\w.-]*", md, re.I):
        u = m.group(0).split("?")[0]
        k = stable_key_from_url(u)
        if k in seen:
            continue
        seen.add(k)
        out.append(("", u))
    return out


def _max_listings() -> int:
    return settings.naukri_max_listings


def _search_urls_for_profile(profile: dict[str, Any]) -> list[str]:
    role = (profile.get("keywords") or profile.get("target_role") or "").strip()
    loc = (profile.get("locations") or profile.get("location") or "").strip() or "india"
    rs = _slug_part(role) if role else "jobs"
    ls = _slug_part(loc)
    return [
        f"{NAUKRI_BASE}/{rs}-jobs-in-{ls}",
        f"{NAUKRI_BASE}/jobs-in-{ls}?keyword={quote_plus(role or 'software developer')}&k={quote_plus(role or '')}",
    ]


@dataclass
class _NaukriListing:
    title: str
    url: str
    description: str


async def _fetch_html(client: httpx.AsyncClient, url: str, timeout: float = 25.0) -> str | None:
    try:
        r = await client.get(url, timeout=timeout, follow_redirects=True)
        r.raise_for_status()
        ct = (r.headers.get("content-type") or "").lower()
        if "html" not in ct and "text" not in ct and ct:
            return None
        return r.text
    except Exception:
        return None


async def _search_naukri_async(profile: dict[str, Any]) -> list[_NaukriListing]:
    out: list[_NaukriListing] = []
    seen: set[str] = set()
    urls = _search_urls_for_profile(profile)

    def append_from_html(html: str) -> None:
        nonlocal out, seen
        soup = BeautifulSoup(html, "html.parser")
        for a in soup.find_all("a", href=True):
            href = (a.get("href") or "").strip()
            if not _href_looks_like_naukri_job(href):
                continue
            full = _absolutize(NAUKRI_BASE, href)
            key = stable_key_from_url(full)
            if key in seen:
                continue
            title = (a.get_text() or "").strip()
            if len(title) < 3:
                title = "Job posting"
            seen.add(key)
            snippet = ""
            parent = a.find_parent(["article", "div", "li"])
            if parent:
                snippet = parent.get_text(separator=" ", strip=True)[:1200]
            out.append(
                _NaukriListing(
                    title=title[:300],
                    url=full.split("?")[0],
                    description=f"{title}\n{snippet}"[:2000],
                )
            )
            if len(out) >= _max_listings():
                return

    async with httpx.AsyncClient(headers=naukri_http_headers(), follow_redirects=True, timeout=30.0) as na_client:
        for url in urls:
            html = await _fetch_html(na_client, url)
            if html:
                append_from_html(html)
            if len(out) >= _max_listings():
                return out
            if out:
                return out

    if out:
        return out

    if not firecrawl_configured():
        if not out:
            _log.info(
                "Naukri: no listings from direct HTML. Set FIRECRAWL_API_KEY for JS-rendered pages, "
                "or NAUKRI_HTTP_USER_AGENT if blocked."
            )
        return out

    for url in urls:
        try:
            _title_meta, md = await asyncio.to_thread(scrape_url_to_markdown, url)
        except Exception as ex:
            _log.warning("Naukri Firecrawl scrape failed for %s: %s", url, ex)
            continue
        for title, full in _extract_job_links_from_markdown(md):
            key = stable_key_from_url(full)
            if key in seen:
                continue
            seen.add(key)
            t = title if len(title) >= 3 else "Job posting"
            out.append(_NaukriListing(title=t[:300], url=full.split("?")[0], description=t[:1200]))
            if len(out) >= _max_listings():
                return out
    return out


def _profile_location_line(profile: dict[str, Any]) -> str:
    return (profile.get("locations") or "").strip() or (profile.get("location") or "").strip() or "India"


def collect_naukri_html(profile: dict[str, Any]) -> tuple[list[CollectedRow], str | None]:
    """
    Sync entry: discover Naukri listing links and map to CollectedRow.

    Returns (rows, optional user-facing note on total failure).
    """
    if not settings.naukri_html_enabled:
        return [], None

    internal = {
        "keywords": profile.get("keywords"),
        "locations": profile.get("locations"),
        "target_role": profile.get("target_role"),
        "location": profile.get("location"),
    }

    try:
        listings = asyncio.run(_search_naukri_async(internal))
    except Exception as exc:
        _log.exception("Naukri HTML search failed")
        msg = str(exc).strip()[:240] or type(exc).__name__
        return [], f"Naukri discovery failed: {msg}"

    loc_line = _profile_location_line(profile)
    rows: list[CollectedRow] = []
    for li in listings:
        rows.append(
            CollectedRow(
                title=li.title,
                company="",
                location=loc_line[:300],
                portal="naukri",
                apply_url=li.url[:2000],
                source_url=li.url[:2000],
                description_snippet=li.description.strip()[:2000],
                external_job_id=stable_key_from_url(li.url)[:500],
                raw_meta={"source": "naukri_html"},
            )
        )

    note: str | None = None
    if not rows and not firecrawl_configured():
        note = (
            "Naukri returned no listing links from HTML. Add FIRECRAWL_API_KEY in backend-ai/.env "
            "if the search page is JS-rendered, or try different keywords/locations."
        )
    elif not rows:
        note = "Naukri returned no listing links (HTML and Firecrawl). Try different keywords or locations."

    return rows, note
