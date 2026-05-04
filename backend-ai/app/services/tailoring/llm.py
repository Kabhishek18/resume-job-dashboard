"""OpenRouter-backed resume tailoring."""

import json
import logging
from typing import Callable

from app.core.config import settings
from app.schemas.tailor_contract import (
    TailorApiV1,
    TailorRequest,
    TailorStructuredContent,
)
from app.services.llm import generate_structured_json
from app.services.llm.contracts import ChatMessage, StructuredJsonGenerationSpec

from .base import TailoringService

_log = logging.getLogger(__name__)


def _build_tailoring_messages(body: TailorRequest) -> list[ChatMessage]:
    job_j = json.dumps(body.job.model_dump(mode="json", exclude_none=True), sort_keys=True, ensure_ascii=False)
    resume_section = body.resume_text.strip()

    if body.match_snapshot is not None:
        snap_v1 = json.dumps(body.match_snapshot.model_dump(mode="json"), sort_keys=True, ensure_ascii=False)
    else:
        snap_v1 = "null"

    if body.match_snapshot_v2 is not None:
        snap_v2 = json.dumps(body.match_snapshot_v2.model_dump(mode="json"), sort_keys=True, ensure_ascii=False)
    else:
        snap_v2 = "null"

    if body.include_cover_letter:
        cover_rule = (
            'Set JSON key cover_letter to a non-empty string containing a concise professional cover letter.'
        )
    else:
        cover_rule = (
            'Set JSON key cover_letter to JSON null exactly. Omit any prose outside the JSON object.'
        )

    schema_rules = (
        "Output exactly one JSON object (no markdown, no preamble) with these keys:\n"
        '- "review": object with string arrays "add", "remove", "improve".\n'
        '- "tailored_resume": object with string "summary" and string array "bullets".\n'
        f'- "cover_letter": string or JSON null — {cover_rule}\n'
        'Do not include "version", "provider_mode", or any extra top-level keys.'
    )

    user_content = (
        "## Role\n"
        "You tailor resumes to jobs using only truthful material from the candidate resume. "
        "Do not invent employers, titles, dates, degrees, certifications, tools, or skills not supported by "
        "the resume text. Prefer JD-aligned wording when it matches real experience.\n\n"
        f"## Constraints\n{schema_rules}\n\n"
        "## JobPosting JSON\n"
        f"{job_j}\n\n"
        "## ResumeText\n"
        f"{resume_section}\n\n"
        "## MatchSnapshotV1 JSON (or null)\n"
        f"{snap_v1}\n\n"
        "## MatchSnapshotV2 JSON (or null)\n"
        f"{snap_v2}\n\n"
        "## Requirement\nRespond with JSON only."
    )

    return [
        ChatMessage(role="system", content="You respond with a single JSON object only; no prose or code fences."),
        ChatMessage(role="user", content=user_content),
    ]


def _tailor_cover_post_validate(
    body: TailorRequest,
) -> Callable[[TailorStructuredContent], None]:
    """Raises ValueError → gateway retries next model."""

    def _pv(content: TailorStructuredContent) -> None:
        if body.include_cover_letter:
            if not (content.cover_letter and str(content.cover_letter).strip()):
                raise ValueError("cover_letter must be a non-empty string when include_cover_letter is true.")
        else:
            if content.cover_letter is not None and str(content.cover_letter).strip():
                raise ValueError("cover_letter must be null when include_cover_letter is false.")

    return _pv


class LLMTailoringService(TailoringService):
    def tailor(self, body: TailorRequest) -> TailorApiV1:
        messages = _build_tailoring_messages(body)
        spec = StructuredJsonGenerationSpec(messages=messages, use_json_object_response_format=True)

        validated = generate_structured_json(
            settings=settings,
            spec=spec,
            response_model=TailorStructuredContent,
            log=_log,
            post_validate=_tailor_cover_post_validate(body),
        )

        return TailorApiV1(
            version="v1",
            provider_mode="llm",
            review=validated.review,
            tailored_resume=validated.tailored_resume,
            cover_letter=validated.cover_letter if body.include_cover_letter else None,
        )
