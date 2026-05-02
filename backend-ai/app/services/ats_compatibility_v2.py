"""Text-first ATS compatibility score (resume only)."""

from __future__ import annotations

from app.services.resume_parse_v2 import ResumeFeaturesV2


def compute_ats(f: ResumeFeaturesV2) -> tuple[float, list[str]]:
    """
    Components (weighted, sum 100):
    20 section completeness | 15 contact | 20 chronology | 15 skill surfacing |
    15 bullets/readability | 15 hygiene
    """

    reasons: list[str] = []
    section_keys = ["experience", "education", "skills", "summary", "projects", "certifications"]
    nonempty = sum(1 for k in section_keys if len((f.sections.get(k, "") or "").strip()) >= 24)
    section_pts = (nonempty / max(1, len(section_keys))) * 20.0
    if nonempty >= 4:
        reasons.append("Multiple resume sections detected with substantive content.")

    contact_pts = 0.0
    if f.contact_emails:
        contact_pts += 7.0
        reasons.append("Email contact signal present.")
    if f.contact_phones:
        contact_pts += 5.0
        reasons.append("Phone-like contact pattern detected.")
    if f.has_linkedin:
        contact_pts += 3.0
        reasons.append("LinkedIn-style profile hint present.")
    contact_pts = min(15.0, contact_pts)
    if contact_pts < 6:
        reasons.append("Limited explicit contact cues—consider adding verified email or phone.")

    chrono_pts = min(20.0, float(f.date_spans_approx) * 3.2 + float(f.degree_hits))
    if chrono_pts < 8:
        reasons.append("Weak date/chronology signals—ATS parsers prefer clear role timelines.")
    elif chrono_pts >= 12:
        reasons.append("Detected date anchors that improve timeline readability.")

    skills_block = len((f.sections.get("skills", "") or "").strip())
    skill_surface = skills_block >= 28 or len(f.resume_canonical_skills) >= 4
    skill_pts = 9.0 if skill_surface else 3.5
    if f.cert_entity_hits:
        skill_pts += min(6.0, f.cert_entity_hits * 2.0)
    skill_pts = min(15.0, skill_pts)
    if not skill_surface:
        reasons.append("Skills/tools could be surfaced in a tighter dedicated section.")

    br = min(1.0, float(f.bullet_lines) / max(6, int(f.non_empty_lines * 0.35)))
    bullet_pts = 15.0 * (0.25 + 0.75 * br)
    wall_penalty = float(f.long_line_ratio)
    bullet_pts *= max(0.35, 1.0 - 0.65 * wall_penalty)
    bullet_pts = min(15.0, bullet_pts)
    if wall_penalty > 0.45:
        reasons.append("Long dense paragraphs detected—prefer bullet structure for parsers.")

    hyg = 15.0
    hyg *= max(0.2, 1.0 - 1.35 * float(f.duplicate_line_ratio))
    hyg *= max(0.2, 1.0 - min(1.6, float(f.tab_density) * 22.0))
    if float(f.noise_token_hits) > len(f.full_text_norm) * 0.12:
        hyg -= 4.0
        reasons.append("High single-character fragment density—possible extraction noise.")
    hyg = max(0.0, min(15.0, hyg))

    total = section_pts + contact_pts + chrono_pts + skill_pts + bullet_pts + hyg
    total = round(max(0.0, min(100.0, total)), 1)
    if total < 50:
        reasons.append("Aggregate ATS parse readiness is below midpoint—prioritize cleaner structure.")

    dedup_reasons = []
    seen = set()
    for r in reasons:
        if r not in seen:
            seen.add(r)
            dedup_reasons.append(r)
    return total, dedup_reasons[:10]
