"""Orchestrate parsers, ATS, embeddings, BM25, explanation for match v2."""

from __future__ import annotations

import re
from typing import Sequence

import numpy as np

from app.schemas.match import MatchRequest
from app.schemas.match_v2 import BandedBucket, MatchApiV2, band_from_score
from app.services import embedding_service as emb
from app.services.ats_compatibility_v2 import compute_ats
from app.services.job_parse_v2 import JobFeaturesV2, parse_job_v2
from app.services.lexical_service import bm25_lexical_score
from app.services.resume_parse_v2 import parse_resume_v2
from app.services.skill_canonicalization import uniq_sorted

_SEMANTIC_NEAR = 0.72

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


def _resume_seniority_rank(text: str, title_guess: str) -> int:
    blob = (title_guess + " " + text).lower()
    if re.search(r"\bintern(ship)?\b|\bstudent\b", blob):
        return _SENIORITY_ORDER["intern"]
    best = 2
    for term, rank in _SENIORITY_ORDER.items():
        if term in blob:
            best = max(best, rank)
    return best


def _jaccard(a: set[str], b: set[str]) -> float:
    if not a or not b:
        return 0.0
    inter = len(a & b)
    union = len(a | b)
    return 100.0 * inter / union if union else 0.0


def _token_overlap(a: str, b: str) -> float:
    ta = set(re.findall(r"[a-z0-9]+", a.lower()))
    tb = set(re.findall(r"[a-z0-9]+", b.lower()))
    ta = {t for t in ta if len(t) > 2}
    tb = {t for t in tb if len(t) > 2}
    if not ta or not tb:
        return 0.0
    return 100.0 * len(ta & tb) / len(ta | tb)


def _chunk_exp_sim(
    resume_sections: dict[str, str],
    jd_resp: str,
    encode,
) -> float:
    blob = (resume_sections.get("experience", "") + "\n" + resume_sections.get("projects", "")).strip()
    chunks = emb.chunked_windows(blob, 280, 140)
    if not chunks or not jd_resp.strip():
        return 0.0
    ch = encode(chunks)
    jd_v = encode([jd_resp[:6000]])[0]
    dots = ch @ jd_v
    if dots.size == 0:
        return 0.0
    return float(max(0.0, min(1.0, 0.55 * float(np.max(dots)) + 0.45 * float(np.mean(dots)))))


def _semantic_similarity_composite(
    full_resume: str,
    full_jd: str,
    resume_sections: dict[str, str],
    jd: JobFeaturesV2,
    encode,
) -> float:
    pair = encode([full_resume[:12000], full_jd[:12000]])
    c_full = float(np.dot(pair[0], pair[1])) if pair.shape[0] == 2 else 0.0
    c_full = max(0.0, min(1.0, c_full))

    c_chunk = _chunk_exp_sim(resume_sections, jd.responsibilities_blob, encode)

    left_ss = (resume_sections.get("summary", "") + "\n" + resume_sections.get("skills", ""))[:4000]
    right = (jd.title_text + "\n" + " ".join(sorted(jd.hard_skills)))[:4000]
    if not left_ss.strip() or not right.strip():
        c_ss = c_full
    else:
        pq = encode([left_ss, right])
        c_ss = float(np.dot(pq[0], pq[1]))
    c_ss = max(0.0, min(1.0, c_ss))

    return float((20.0 * c_full + 15.0 * c_chunk + 10.0 * c_ss) / 45.0 * 100.0)


def _missing_and_semantic(
    jd_skills: set[str],
    resume_canon: set[str],
    phrases: Sequence[str],
    encode,
) -> tuple[list[str], list[str]]:
    if not jd_skills:
        return [], []

    resume_list = sorted(resume_canon)
    phrase_list = uniq_sorted([p for p in phrases if len(p) > 1])[:60]
    texts_to_encode = sorted(jd_skills) + resume_list + phrase_list
    if not texts_to_encode:
        return [], []
    mtx = encode(texts_to_encode)
    idx = {t: i for i, t in enumerate(texts_to_encode)}

    missing: list[str] = []
    matches: list[str] = []
    for jd_s in sorted(jd_skills):
        if jd_s in resume_canon:
            continue
        vj = mtx[idx[jd_s]]
        best = 0.0
        best_label = ""
        for cand in list(resume_canon) + phrase_list:
            sim = float(np.dot(vj, mtx[idx[cand]]))
            if sim > best:
                best = sim
                best_label = cand
        if best >= _SEMANTIC_NEAR and best_label:
            matches.append(f"JD skill “{jd_s}” ≈ resume signal “{best_label}” (semantic match).")
        else:
            missing.append(jd_s)

    return missing, matches


def score_match_v2(body: MatchRequest) -> MatchApiV2:
    rf = parse_resume_v2(body.raw_resume_text)
    jf = parse_job_v2(body.job)

    encode = emb.encode_texts

    ats_score, ats_reasons = compute_ats(rf)
    ats_bucket = BandedBucket(score=ats_score, band=band_from_score(ats_score), reasons=ats_reasons[:6])

    semantic_sim = _semantic_similarity_composite(
        rf.full_text_norm,
        jf.raw_norm,
        rf.sections,
        jf,
        encode,
    )

    exact_overlap = _jaccard(rf.resume_canonical_skills, jf.hard_skills)

    query_bits: list[str] = list(jf.hard_skills) + jf.domain_terms + [jf.title_text]
    lexical = bm25_lexical_score(rf.sections, query_bits)

    head = (rf.sections.get("summary", "") or rf.sections.get("contact", ""))[:900]
    tv = encode([head, jf.title_text or "role"])
    title_cos = float(np.dot(tv[0], tv[1])) if tv.shape[0] == 2 else 0.0
    title_cos = max(0.0, min(1.0, title_cos))
    token_t = _token_overlap(head, jf.title_text) / 100.0
    title_align = (0.7 * title_cos + 0.3 * token_t) * 100.0

    r_rank = _resume_seniority_rank(rf.full_text_norm, head[:80])
    jd_rank = jf.seniority_rank
    exp_align = max(0.0, 100.0 - abs(jd_rank - r_rank) * 12.0)

    job_score = (
        0.45 * semantic_sim
        + 0.20 * exact_overlap
        + 0.15 * lexical
        + 0.10 * title_align
        + 0.10 * exp_align
    )
    job_score = round(max(0.0, min(100.0, job_score)), 1)

    missing_hs, sem_m = _missing_and_semantic(
        jf.hard_skills,
        rf.resume_canonical_skills,
        rf.skill_phrase_candidates + list(rf.resume_canonical_skills),
        encode,
    )

    comps = {
        "Semantic alignment": semantic_sim,
        "Exact hard-skill overlap": exact_overlap,
        "Lexical JD overlap (BM25-weighted)": lexical,
        "Title alignment": title_align,
        "Experience/seniority fit": exp_align,
    }
    sorted_weak = sorted(comps.items(), key=lambda kv: kv[1])

    strengths: list[str] = []
    for name, val in sorted(comps.items(), key=lambda kv: -kv[1])[:2]:
        if val >= 62:
            strengths.append(f"{name} is relatively strong ({val:.0f}/100).")
    for line in sem_m[:3]:
        strengths.append(line)

    actions: list[str] = []
    for name, val in sorted_weak[:2]:
        if val < 55:
            actions.append(
                f"Raise {name.lower()}: currently about {val:.0f}/100 — tighten resume against the JD.",
            )

    for sk in missing_hs[:4]:
        actions.append(f"Address missing or unclear hard skill: {sk}.")

    if not actions:
        actions.append("Polish wording to mirror JD outcomes while keeping factual claims.")

    why = [
        (
            f"Job Match blends semantic ({semantic_sim:.0f}), exact skills ({exact_overlap:.0f}), "
            f"lexical ({lexical:.0f}), title ({title_align:.0f}), and seniority ({exp_align:.0f}) signals."
        ),
        "Higher weight is on semantic similarity (45%) followed by exact skill overlap (20%).",
    ]

    jm_reasons = [f"{sorted_weak[0][0]} dragged the score ({sorted_weak[0][1]:.0f}/100)."]
    if missing_hs:
        jm_reasons.append("Outstanding hard-skill gaps flagged: " + ", ".join(missing_hs[:6]) + ".")

    job_bucket = BandedBucket(
        score=job_score,
        band=band_from_score(job_score),
        reasons=jm_reasons[:6],
    )

    return MatchApiV2(
        ats_compatibility=ats_bucket,
        job_match=job_bucket,
        semantic_similarity=round(semantic_sim, 1),
        exact_skill_overlap=round(exact_overlap, 1),
        lexical_match=round(lexical, 1),
        title_alignment=round(title_align, 1),
        experience_alignment=round(exp_align, 1),
        missing_hard_skills=missing_hs[:25],
        semantic_matches=sorted(sem_m)[:25],
        strengths=strengths[:10],
        actions=actions[:12],
        why_this_score=why,
    )
