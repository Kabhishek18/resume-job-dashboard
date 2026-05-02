"""CSV serialization for aggregated job rows."""

from __future__ import annotations

import csv
from io import StringIO
from typing import Any, Iterable


def aggregated_jobs_to_csv_rows(rows: Iterable[dict[str, Any]]) -> str:
    fieldnames = [
        "id",
        "portal",
        "title",
        "company",
        "location",
        "posted_at",
        "salary_text",
        "apply_url",
        "description_snippet",
        "duplicate_count",
        "board_status",
        "source_count",
    ]
    buf = StringIO()
    writer = csv.DictWriter(buf, fieldnames=fieldnames, extrasaction="ignore", quoting=csv.QUOTE_MINIMAL)
    writer.writeheader()
    for row in rows:
        writer.writerow(row)
    return buf.getvalue()
