"use client"

import { ResumeWizard } from "@/components/resume/resume-wizard"
import { useAuthStore } from "@/store/useAuthStore"

/** Ensures wizard local state resets on account switch (scoped persist key alignment). */
export function ResumeWizardGate() {
  const userId = useAuthStore((s) => s.user?.id ?? 0)
  return <ResumeWizard key={userId} />
}
