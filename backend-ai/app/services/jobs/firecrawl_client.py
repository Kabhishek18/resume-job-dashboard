"""Firecrawl v1 scrape API — render JS-heavy pages and return markdown (Naukri search fallback)."""

from __future__ import annotations

from typing import Tuple

import httpx

from app.core.config import settings


def firecrawl_configured() -> bool:
    """True when Firecrawl may be called (key present and not disabled via settings)."""
    return bool(settings.firecrawl_enabled) and bool((settings.firecrawl_api_key or "").strip())


def scrape_url_to_markdown(url: str, timeout: float = 60.0) -> Tuple[str, str]:
    """
    POST /v1/scrape. Returns (title_guess, markdown_or_plain_text).
    Raises on HTTP error or missing body.
    """
    key = (settings.firecrawl_api_key or "").strip()
    if not key:
        raise ValueError("Firecrawl API key not configured")

    base = (settings.firecrawl_api_url or "https://api.firecrawl.dev").rstrip("/")
    endpoint = f"{base}/v1/scrape"
    payload = {"url": url.strip(), "formats": ["markdown"]}

    with httpx.Client(timeout=timeout) as client:
        r = client.post(
            endpoint,
            headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
            json=payload,
        )
        r.raise_for_status()
        data = r.json()

    if not data.get("success"):
        err = data.get("error") or data.get("message") or "Firecrawl success=false"
        raise ValueError(str(err))

    inner = data.get("data") or {}
    md = (inner.get("markdown") or inner.get("content") or "").strip()
    meta = inner.get("metadata") or {}
    title = (meta.get("title") or meta.get("ogTitle") or "").strip()
    if not md and inner.get("html"):
        md = str(inner.get("html") or "")[:50_000]
    if not md:
        raise ValueError("Firecrawl returned empty content")
    return title, md[:50_000]
