import type { JobDescriptionInput } from "./job"
import type { MatchApiV1, MatchPayload } from "./match"

export type TailorReview = {
  add: string[]
  remove: string[]
  improve: string[]
}

export type TailoredResume = {
  summary: string
  bullets: string[]
}

export type TailorApiV1 = {
  version: "v1"
  provider_mode: "stub" | "llm"
  review: TailorReview
  tailored_resume: TailoredResume
  cover_letter?: string | null
}

/** POST /api/resume/tailor — omit version from MatchApiV1 for snapshot. */
export type MatchSnapshotPayload = Omit<MatchApiV1, "version">

export type MatchSnapshotV2Payload = {
  version: "v2"
  ats_score: number
  job_match_score: number
  missing_hard_skills: string[]
  semantic_matches: string[]
  strengths: string[]
  actions: string[]
  why_this_score: string[]
}

export type TailorRequest = {
  resume_text: string
  job: JobDescriptionInput
  include_cover_letter: boolean
  match_snapshot?: MatchSnapshotPayload | null
  match_snapshot_v2?: MatchSnapshotV2Payload | null
}

/** Build tailoring snapshot from a successful wizard match bundle. */
export function matchBundleToSnapshots(match: MatchPayload): {
  match_snapshot?: MatchSnapshotPayload | null
  match_snapshot_v2?: MatchSnapshotV2Payload | null
} {
  if (match.version === "v2") {
    return {
      match_snapshot: null,
      match_snapshot_v2: {
        version: "v2",
        ats_score: match.ats_compatibility.score,
        job_match_score: match.job_match.score,
        missing_hard_skills: match.missing_hard_skills,
        semantic_matches: match.semantic_matches,
        strengths: match.strengths,
        actions: match.actions,
        why_this_score: match.why_this_score,
      },
    }
  }
  const { version, ...rest } = match
  void version
  return {
    match_snapshot: rest as MatchSnapshotPayload,
    match_snapshot_v2: null,
  }
}
