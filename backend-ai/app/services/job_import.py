"""Fetch and extract plain text from public HTML job postings (generic; no portals)."""

from __future__ import annotations

import ipaddress
import json
import re
from typing import Any, Iterable, Literal, Optional, Tuple
from urllib.parse import urlparse

import httpx
from bs4 import BeautifulSoup
from pydantic import BaseModel, HttpUrl


class ImportPreviewRequest(BaseModel):
    url: HttpUrl


Mode = Literal["imported_full", "imported_partial", "fallback_required"]


class ImportPreviewApiV1(BaseModel):
    version: Literal["v1"] = "v1"
    mode: Mode
    title: Optional[str] = None
    company: Optional[str] = None
    raw_text: Optional[str] = None
    warnings: list[str]


def _host_ips(hostname: str) -> Iterable[Tuple[str, str]]:
    """Yield (family, ip) for resolved hostname (blocking). Minimal resolution."""
    import socket

    for res in socket.getaddrinfo(hostname, None):
        sockaddr = res[4]
        if len(sockaddr) >= 1:
            yield res[0], sockaddr[0]


def _ip_blocked(ip_str: str) -> bool:
    try:
        ip = ipaddress.ip_address(ip_str)
    except ValueError:
        return True
    if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved:
        return True
    if ip.version == 4:
        parts = ip.packed[:2]
        if parts == (127, 0) or parts == (0, 0):
            return True
    if ip.version == 6 and ip in ipaddress.ip_network("fe80::/10"):
        return True
    return False


def assert_public_http_url(raw: str) -> tuple[str, str]:
    parsed = urlparse(raw)
    if parsed.scheme not in ("http", "https"):
        raise ValueError("Only http/https URLs are allowed")
    hostname = parsed.hostname or ""
    if hostname in ("localhost",) or hostname.endswith(".local"):
        raise ValueError("Host not allowed")

    ips = list(_host_ips(hostname))
    if not ips:
        raise ValueError("Could not resolve host")

    for _fam, addr in ips:
        if ":" in addr and addr.startswith("["):  # not typical getaddrinfo
            continue
        if _ip_blocked(addr):
            raise ValueError("Address not allowed")

    return raw, hostname


FETCH_TIMEOUT_SEC = 12.0
MAX_HTML_BYTES = 2_500_000
MIN_TEXT_CHARS_FOR_IMPORT = 80


def _portal_js_warnings(hostname: str) -> list[str]:
    hn = hostname.lower()
    warns: list[str] = []
    if "linkedin.com" in hn:
        warns.append("LinkedIn often serves job content via JavaScript; extraction may be incomplete.")
    if "indeed." in hn or "indeed.com" in hn:
        warns.append("Indeed listings are frequently client-rendered; manual paste may be required.")
    if "naukri.com" in hn:
        warns.append("Naukri pages are often heavily scripted; pasted JD text is usually more reliable.")
    if any(x in hn for x in ("glassdoor.", "monster.", "ziprecruiter.")):
        warns.append(
            "This domain may hydrate job text in the browser — if import looks empty or minimal, paste the JD."
        )
    return warns


def _clean_title(html_title: Optional[str]) -> Optional[str]:
    if not html_title:
        return None
    title = html_title.strip()
    if len(title) < 2:
        return None
    parts = title.split("|")
    if parts:
        return parts[0].strip()[:200]
    return title[:200] or None


def _snippet_to_plain(html_or_text: str) -> str:
    if "<" not in html_or_text:
        return html_or_text.strip()
    frag = BeautifulSoup(html_or_text, "html.parser")
    return frag.get_text("\n", strip=True)


def _coerce_ld_value(val: Any) -> str:
    if val is None:
        return ""
    if isinstance(val, str):
        return _snippet_to_plain(val)
    if isinstance(val, dict):
        if "@value" in val:
            return _coerce_ld_value(val["@value"])
        if "value" in val:
            return _coerce_ld_value(val["value"])
        txt = val.get("name") or val.get("description")
        if txt:
            return _coerce_ld_value(txt)
        return ""
    if isinstance(val, list):
        return "\n".join(_coerce_ld_value(x) for x in val if x)
    return str(val)


def _iter_ld_root(data: Any) -> list[dict[str, Any]]:
    if isinstance(data, dict):
        if "@graph" in data:
            g = data["@graph"]
            return [x for x in g if isinstance(x, dict)]
        return [data]
    if isinstance(data, list):
        out: list[dict[str, Any]] = []
        for x in data:
            out.extend(_iter_ld_root(x))
        return out
    return []


def _is_job_posting(obj: dict[str, Any]) -> bool:
    t = obj.get("@type") or obj.get("type")
    if isinstance(t, list):
        return any(str(x) == "JobPosting" for x in t)
    return str(t) == "JobPosting"


def _extract_json_ld_job(soup: BeautifulSoup) -> tuple[str, Optional[str], Optional[str]]:
    """Return (description_text, title, company) from JSON-LD JobPosting."""
    desc_parts: list[str] = []
    best_title: Optional[str] = None
    best_company: Optional[str] = None

    for script in soup.find_all("script", attrs={"type": True}):
        st = str(script.get("type", "")).lower()
        if "ld+json" not in st:
            continue
        raw = script.string or script.get_text() or ""
        raw = raw.strip()
        if not raw:
            continue
        try:
            data = json.loads(raw)
        except (json.JSONDecodeError, TypeError):
            continue
        for obj in _iter_ld_root(data):
            if not isinstance(obj, dict) or not _is_job_posting(obj):
                continue
            d = _coerce_ld_value(obj.get("description"))
            if d and len(d) > 10:
                desc_parts.append(d)
            tit = obj.get("title") or obj.get("name")
            if isinstance(tit, str) and tit.strip():
                best_title = tit.strip()[:200]
            org = obj.get("hiringOrganization") or obj.get("employer")
            if isinstance(org, dict):
                cn = org.get("name")
                if isinstance(cn, str) and cn.strip():
                    best_company = cn.strip()[:120]
            elif isinstance(org, str) and org.strip():
                best_company = org.strip()[:120]

    merged = "\n\n".join(desc_parts).strip()[:200_000]
    return merged, best_title, best_company


def _extract_meta_descriptions(soup: BeautifulSoup) -> str:
    for prop in ("og:description", "twitter:description"):
        tag = soup.find("meta", property=prop) or soup.find("meta", attrs={"name": prop})
        if tag and tag.get("content"):
            t = tag["content"].strip()
            if len(t) > 5:
                return t[:200_000]
    meta = soup.find("meta", attrs={"name": re.compile(r"^description$", re.I)})
    if meta and meta.get("content"):
        return str(meta["content"]).strip()[:200_000]
    return ""


def _extract_structural(soup: BeautifulSoup) -> str:
    selectors = (
        '[class*="job-description"]',
        '[class*="jobDescription"]',
        '[data-testid*="jobDescription"]',
        '[class*="jobdescription"]',
    )
    for sel in selectors:
        try:
            nodes = soup.select(sel)
        except Exception:  # noqa: BLE001
            nodes = []
        for n in nodes:
            txt = n.get_text("\n", strip=True)
            if len(txt) > 40:
                return txt.strip()[:200_000]

    root = soup.find("main") or soup.find("article")
    if root:
        chunks: list[str] = []
        for el in root.find_all(["p", "li", "h2", "h3", "h4"], limit=400):
            t = el.get_text(" ", strip=True)
            if len(t) > 2:
                chunks.append(t)
        joined = "\n".join(chunks).strip()
        if joined:
            return joined[:200_000]
        return root.get_text("\n", strip=True)[:200_000]

    body = soup.body
    if body is None:
        return ""

    segments: list[str] = []
    for el in body.find_all(["p", "li", "h1", "h2", "h3", "h4"], limit=600):
        t = el.get_text(" ", strip=True)
        if len(t) > 2:
            segments.append(t)
    joined = "\n".join(segments).strip()
    if len(joined) < MIN_TEXT_CHARS_FOR_IMPORT:
        joined = body.get_text("\n", strip=True)
        joined = "\n".join(line for line in joined.split("\n") if line.strip())

    return joined.strip()[:200_000]


def _pipeline_description(soup_ld: BeautifulSoup, soup_plain: BeautifulSoup) -> Tuple[str, str, str, str]:
    ld_text, _, _ = _extract_json_ld_job(soup_ld)
    meta_txt = _extract_meta_descriptions(soup_plain)
    struct_txt = _extract_structural(soup_plain)

    body_root = soup_plain.body or soup_plain
    segments: list[str] = []
    for el in body_root.find_all(["p", "li"], limit=700):
        t = el.get_text(" ", strip=True)
        if len(t) > 2:
            segments.append(t)
    body_txt = "\n".join(segments).strip()
    if len(body_txt) < MIN_TEXT_CHARS_FOR_IMPORT:
        body_txt = "\n".join(
            line for line in body_root.get_text("\n", strip=True).split("\n") if line.strip()
        )

    body_txt = body_txt.strip()[:200_000]
    return ld_text.strip(), meta_txt.strip(), struct_txt.strip(), body_txt.strip()


def _pick_description_in_order(ld: str, meta: str, struct: str, body: str) -> str:
    for chunk in (ld, meta, struct, body):
        if chunk and len(chunk.strip()) >= MIN_TEXT_CHARS_FOR_IMPORT:
            return chunk.strip()
    return max((ld, meta, struct, body), key=len)


def _prepare_soups(html: bytes) -> tuple[BeautifulSoup, BeautifulSoup]:
    soup_ld = BeautifulSoup(html, "html.parser")
    soup_plain = BeautifulSoup(html, "html.parser")
    for tag in soup_plain(["script", "style", "noscript"]):
        tag.decompose()
    return soup_ld, soup_plain


def classify_import(
    best_text: str,
    *,
    ld_title: Optional[str],
    ld_company: Optional[str],
    html_title_fallback: Optional[str],
) -> ImportPreviewApiV1:
    title = ld_title or html_title_fallback
    company = ld_company

    has_useful_body = len(best_text.strip()) >= MIN_TEXT_CHARS_FOR_IMPORT
    warnings: list[str] = []

    if has_useful_body:
        mode: Mode = "imported_full"
    elif title or ld_company:
        mode = "imported_partial"
        warnings.append(
            "Title imported, description not extracted. Paste JD manually to continue."
        )
    else:
        mode = "fallback_required"
        warnings.append("Could not extract enough job-like text.")

    return ImportPreviewApiV1(
        mode=mode,
        title=title,
        company=company,
        raw_text=best_text.strip()[:200_000] if best_text.strip() else None,
        warnings=warnings,
    )


def fetch_import_preview(url_str: str) -> ImportPreviewApiV1:
    warnings: list[str] = []

    try:
        _, hostname = assert_public_http_url(url_str)
    except (ValueError, OSError) as e:
        return ImportPreviewApiV1(
            mode="fallback_required",
            warnings=[f"URL validation failed: {e}"],
        )

    warnings.extend(_portal_js_warnings(hostname))

    try:
        with httpx.Client(
            timeout=FETCH_TIMEOUT_SEC,
            headers={
                "User-Agent": (
                    "ResumeJobDashboard/1.0 "
                    "(import-preview; generic public page extraction)"
                )
            },
            follow_redirects=True,
        ) as client:
            r = client.get(url_str)
        assert_public_http_url(str(r.url))
    except Exception as exc:  # noqa: BLE001
        return ImportPreviewApiV1(mode="fallback_required", warnings=warnings + [f"Fetch failed: {exc}"])

    if r.status_code >= 400:
        return ImportPreviewApiV1(
            mode="fallback_required",
            warnings=warnings + [f"HTTP status {r.status_code}"],
        )

    body = r.content[:MAX_HTML_BYTES]
    ctype = r.headers.get("content-type", "")

    if "html" not in ctype.lower():
        txt = ""
        if body:
            txt = body.decode("utf-8", errors="replace").strip()
        if txt and len(txt) >= MIN_TEXT_CHARS_FOR_IMPORT:
            return ImportPreviewApiV1(
                mode="imported_full",
                title=None,
                company=None,
                raw_text=txt[:200_000],
                warnings=warnings + ["Non-HTML response; text used as-is."],
            )
        return ImportPreviewApiV1(
            mode="fallback_required",
            warnings=warnings + ["Not an HTML page and text was insufficient."],
        )

    soup_ld, soup_plain = _prepare_soups(body)

    _, ld_title_from_ld, ld_company_from_ld = _extract_json_ld_job(soup_ld)

    ld_d, meta_d, struct_d, body_d = _pipeline_description(soup_ld, soup_plain)
    picked = _pick_description_in_order(ld_d, meta_d, struct_d, body_d)

    html_tt = soup_plain.find("title")
    html_clean = _clean_title(html_tt.get_text(" ", strip=True) if html_tt else None)

    merged_result = classify_import(
        picked,
        ld_title=ld_title_from_ld or None,
        ld_company=ld_company_from_ld or None,
        html_title_fallback=html_clean,
    )
    merged_warnings = warnings + merged_result.warnings

    return ImportPreviewApiV1(
        mode=merged_result.mode,
        title=merged_result.title,
        company=merged_result.company,
        raw_text=merged_result.raw_text,
        warnings=merged_warnings if merged_warnings else merged_result.warnings,
    )
