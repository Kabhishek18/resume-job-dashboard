import {
  LEGACY_RESUME_WIZARD_STORAGE_KEY,
  resumeWizardPersistStorageName,
} from "@/store/resumeWizardStorageConstants"
import {
  resetResumeWizardStore,
  useResumeWizardStore,
} from "@/store/useResumeWizardStore"

export { LEGACY_RESUME_WIZARD_STORAGE_KEY, resumeWizardPersistStorageName }

let legacyPurgeRan = false

/** Resets purge guard — use only from tests that need purge to run twice. */
export function resumeWizardResetLegacyPurgeFlagForTests(): void {
  legacyPurgeRan = false
}

/** Remove stale global drafts once per tab session before loading a user-scoped bucket. */
export function purgeLegacyResumeWizardStorageOnce(): void {
  if (legacyPurgeRan || typeof window === "undefined") return
  legacyPurgeRan = true
  try {
    localStorage.removeItem(LEGACY_RESUME_WIZARD_STORAGE_KEY)
  } catch {
    /* ignore quota / privacy mode */
  }
}

/**
 * Target the departing user's persisted blob, drop in-memory wizard state,
 * remove that user's localStorage snapshot (privacy on shared logout).
 */
export function clearWizardPersistBlobForUser(userId: number): void {
  useResumeWizardStore.persist.setOptions({
    name: resumeWizardPersistStorageName(userId),
  })
  resetResumeWizardStore()
  useResumeWizardStore.persist.clearStorage()
}

/** In-memory wizard reset without touching a specific persist key (logged-out / unknown user). */
export function resetWizardMemoryOnly(): void {
  resetResumeWizardStore()
}
