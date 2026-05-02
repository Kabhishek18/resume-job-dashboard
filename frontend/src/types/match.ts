import type { JobDescriptionInput } from "./job"

/** MVP: plain-text resume only (no file upload). */
export type MatchRequest = {
  raw_resume_text: string
  job: JobDescriptionInput
}

export type MatchApiV1 = {
  version: "v1"
  score: number
  skill_match: number
  experience_match: number
  keyword_ats_match: number
  context_fit: number
  missing_skills: string[]
  suggestions: string[]
  weak_areas: string[]
}

export type MatchScoreBand = "weak" | "needs_work" | "strong"

export type MatchBandedBucket = {
  score: number
  band: MatchScoreBand
  reasons: string[]
}

export type MatchApiV2 = {
  version: "v2"
  ats_compatibility: MatchBandedBucket
  job_match: MatchBandedBucket
  semantic_similarity: number
  exact_skill_overlap: number
  lexical_match: number
  title_alignment: number
  experience_alignment: number
  missing_hard_skills: string[]
  semantic_matches: string[]
  strengths: string[]
  actions: string[]
  why_this_score: string[]
}

/** Discriminated union for wizard bundle + UI. */
export type MatchPayload = MatchApiV1 | MatchApiV2

export function isMatchV2(m: MatchPayload): m is MatchApiV2 {
  return m.version === "v2"
}
