import { cleanup, render, screen } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest"

import { StepTwoTailorCard } from "./step-two-tailor"
import * as tailorService from "@/services/tailor.service"
import { resetResumeWizardStore, useResumeWizardStore } from "@/store/useResumeWizardStore"

afterEach(() => {
  cleanup()
  vi.unstubAllGlobals()
})

vi.mock("@/services/tailor.service", () => ({
  postTailor: vi.fn(),
}))

describe("StepTwoTailorCard", () => {
  const writeText = vi.fn(() => Promise.resolve())

  beforeEach(() => {
    localStorage.clear()
    resetResumeWizardStore()
    writeText.mockClear()
    vi.stubGlobal("navigator", { ...globalThis.navigator, clipboard: { writeText } })
  })

  function seedUnlockedTailorStep() {
    const matchFixture = {
      version: "v2" as const,
      ats_compatibility: { score: 60, band: "needs_work" as const, reasons: ["x"] },
      job_match: { score: 65, band: "needs_work" as const, reasons: ["y"] },
      semantic_similarity: 50,
      exact_skill_overlap: 50,
      lexical_match: 55,
      title_alignment: 50,
      experience_alignment: 55,
      missing_hard_skills: ["Rust"],
      semantic_matches: [],
      strengths: [],
      actions: ["Add metrics"],
      why_this_score: [],
    }
    useResumeWizardStore.setState({
      savedResumeText: "R",
      stepWorkingResume: "R",
      resumeSource: "saved",
      jobTitle: "Eng",
      jobCompany: "Co",
      jobDescription: "JD",
    })
    useResumeWizardStore.getState().recordMatchSuccess({
      resolvedResumeText: "R",
      job: { raw_text: "JD", title: "Eng", company: "Co" },
      match: matchFixture,
    })
  }

  it("shows locked state when Step 1 not completed", () => {
    resetResumeWizardStore()
    render(<StepTwoTailorCard />)
    expect(screen.getByText(/complete step\s*1/i)).not.toBeNull()
  })

  it("shows summary and defaults to Overview tab after tailoring exists", async () => {
    seedUnlockedTailorStep()
    const api = tailorService.postTailor as ReturnType<typeof vi.fn>
    api.mockResolvedValueOnce({
      version: "v1",
      provider_mode: "stub",
      review: { add: ["Z"], remove: [], improve: [] },
      tailored_resume: { summary: "S", bullets: ["B1"] },
      cover_letter: null,
    })
    render(<StepTwoTailorCard />)
    await userEvent.click(screen.getByRole("button", { name: /generate tailored draft/i }))
    expect(screen.getByRole("tab", { name: /^overview$/i }).getAttribute("aria-selected")).toBe("true")
    expect(screen.getByRole("heading", { name: /^what to add$/i })).not.toBeNull()
  })

  it("preserves edited summary when switching tabs", async () => {
    seedUnlockedTailorStep()
    useResumeWizardStore.setState({
      activeTailorTab: "resume",
      lastTailoring: {
        includeCoverLetterRequested: false,
        result: {
          version: "v1",
          provider_mode: "stub",
          review: { add: [], remove: [], improve: [] },
          tailored_resume: { summary: "Orig", bullets: ["x"] },
        },
      },
      editedSummary: "Orig",
      editedBullets: "x",
    })
    render(<StepTwoTailorCard />)
    const summary = screen.getByLabelText(/professional summary/i) as HTMLTextAreaElement
    await userEvent.clear(summary)
    await userEvent.type(summary, "Edited by user")

    await userEvent.click(screen.getByRole("tab", { name: /^overview$/i }))
    await userEvent.click(screen.getByRole("tab", { name: /^tailored resume$/i }))

    const again = screen.getByLabelText(/professional summary/i) as HTMLTextAreaElement
    expect(again.value).toContain("Edited by user")
  })

  it("copy summary triggers clipboard", async () => {
    seedUnlockedTailorStep()
    useResumeWizardStore.setState({
      lastTailoring: {
        includeCoverLetterRequested: false,
        result: {
          version: "v1",
          provider_mode: "stub",
          review: { add: [], remove: [], improve: [] },
          tailored_resume: { summary: "Copy me", bullets: [] },
        },
      },
      editedSummary: "Copy me",
      editedBullets: "",
    })
    render(<StepTwoTailorCard />)
    await userEvent.click(screen.getByRole("tab", { name: /^tailored resume$/i }))
    await userEvent.click(screen.getByRole("button", { name: /^copy summary$/i }))
    expect(writeText).toHaveBeenCalledWith("Copy me")
  })

  it("shows stale tailoring path when fingerprint drifted after generation", async () => {
    seedUnlockedTailorStep()
    vi.mocked(tailorService.postTailor).mockResolvedValueOnce({
      version: "v1",
      provider_mode: "stub",
      review: { add: [], remove: [], improve: [] },
      tailored_resume: { summary: "S", bullets: [] },
    })
    render(<StepTwoTailorCard />)
    await userEvent.click(screen.getByRole("button", { name: /generate tailored draft/i }))
    useResumeWizardStore.getState().setJobDescription("New JD drift")
    const { lastSuccessfulBundle, lastTailoring } = useResumeWizardStore.getState()
    expect(lastSuccessfulBundle).toBeNull()
    expect(lastTailoring).not.toBeNull()

    cleanup()
    render(<StepTwoTailorCard />)
    expect(screen.getByText(/drafts may be outdated/i)).not.toBeNull()
  })
})
