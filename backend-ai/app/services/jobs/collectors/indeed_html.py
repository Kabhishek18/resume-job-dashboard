"""Indeed job SERP via direct HTML fetch (httpx + BeautifulSoup).

Complements python-jobspy when JobSpy Indeed returns 403 or empty rows.
Best-effort; Indeed markup and bot rules change without notice.
"""

from __future__ import annotations

import logging
import re
from typing import Any
from urllib.parse import urlencode, urljoin

import httpx
from bs4 import BeautifulSoup

from app.core.config import settings
from app.services.jobs.collectors.naukri_html import stable_key_from_url
from app.services.jobs.collectors.types import CollectedRow
from app.services.jobs.proxy_http import looks_like_proxy_failure

_log = logging.getLogger(__name__)

_DEFAULT_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)


def _indeed_base_url() -> str:
    c = (settings.jobspy_country_indeed or "").strip().lower()
    if c in ("india", "in", "indi"):
        return "https://in.indeed.com"
    if c in ("usa", "us", "united states", "united_states"):
        return "https://www.indeed.com"
    if c in ("uk", "gb", "united kingdom", "united_kingdom"):
        return "https://uk.indeed.com"
    if c in ("ca", "canada"):
        return "https://ca.indeed.com"
    if c in ("au", "australia"):
        return "https://au.indeed.com"
    return "https://www.indeed.com"


def _default_location_for_base(base: str) -> str:
    if "in.indeed" in base:
        return "India"
    if "uk.indeed" in base:
        return "United Kingdom"
    if "ca.indeed" in base:
        return "Canada"
    if "au.indeed" in base:
        return "Australia"
    return ""


def _absolutize(base: str, href: str) -> str:
    return urljoin(base, href)


def _indeed_headers() -> dict[str, str]:
    ua = (settings.naukri_http_user_agent or "").strip() or _DEFAULT_UA
    return {
        "User-Agent": ua,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
    }


def _http_get_html(url: str, proxy: str | None) -> tuple[str | None, Exception | None]:
    kwargs: dict[str, Any] = {
        "headers": _indeed_headers(),
        "follow_redirects": True,
        "timeout": 25.0,
    }
    if proxy:
        kwargs["proxy"] = proxy
    try:
        with httpx.Client(**kwargs) as client:
            r = client.get(url)
            r.raise_for_status()
            return r.text, None
    except Exception as ex:
        return None, ex


def _fetch_indeed_jobs_html(url: str) -> tuple[str | None, str | None]:
    """Return (html, error_note). Uses JOBSPY_PROXY when set; retries without proxy on proxy transport failures."""
    pxy = (settings.jobspy_proxy or "").strip()
    if pxy:
        html, ex = _http_get_html(url, pxy)
        if html is not None:
            return html, None
        if ex is not None and looks_like_proxy_failure(ex, pxy):
            _log.warning("Indeed HTML via proxy failed (%s); retrying without proxy", ex)
            html2, ex2 = _http_get_html(url, None)
            if html2 is not None:
                return html2, None
            ex = ex2 or ex
        if ex is not None:
            _log.warning("Indeed HTML fetch failed: %s", ex)
            return None, f"Indeed HTML: {type(ex).__name__}"
        return None, "Indeed HTML: unknown error"

    html, ex = _http_get_html(url, None)
    if html is not None:
        return html, None
    if ex is not None:
        _log.warning("Indeed HTML fetch failed: %s", ex)
        return None, f"Indeed HTML: {type(ex).__name__}"
    return None, "Indeed HTML: unknown error"


def collect_indeed_html(profile: dict[str, Any]) -> tuple[list[CollectedRow], str | None]:
    """Fetch Indeed search HTML and parse listing cards into CollectedRow (portal=indeed)."""
    if not settings.indeed_html_fallback_enabled:
        return [], None

    base = _indeed_base_url()
    q = (profile.get("keywords") or "").strip() or "software engineer"
    loc = (profile.get("locations") or "").strip() or _default_location_for_base(base)
    cap = max(1, min(50, settings.indeed_html_max_listings))
    fromage = max(1, min(30, settings.indeed_html_from_age_days))

    params = {"q": q, "l": loc, "fromage": str(fromage)}
    url = f"{base}/jobs?{urlencode(params)}"

    rows: list[CollectedRow] = []
    html, fetch_note = _fetch_indeed_jobs_html(url)
    if fetch_note:
        return [], fetch_note

    if not html or len(html) < 200:
        return [], "Indeed HTML: empty response"

    soup = BeautifulSoup(html, "html.parser")
    seen: set[str] = set()

    for td in soup.select("td.resultContent, div.job_seen_beacon, div.slider_container"):
        a = td.select_one("h2.jobTitle a, a.jcs-JobTitle, span[data-testid='job-title'] a")
        if not a or not a.get("href"):
            continue
        href = a["href"]
        if "/pagead/" in href or "/apply" in href:
            continue
        full = _absolutize(base, href)
        jk = ""
        m = re.search(r"[?&]jk=([^&]+)", full)
        if m:
            jk = m.group(1)
        if not jk:
            m2 = re.search(r"/jobs/view/([^/?]+)", full)
            if m2:
                jk = m2.group(1)
        key = jk or stable_key_from_url(full)
        if key in seen:
            continue
        title = (a.get_text() or "").strip()
        if len(title) < 2:
            continue
        seen.add(key)
        snippet_el = td.select_one(".summary, .job-snippet, .underShelfFooter")
        snippet = snippet_el.get_text(separator=" ", strip=True) if snippet_el else ""
        apply_url = full.split("&")[0].split("?")[0] if "jk=" in full else full
        rows.append(
            CollectedRow(
                title=title[:300],
                company="",
                location=loc[:300],
                portal="indeed",
                apply_url=apply_url[:2000],
                source_url=full[:2000],
                description_snippet=f"{title}\n{snippet}"[:2000],
                raw_meta={"source": "indeed_html"},
            )
        )
        if len(rows) >= cap:
            break

    if not rows:
        for a in soup.find_all("a", href=True):
            href = a["href"]
            if "/rc/clk" not in href and "viewjob" not in href.lower():
                continue
            full = _absolutize(base, href)
            key = stable_key_from_url(full)
            if key in seen:
                continue
            title = (a.get_text() or "").strip()
            if len(title) < 2:
                continue
            seen.add(key)
            rows.append(
                CollectedRow(
                    title=title[:300],
                    company="",
                    location=loc[:300],
                    portal="indeed",
                    apply_url=full[:2000],
                    source_url=full[:2000],
                    description_snippet=title[:2000],
                    raw_meta={"source": "indeed_html"},
                )
            )
            if len(rows) >= cap:
                break

    if not rows:
        return [], "Indeed HTML: no listings parsed (markup or block)"

    return rows, None
