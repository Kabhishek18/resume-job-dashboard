"""Canonical skill keys and synonyms for deterministic matching."""

from __future__ import annotations

import re
from typing import Dict, Iterable, Set

# canonical key lowercase -> synonym phrases matched as substrings / tokens
SYNONYMS: Dict[str, tuple[str, ...]] = {
    "kubernetes": ("k8s", "kube", "container orchestration"),
    "docker": ("docker-compose",),
    "postgresql": ("postgres", "psql"),
    "mongodb": ("mongo ", "mongo,", "mongo\n"),
    "api development": ("rest api", "restful api", "rest apis", "web api"),
    "graphql": (" gql", "gql,", "gql\n"),
    "aws": ("amazon web services",),
    "gcp": ("google cloud platform", "google cloud"),
    "azure": ("microsoft azure",),
    "python": (),
    "fastapi": (),
    "django": (),
    "flask": (),
    "java": (),
    "typescript": (),
    "javascript": (),
    "react": ("react.js", "reactjs"),
    "kafka": (),
    "redis": (),
    "sql": (),
    "terraform": (),
    "ci cd": ("cicd", "continuous integration", "continuous delivery"),
    "machine learning": ("deep learning", " ml ", ", ml,", " ml\n"),
    "pandas": (),
    "spark": ("apache spark",),
    "go": (),  # token-only; substring " go " risky
}


def invert_synonyms() -> Dict[str, str]:
    m: Dict[str, str] = {}
    for canon, aliases in SYNONYMS.items():
        ck = canon.lower().strip()
        m[ck] = ck
        for a in aliases:
            ak = a.lower().strip()
            if ak:
                m[ak] = ck
    return m


_ALIAS_TO_CANONICAL = invert_synonyms()
_SORTED_KEYS = sorted(SYNONYMS.keys(), key=len, reverse=True)
_TOKEN_SPLIT = re.compile(r"[^\w/+.#\s-]+", re.UNICODE)
_WS = re.compile(r"\s+")


def normalize_whitespace(text: str) -> str:
    return _WS.sub(" ", text).strip()


def canonicalize_skill_phrase(phrase: str) -> str | None:
    raw = normalize_whitespace(phrase.lower()).strip()
    if not raw or len(raw) < 2:
        return None
    if raw in _ALIAS_TO_CANONICAL:
        return _ALIAS_TO_CANONICAL[raw]
    # handle multi-token glue
    for alias, canon in _ALIAS_TO_CANONICAL.items():
        if alias == raw:
            return canon
    return raw


def extract_canonical_skills_from_blob(blob: str) -> Set[str]:
    lowered = normalize_whitespace(blob.lower())
    seen: Set[str] = set()
    for key in _SORTED_KEYS:
        k = key.lower()
        if _word_boundary_contains(lowered, k):
            seen.add(k)
    for alias, canon in _ALIAS_TO_CANONICAL.items():
        if len(alias) >= 4 and alias in lowered:
            seen.add(canon)
    for t in _TOKEN_SPLIT.split(lowered):
        if len(t) < 2:
            continue
        tl = t.lower()
        ck = canonicalize_skill_phrase(tl)
        if ck and (ck in _ALIAS_TO_CANONICAL.values() or ck in SYNONYMS):
            seen.add(ck)
    # single-char lang token "go"
    tokens = lowered.replace(",", " ").split()
    if "go" in tokens or re.search(r"\bgo\b", lowered):
        if re.search(r"\b(golang|go developer|go engineer|software go)\b", lowered):
            seen.add("go")
    return seen


def _word_boundary_contains(text: str, needle: str) -> bool:
    pat = r"(?<![\w/+.#-])" + re.escape(needle) + r"(?![\w/+.#-])"
    return bool(re.search(pat, text, re.IGNORECASE))


def uniq_sorted(items: Iterable[str]) -> list[str]:
    return sorted({i.strip() for i in items if i and i.strip()})

