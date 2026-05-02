import { beforeEach, describe, expect, it } from "vitest"

import {
  isProfileResumeDirty,
  isStep2UnlockedFromState,
  isTailorDraftStale,
  reconcilePersistedWizard,
  resetResumeWizardStore,
  resumeWizardInitialState,
  useResumeWizardStore,
} from "@/store/useResumeWizardStore"

describe("useResumeWizardStore import + lock", () => {
  beforeEach(() => {
    localStorage.clear()
    resetResumeWizardStore()
  })

  it("applyImportPreview does not wipe jobDescription when raw_text missing", () => {
    useResumeWizardStore.setState({ jobDescription: "Manual JD pasted by user.", jobTitle: "" })
    useResumeWizardStore.getState().applyImportPreview({
      title: "Imported role title",
      company: null,
      raw_text: null,
    })
    const s = useResumeWizardStore.getState()
    expect(s.jobTitle).toBe("Imported role title")
    expect(s.jobDescription).toBe("Manual JD pasted by user.")
  })

  it("editing JD after match clears Step2 bundle", () => {
    const matchFixture = {
      version: "v1" as const,
      score: 50,
      skill_match: 50,
      experience_match: 50,
      keyword_ats_match: 50,
      context_fit: 50,
      missing_skills: [],
      suggestions: [],
      weak_areas: [],
    }
    useResumeWizardStore.setState({
      savedResumeText: "Resume body",
      stepWorkingResume: "Resume body",
      resumeSource: "saved",
      jobTitle: "",
      jobDescription: "Job desc",
    })
    useResumeWizardStore.getState().recordMatchSuccess({
      resolvedResumeText: "Resume body",
      job: { raw_text: "Job desc" },
      match: matchFixture,
    })
    expect(useResumeWizardStore.getState().lastSuccessfulBundle).not.toBeNull()
    expect(isStep2UnlockedFromState(useResumeWizardStore.getState())).toBe(true)
    useResumeWizardStore.getState().setJobDescription("Changed JD")
    expect(useResumeWizardStore.getState().lastSuccessfulBundle).toBeNull()
    expect(isStep2UnlockedFromState(useResumeWizardStore.getState())).toBe(false)
  })

  it("keeps last tailoring after JD drift for stale-draft messaging", () => {
    useResumeWizardStore.setState({
      savedResumeText: "Resume body",
      stepWorkingResume: "Resume body",
      resumeSource: "saved",
      jobDescription: "Job desc",
    })
    const matchFixture = {
      version: "v1" as const,
      score: 50,
      skill_match: 50,
      experience_match: 50,
      keyword_ats_match: 50,
      context_fit: 50,
      missing_skills: [],
      suggestions: [],
      weak_areas: [],
    }
    useResumeWizardStore.getState().recordMatchSuccess({
      resolvedResumeText: "Resume body",
      job: { raw_text: "Job desc" },
      match: matchFixture,
    })
    useResumeWizardStore.setState({
      lastTailoring: {
        includeCoverLetterRequested: false,
        result: {
          version: "v1",
          provider_mode: "stub",
          review: { add: [], remove: [], improve: [] },
          tailored_resume: { summary: "S", bullets: [] },
        },
      },
    })
    useResumeWizardStore.getState().setJobDescription("Different")
    expect(useResumeWizardStore.getState().lastTailoring).not.toBeNull()
    expect(isTailorDraftStale(useResumeWizardStore.getState())).toBe(true)
  })
})

describe("hydrateWorkingFromProfileIfEmpty", () => {
  beforeEach(() => resetResumeWizardStore())

  it("fills working resume and sets source saved when working empty", () => {
    useResumeWizardStore.getState().hydrateWorkingFromProfileIfEmpty("Canonical profile text")
    const s = useResumeWizardStore.getState()
    expect(s.stepWorkingResume).toBe("Canonical profile text")
    expect(s.resumeSource).toBe("saved")
  })

  it("does not overwrite existing working resume", () => {
    useResumeWizardStore.setState({ stepWorkingResume: "Pinned draft", resumeSource: "paste" })
    useResumeWizardStore.getState().hydrateWorkingFromProfileIfEmpty("canonical")
    const s = useResumeWizardStore.getState()
    expect(s.stepWorkingResume).toBe("Pinned draft")
  })
})

describe("reconcilePersistedWizard", () => {
  it("maps legacy custom run onto working resume", () => {
    const merged = reconcilePersistedWizard(
      {
        savedResumeText: "Profile",
        useCustomResumeForRun: true,
        oneOffResumeText: "Scratch",
      },
      resumeWizardInitialState,
    )
    expect(merged.stepWorkingResume).toBe("Scratch")
    expect(merged.resumeSource).toBe("paste")
  })

  it("respects persisted stepWorkingResume when present", () => {
    const merged = reconcilePersistedWizard(
      {
        savedResumeText: "A",
        stepWorkingResume: "Working",
        resumeSource: "upload",
      },
      resumeWizardInitialState,
    )
    expect(merged.stepWorkingResume).toBe("Working")
    expect(merged.resumeSource).toBe("upload")
  })

  it("returns current when persisted undefined", () => {
    expect(reconcilePersistedWizard(undefined, resumeWizardInitialState)).toEqual(resumeWizardInitialState)
  })
})

describe("isProfileResumeDirty", () => {
  beforeEach(() => resetResumeWizardStore())

  it("true when trims differ between working and saved", () => {
    useResumeWizardStore.setState({ savedResumeText: "same", stepWorkingResume: "different \n", resumeSource: "paste" })
    expect(isProfileResumeDirty(useResumeWizardStore.getState())).toBe(true)
  })

  it("false when equal after trim", () => {
    useResumeWizardStore.setState({
      savedResumeText: "x",
      stepWorkingResume: "x \n ",
      resumeSource: "paste",
    })
    expect(isProfileResumeDirty(useResumeWizardStore.getState())).toBe(false)
  })
})
