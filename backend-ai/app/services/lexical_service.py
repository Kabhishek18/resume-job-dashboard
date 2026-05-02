"""In-process BM25 with section boosts (no Elasticsearch)."""

from __future__ import annotations

import math
import re
from typing import Sequence

try:
    from rank_bm25 import BM25Okapi
except ImportError:
    BM25Okapi = None  # type: ignore

_TOKEN = re.compile(r"[a-z0-9][a-z0-9/+.-]*", re.I)


def tokenize(doc: str) -> list[str]:
    return _TOKEN.findall(doc.lower())


SECTION_ORDER_KEYS = ["skills", "experience", "projects", "summary", "certifications", "education", "other"]
SECTION_BOOST = {
    "skills": 1.6,
    "experience": 1.4,
    "projects": 1.4,
    "summary": 1.2,
    "certifications": 1.0,
    "education": 0.7,
    "other": 1.0,
}


def bm25_lexical_score(
    sections: dict[str, str],
    query_parts: Sequence[str],
) -> float:
    """Return 0-100 lexical relevance with section boosts."""

    docs: list[list[str]] = []
    boosts: list[float] = []
    for k in SECTION_ORDER_KEYS:
        text = sections.get(k, "") or ""
        docs.append(tokenize(text))
        boosts.append(SECTION_BOOST.get(k, 1.0))
    if BM25Okapi is None:
        raise RuntimeError("rank-bm25 is required for match_v2")
    bm = BM25Okapi(docs)
    q_tokens: list[str] = []
    for p in query_parts:
        q_tokens.extend(tokenize(str(p)))
    q_tokens = sorted(set(q_tokens))
    if not q_tokens:
        q_tokens = ["role"]
    scores = bm.get_scores(q_tokens)
    weighted_sum = sum(float(scores[i]) * boosts[i] for i in range(len(docs)))
    wsum = sum(boosts)
    raw = weighted_sum / max(1e-9, wsum)
    # Map BM25 aggregate to [0,100] — bounded curve (short single-resume corpuses skew low raw).
    normed = 100.0 * math.tanh(min(raw / 3.8, 4.5))
    return float(max(0.0, min(100.0, normed)))
