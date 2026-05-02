import type { MatchApiV1 } from "@/types/match"

export type ScoreBand = "weak" | "needs_work" | "strong"

/** 0–39 weak, 40–69 needs work, 70–100 strong (inclusive). */
export function scoreBand(score: number): ScoreBand {
  if (score <= 39) return "weak"
  if (score <= 69) return "needs_work"
  return "strong"
}

export function verdictTitle(band: ScoreBand): string {
  switch (band) {
    case "weak":
      return "Weak match"
    case "needs_work":
      return "Needs work"
    case "strong":
      return "Strong match"
  }
}

/** Traffic-light visual for badge + border context. */
export function verdictHueClasses(band: ScoreBand): { badge: string; card: string } {
  switch (band) {
    case "weak":
      return {
        badge: "border-destructive/50 bg-destructive/10 text-destructive",
        card: "border-destructive/30 bg-destructive/5",
      }
    case "needs_work":
      return {
        badge: "border-amber-500/50 bg-amber-500/10 text-amber-950 dark:text-amber-100",
        card: "border-amber-500/25 bg-amber-500/5",
      }
    case "strong":
      return {
        badge: "border-emerald-500/50 bg-emerald-500/10 text-emerald-950 dark:text-emerald-200",
        card: "border-emerald-500/25 bg-emerald-500/5",
      }
  }
}

export function verdictExplanationLine(band: ScoreBand, score: number): string {
  switch (band) {
    case "weak":
      return `At ${score}/100, this resume is well short of the job profile—focus on skills, keywords, and proof of impact before applying.`
    case "needs_work":
      return `At ${score}/100, you are in range but several gaps remain—tighten alignment with the job description and missing skills.`
    case "strong":
      return `At ${score}/100, your resume lines up well with this posting—polish weak spots and tailor phrasing for the final pass.`
  }
}

type SubKey = "skill_match" | "experience_match" | "keyword_ats_match" | "context_fit"

const SUB_LABELS: Record<SubKey, string> = {
  skill_match: "Skills alignment with the role",
  experience_match: "Experience depth for this level",
  keyword_ats_match: "Keywords and ATS-relevant wording",
  context_fit: "Overall context and role fit",
}

function orderedSubscores(m: MatchApiV1): { key: SubKey; value: number }[] {
  const rows: { key: SubKey; value: number }[] = [
    { key: "skill_match", value: m.skill_match },
    { key: "experience_match", value: m.experience_match },
    { key: "keyword_ats_match", value: m.keyword_ats_match },
    { key: "context_fit", value: m.context_fit },
  ]
  rows.sort((a, b) => a.value - b.value)
  return rows
}

function uniqCap(items: string[], max: number): string[] {
  const seen = new Set<string>()
  const out: string[] = []
  for (const raw of items) {
    const t = raw.trim()
    if (!t || seen.has(t)) continue
    seen.add(t)
    out.push(t)
    if (out.length >= max) break
  }
  return out
}

/** Top drivers: missing and weak signals first; pad with weakest dimension labels. */
export function topReasonsFromMatch(m: MatchApiV1, max = 3): string[] {
  const fromData = uniqCap([...m.missing_skills, ...m.weak_areas], max)
  if (fromData.length >= max) return fromData

  const subs = orderedSubscores(m)
  const fillers: string[] = []
  for (const row of subs) {
    if (row.value >= 65) continue
    fillers.push(`${SUB_LABELS[row.key]} is relatively low (${row.value}).`)
  }
  return uniqCap([...fromData, ...fillers], max)
}

/** Prefer suggestions; fall back to missing/weak without duplicating top reasons. */
export function topActionsFromMatch(m: MatchApiV1, max = 3): string[] {
  const reasonNorm = new Set(topReasonsFromMatch(m, 12).map((r) => r.toLowerCase()))
  const out: string[] = []
  for (const s of m.suggestions) {
    const t = s.trim()
    if (!t || reasonNorm.has(t.toLowerCase())) continue
    out.push(t)
    if (out.length >= max) return out.slice(0, max)
  }
  for (const item of [...m.missing_skills, ...m.weak_areas]) {
    const t = item.trim()
    if (!t || reasonNorm.has(t.toLowerCase())) continue
    const action = `Add or emphasize: ${t}`
    if (out.some((x) => x.toLowerCase() === action.toLowerCase())) continue
    out.push(action)
    reasonNorm.add(t.toLowerCase())
    if (out.length >= max) break
  }
  return out.slice(0, max)
}

/** Supporting list: prioritize weak_areas then remaining suggestions. */
export function whatToImproveFirst(m: MatchApiV1): string[] {
  return uniqCap([...m.weak_areas, ...m.suggestions], 8)
}

export function whyScoreBullets(m: MatchApiV1, max = 3): string[] {
  const rows = orderedSubscores(m).slice(0, 2)
  const bullets: string[] = rows.map(
    (r) => `${SUB_LABELS[r.key]} scored ${r.value}/100, which pulls the headline score toward that band.`,
  )
  if (m.keyword_ats_match < m.skill_match && bullets.length < max) {
    bullets.push(
      "Keyword overlap with the job posting is influencing the ATS-style sub-score versus pure skills overlap.",
    )
  }
  return uniqCap(bullets, max)
}
