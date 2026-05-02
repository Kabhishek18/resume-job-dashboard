from __future__ import annotations

from typing import Any

from app.services.jobs.collectors.jobspy_collector import collect_jobspy
from app.services.jobs.collectors.types import CollectedRow, PortalRunOutcome


def run_collectors_for_profile(
    profile: dict[str, Any],
) -> tuple[list[CollectedRow], dict[str, PortalRunOutcome], str | None]:
    """Run JobSpy for all selected portals; merge rows and per-portal outcomes."""
    return collect_jobspy(profile)
