import { cleanup, render, screen, waitFor } from "@testing-library/react"
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest"

import { ResumeWizard } from "@/components/resume/resume-wizard"
import { useAuthStore } from "@/store/useAuthStore"
import {
  purgeLegacyResumeWizardStorageOnce,
  resumeWizardResetLegacyPurgeFlagForTests,
} from "@/store/resume-wizard-persistence"
import { resumeWizardPersistStorageName } from "@/store/resumeWizardStorageConstants"
import { resetResumeWizardStore, useResumeWizardStore } from "@/store/useResumeWizardStore"

const getProfileMock = vi.fn()

vi.mock("@/services/profile.service", () => ({
  getProfile: (...args: unknown[]) => getProfileMock(...args),
}))

afterEach(() => cleanup())

describe("ResumeWizard persisted isolation", () => {
  beforeEach(() => {
    localStorage.clear()
    resetResumeWizardStore()
    resumeWizardResetLegacyPurgeFlagForTests()
    purgeLegacyResumeWizardStorageOnce()
    getProfileMock.mockResolvedValue({
      version: "v1",
      id: 999,
      email: "bob@example.dev",
      name: "Bob",
      resume_text: null,
      resume_updated_at: null,
    })
    useAuthStore.setState({
      token: null,
      user: null,
      sessionExpiredRedirect: false,
    })
  })

  it("does not show another user's scoped drafts after switch to Bob", async () => {
    const user1Key = resumeWizardPersistStorageName(111)
    useResumeWizardStore.persist.setOptions({ name: user1Key })
    await useResumeWizardStore.persist.rehydrate()
    useResumeWizardStore.setState({
      stepWorkingResume: "ALICE_ONLY_RESUME_BODY",
      jobDescription: "ALICE JD SECRET PHRASE",
      jobCompany: "OtherCo",
      jobTitle: "OtherRole",
      savedResumeText: "",
      resumeSource: "paste",
      currentStep: 1,
    })

    useAuthStore.setState({
      token: "token-b",
      user: {
        id: 222,
        email: "bob@example.dev",
        name: "Bob",
      },
      sessionExpiredRedirect: false,
    })

    render(<ResumeWizard />)

    await waitFor(() => {
      const tab = screen.getByRole("tab", { name: /step 1\.\s*relevance score/i })
      expect(tab).toBeTruthy()
    })

    await waitFor(() => {
      expect(getProfileMock).toHaveBeenCalled()
    })

    const persistedAlice = localStorage.getItem(user1Key)
    expect(persistedAlice ?? "").toContain("ALICE_ONLY")

    const s = useResumeWizardStore.getState()
    expect(s.stepWorkingResume).not.toBe("ALICE_ONLY_RESUME_BODY")
    expect(s.jobDescription).not.toContain("ALICE JD SECRET")
  })
})
