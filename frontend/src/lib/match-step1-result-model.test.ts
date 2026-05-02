import { describe, expect, it } from "vitest"

import type { MatchPayload } from "@/types/match"

import {
  applyGuidanceLine,
  bucketImproveLines,
  buildGapRows,
  buildStep1ResultViewModel,
  classifyAtsSignals,
  mustAddressCount,
} from "./match-verdict-ui"

describe("mustAddressCount + buildGapRows", () => {
  it("uses more must-fix slots when score is weaker", () => {
    expect(mustAddressCount(54, 8)).toBeGreaterThanOrEqual(mustAddressCount(75, 8))
    const weak = buildGapRows(["a", "b", "c", "d", "e", "f"], 30)
    const strong = buildGapRows(["a", "b", "c", "d", "e", "f"], 92)
    expect(weak.filter((r) => r.priority === "must").length).toBeGreaterThanOrEqual(
      strong.filter((r) => r.priority === "must").length,
    )
  })

  it("never marks more must than gaps", () => {
    const gaps = ["x", "y"]
    expect(buildGapRows(gaps, 20).every((r) => ["must", "optional"].includes(r.priority))).toBe(true)
    expect(buildGapRows(gaps, 20).filter((r) => r.priority === "must")).toHaveLength(2)
  })
})

describe("bucketImproveLines", () => {
  it("routes lines into deterministic buckets via keyword heuristics", () => {
    const buckets = bucketImproveLines([
      "Mirror the JD wording in bullets",
      "Address missing hard skill: kubernetes",
      "Align title seniority with the JD level",
      "Oddball leftover",
    ])
    expect(buckets.resumeWording.some((s) => s.includes("Mirror"))).toBe(true)
    expect(buckets.missingSkills.some((s) => s.includes("kubernetes"))).toBe(true)
    expect(buckets.experienceTitle.some((s) => s.includes("senior"))).toBe(true)
    expect(buckets.resumeWording.some((s) => s.includes("Oddball"))).toBe(true)
  })
})

describe("classifyAtsSignals", () => {
  it("splits positives and negatives with keyword cues", () => {
    const { help, hurt } = classifyAtsSignals([
      "Limited sections weaken parseability.",
      "Email readable and present.",
      "Neutral line about structure",
    ])
    expect(hurt.some((s) => s.includes("Limited"))).toBe(true)
    expect(help.some((s) => s.includes("readable"))).toBe(true)
  })
})

describe("buildStep1ResultViewModel", () => {
  const v2: MatchPayload = {
    version: "v2",
    ats_compatibility: {
      score: 62,
      band: "needs_work",
      reasons: ["Limited sections weaken parseability.", "Email readable and present."],
    },
    job_match: {
      score: 58,
      band: "needs_work",
      reasons: ["Lexical gap.", "Thin evidence."],
    },
    semantic_similarity: 40,
    exact_skill_overlap: 35,
    lexical_match: 45,
    title_alignment: 50,
    experience_alignment: 55,
    missing_hard_skills: ["rust"],
    semantic_matches: ["async"],
    strengths: ["Overlap"],
    actions: ["Add metrics", "Sharpen wording", "Clarify title"],
    why_this_score: ["Weighted blend of signals."],
  }

  it("sets applyGuidanceLine from score band only (not ATS)", () => {
    const vm = buildStep1ResultViewModel(v2)
    expect(vm.applyGuidanceLine).toBe(applyGuidanceLine("needs_work"))
    expect(vm.jobMatchScore).toBe(58)
    expect(vm.atsScore).toBe(62)
  })

  it("surfaces first three actions and preserves semantic_matches for gaps context", () => {
    const vm = buildStep1ResultViewModel(v2)
    expect(vm.topThreeActions).toHaveLength(3)
    expect(vm.semanticMatches).toContain("async")
    expect(vm.gapRows[0]?.priority).toBe("must")
  })
})
