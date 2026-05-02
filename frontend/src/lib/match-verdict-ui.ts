import {
  scoreBand,
  topActionsFromMatch,
  verdictTitle,
  whatToImproveFirst,
  whyScoreBullets,
} from "@/lib/match-verdict"
import type { MatchApiV1, MatchApiV2, MatchPayload, MatchScoreBand } from "@/types/match"
import { isMatchV2 } from "@/types/match"

export type Step1TabId = "overview" | "gaps" | "improve" | "breakdown"

function uniqDedup(items: string[]): string[] {
  const seen = new Set<string>()
  const out: string[] = []
  for (const raw of items) {
    const t = raw.trim()
    if (!t || seen.has(t.toLowerCase())) continue
    seen.add(t.toLowerCase())
    out.push(t)
  }
  return out
}

function uniqCap(items: string[], max: number): string[] {
  return uniqDedup(items).slice(0, max)
}

/** Apply what to do next — one line, spec wording */
export function applyGuidanceLine(band: MatchScoreBand): string {
  switch (band) {
    case "weak":
      return "Weak match — don't apply yet without tailoring."
    case "needs_work":
      return "Needs work — close, but you should fix key gaps first."
    case "strong":
      return "Strong match — worth tailoring and applying."
  }
}

/** Heuristic split of ATS reason strings without backend changes */
export function classifyAtsSignals(reasons: string[]): { help: string[]; hurt: string[] } {
  const helpKw =
    /\b(?:present|detected|detect|multiple\s+sections|email|linkedin|readable|anchors|signals)\b/i
  const hurtKw =
    /\b(?:limited|weak|below|duplicate|tabular|dense|noise|sparse|thin|few|penalt|Penalty|wall|paragraphs)\b/i

  const help: string[] = []
  const hurt: string[] = []

  let alt = false
  for (const r of reasons) {
    const t = r.trim()
    if (!t) continue
    const hurts = hurtKw.test(t)
    const helps = helpKw.test(t)
    if (hurts && !helps) hurt.push(t)
    else if (helps && !hurts) help.push(t)
    else if (alt) {
      hurt.push(t)
      alt = false
    } else {
      help.push(t)
      alt = true
    }
  }
  return { help, hurt }
}

/** How many missing gaps count as Must address — scales with weakness */
export function mustAddressCount(jobScore: number, totalGaps: number): number {
  if (totalGaps <= 0) return 0
  const band = scoreBand(jobScore)
  let k = band === "weak" ? 6 : band === "needs_work" ? 4 : 2
  k = Math.min(k, totalGaps)
  return k
}

export type GapRow = { skill: string; priority: "must" | "optional" }

export function buildGapRows(missingSkills: string[], jobScore: number): GapRow[] {
  const uniq = uniqDedup(missingSkills)
  const k = mustAddressCount(jobScore, uniq.length)
  return uniq.map((skill, i) => ({
    skill,
    priority: i < k ? ("must" as const) : ("optional" as const),
  }))
}

export type MeterRow = {
  label: string
  value: number
  helperCopy: string
}

const V2_METER_HELP: Record<string, string> = {
  Semantic:
    "How closely your resume wording matches the job's meaning—not just identical keywords.",
  "Exact skills": "Canonical toolkit overlap between your resume and the posting's stack.",
  Lexical:
    "How well JD terms appear in searchable sections (skills/experience)—good for parsers and skim readers.",
  Title: "Alignment between how you headline yourself versus the advertised role.",
  Experience: "Seniority depth and trajectory vs what the JD implies.",
}

const V1_METER_HELP: Record<string, string> = {
  Skills: "Overlapping capability signals compared to inferred JD requirements.",
  Experience: "Depth of experience vs what the scorer inferred the role expects.",
  Keywords: "Literal phrase overlap—useful but not sufficient on its own.",
  Context: "Blended contextual fit combining skills-like and keyword cues.",
}

function metersWithHelpers(metrics: { label: string; value: number }[], v2: boolean): MeterRow[] {
  const table = v2 ? V2_METER_HELP : V1_METER_HELP
  return metrics.map((m) => ({
    label: m.label,
    value: m.value,
    helperCopy: table[m.label] ?? "Contributor to overall match.",
  }))
}

/** Bucket labels for grouped improvement checklist */
export type ImproveBuckets = Record<
  "resumeWording" | "missingSkills" | "experienceTitle",
  string[]
>

const WORDING_RX =
  /\b(?:mirror|phrase|wording|summary|ATS|keyword|bullet|verbs?)\b/i
const SKILL_RX =
  /\b(?:skill|Add or emphasize:|missing\s+hard|hard\s+skill|[Kk]nowledge\s+of)\b/i
const TITLE_EXP_RX =
  /\b(?:title|senior|intern|experience|depth|years|staff|principal|alignment|JD level)\b/i

export function bucketImproveLines(lines: string[]): ImproveBuckets {
  const resumeWording: string[] = []
  const missingSkills: string[] = []
  const experienceTitle: string[] = []
  const other: string[] = []

  for (const line of lines) {
    const lower = line.toLowerCase()
    if (TITLE_EXP_RX.test(lower)) experienceTitle.push(line)
    else if (SKILL_RX.test(lower)) missingSkills.push(line)
    else if (WORDING_RX.test(lower)) resumeWording.push(line)
    else other.push(line)
  }
  resumeWording.push(...other)

  return {
    resumeWording: uniqDedup(resumeWording),
    missingSkills: uniqDedup(missingSkills),
    experienceTitle: uniqDedup(experienceTitle),
  }
}

function v1StrengthsFromSubs(m: {
  skill_match: number
  experience_match: number
  keyword_ats_match: number
  context_fit: number
}): string[] {
  const rows = [
    { k: "Skill alignment looks solid." as const, v: m.skill_match },
    { k: "Experience line reads credible for scope." as const, v: m.experience_match },
    { k: "Keyword/phrasing echoes the JD well." as const, v: m.keyword_ats_match },
    { k: "Overall context aligns with posting tone." as const, v: m.context_fit },
  ]
    .sort((a, b) => b.v - a.v)
    .filter((x) => x.v >= 55)
    .map((x) => x.k)
  return rows.slice(0, 3)
}

function lowestMeterHint(metrics: MeterRow[]): string | null {
  if (!metrics.length) return null
  const sorted = [...metrics].sort((a, b) => a.value - b.value)[0]
  if (sorted.value >= 58) return null
  return `${sorted.label} is the lowest component (${Math.round(sorted.value)}).`
}

function detailNumsV2(m: MatchApiV2) {
  return [
    { label: "Semantic", value: m.semantic_similarity },
    { label: "Exact skills", value: m.exact_skill_overlap },
    { label: "Lexical", value: m.lexical_match },
    { label: "Title", value: m.title_alignment },
    { label: "Experience", value: m.experience_alignment },
  ]
}

function detailNumsV1(m: MatchApiV1) {
  return [
    { label: "Skills", value: m.skill_match },
    { label: "Experience", value: m.experience_match },
    { label: "Keywords", value: m.keyword_ats_match },
    { label: "Context", value: m.context_fit },
  ]
}

export type Step1ResultViewModel = {
  apiLabel: string
  jobMatchScore: number
  jobBand: MatchScoreBand
  jobVerdictHeadline: string
  applyGuidanceLine: string

  /** v2 ATS only */
  atsScore: number | null
  atsBand: MatchScoreBand | null
  atsHelpSignals: string[]
  atsHurtSignals: string[]
  jobMatchSummarySentence: string
  atsSummarySentence: string

  topThreeActions: string[]
  blockersTeaser: string[]
  overviewBlockers: string[]
  strengths: string[]
  whySentence: string | null

  gapRows: GapRow[]
  semanticMatches: string[]

  improvementOrdered: string[]
  improveBuckets: ImproveBuckets

  meterRows: MeterRow[]
}

function buildImprovementOrderedV2(m: MatchApiV2): string[] {
  return uniqDedup([
    ...m.actions,
    ...m.strengths.map((s) => `Leverage strength: ${s}`),
    ...m.missing_hard_skills.map((s) => `Address gap: ${s}`),
  ])
}

function buildImprovementOrderedV1(m: MatchApiV1): string[] {
  return uniqDedup([
    ...m.suggestions,
    ...m.weak_areas.map((w) => `Sharpen weak area: ${w}`),
    ...whatToImproveFirst(m),
  ])
}

/** Primary builder for Step 1 redesign */
export function buildStep1ResultViewModel(m: MatchPayload): Step1ResultViewModel {
  if (isMatchV2(m)) {
    const jobMatchScore = m.job_match.score
    const jobBand = scoreBand(jobMatchScore)
    const atsScore = m.ats_compatibility.score
    const atsBand = scoreBand(atsScore)
    const classified = classifyAtsSignals(m.ats_compatibility.reasons)

    const topThreeActions = uniqCap(m.actions, 3)
    const missingUnique = uniqDedup(m.missing_hard_skills)
    const gapRows = buildGapRows(missingUnique, jobMatchScore)
    const meterRows = metersWithHelpers(detailNumsV2(m), true)
    const lowHint = lowestMeterHint(meterRows)

    const blockersTeaser = uniqDedup([
      ...missingUnique.slice(0, 2),
      m.job_match.reasons[0] ?? "",
      lowHint ?? "",
    ]).slice(0, 3)

    const overviewBlockers = uniqDedup([
      ...missingUnique.slice(0, 5),
      ...m.job_match.reasons.slice(0, 3),
      ...(lowHint ? [lowHint] : []),
    ]).slice(0, 7)

    const whySentence = m.why_this_score?.[0]?.trim().slice(0, 280) ?? null

    const improvementOrdered = buildImprovementOrderedV2(m)
    const improveBuckets = bucketImproveLines(improvementOrdered)

    return {
      apiLabel: "API v2",
      jobMatchScore,
      jobBand,
      jobVerdictHeadline: verdictTitle(jobBand),
      applyGuidanceLine: applyGuidanceLine(jobBand),
      atsScore,
      atsBand,
      atsHelpSignals: classified.help.slice(0, 8),
      atsHurtSignals: classified.hurt.slice(0, 8),
      jobMatchSummarySentence: `${Math.round(jobMatchScore)}/100 job fit — heavier weight on meaning and JD overlap than keyword tricks alone.`,
      atsSummarySentence: `${Math.round(atsScore)}/100 ATS-style parse readiness from plain-text structure, contact cues, bullets, and noise penalties.`,
      topThreeActions,
      blockersTeaser,
      overviewBlockers,
      strengths: m.strengths.slice(0, 6),
      whySentence,
      gapRows,
      semanticMatches: m.semantic_matches,
      improvementOrdered,
      improveBuckets,
      meterRows,
    }
  }

  const jobMatchScore = m.score
  const jobBand = scoreBand(jobMatchScore)
  const meterRows = metersWithHelpers(detailNumsV1(m), false)
  const lowHint = lowestMeterHint(meterRows)

  const topThreeActions = topActionsFromMatch(m, 3)
  const missingUnique = uniqDedup(m.missing_skills)
  const gapRows = buildGapRows(missingUnique, jobMatchScore)

  const blockersTeaser = uniqDedup([...missingUnique.slice(0, 2), m.weak_areas[0] ?? lowHint ?? ""]).slice(
    0,
    3,
  )
  const overviewBlockers = uniqDedup([
    ...missingUnique.slice(0, 6),
    ...m.weak_areas,
    ...(lowHint ? [lowHint] : []),
  ]).slice(0, 7)

  const improvementOrdered = buildImprovementOrderedV1(m)

  const whyBullets = whyScoreBullets(m, 4)
  const whySentence = whyBullets[0] ?? null

  return {
    apiLabel: "API v1",
    jobMatchScore,
    jobBand,
    jobVerdictHeadline: verdictTitle(jobBand),
    applyGuidanceLine: applyGuidanceLine(jobBand),
    atsScore: null,
    atsBand: null,
    atsHelpSignals: [],
    atsHurtSignals: [],
    jobMatchSummarySentence: `${Math.round(jobMatchScore)}/100 from the legacy heuristic blend across skills, experience, keywords, and context.`,
    atsSummarySentence:
      "ATS readiness isn't modeled for v1 scoring — rerun with v2 for machine-readability cues.",
    topThreeActions,
    blockersTeaser,
    overviewBlockers,
    strengths: v1StrengthsFromSubs(m),
    whySentence,
    gapRows,
    semanticMatches: [],
    improvementOrdered,
    improveBuckets: bucketImproveLines(improvementOrdered),
    meterRows,
  }
}

export type DetailMetric = { label: string; value: number }

/** @deprecated Prefer buildStep1ResultViewModel — thin adapter for legacy callers */
export type VerdictUIModel = {
  apiLabel: string
  primaryScore: number
  primaryBand: MatchScoreBand
  explainer: string
  ats?: { score: number; band: MatchScoreBand; reasons: string[] }
  topReasons: string[]
  topActions: string[]
  missingHeading: string
  missingItems: string[]
  improveFirst: string[]
  whyHeading: string
  whyItems: string[]
  semanticMatches: string[]
  detailsMetrics: DetailMetric[]
}

/** @deprecated */
export function buildVerdictUIModel(m: MatchPayload): VerdictUIModel {
  const vm = buildStep1ResultViewModel(m)
  return {
    apiLabel: vm.apiLabel,
    primaryScore: vm.jobMatchScore,
    primaryBand: vm.jobBand,
    explainer: vm.applyGuidanceLine,
    ats:
      vm.atsScore != null && vm.atsBand != null
        ? {
            score: vm.atsScore,
            band: vm.atsBand,
            reasons: [...vm.atsHelpSignals, ...vm.atsHurtSignals],
          }
        : undefined,
    topReasons: uniqCap([...vm.blockersTeaser, ...vm.strengths], 3),
    topActions: vm.topThreeActions,
    missingHeading: "Missing keywords / skills",
    missingItems: vm.gapRows.map((r) => r.skill),
    improveFirst: vm.improvementOrdered.slice(0, 8),
    whyHeading: "Why this happened",
    whyItems: vm.whySentence ? [vm.whySentence] : [],
    semanticMatches: vm.semanticMatches,
    detailsMetrics: vm.meterRows.map((r) => ({ label: r.label, value: r.value })),
  }
}
