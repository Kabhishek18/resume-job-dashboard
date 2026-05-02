import { describe, expect, it } from "vitest"

import { friendlyRunSummaryLine, portalLabel } from "@/lib/jobs-run-summary"
import type { JobSearchRunApi } from "@/types/jobs"

describe("portalLabel", () => {
  it("maps known portal keys including zip_recruiter", () => {
    expect(portalLabel("zip_recruiter")).toBe("ZipRecruiter")
    expect(portalLabel("linkedin")).toBe("LinkedIn")
    expect(portalLabel("unknown_board")).toBe("Unknown_board")
  })
})

describe("friendlyRunSummaryLine", () => {
  it("uses portalLabel for unavailable portal names", () => {
    const run: JobSearchRunApi = {
      id: 1,
      user_id: 1,
      search_profile_id: 1,
      trigger_mode: "manual",
      status: "completed",
      summary_json: {
        outcome: "ok",
        portals: { zip_recruiter: { rows: 0, state: "unavailable" } },
      },
    }
    const line = friendlyRunSummaryLine(run)
    expect(line).toContain("ZipRecruiter")
    expect(line).not.toContain("Zip_recruiter")
  })
})
