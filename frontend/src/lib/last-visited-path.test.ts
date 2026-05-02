import { afterEach, describe, expect, it, vi } from "vitest"

import { readLastVisitedPath, resolvePostAuthPath, writeLastVisitedPath } from "@/lib/last-visited-path"

describe("last-visited-path", () => {
  afterEach(() => {
    vi.unstubAllGlobals()
    localStorage.clear()
  })

  it("resolvePostAuthPath prefers explicit next when valid", () => {
    expect(resolvePostAuthPath("/jobs")).toBe("/jobs")
  })

  it("resolvePostAuthPath falls back to stored path then dashboard", () => {
    writeLastVisitedPath("/resume")
    expect(resolvePostAuthPath(null)).toBe("/resume")
    localStorage.clear()
    expect(resolvePostAuthPath("//evil")).toBe("/dashboard")
  })

  it("readLastVisitedPath returns null for unsafe paths", () => {
    localStorage.setItem("resumeJobDashboard:lastPath", "//x")
    expect(readLastVisitedPath()).toBe(null)
  })
})
