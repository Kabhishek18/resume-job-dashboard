import { beforeEach, describe, expect, it } from "vitest"

import {
  clearWizardPersistBlobForUser,
  purgeLegacyResumeWizardStorageOnce,
  resumeWizardResetLegacyPurgeFlagForTests,
} from "@/store/resume-wizard-persistence"
import { LEGACY_RESUME_WIZARD_STORAGE_KEY, resumeWizardPersistStorageName } from "@/store/resumeWizardStorageConstants"
import { useAuthStore } from "@/store/useAuthStore"
import { resetResumeWizardStore, useResumeWizardStore } from "@/store/useResumeWizardStore"

describe("resumeWizardPersistence", () => {
  beforeEach(() => {
    localStorage.clear()
    resetResumeWizardStore()
    resumeWizardResetLegacyPurgeFlagForTests()
    useResumeWizardStore.persist.setOptions({
      name: LEGACY_RESUME_WIZARD_STORAGE_KEY,
    })
  })

  it("isolates drafts under different user-scoped storage names", async () => {
    const nameUser1 = resumeWizardPersistStorageName(111)
    const nameUser2 = resumeWizardPersistStorageName(222)

    useResumeWizardStore.persist.setOptions({ name: nameUser1 })
    await useResumeWizardStore.persist.rehydrate()
    useResumeWizardStore.setState({ stepWorkingResume: "alice_resume", jobDescription: "alice_jd" })

    useResumeWizardStore.persist.setOptions({ name: nameUser2 })
    resetResumeWizardStore()
    await useResumeWizardStore.persist.rehydrate()

    const sEmpty = useResumeWizardStore.getState()
    expect(sEmpty.stepWorkingResume).toBe("")
    expect(sEmpty.jobDescription).toBe("")

    useResumeWizardStore.persist.setOptions({ name: nameUser1 })
    await useResumeWizardStore.persist.rehydrate()
    expect(useResumeWizardStore.getState().stepWorkingResume).toBe("alice_resume")
    expect(useResumeWizardStore.getState().jobDescription).toBe("alice_jd")
  })

  it("purgeLegacyResumeWizardStorageOnce removes the legacy unprefixed blob", () => {
    localStorage.setItem(LEGACY_RESUME_WIZARD_STORAGE_KEY, "{}")
    purgeLegacyResumeWizardStorageOnce()
    expect(localStorage.getItem(LEGACY_RESUME_WIZARD_STORAGE_KEY)).toBeNull()
    localStorage.setItem(LEGACY_RESUME_WIZARD_STORAGE_KEY, "{}")
    purgeLegacyResumeWizardStorageOnce()
    expect(localStorage.getItem(LEGACY_RESUME_WIZARD_STORAGE_KEY)).not.toBeNull()
    resumeWizardResetLegacyPurgeFlagForTests()
    purgeLegacyResumeWizardStorageOnce()
    expect(localStorage.getItem(LEGACY_RESUME_WIZARD_STORAGE_KEY)).toBeNull()
  })

  it("clearWizardPersistBlobForUser resets memory and removes that user's persist entry", async () => {
    const uid = 9001
    const nameUser = resumeWizardPersistStorageName(uid)
    useResumeWizardStore.persist.setOptions({ name: nameUser })
    await useResumeWizardStore.persist.rehydrate()
    useResumeWizardStore.setState({ stepWorkingResume: "leaving_user", jobCompany: "acme" })
    clearWizardPersistBlobForUser(uid)

    expect(useResumeWizardStore.getState().stepWorkingResume).toBe("")
    expect(localStorage.getItem(nameUser)).toBeNull()

    await useResumeWizardStore.persist.rehydrate()
    expect(useResumeWizardStore.getState().stepWorkingResume).toBe("")
    expect(useResumeWizardStore.getState().jobCompany).toBe("")
  })

  it("logout clears departing user's scoped blob via clearWizardPersistBlobForUser path", async () => {
    const uid = 42
    const nameUser = resumeWizardPersistStorageName(uid)
    useResumeWizardStore.persist.setOptions({ name: nameUser })
    await useResumeWizardStore.persist.rehydrate()
    useResumeWizardStore.setState({ stepWorkingResume: "draft_on_logout", jobCompany: "x" })
    useAuthStore.setState({
      token: "t",
      user: { id: uid, email: "x@example.com", name: "Log" },
      sessionExpiredRedirect: false,
    })

    useAuthStore.getState().logout()

    expect(useAuthStore.getState().token).toBeNull()
    expect(localStorage.getItem(nameUser)).toBeNull()
    expect(useResumeWizardStore.getState().stepWorkingResume).toBe("")
  })
})
