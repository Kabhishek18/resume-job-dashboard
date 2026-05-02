"""Job description feature extraction for match v2."""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from app.schemas.job import JobDescriptionInput
from app.services.skill_canonicalization import extract_canonical_skills_from_blob, uniq_sorted
from app.utils.text_cleaner import normalize_text

_SENIORITY_ORDER = {
    "intern": 0,
    "junior": 1,
    "associate": 1,
    "mid": 2,
    "engineer": 2,
    "senior": 3,
    "staff": 4,
    "principal": 5,
    "lead": 4,
    "manager": 4,
    "director": 6,
    "head": 6,
    "vp": 7,
    "chief": 8,
}

_SOFT = frozenset(
    {
        "communication",
        "leadership",
        "collaboration",
        "teamwork",
        "problem solving",
        "stakeholder",
        "mentoring",
    }
)


@dataclass
class JobFeaturesV2:
    title_text: str
    raw_norm: str
    hard_skills: set[str] = field(default_factory=set)
    soft_skills: set[str] = field(default_factory=set)
    responsibilities_blob: str = ""
    qualifiers: list[str] = field(default_factory=list)
    seniority_terms: list[str] = field(default_factory=list)
    domain_terms: list[str] = field(default_factory=list)
    seniority_rank: int = 2


def _infer_seniority_rank(title: str, blob: str) -> int:
    text = (title + " " + blob).lower()
    # Intern / internship dominates generic "engineer" tokens in compound titles.
    if re.search(r"\bintern(ship)?\b|\bstudent\b", text):
        return _SENIORITY_ORDER["intern"]
    best = 2
    for term, rank in _SENIORITY_ORDER.items():
        if term in text:
            best = max(best, rank)
    return best


def extract_domain_terms(blob: str) -> list[str]:
    # capitalized noun-ish tokens & fintech/saas heuristic
    found = []
    for m in re.finditer(r"\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+){0,2}\b", blob):
        w = m.group(0)
        if len(w) > 3 and w.lower() not in {"The", "We", "Our", "You", "Team"}:
            found.append(w.lower())
    for buzz in ("saas", "fintech", "e-commerce", "healthcare", "b2b", "platform", "api", "cloud"):
        if buzz in blob.lower():
            found.append(buzz)
    return uniq_sorted(found)[:25]


def parse_job_v2(job: JobDescriptionInput) -> JobFeaturesV2:
    title = normalize_text(job.title or "")
    company = normalize_text(job.company or "") if job.company else ""
    raw = normalize_text(job.raw_text or "")
    blob = normalize_text(f"{title}\n{company}\n{raw}")

    resp = blob
    m = re.search(r"(?i)(requirements|responsibilities|what you'?ll do|qualifications)\s*[:]?\s*\n(?P<body>.{20,})", blob)
    if m:
        resp = m.group("body")[:6000]

    hard = extract_canonical_skills_from_blob(blob)
    # soft skills heuristic
    soft = {s for s in _SOFT if s.replace(" ", "") in blob.lower().replace(" ", "") or s in blob.lower()}

    sen_terms = sorted({t for t in _SENIORITY_ORDER if t in blob.lower()} | {t for t in _SENIORITY_ORDER if t in title.lower()})
    qualifiers = uniq_sorted([ln.strip("-• ") for ln in resp.split("\n") if len(ln.strip()) > 5][:30])
    domains = extract_domain_terms(blob)
    sr = _infer_seniority_rank(title, blob)

    return JobFeaturesV2(
        title_text=title or raw.split("\n", 1)[0][:140],
        raw_norm=blob,
        hard_skills=hard,
        soft_skills=soft,
        responsibilities_blob=resp[:8000],
        qualifiers=qualifiers,
        seniority_terms=sen_terms,
        domain_terms=domains,
        seniority_rank=sr,
    )
