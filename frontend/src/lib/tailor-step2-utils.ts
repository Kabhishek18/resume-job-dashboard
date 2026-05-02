/**
 * Frontend-only helpers for Step 2 presentation (no TailorApiV1 schema change).
 */

import type { TailorReview } from "@/types/tailor"

/** Top picks from review buckets merged with Step 1 action cues; capped length */
export function buildDoTheseFirst(review: TailorReview, stepOneActions: readonly string[]): string[] {
  const fromReview = [...review.add.slice(0, 2), ...review.remove.slice(0, 2), ...review.improve.slice(0, 2)]
  const merged = [...fromReview.filter(Boolean), ...stepOneActions.slice(0, 2)]
  const seen = new Set<string>()
  const out: string[] = []
  for (const raw of merged) {
    const t = raw.trim()
    if (!t || seen.has(t.toLowerCase())) continue
    seen.add(t.toLowerCase())
    out.push(t)
    if (out.length >= 6) break
  }
  return out
}
