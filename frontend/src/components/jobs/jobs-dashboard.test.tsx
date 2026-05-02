import { cleanup, render, screen, waitFor } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest"

vi.mock("@/store/useAuthStore", () => ({
  useAuthStore: (selector: (s: unknown) => unknown) =>
    selector({
      token: "test-token",
      user: null,
      setAuth: () => {},
      logout: () => {},
    }),
}))

vi.mock("@/services/jobs.service", () => ({
  listSearchProfiles: vi.fn(),
  listBoard: vi.fn(),
  createSearchProfile: vi.fn(),
  patchSearchProfile: vi.fn(),
  runSearchProfile: vi.fn(),
  getRun: vi.fn(),
  getRunResults: vi.fn(),
  addJobToBoard: vi.fn(),
  patchBoardEntry: vi.fn(),
}))

import { JobsDashboard } from "@/components/jobs/jobs-dashboard"
import { aggregatedJobsToTsv } from "@/lib/jobs-results-export"
import type { AggregatedJobRowApi, JobSearchRunApi } from "@/types/jobs"
import * as JobsService from "@/services/jobs.service"

describe("JobsDashboard", () => {
  afterEach(() => {
    cleanup()
    vi.mocked(JobsService.listSearchProfiles).mockReset()
    vi.mocked(JobsService.listBoard).mockReset()
    vi.mocked(JobsService.createSearchProfile).mockReset()
    vi.mocked(JobsService.patchSearchProfile).mockReset()
    vi.mocked(JobsService.runSearchProfile).mockReset()
    vi.mocked(JobsService.getRun).mockReset()
    vi.mocked(JobsService.getRunResults).mockReset()
    vi.mocked(JobsService.addJobToBoard).mockReset()
    vi.mocked(JobsService.patchBoardEntry).mockReset()
  })

  beforeEach(() => {
    vi.mocked(JobsService.listSearchProfiles).mockResolvedValue([])
    vi.mocked(JobsService.listBoard).mockResolvedValue([])
  })

  it("renders Results and Board tabs", async () => {
    render(<JobsDashboard />)
    expect(screen.getByTestId("jobs-tab-results")).toBeTruthy()
    expect(screen.getByTestId("jobs-tab-board")).toBeTruthy()
    await waitFor(() => expect(JobsService.listSearchProfiles).toHaveBeenCalledWith("test-token"))
  })

  it("loads board when switching to Board tab", async () => {
    render(<JobsDashboard />)
    const user = userEvent.setup()
    await user.click(screen.getByTestId("jobs-tab-board"))
    await waitFor(() => expect(JobsService.listBoard).toHaveBeenCalledWith("test-token"))
    expect(screen.getByText(/application board/i)).toBeTruthy()
  })

  it("aggregatedJobsToTsv replaces literal tabs inside cells", () => {
    const rows: AggregatedJobRowApi[] = [
      {
        id: 1,
        portal: "linkedin",
        title: "A\tRole",
        company: "Acme",
        location: "",
        posted_at: null,
        salary_text: "",
        apply_url: "https://jobs.example.invalid",
        duplicate_count: 1,
        source_count: 1,
      },
    ]
    const tsv = aggregatedJobsToTsv(rows)
    expect(tsv.includes("portal\t")).toBe(true)
    expect(tsv.includes("linkedin\tA Role\t")).toBe(true)
  })

  it("runs search and paginates: page 2 shows different rows", async () => {
    vi.mocked(JobsService.listSearchProfiles).mockResolvedValue([
      {
        id: 5,
        user_id: 1,
        name: "Mine",
        keywords: "rust",
        locations: "",
        experience_levels: "",
        employment_types: "",
        remote_only: false,
        selected_portals: ["linkedin"],
        schedule_enabled: false,
        schedule_frequency: null,
        schedule_time: null,
        schedule_timezone: "UTC",
      },
    ])

    const run: JobSearchRunApi = {
      id: 9,
      user_id: 1,
      search_profile_id: 5,
      trigger_mode: "manual",
      status: "queued",
      summary_json: {},
    }
    const many: AggregatedJobRowApi[] = Array.from({ length: 30 }, (_, i) => ({
      id: 100 + i,
      portal: "linkedin",
      title: `JobTitle-${String(i).padStart(3, "0")}`,
      company: "Co",
      location: "",
      posted_at: null,
      salary_text: "",
      apply_url: `https://jobs.example.invalid/${i}`,
      duplicate_count: 1,
      source_count: 1,
    }))

    vi.mocked(JobsService.runSearchProfile).mockResolvedValue(run)
    vi.mocked(JobsService.getRun).mockResolvedValue({ ...run, status: "completed" })
    vi.mocked(JobsService.getRunResults).mockResolvedValue(many)

    render(<JobsDashboard />)

    await waitFor(() => expect(screen.getByTestId("jobs-profile-select")).toBeTruthy())
    await userEvent.selectOptions(screen.getByTestId("jobs-profile-select"), "5")
    await userEvent.click(screen.getByTestId("jobs-run-search"))

    await waitFor(() => expect(screen.getByText("JobTitle-000")).toBeTruthy())
    expect(screen.getByText("JobTitle-024")).toBeTruthy()
    expect(screen.queryByText("JobTitle-025")).toBeNull()

    await userEvent.click(screen.getByTestId("jobs-page-next"))
    await waitFor(() => expect(screen.getByText("JobTitle-025")).toBeTruthy())
    expect(screen.queryByText("JobTitle-000")).toBeNull()
  })

  it("Copy current page vs Copy all uses different clipboard payloads", async () => {
    vi.mocked(JobsService.listSearchProfiles).mockResolvedValue([
      {
        id: 5,
        user_id: 1,
        name: "Mine",
        keywords: "rust",
        locations: "",
        experience_levels: "",
        employment_types: "",
        remote_only: false,
        selected_portals: ["linkedin"],
        schedule_enabled: false,
        schedule_frequency: null,
        schedule_time: null,
        schedule_timezone: "UTC",
      },
    ])
    const run: JobSearchRunApi = {
      id: 9,
      user_id: 1,
      search_profile_id: 5,
      trigger_mode: "manual",
      status: "completed",
      summary_json: {},
    }
    const many: AggregatedJobRowApi[] = Array.from({ length: 30 }, (_, i) => ({
      id: 100 + i,
      portal: "linkedin",
      title: `JobTitle-${String(i).padStart(3, "0")}`,
      company: "Co",
      location: "",
      posted_at: null,
      salary_text: "",
      apply_url: `https://jobs.example.invalid/${i}`,
      duplicate_count: 1,
      source_count: 1,
    }))
    vi.mocked(JobsService.runSearchProfile).mockResolvedValue(run)
    vi.mocked(JobsService.getRun).mockResolvedValue(run)
    vi.mocked(JobsService.getRunResults).mockResolvedValue(many)

    const write = vi.fn().mockResolvedValue(undefined)
    vi.stubGlobal("navigator", { clipboard: { writeText: write } })

    render(<JobsDashboard />)
    await waitFor(() => expect(screen.getByTestId("jobs-profile-select")).toBeTruthy())
    await userEvent.selectOptions(screen.getByTestId("jobs-profile-select"), "5")
    await userEvent.click(screen.getByTestId("jobs-run-search"))
    await waitFor(() => expect(screen.getByTestId("jobs-copy-page")).toBeTruthy())

    await userEvent.click(screen.getByTestId("jobs-copy-page"))
    await waitFor(() => expect(write).toHaveBeenCalled())
    const pagePayload = write.mock.calls[0][0] as string
    expect(pagePayload.split("\n").length).toBe(26)

    await userEvent.click(screen.getByTestId("jobs-copy-all"))
    await waitFor(() => expect(write).toHaveBeenCalledTimes(2))
    const allPayload = write.mock.calls[1][0] as string
    expect(allPayload.split("\n").length).toBe(31)
    expect(pagePayload).not.toBe(allPayload)
  })
})
