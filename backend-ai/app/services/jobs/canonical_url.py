"""Strip tracking fragments and normalize job apply URLs."""

from __future__ import annotations

from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

TRACKING_PARAMS = frozenset(
    {
        "ref",
        "refId",
        "source",
        "src",
        "trackingId",
        "trk",
        "campaignid",
        "mcid",
        "icid",
    }
)


def canonicalize_apply_url(raw: str) -> str:
    """Normalize URL for duplicate matching: no fragment; drop known tracking params; stable query order."""
    if not raw or not raw.strip():
        return ""
    url = raw.strip()
    parts = urlsplit(url)
    query_pairs = [(k, v) for k, v in parse_qsl(parts.query, keep_blank_values=False) if k.lower() not in TRACKING_PARAMS and not k.lower().startswith("utm_")]
    query_pairs.sort(key=lambda x: (x[0].lower(), x[1]))
    new_query = urlencode(query_pairs)
    rebuilt = urlunsplit((parts.scheme.lower() or parts.scheme, parts.netloc.lower() or parts.netloc, parts.path, new_query, ""))
    return rebuilt.rstrip("/") if rebuilt.endswith("/") and len(parts.path) > 1 else rebuilt


def posted_date_bucket(posted_at: str | None) -> str:
    """Coarse bucket for fingerprint dedupe."""
    if not posted_at:
        return "unknown"
    t = posted_at.strip()[:16]
    return t.lower()
