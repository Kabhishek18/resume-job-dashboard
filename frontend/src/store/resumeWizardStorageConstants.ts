/** Pre–user-scoping persist key (tests and fallback before ResumeWizard configures per-user name). */
export const LEGACY_RESUME_WIZARD_STORAGE_KEY = "resume-wizard-storage"

export function resumeWizardPersistStorageName(userId: number): string {
  return `${LEGACY_RESUME_WIZARD_STORAGE_KEY}-u-${userId}`
}
