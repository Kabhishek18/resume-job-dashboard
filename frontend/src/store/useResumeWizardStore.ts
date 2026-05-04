import { create } from "zustand"
import { persist } from "zustand/middleware"

import { LEGACY_RESUME_WIZARD_STORAGE_KEY } from "@/store/resumeWizardStorageConstants"
import type { JobDescriptionInput } from "@/types/job"
import type { MatchPayload } from "@/types/match"
import type { TailorApiV1 } from "@/types/tailor"

export type ActiveTailorTab = "overview" | "resume" | "cover_letter"

export type SuccessfulMatchBundle = {
  resolvedResumeText: string
  job: JobDescriptionInput
  match: MatchPayload
}

export type ResumeExtractStatus = "idle" | "uploading" | "success" | "error"

export type ResumeExtractState = {
  status: ResumeExtractStatus
  errorMessage: string | null
  warnings: string[]
}

export type ResumeSourceMode = "saved" | "upload" | "paste"

type WizardState = {
  currentStep: 1 | 2
  /** Last profile resume from server or after successful PUT /profile/resume */
  savedResumeText: string
  savedResumeUpdatedAt: string | null
  /** Editable resume used for Step 1 scoring */
  stepWorkingResume: string
  resumeSource: ResumeSourceMode
  jobTitle: string
  jobUrl: string
  jobCompany: string
  jobDescription: string
  matchFingerprintAtSuccess: string | null
  lastSuccessfulBundle: SuccessfulMatchBundle | null
  includeCoverLetter: boolean
  lastTailoring: { result: TailorApiV1; includeCoverLetterRequested: boolean } | null
  /** Step 2 workspace */
  activeTailorTab: ActiveTailorTab
  editedSummary: string
  /** One bullet per line */
  editedBullets: string
  editedCoverLetter: string
  tailorDraftDirty: boolean
  resumeExtract: ResumeExtractState
}

type WizardActions = {
  setCurrentStep: (step: 1 | 2) => void
  setSavedResumeFromServer: (text: string, updatedAt: string | null) => void
  setStepWorkingResume: (text: string) => void
  setResumeSource: (mode: ResumeSourceMode) => void
  /** When profile loads and working resume is still empty, pull from profile and default source to saved */
  hydrateWorkingFromProfileIfEmpty: (profileText: string) => void
  setJobTitle: (v: string) => void
  setJobUrl: (v: string) => void
  setJobCompany: (v: string) => void
  setJobDescription: (v: string) => void
  applyImportPreview: (p: {
    title?: string | null
    company?: string | null
    raw_text?: string | null
  }) => void
  recordMatchSuccess: (bundle: SuccessfulMatchBundle) => void
  setIncludeCoverLetter: (v: boolean) => void
  setLastTailoring: (value: WizardState["lastTailoring"]) => void
  setActiveTailorTab: (tab: ActiveTailorTab) => void
  setTailorEditedSummary: (v: string) => void
  setTailorEditedBullets: (v: string) => void
  setTailorEditedCoverLetter: (v: string) => void
  resumeExtractStart: () => void
  resumeExtractSuccess: (warnings: string[]) => void
  resumeExtractError: (message: string) => void
  resumeExtractReset: () => void
}

type WizardStoreSnapshot = WizardState & WizardActions

function wizardSliceOnly(s: WizardStoreSnapshot): WizardState {
  return {
    currentStep: s.currentStep,
    savedResumeText: s.savedResumeText,
    savedResumeUpdatedAt: s.savedResumeUpdatedAt,
    stepWorkingResume: s.stepWorkingResume,
    resumeSource: s.resumeSource,
    jobTitle: s.jobTitle,
    jobUrl: s.jobUrl,
    jobCompany: s.jobCompany,
    jobDescription: s.jobDescription,
    matchFingerprintAtSuccess: s.matchFingerprintAtSuccess,
    lastSuccessfulBundle: s.lastSuccessfulBundle,
    includeCoverLetter: s.includeCoverLetter,
    lastTailoring: s.lastTailoring,
    activeTailorTab: s.activeTailorTab,
    editedSummary: s.editedSummary,
    editedBullets: s.editedBullets,
    editedCoverLetter: s.editedCoverLetter,
    tailorDraftDirty: s.tailorDraftDirty,
    resumeExtract: s.resumeExtract,
  }
}

function fingerprintInputs(s: WizardState): string {
  const resume = s.stepWorkingResume.trim()
  return JSON.stringify({
    r: resume,
    title: s.jobTitle.trim(),
    company: s.jobCompany.trim(),
    url: s.jobUrl.trim(),
    jd: s.jobDescription.trim(),
  })
}

function applyTrackedInputChange(prev: WizardState, patch: Partial<WizardState>): WizardState {
  const next = { ...prev, ...patch }
  if (!prev.matchFingerprintAtSuccess) {
    return next
  }
  if (fingerprintInputs(next) !== prev.matchFingerprintAtSuccess) {
    return {
      ...next,
      lastSuccessfulBundle: null,
      matchFingerprintAtSuccess: null,
    }
  }
  return next
}

const PERSIST_VERSION = 3

type LegacyStoredSlice = Partial<WizardState> & {
  useCustomResumeForRun?: boolean
  oneOffResumeText?: string
}

/** @internal exported for persist migration tests */
export function reconcilePersistedWizard(
  persisted: LegacyStoredSlice | undefined,
  current: WizardState,
): WizardState {
  if (!persisted || typeof persisted !== "object") {
    return current
  }

  const {
    useCustomResumeForRun: legCustom,
    oneOffResumeText: legOneOff,
    ...incoming
  } = persisted as LegacyStoredSlice

  let stepWorkingResume: string
  let resumeSource: ResumeSourceMode

  if (Object.prototype.hasOwnProperty.call(persisted, "stepWorkingResume")) {
    stepWorkingResume = String((persisted as WizardState).stepWorkingResume ?? "")
    const rs = (persisted as WizardState).resumeSource
    resumeSource =
      rs === "saved" || rs === "upload" || rs === "paste"
        ? rs
        : ((persisted.savedResumeText ?? "").trim() ? "saved" : "paste")
  } else if (typeof legCustom === "boolean") {
    const saved = typeof persisted.savedResumeText === "string" ? persisted.savedResumeText : ""
    stepWorkingResume = legCustom ? String(legOneOff ?? "") : saved
    resumeSource = saved.trim() ? (legCustom ? "paste" : "saved") : "paste"
  } else {
    stepWorkingResume = ""
    resumeSource =
      persisted.resumeSource === "saved" || persisted.resumeSource === "upload"
        ? persisted.resumeSource
        : persisted.resumeSource === "paste"
          ? "paste"
          : "paste"
  }

  return {
    ...current,
    ...incoming,
    stepWorkingResume,
    resumeSource,
  }
}

/** Initial wizard slice (persisted fields). Use {@link resetResumeWizardStore} in tests. */
export const resumeWizardInitialState: WizardState = {
  currentStep: 1,
  savedResumeText: "",
  savedResumeUpdatedAt: null,
  stepWorkingResume: "",
  resumeSource: "paste",
  jobTitle: "",
  jobUrl: "",
  jobCompany: "",
  jobDescription: "",
  matchFingerprintAtSuccess: null,
  lastSuccessfulBundle: null,
  includeCoverLetter: false,
  lastTailoring: null,
  activeTailorTab: "overview",
  editedSummary: "",
  editedBullets: "",
  editedCoverLetter: "",
  tailorDraftDirty: false,
  resumeExtract: {
    status: "idle",
    errorMessage: null,
    warnings: [],
  },
}

export const useResumeWizardStore = create<WizardState & WizardActions>()(
  persist(
    (set) => ({
      ...resumeWizardInitialState,
      setCurrentStep: (currentStep) => set({ currentStep }),
      setSavedResumeFromServer: (savedResumeText, savedResumeUpdatedAt) =>
        set((s) =>
          applyTrackedInputChange(s, {
            savedResumeText,
            savedResumeUpdatedAt,
          }),
        ),
      setStepWorkingResume: (stepWorkingResume) =>
        set((s) => applyTrackedInputChange(s, { stepWorkingResume })),
      setResumeSource: (resumeSource) =>
        set((s) => {
          if (resumeSource === "saved") {
            return applyTrackedInputChange(s, {
              resumeSource,
              stepWorkingResume: s.savedResumeText,
            })
          }
          return applyTrackedInputChange(s, { resumeSource })
        }),
      hydrateWorkingFromProfileIfEmpty: (profileText) =>
        set((s) => {
          if (s.stepWorkingResume.trim() !== "") return s
          const t = profileText.trim()
          if (!t) return s
          return applyTrackedInputChange(s, {
            stepWorkingResume: profileText,
            resumeSource: "saved",
          })
        }),
      setJobTitle: (jobTitle) => set((s) => applyTrackedInputChange(s, { jobTitle })),
      setJobUrl: (jobUrl) => set((s) => applyTrackedInputChange(s, { jobUrl })),
      setJobCompany: (jobCompany) => set((s) => applyTrackedInputChange(s, { jobCompany })),
      setJobDescription: (jobDescription) =>
        set((s) => applyTrackedInputChange(s, { jobDescription })),
      applyImportPreview: ({ title, company, raw_text }) =>
        set((s) =>
          applyTrackedInputChange(s, {
            jobTitle: title?.trim() || s.jobTitle,
            jobCompany: company?.trim() || s.jobCompany,
            jobDescription: raw_text?.trim() || s.jobDescription,
          }),
        ),
      recordMatchSuccess: (bundle) =>
        set((s) => ({
          ...s,
          lastSuccessfulBundle: bundle,
          matchFingerprintAtSuccess: fingerprintInputs(s),
          lastTailoring: null,
          activeTailorTab: "overview",
          editedSummary: "",
          editedBullets: "",
          editedCoverLetter: "",
          tailorDraftDirty: false,
        })),
      setIncludeCoverLetter: (includeCoverLetter) =>
        set((s) => ({
          ...s,
          includeCoverLetter,
          ...(includeCoverLetter
            ? {}
            : {
                editedCoverLetter: "",
                activeTailorTab:
                  s.activeTailorTab === "cover_letter" ? ("overview" as const) : s.activeTailorTab,
              }),
        })),
      setLastTailoring: (lastTailoring) =>
        set((s) => {
          if (!lastTailoring)
            return { ...s, lastTailoring: null, tailorDraftDirty: false }
          const r = lastTailoring.result
          return {
            ...s,
            lastTailoring,
            editedSummary: r.tailored_resume.summary,
            editedBullets: r.tailored_resume.bullets.join("\n"),
            editedCoverLetter: r.cover_letter ?? "",
            tailorDraftDirty: false,
          }
        }),
      setActiveTailorTab: (activeTailorTab) => set({ activeTailorTab }),
      setTailorEditedSummary: (editedSummary) => set({ editedSummary, tailorDraftDirty: true }),
      setTailorEditedBullets: (editedBullets) => set({ editedBullets, tailorDraftDirty: true }),
      setTailorEditedCoverLetter: (editedCoverLetter) =>
        set({ editedCoverLetter, tailorDraftDirty: true }),
      resumeExtractStart: () =>
        set({
          resumeExtract: { status: "uploading", errorMessage: null, warnings: [] },
        }),
      resumeExtractSuccess: (warnings: string[]) =>
        set(() => ({
          resumeExtract: { status: "success", errorMessage: null, warnings: warnings ?? [] },
        })),
      resumeExtractError: (message: string) =>
        set(() => ({
          resumeExtract: { status: "error", errorMessage: message, warnings: [] },
        })),
      resumeExtractReset: () =>
        set(() => ({
          resumeExtract: { status: "idle", errorMessage: null, warnings: [] },
        })),
    }),
    {
      name: LEGACY_RESUME_WIZARD_STORAGE_KEY,
      version: PERSIST_VERSION,
      merge: (persistedState, currentState) => ({
        ...currentState,
        ...reconcilePersistedWizard(
          persistedState as LegacyStoredSlice | undefined,
          wizardSliceOnly(currentState),
        ),
      }),
      partialize: (s): Partial<WizardState> => ({
        currentStep: s.currentStep,
        savedResumeText: s.savedResumeText,
        savedResumeUpdatedAt: s.savedResumeUpdatedAt,
        stepWorkingResume: s.stepWorkingResume,
        resumeSource: s.resumeSource,
        jobTitle: s.jobTitle,
        jobUrl: s.jobUrl,
        jobCompany: s.jobCompany,
        jobDescription: s.jobDescription,
        matchFingerprintAtSuccess: s.matchFingerprintAtSuccess,
        lastSuccessfulBundle: s.lastSuccessfulBundle,
        includeCoverLetter: s.includeCoverLetter,
        lastTailoring: s.lastTailoring,
        activeTailorTab: s.activeTailorTab,
        editedSummary: s.editedSummary,
        editedBullets: s.editedBullets,
        editedCoverLetter: s.editedCoverLetter,
        tailorDraftDirty: s.tailorDraftDirty,
      }),
      skipHydration: true,
    },
  ),
)

export function resetResumeWizardStore() {
  useResumeWizardStore.setState(resumeWizardInitialState)
}

export type ResumeWizardSlice = WizardState

export function resolvedResumeForRun(s: WizardState): string {
  return s.stepWorkingResume
}

export function isStep2UnlockedFromState(s: WizardState): boolean {
  return (
    s.lastSuccessfulBundle !== null &&
    s.matchFingerprintAtSuccess !== null &&
    s.matchFingerprintAtSuccess === fingerprintInputs(s)
  )
}

/** True when prior tailoring exists but resume/JD no longer match the analyzed fingerprint */
export function isTailorDraftStale(s: WizardState): boolean {
  return Boolean(s.lastTailoring && !isStep2UnlockedFromState(s))
}

export function isProfileResumeDirty(s: WizardState): boolean {
  return s.stepWorkingResume.trim() !== s.savedResumeText.trim()
}
