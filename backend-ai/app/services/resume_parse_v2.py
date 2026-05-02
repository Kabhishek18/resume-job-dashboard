"""Rule-based resume sectioning and ATS-oriented features."""

from __future__ import annotations

import re
from collections import defaultdict
from dataclasses import dataclass, field

from app.services.nlp_v2 import get_v2_nlp, make_date_matcher
from app.services.skill_canonicalization import extract_canonical_skills_from_blob
from app.utils.text_cleaner import normalize_text

_SECTION_ALIASES: dict[str, tuple[str, ...]] = {
    "contact": ("contact", "contact information", "personal"),
    "summary": ("summary", "professional summary", "profile", "objective", "about me"),
    "skills": ("skills", "technical skills", "core competencies", "technologies", "tools"),
    "experience": (
        "experience",
        "work experience",
        "employment",
        "professional experience",
        "work history",
    ),
    "projects": ("projects", "selected projects"),
    "education": ("education", "academic"),
    "certifications": ("certifications", "licenses & certifications", "certificates"),
}

_HEADER_LINE = re.compile(
    r"^(\s*)(?P<title>[A-Za-z][A-Za-z0-9 &,/'+\-]{0,48})\s*$",
    re.MULTILINE,
)


@dataclass
class ResumeFeaturesV2:
    sections: dict[str, str]
    full_text_norm: str
    contact_emails: list[str] = field(default_factory=list)
    contact_phones: list[str] = field(default_factory=list)
    has_linkedin: bool = False
    date_spans_approx: int = 0
    degree_hits: int = 0
    cert_entity_hits: int = 0
    bullet_lines: int = 0
    non_empty_lines: int = 1
    duplicate_line_ratio: float = 0.0
    tab_density: float = 0.0
    long_line_ratio: float = 0.0
    noise_token_hits: int = 0
    resume_canonical_skills: set[str] = field(default_factory=set)
    skill_phrase_candidates: list[str] = field(default_factory=list)


def _normalize_header(h: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", h.lower()).strip()


def _match_section_key(line: str) -> str | None:
    t = _normalize_header(line)
    if len(t) < 3 or len(t) > 55:
        return None
    for key, aliases in _SECTION_ALIASES.items():
        for a in aliases:
            if t == a or t.startswith(a + " ") or t.endswith(" " + a):
                return key
            if a in t and len(t) - len(a) < 8:
                return key
    return None


def _split_sections(text: str) -> dict[str, list[str]]:
    lines = text.split("\n")
    current = "preamble"
    buckets: dict[str, list[str]] = defaultdict(list)

    for raw in lines:
        line = raw.strip()
        if not line:
            buckets[current].append("")
            continue
        key = _match_section_key(line)
        if key:
            current = key
            continue
        buckets[current].append(raw)

    return buckets


def _email_re() -> re.Pattern:
    return re.compile(r"[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}", re.I)


def _phone_re() -> re.Pattern:
    return re.compile(r"(\+?\d[\d\-\s().]{7,}\d)")


def parse_resume_v2(raw_resume_text: str) -> ResumeFeaturesV2:
    full = normalize_text(raw_resume_text)
    buckets = _split_sections(full)

    # Map buckets to normalized section keys; preamble -> contact/summary heuristics
    sections: dict[str, str] = {
        "contact": "",
        "summary": "",
        "skills": "",
        "experience": "",
        "projects": "",
        "education": "",
        "certifications": "",
        "other": "",
    }
    preamble = "\n".join(buckets.get("preamble", [])).strip()

    contact_from_header = "\n".join(buckets.get("contact", [])).strip()
    sections["contact"] = (contact_from_header or preamble[:1200]).strip()

    for key in sections:
        if key == "contact":
            continue
        if key in buckets:
            sections[key] = "\n".join(buckets[key]).strip()

    if not sections["summary"] and preamble:
        # try first paragraph as summary
        parts = re.split(r"\n\n+", preamble, maxsplit=1)
        if parts:
            sections["summary"] = parts[0][:1500]

    emails = _email_re().findall(full)
    phones = _phone_re().findall(full)
    has_li = bool(re.search(r"linkedin\.com/", full, re.I))

    lines = [ln for ln in full.split("\n") if ln.strip()]
    non_empty = max(1, len(lines))
    norm_lines = [ln.strip().lower() for ln in lines]
    dup = 0
    seen: set[str] = set()
    for ln in norm_lines:
        if ln in seen:
            dup += 1
        seen.add(ln)
    dup_ratio = dup / non_empty

    tab_chars = full.count("\t")
    tab_density = tab_chars / max(1, len(full))

    bulletish = sum(1 for ln in lines if re.match(r"^[\s•\-\*\+]\s+\S", ln) or ln.lstrip().startswith("•"))
    long_lines = sum(1 for ln in lines if len(ln) > 140)
    long_ratio = long_lines / non_empty

    # OCR-ish: lots of single-char tokens
    toks = re.findall(r"\b\w\b", full)
    noise = len(toks)

    nlp = get_v2_nlp()
    doc = nlp(full[:100_000])
    deg = sum(1 for e in doc.ents if e.label_ == "DEG")
    cert = sum(1 for e in doc.ents if e.label_ == "CERT")

    matcher = make_date_matcher()
    match_doc = nlp(full[:50_000])
    date_hits = len(matcher(match_doc))

    canon = extract_canonical_skills_from_blob(full)
    phrases = _skill_phrase_split(sections["skills"])

    return ResumeFeaturesV2(
        sections=sections,
        full_text_norm=full,
        contact_emails=emails[:5],
        contact_phones=phones[:5],
        has_linkedin=has_li,
        date_spans_approx=date_hits,
        degree_hits=deg,
        cert_entity_hits=cert,
        bullet_lines=bulletish,
        non_empty_lines=non_empty,
        duplicate_line_ratio=dup_ratio,
        tab_density=tab_density,
        long_line_ratio=long_ratio,
        noise_token_hits=noise,
        resume_canonical_skills=canon,
        skill_phrase_candidates=phrases,
    )


def _skill_phrase_split(skills_block: str) -> list[str]:
    if not skills_block:
        return []
    parts = re.split(r"[,;•\n|]+", skills_block)
    out = []
    for p in parts:
        t = p.strip()
        if 2 <= len(t) <= 80:
            out.append(t)
    return out[:80]
