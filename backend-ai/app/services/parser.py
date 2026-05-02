from app.schemas.job import JobDescriptionInput
from app.schemas.resume import ParseResumeRequest, ParseResumeResponse, ParsedResume
from app.utils.text_cleaner import normalize_text

# Stub: pretend keywords from resume
DEFAULT_SKILLS = ["python", "fastapi", "sql"]


def parse_resume(request: ParseResumeRequest) -> ParseResumeResponse:
    cleaned = normalize_text(request.raw_text)
    text_lower = cleaned.lower()
    skills = [s for s in DEFAULT_SKILLS if s in text_lower]
    if not skills and cleaned:
        skills = ["general"]

    parsed = ParsedResume(
        skills=skills[:20],
        experience_years_est=3.0,
        education=[],
        tools=[t for t in ["docker", "kubernetes", "aws"] if t in text_lower],
        keywords=list(dict.fromkeys(cleaned.split()[:30])),
    )
    preview = cleaned[:500] + ("…" if len(cleaned) > 500 else "")
    return ParseResumeResponse(parsed=parsed, cleaned_text_preview=preview)


def parse_raw_for_match(raw: str) -> ParsedResume:
    return parse_resume(ParseResumeRequest(raw_text=raw)).parsed


def extract_job_keywords(job: JobDescriptionInput) -> set[str]:
    blob = normalize_text(f"{job.title or ''} {job.company or ''} {job.raw_text}")
    words = {w.lower().strip(".,;:()[]") for w in blob.split() if len(w) > 2}
    return words
