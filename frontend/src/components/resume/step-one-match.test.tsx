import { cleanup, render, screen } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest"

import { StepOneMatchCard } from "./step-one-match"
import { resetResumeWizardStore, useResumeWizardStore } from "@/store/useResumeWizardStore"

vi.mock("@/store/useAuthStore", () => ({
  useAuthStore: (selector: (s: unknown) => unknown) =>
    selector({
      token: "test-token",
      user: null,
      setAuth: () => {},
      logout: () => {},
    }),
}))
afterEach(() => cleanup())

beforeEach(() => {
  localStorage.clear()
  resetResumeWizardStore()
})

describe("StepOneMatchCard", () => {
  it("disables Analyze without JD when resume is resolved", () => {
    useResumeWizardStore.setState({
      savedResumeText: "Engineer with skills",
      stepWorkingResume: "Engineer with skills",
      resumeSource: "saved",
      jobDescription: "",
      jobUrl: "",
    })
    render(<StepOneMatchCard />)
    const btn = screen.getByRole("button", { name: /analyze match/i })
    expect((btn as HTMLButtonElement).disabled).toBe(true)
  })

  it("enables Analyze with resume plus JD while URL is blank", () => {
    useResumeWizardStore.setState({
      savedResumeText: "Engineer",
      stepWorkingResume: "Engineer",
      resumeSource: "saved",
      jobDescription: "We need JD text here.",
      jobUrl: "",
    })
    render(<StepOneMatchCard />)
    const btn = screen.getByRole("button", { name: /analyze match/i })
    expect((btn as HTMLButtonElement).disabled).toBe(false)
  })

  it("shows Save profile when working resume differs from saved profile", () => {
    useResumeWizardStore.setState({
      savedResumeText: "Profile version",
      stepWorkingResume: "Edited elsewhere",
      resumeSource: "paste",
    })
    render(<StepOneMatchCard />)
    expect(screen.queryByRole("button", { name: /save to profile/i })).not.toBeNull()
  })

  function withUnlockedBundle(match: object) {
    return {
      lastSuccessfulBundle: {
        resolvedResumeText: "Engineer",
        job: { raw_text: "Need skills." },
        match,
      },
      matchFingerprintAtSuccess: JSON.stringify({
        r: "Engineer",
        title: "",
        company: "",
        url: "",
        jd: "Need skills.",
      }),
    }
  }

  it("shows primary job hero, ATS sidebar, guidance line, and API label after v2 match", () => {
    const fixture = {
      version: "v2" as const,
      ats_compatibility: { score: 62, band: "needs_work" as const, reasons: ["Limited sections weaken parseability."] },
      job_match: { score: 58, band: "needs_work" as const, reasons: ["Lexical gap."] },
      semantic_similarity: 50,
      exact_skill_overlap: 40,
      lexical_match: 45,
      title_alignment: 52,
      experience_alignment: 60,
      missing_hard_skills: ["rust"],
      semantic_matches: [],
      strengths: ["Python overlap"],
      actions: ["Add metrics", "Tighten skills", "Clarify title"],
      why_this_score: ["Weighted blend."],
    }
    useResumeWizardStore.setState({
      savedResumeText: "Engineer",
      stepWorkingResume: "Engineer",
      resumeSource: "saved",
      jobDescription: "Need skills.",
      jobUrl: "",
      ...withUnlockedBundle(fixture),
    })
    render(<StepOneMatchCard />)
    expect(screen.getByRole("heading", { name: /^job match$/i })).not.toBeNull()
    expect(screen.getByLabelText(/^match api version$/i).textContent).toContain("API v2")
    expect(screen.queryByText(/^ATS Compatibility$/)).not.toBeNull()
    expect(
      screen.getByText(/^Needs work — close, but you should fix key gaps first\.$/),
    ).not.toBeNull()
  })

  it("puts Top 3 next actions above the tablist in document order", () => {
    const fixture = {
      version: "v2" as const,
      ats_compatibility: { score: 80, band: "strong" as const, reasons: ["Readable anchors."] },
      job_match: { score: 72, band: "strong" as const, reasons: ["Good fit."] },
      semantic_similarity: 72,
      exact_skill_overlap: 70,
      lexical_match: 74,
      title_alignment: 75,
      experience_alignment: 70,
      missing_hard_skills: [],
      semantic_matches: [],
      strengths: ["Solid overlap"],
      actions: ["A", "B", "C"],
      why_this_score: ["Weighted blend."],
    }
    useResumeWizardStore.setState({
      savedResumeText: "Engineer",
      stepWorkingResume: "Engineer",
      resumeSource: "saved",
      jobDescription: "Need skills.",
      jobUrl: "",
      ...withUnlockedBundle(fixture),
    })
    render(<StepOneMatchCard />)
    const topHeading = screen.getByRole("heading", { name: /top 3 next actions/i })
    const tablist = screen.getByRole("tablist", { name: /match detail sections/i })
    const pos = topHeading.compareDocumentPosition(tablist)
    expect(pos & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy()
  })

  it("defaults to Overview tab and exposes Score breakdown meters as progressbars", async () => {
    const fixture = {
      version: "v2" as const,
      ats_compatibility: { score: 62, band: "needs_work" as const, reasons: ["Structured sections."] },
      job_match: { score: 58, band: "needs_work" as const, reasons: ["Lexical gap."] },
      semantic_similarity: 50,
      exact_skill_overlap: 40,
      lexical_match: 45,
      title_alignment: 52,
      experience_alignment: 60,
      missing_hard_skills: ["rust"],
      semantic_matches: [],
      strengths: ["Python overlap"],
      actions: ["Add metrics"],
      why_this_score: ["Weighted blend."],
    }
    useResumeWizardStore.setState({
      savedResumeText: "Engineer",
      stepWorkingResume: "Engineer",
      resumeSource: "saved",
      jobDescription: "Need skills.",
      jobUrl: "",
      ...withUnlockedBundle(fixture),
    })
    render(<StepOneMatchCard />)
    const overview = screen.getByRole("tab", { name: /^overview$/i })
    expect(overview.getAttribute("aria-selected")).toBe("true")

    await userEvent.click(screen.getByRole("tab", { name: /^score breakdown$/i }))
    expect(screen.getByRole("progressbar", { name: /semantic score/i })).not.toBeNull()
    expect(screen.getByRole("progressbar", { name: /lexical score/i })).not.toBeNull()

    await userEvent.click(screen.getByRole("tab", { name: /^gaps$/i }))
    expect(screen.getByRole("tab", { name: /^gaps$/i }).getAttribute("aria-selected")).toBe("true")
  })

  it("Score breakdown lists v1 dimension labels inside progressbars", async () => {
    const fixture = {
      version: "v1" as const,
      score: 55,
      skill_match: 40,
      experience_match: 60,
      keyword_ats_match: 55,
      context_fit: 60,
      missing_skills: ["X"],
      suggestions: [],
      weak_areas: [],
    }
    useResumeWizardStore.setState({
      savedResumeText: "Engineer",
      stepWorkingResume: "Engineer",
      resumeSource: "saved",
      jobDescription: "Need skills.",
      jobUrl: "",
      ...withUnlockedBundle(fixture),
    })
    render(<StepOneMatchCard />)
    expect(
      screen.getByText(/^Needs work — close, but you should fix key gaps first\.$/),
    ).not.toBeNull()
    await userEvent.click(screen.getByRole("tab", { name: /^score breakdown$/i }))
    expect(screen.getByRole("progressbar", { name: /skills score/i })).not.toBeNull()
    expect(screen.getByRole("progressbar", { name: /keywords score/i })).not.toBeNull()
  })
})
