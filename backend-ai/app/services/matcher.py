"""Deterministic stub matcher for resume vs job description.

Scoring rules (v1):
- Overall ``score`` is in [0, 100], rounded to one decimal for responses.
- Sub-scores (skill_match, experience_match, keyword_ats_match, context_fit) are each
  in [0, 100]. They are independent dimensions; they do not sum to 100.
- Overall is a weighted blend: 40% skill_match + 25% experience_match
  + 20% keyword_ats_match + 15% context_fit.
- ``context_fit`` in this stub is (skill_match + keyword_ats_match) / 2. A future
  implementation that changes semantics should bump the API contract version.
- Same inputs produce the same outputs (no randomness; missing skills are sorted).
"""

from app.schemas.match import MatchRequest, MatchResult
from app.services import parser


def _overlap_score(a: set[str], b: set[str]) -> float:
    if not a or not b:
        return 0.0
    inter = len(a & b)
    union = len(a | b)
    return 100.0 * inter / union if union else 0.0


def score_match(request: MatchRequest) -> MatchResult:
    parsed = parser.parse_raw_for_match(request.raw_resume_text)

    job_kw = parser.extract_job_keywords(request.job)
    resume_skills = {s.lower() for s in parsed.skills}
    resume_kw = {k.lower() for k in parsed.keywords[:50]}

    skill_match = min(100.0, 40.0 + _overlap_score(resume_skills, job_kw))
    exp = parsed.experience_years_est or 0.0
    experience_match = min(100.0, 25.0 + min(exp * 8.0, 75.0))
    keyword_ats_match = _overlap_score(resume_kw, job_kw)
    context_fit = (skill_match + keyword_ats_match) / 2

    score = (
        0.40 * skill_match
        + 0.25 * experience_match
        + 0.20 * keyword_ats_match
        + 0.15 * context_fit
    )

    missing = sorted(job_kw - resume_skills - resume_kw)[:15]
    missing_skills = missing[:10] if missing else ["(stub) add more JD-specific requirements"]

    suggestions = []
    if skill_match < 60:
        suggestions.append("Surface more matching skills from your experience in the resume.")
    if keyword_ats_match < 40:
        suggestions.append("Mirror important phrases from the job description (honestly) in your summary or bullets.")
    if not suggestions:
        suggestions.append("Stub matcher: replace with embeddings + LLM for real suggestions tied to this JD.")

    weak = []
    if experience_match < 50:
        weak.append("Experience depth vs role")

    return MatchResult(
        score=round(score, 1),
        skill_match=round(skill_match, 1),
        experience_match=round(experience_match, 1),
        keyword_ats_match=round(keyword_ats_match, 1),
        context_fit=round(context_fit, 1),
        missing_skills=missing_skills,
        suggestions=suggestions,
        weak_areas=weak,
    )
