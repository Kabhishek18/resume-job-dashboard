import { describe, expect, it } from "vitest"

import { buildDoTheseFirst } from "./tailor-step2-utils"

describe("buildDoTheseFirst", () => {
  it("dedupes case-insensitively across review and step cues", () => {
    const out = buildDoTheseFirst(
      {
        add: ["Mirror JD keywords"],
        remove: ["Thin summary"],
        improve: [],
      },
      ["mirror jd keywords"],
    )
    const lowerHits = out.filter((x) => x.toLowerCase().includes("mirror jd"))
    expect(lowerHits.length).toBeLessThanOrEqual(1)
    expect(out).toContain("Thin summary")
  })
})
