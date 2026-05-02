import hashlib
import json

from app.schemas.tailor_contract import TailorApiV1, TailorRequest, TailorReview, TailoredResumeOut

from .base import TailoringService


def _stub_seed(body: TailorRequest) -> str:
    snap_data = body.match_snapshot.model_dump() if body.match_snapshot else None
    snap_v2_data = body.match_snapshot_v2.model_dump() if body.match_snapshot_v2 else None
    payload = {
        "resume": body.resume_text.strip().lower()[:8000],
        "job_raw": body.job.raw_text.strip().lower()[:8000],
        "job_meta": {
            "title": body.job.title,
            "company": body.job.company,
            "url": str(body.job.url) if body.job.url else None,
        },
        "snap": snap_data,
        "snap_v2": snap_v2_data,
        "cov": body.include_cover_letter,
    }
    raw = json.dumps(payload, sort_keys=True)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


class StubTailoringService(TailoringService):
    ADD_CATALOG = (
        "JD keyword alignment in summary for the role's core stack.",
        "One metric-driven bullet mirroring JD outcomes language.",
        "Skills line echoing tooling named in posting (truthfully).",
    )
    REMOVE_CATALOG = (
        "Outdated toolchain callouts unrelated to JD.",
        "Buzzwords duplicated between summary and bullets.",
        "Stale internship bullets for senior-scope roles.",
    )
    IMPROVE_CATALOG = (
        "Tighten first bullet around API ownership and uptime.",
        "Quantify backlog impact (% time saved, latency).",
        "Align role titles with title level in posting.",
    )
    COVER_STUB = (
        "I am interested in contributing to priorities described in your posting "
        "(stub tailoring). I bring relevant backend experience aligned with "
        "your team's focus areas noted in the JD."
    )

    def tailor(self, body: TailorRequest) -> TailorApiV1:
        seed = _stub_seed(body)
        ix = int(seed[:8], 16)

        def pick(cat: tuple[str, ...], n: int) -> list[str]:
            return [cat[(ix + j) % len(cat)] for j in range(n)]

        summary = (
            "Stub-tailored summary: emphasize overlap with JD themes while keeping factual claims. "
            f"(seed:{seed[:12]})"
        )
        bullets = [
            "Stub bullet A: outcome + tool from resume/JD overlap.",
            "Stub bullet B: collaboration + measurable delivery cue.",
            f"Stub bullet C: reinforcement token {seed[12:18]}.",
        ]
        review = TailorReview(
            add=pick(self.ADD_CATALOG, min(3, len(self.ADD_CATALOG))),
            remove=pick(self.REMOVE_CATALOG, min(2, len(self.REMOVE_CATALOG))),
            improve=pick(self.IMPROVE_CATALOG, min(2, len(self.IMPROVE_CATALOG))),
        )

        cover = self.COVER_STUB + f" ref:{seed[18:26]}" if body.include_cover_letter else None
        return TailorApiV1(
            provider_mode="stub",
            review=review,
            tailored_resume=TailoredResumeOut(summary=summary, bullets=bullets),
            cover_letter=cover,
        )
