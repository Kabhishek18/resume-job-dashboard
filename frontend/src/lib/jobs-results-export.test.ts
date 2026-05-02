import { describe, expect, it } from "vitest"

import { aggregatedJobsToCsv, aggregatedJobsToTsv } from "@/lib/jobs-results-export"
import type { AggregatedJobRowApi } from "@/types/jobs"

function makeRow(i: number): AggregatedJobRowApi {
  return {
    id: i,
    portal: "linkedin",
    title: `Role-${i}`,
    company: "Co",
    location: "",
    posted_at: null,
    salary_text: "",
    apply_url: `https://x.invalid/${i}`,
    duplicate_count: 1,
    board_status: i % 2 === 0 ? "saved" : null,
    source_count: 1,
  }
}

describe("jobs-results-export", () => {
  it("CSV current page vs all filtered: different line counts when multiple pages of rows", () => {
    const many = Array.from({ length: 30 }, (_, i) => makeRow(i))
    const page = many.slice(0, 25)
    const csvPage = aggregatedJobsToCsv(page)
    const csvAll = aggregatedJobsToCsv(many)
    expect(csvPage.split(/\r?\n/).length).toBe(26)
    expect(csvAll.split(/\r?\n/).length).toBe(31)
  })

  it("TSV copy all includes more lines than one page slice", () => {
    const many = Array.from({ length: 30 }, (_, i) => makeRow(i))
    const page = many.slice(0, 25)
    expect(aggregatedJobsToTsv(page).split("\n").length).toBe(26)
    expect(aggregatedJobsToTsv(many).split("\n").length).toBe(31)
  })
})
