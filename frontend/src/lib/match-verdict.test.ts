import { describe, expect, it } from "vitest"

import { scoreBand, topActionsFromMatch, topReasonsFromMatch } from "@/lib/match-verdict"
import type { MatchApiV1 } from "@/types/match"

function baseMatch(over: Partial<MatchApiV1> = {}): MatchApiV1 {
  return {
    version: "v1",
    score: 50,
    skill_match: 50,
    experience_match: 50,
    keyword_ats_match: 50,
    context_fit: 50,
    missing_skills: [],
    suggestions: [],
    weak_areas: [],
    ...over,
  }
}

describe("scoreBand", () => {
  it("bounds weak vs needs_work at 39/40", () => {
    expect(scoreBand(39)).toBe("weak")
    expect(scoreBand(40)).toBe("needs_work")
  })

  it("bounds needs_work vs strong at 69/70", () => {
    expect(scoreBand(69)).toBe("needs_work")
    expect(scoreBand(70)).toBe("strong")
  })

  it("caps weak at zero and strong at 100", () => {
    expect(scoreBand(0)).toBe("weak")
    expect(scoreBand(100)).toBe("strong")
  })
})

describe("topReasonsFromMatch", () => {
  it("prioritizes missing_skills before weak_areas", () => {
    const m = baseMatch({
      missing_skills: ["Rust"],
      weak_areas: ["Thin leadership narrative"],
      skill_match: 30,
      experience_match: 80,
    })
    const r = topReasonsFromMatch(m, 3)
    expect(r[0]).toBe("Rust")
    expect(r).toContain("Thin leadership narrative")
  })

  it("caps at three items", () => {
    const m = baseMatch({
      missing_skills: ["a", "b", "c", "d"],
      weak_areas: [],
    })
    expect(topReasonsFromMatch(m, 3)).toHaveLength(3)
  })
})

describe("topActionsFromMatch", () => {
  it("prefers suggestions first", () => {
    const m = baseMatch({
      suggestions: ["Tailor summary to fintech"],
      missing_skills: ["Kafka"],
    })
    expect(topActionsFromMatch(m, 3)[0]).toBe("Tailor summary to fintech")
  })
})
