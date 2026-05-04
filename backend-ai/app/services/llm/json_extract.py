"""Strict JSON extraction for provider content (minimal salvage)."""

import json
import re


def strip_optional_json_fence(content: str) -> str:
    s = content.strip()
    fence = re.match(r"^```(?:json)?\s*\r?\n(.*?)\r?\n```\s*$", s, re.DOTALL | re.IGNORECASE)
    if fence:
        return fence.group(1).strip()
    return s


def parse_json_object_strict(content: str) -> dict:
    """Parse a single JSON object; strip one ```json fenced block only."""
    s = strip_optional_json_fence(content.strip())
    data = json.loads(s)
    if not isinstance(data, dict):
        raise ValueError("JSON root must be an object.")
    return data
