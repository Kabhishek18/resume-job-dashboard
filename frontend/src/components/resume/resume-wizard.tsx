"use client"

import { useEffect, useState } from "react"

import { ResumeWizardTabs } from "@/components/resume/resume-wizard-tabs"
import { StepOneMatchCard } from "@/components/resume/step-one-match"
import { StepTwoTailorCard } from "@/components/resume/step-two-tailor"
import { Skeleton } from "@/components/ui/skeleton"
import { getProfile } from "@/services/profile.service"
import { useAuthStore } from "@/store/useAuthStore"
import { purgeLegacyResumeWizardStorageOnce } from "@/store/resume-wizard-persistence"
import { resumeWizardPersistStorageName } from "@/store/resumeWizardStorageConstants"
import {
  isStep2UnlockedFromState,
  resetResumeWizardStore,
  useResumeWizardStore,
} from "@/store/useResumeWizardStore"

export function ResumeWizard() {
  const token = useAuthStore((s) => s.token)
  const userId = useAuthStore((s) => s.user?.id)
  const currentStep = useResumeWizardStore((s) => s.currentStep)
  const setStep = useResumeWizardStore((s) => s.setCurrentStep)
  const setSavedFromServer = useResumeWizardStore((s) => s.setSavedResumeFromServer)
  const hydrateWorkingFromProfileIfEmpty = useResumeWizardStore((s) => s.hydrateWorkingFromProfileIfEmpty)

  const [wizReady, setWizReady] = useState(false)

  useEffect(() => {
    if (userId == null) return undefined
    purgeLegacyResumeWizardStorageOnce()
    useResumeWizardStore.persist.setOptions({
      name: resumeWizardPersistStorageName(userId),
    })
    resetResumeWizardStore()
    const unsub = useResumeWizardStore.persist.onFinishHydration(() => setWizReady(true))
    void useResumeWizardStore.persist.rehydrate()
    return unsub
  }, [userId])

  useEffect(() => {
    if (!wizReady || !token) return
    void getProfile(token)
      .then((p) => {
        const text = p.resume_text ?? ""
        setSavedFromServer(text, p.resume_updated_at ?? null)
        hydrateWorkingFromProfileIfEmpty(text)
      })
      .catch(() => {
        /* keep persisted draft */
      })
  }, [wizReady, token, setSavedFromServer, hydrateWorkingFromProfileIfEmpty])

  const unlocked = useResumeWizardStore((s) => isStep2UnlockedFromState(s))

  if (!wizReady) {
    return <Skeleton className="h-[480px] w-full rounded-xl" />
  }

  return (
    <div className="flex min-w-0 flex-col gap-6">
      <ResumeWizardTabs
        currentStep={currentStep}
        canAccessStep2={unlocked}
        onSelectStep={(s) => {
          if (s === 2 && !unlocked) return
          setStep(s)
        }}
      />
      <div className="min-w-0 space-y-6">
        {currentStep === 1 ? <StepOneMatchCard /> : null}
        {currentStep === 2 ? <StepTwoTailorCard /> : null}
      </div>
    </div>
  )
}
