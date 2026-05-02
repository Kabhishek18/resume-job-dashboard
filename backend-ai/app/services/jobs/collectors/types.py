from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Literal

PortalId = Literal[
    "linkedin",
    "naukri",
    "glassdoor",
    "indeed",
    "zip_recruiter",
    "google",
    "bayt",
    "bdjobs",
    "other",
]
PortalState = Literal["ok", "no_results", "unavailable"]


@dataclass
class CollectedRow:
    title: str
    company: str
    location: str
    portal: str
    apply_url: str = ""
    source_url: str = ""
    salary_text: str = ""
    posted_at: str | None = None
    description_snippet: str = ""
    external_job_id: str | None = None
    raw_meta: dict[str, Any] = field(default_factory=dict)


@dataclass
class CollectorResult:
    rows: list[CollectedRow]
    warnings: list[str] = field(default_factory=list)


@dataclass
class PortalRunOutcome:
    row_count: int
    state: PortalState


CollectorFn = Callable[[dict[str, Any]], CollectorResult]

PORTAL_IDS: tuple[PortalId, ...] = (
    "linkedin",
    "naukri",
    "glassdoor",
    "indeed",
    "zip_recruiter",
    "google",
    "bayt",
    "bdjobs",
    "other",
)

_ALIAS_TO_CANONICAL: dict[str, PortalId] = {
    "ziprecruiter": "zip_recruiter",
    "zip recruiter": "zip_recruiter",
    "bd_jobs": "bdjobs",
    "bd-jobs": "bdjobs",
}


def normalize_portal_id(p: str) -> PortalId:
    lp = (p or "").lower().strip()
    if lp in PORTAL_IDS:
        return lp  # type: ignore[return-value]
    if lp in _ALIAS_TO_CANONICAL:
        return _ALIAS_TO_CANONICAL[lp]
    return "other"
