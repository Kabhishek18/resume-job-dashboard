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


# Class / attr hints for company on Naukri SERP cards (best-effort; markup changes often).
_COMPANY_CLASS_HINTS = (
    "comp-name",
    "company-name",
    "companyName",
    "subTitle",
    "subtitle",
    "org-name",
    "naukri-organ",
    "ni-company",
)


def _text_looks_like_company(text: str, title: str) -> bool:
    s = (text or "").strip()
    if len(s) < 2 or len(s) > 120 or "http" in s.lower():
        return False
    if s.casefold() == (title or "").strip().casefold():
        return False
    if len(s) > 72 and (s.count(" ") > 10 or s.count(".") > 1):
        return False
    return True


def _company_from_snippet_fallback(snippet: str, title: str) -> str:
    if not snippet or "http" in snippet.lower():
        return ""
    first_line = snippet.split("\n")[0].strip()
    for sep in ("·", "|"):
        if sep not in first_line:
            continue
        parts = [p.strip() for p in first_line.split(sep) if p.strip()]
        if not parts:
            continue
        cand = parts[0]
        if not _text_looks_like_company(cand, title):
            continue
        if re.search(r"\d+\s*-\s*\d+\s*yr", cand, re.I):
            continue
        if re.match(r"^\d", cand):
            continue
        return cand[:300]
    return ""


def _company_from_context(anchor: Any, title: str, snippet: str) -> str:
    """Walk up from job link; read data-* / typical class nodes. Selectors are best-effort."""
    el: Any = anchor
    for _ in range(10):
        if el is None or not getattr(el, "name", None):
            break
        for attr in ("data-company", "data-comp", "data-orgname", "data-org"):
            raw = el.get(attr) if hasattr(el, "get") else None
            if raw and _text_looks_like_company(str(raw), title):
                return str(raw).strip()[:300]
        klass = el.get("class") if hasattr(el, "get") else None
        if klass:
            cl = " ".join(klass).lower()
            if any(h.lower() in cl for h in _COMPANY_CLASS_HINTS):
                tx = el.get_text(separator=" ", strip=True)
                if tx and _text_looks_like_company(tx, title) and tx.casefold() != title.casefold():
                    first = tx.split("\n")[0].strip()[:120]
                    if _text_looks_like_company(first, title):
                        return first[:300]
        if hasattr(el, "find_all"):
            pat = re.compile("|".join(re.escape(h) for h in _COMPANY_CLASS_HINTS), re.I)
            for node in el.find_all(class_=pat):
                tx = node.get_text(separator=" ", strip=True)
                if tx and _text_looks_like_company(tx, title):
                    seg = tx.split("\n")[0].strip()[:120]
                    if _text_looks_like_company(seg, title):
                        return seg[:300]
        el = getattr(el, "parent", None)

    return _company_from_snippet_fallback(snippet, title)


def _split_title_company(title: str) -> tuple[str, str]:
    """If link text looks like 'Role at Company' / 'Role | Company', split into (title, company)."""
    t = (title or "").strip()
    if len(t) < 5 or t == "Job posting":
        return t[:300] if t else "", ""
    low = t.casefold()
    for sep in (" at ", " @ ", " | "):
        pos = low.find(sep)
        if pos == -1:
            continue
        left, right = t[:pos].strip(), t[pos + len(sep) :].strip()
        if len(left) >= 2 and 2 <= len(right) <= 120 and "http" not in right.lower():
            return left[:300], right[:300]
    if " - " in t:
        left, right = t.split(" - ", 1)
        left, right = left.strip(), right.strip()
        if (
            len(left) >= 2
            and 2 <= len(right) <= 80
            and "http" not in right.lower()
            and "\n" not in right
            and len(right.split()) <= 8
            and not re.match(r"^\d", right)
        ):
            return left[:300], right[:300]
    return t[:300], ""


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


def _effective_naukri_max_listings(profile: dict[str, Any] | None) -> int:
    rw = (profile or {}).get("results_wanted")
    if isinstance(rw, int):
        return max(1, min(rw, 100))
    return settings.naukri_max_listings


def _max_listings() -> int:
    """Global default when no profile dict (e.g. isolated HTML parse tests)."""
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
    company: str = ""


def parse_naukri_serp_html(html: str, *, max_listings: int | None = None) -> list[_NaukriListing]:
    """Parse one Naukri search-results HTML page into listings (for tests and direct reuse)."""
    cap = max_listings if max_listings is not None else _max_listings()
    soup = BeautifulSoup(html, "html.parser")
    found: list[_NaukriListing] = []
    for a in soup.find_all("a", href=True):
        href = (a.get("href") or "").strip()
        if not _href_looks_like_naukri_job(href):
            continue
        full = _absolutize(NAUKRI_BASE, href)
        raw = (a.get_text() or "").strip()
        if len(raw) < 3:
            raw = "Job posting"
        snippet = ""
        parent = a.find_parent(["article", "div", "li"])
        if parent:
            snippet = parent.get_text(separator=" ", strip=True)[:1200]
        company = (_company_from_context(a, raw, snippet) or "").strip()[:300]
        tit, comp_link = _split_title_company(raw)
        if comp_link and not company:
            company = comp_link[:300]
        display_title = tit[:300] if comp_link else raw[:300]
        desc = f"{display_title}\n{snippet}"[:2000]
        found.append(
            _NaukriListing(
                title=display_title,
                url=full.split("?")[0],
                description=desc,
                company=company[:300],
            )
        )
        if len(found) >= cap:
            break
    return found


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
    cap = _effective_naukri_max_listings(profile)

    def append_from_html(html: str) -> None:
        nonlocal out, seen
        for li in parse_naukri_serp_html(html, max_listings=cap):
            key = stable_key_from_url(li.url)
            if key in seen:
                continue
            seen.add(key)
            out.append(li)
            if len(out) >= cap:
                return

    async with httpx.AsyncClient(headers=naukri_http_headers(), follow_redirects=True, timeout=30.0) as na_client:
        for url in urls:
            html = await _fetch_html(na_client, url)
            if html:
                append_from_html(html)
            if len(out) >= cap:
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
            raw = title if len(title) >= 3 else "Job posting"
            tit, comp_link = _split_title_company(raw)
            display_title = tit[:300] if comp_link else raw[:300]
            company = (comp_link or "")[:300]
            if len(display_title) < 3:
                display_title = "Job posting"
            out.append(
                _NaukriListing(
                    title=display_title,
                    url=full.split("?")[0],
                    description=display_title[:1200],
                    company=company,
                )
            )
            if len(out) >= cap:
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
        "results_wanted": profile.get("results_wanted"),
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
                company=(li.company or "").strip()[:300],
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
