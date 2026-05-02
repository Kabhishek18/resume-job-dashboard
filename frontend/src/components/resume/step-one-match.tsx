"use client"

import { useCallback, useMemo, useRef, useState } from "react"

import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { MatchResultSummaryStrip } from "@/components/resume/step-one-result/match-result-summary-strip"
import { MatchResultTabs } from "@/components/resume/step-one-result/match-result-tabs"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Textarea } from "@/components/ui/textarea"
import { useMatch } from "@/hooks/useMatch"
import { ApiError } from "@/lib/api"
import { buildStep1ResultViewModel, type Step1TabId } from "@/lib/match-verdict-ui"
import { cn } from "@/lib/utils"
import { postExtractResumeFile } from "@/services/resume-extract.service"
import { putSavedResume } from "@/services/profile.service"
import { postImportPreview } from "@/services/import-job.service"
import {
  isProfileResumeDirty,
  isStep2UnlockedFromState,
  resolvedResumeForRun,
  useResumeWizardStore,
} from "@/store/useResumeWizardStore"
import type { ResumeSourceMode } from "@/store/useResumeWizardStore"
import { useAuthStore } from "@/store/useAuthStore"
import type { ImportPreviewMode } from "@/types/import-job"
import type { JobDescriptionInput } from "@/types/job"
import type { MatchPayload } from "@/types/match"

const RESUME_UPLOAD_ACCEPT =
  ".pdf,.docx,.txt,application/pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document,text/plain"

function apiBaseHint(): string {
  return (process.env.NEXT_PUBLIC_API_BASE || process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000").replace(
    /\/$/,
    "",
  )
}

function ImportHealthBadge({ mode }: { mode: ImportPreviewMode | null }) {
  if (!mode) return null
  const variants: Record<ImportPreviewMode, { label: string; className: string }> = {
    imported_full: {
      label: "Import: JD captured",
      className: "border-emerald-500/40 bg-emerald-500/10 text-emerald-900 dark:text-emerald-200",
    },
    imported_partial: {
      label: "Import: partial",
      className: "border-amber-500/40 bg-amber-500/10 text-amber-950 dark:text-amber-100",
    },
    fallback_required: {
      label: "Import: failed / manual needed",
      className: "border-destructive/40 bg-destructive/5 text-destructive",
    },
  }
  const v = variants[mode]
  return (
    <span
      className={cn("inline-flex items-center rounded-full border px-2 py-0.5 text-xs font-medium", v.className)}
    >
      {v.label}
    </span>
  )
}

const SOURCE_CHOICES: { id: ResumeSourceMode; label: string }[] = [
  { id: "saved", label: "Use saved resume" },
  { id: "upload", label: "Upload resume" },
  { id: "paste", label: "Paste resume text" },
]

export function StepOneMatchCard() {
  const token = useAuthStore((s) => s.token)!

  const stepWorkingResume = useResumeWizardStore((s) => s.stepWorkingResume)
  const setStepWorkingResume = useResumeWizardStore((s) => s.setStepWorkingResume)
  const resumeSource = useResumeWizardStore((s) => s.resumeSource)
  const setResumeSource = useResumeWizardStore((s) => s.setResumeSource)
  const savedResumeUpdatedAt = useResumeWizardStore((s) => s.savedResumeUpdatedAt)
  const setSavedFromServer = useResumeWizardStore((s) => s.setSavedResumeFromServer)

  const jobTitle = useResumeWizardStore((s) => s.jobTitle)
  const jobUrl = useResumeWizardStore((s) => s.jobUrl)
  const jobCompany = useResumeWizardStore((s) => s.jobCompany)
  const jobDescription = useResumeWizardStore((s) => s.jobDescription)
  const setJobTitle = useResumeWizardStore((s) => s.setJobTitle)
  const setJobUrl = useResumeWizardStore((s) => s.setJobUrl)
  const setJobCompany = useResumeWizardStore((s) => s.setJobCompany)
  const setJobDesc = useResumeWizardStore((s) => s.setJobDescription)
  const applyImportPreview = useResumeWizardStore((s) => s.applyImportPreview)
  const recordMatchSuccess = useResumeWizardStore((s) => s.recordMatchSuccess)
  const setStep = useResumeWizardStore((s) => s.setCurrentStep)

  const resumeExtract = useResumeWizardStore((s) => s.resumeExtract)
  const resumeExtractStart = useResumeWizardStore((s) => s.resumeExtractStart)
  const resumeExtractSuccess = useResumeWizardStore((s) => s.resumeExtractSuccess)
  const resumeExtractError = useResumeWizardStore((s) => s.resumeExtractError)

  const state = useResumeWizardStore()

  const lastSuccessfulBundle = useResumeWizardStore((s) => s.lastSuccessfulBundle)

  const matchFingerprintAtSuccess = useResumeWizardStore((s) => s.matchFingerprintAtSuccess)

  const fileInputRef = useRef<HTMLInputElement>(null)

  const { error, loading, runMatch } = useMatch()
  const [importBusy, setImportBusy] = useState(false)
  const [importNotes, setImportNotes] = useState<string[] | null>(null)
  const [importError, setImportError] = useState<string | null>(null)
  const [lastImportMode, setLastImportMode] = useState<ImportPreviewMode | null>(null)

  const [saveBusy, setSaveBusy] = useState(false)
  const [saveMessage, setSaveMessage] = useState<string | null>(null)
  const [saveError, setSaveError] = useState<string | null>(null)

  const resolved = resolvedResumeForRun(state)
  const canContinue = useMemo(() => isStep2UnlockedFromState(state), [state])
  const profileDirty = useMemo(() => isProfileResumeDirty(state), [state])

  const hasUsableJd = jobDescription.trim().length >= 1

  const uploadBusy = resumeExtract.status === "uploading"
  const uploadErrorFlag = resumeExtract.status === "error" ? resumeExtract.errorMessage : null
  const uploadWarnings = resumeExtract.warnings

  const jobPayload: JobDescriptionInput = useMemo(
    () => ({
      title: jobTitle.trim() || undefined,
      company: jobCompany.trim() || undefined,
      raw_text: jobDescription.trim(),
      url: jobUrl.trim() || undefined,
    }),
    [jobTitle, jobCompany, jobDescription, jobUrl],
  )

  const focusWorkingResume = useCallback(() => {
    requestAnimationFrame(() => {
      const el = document.getElementById("step-working-resume") as HTMLTextAreaElement | null
      el?.focus()
      el?.setSelectionRange(el.value.length, el.value.length)
    })
  }, [])

  const saveWorkingToProfile = useCallback(async () => {
    setSaveBusy(true)
    setSaveError(null)
    setSaveMessage(null)
    try {
      const res = await putSavedResume(token, stepWorkingResume.trim())
      setSavedFromServer(res.resume_text ?? "", res.resume_updated_at ?? null)
      setSaveMessage("Saved to your profile.")
    } catch (e) {
      setSaveError(e instanceof Error ? e.message : "Save failed.")
    } finally {
      setSaveBusy(false)
    }
  }, [setSavedFromServer, stepWorkingResume, token])

  async function extractFileIntoWorking(file: File) {
    setResumeSource("upload")
    resumeExtractStart()
    try {
      const res = await postExtractResumeFile(token, file)
      resumeExtractSuccess(res.warnings ?? [])
      setStepWorkingResume(res.plain_text)
      focusWorkingResume()
    } catch (e) {
      resumeExtractError(
        e instanceof ApiError ? `${e.code}: ${e.message}` : e instanceof Error ? e.message : "Extract failed.",
      )
    } finally {
      if (fileInputRef.current) fileInputRef.current.value = ""
    }
  }

  async function analyzeClick(ev: React.FormEvent) {
    ev.preventDefault()
    try {
      const result = await runMatch({
        raw_resume_text: resolved.trim(),
        job: jobPayload,
      })
      recordMatchSuccess({
        resolvedResumeText: resolved.trim(),
        job: jobPayload,
        match: result,
      })
    } catch {
      /* hook sets error */
    }
  }

  async function importFromUrl() {
    setImportBusy(true)
    setImportError(null)
    setImportNotes(null)
    try {
      const url = jobUrl.trim()
      if (!url) {
        setImportError("Enter a URL first, or paste job title and description manually.")
        return
      }
      const preview = await postImportPreview(url)
      setLastImportMode(preview.mode)
      setImportNotes(preview.warnings.length ? preview.warnings : null)
      applyImportPreview({
        title: preview.title ?? undefined,
        company: preview.company ?? undefined,
        raw_text: preview.raw_text ?? undefined,
      })
      const noJdImported = !(preview.raw_text ?? "").trim()
      if (noJdImported && preview.mode === "imported_full") {
        setImportError("Import reported JD captured but returned empty text — paste the description manually.")
      }
    } catch (e) {
      setLastImportMode("fallback_required")
      setImportError(e instanceof Error ? e.message : "Import failed.")
    } finally {
      setImportBusy(false)
    }
  }

  const showTitleOnlyBanner =
    !hasUsableJd &&
    Boolean(jobTitle.trim()) &&
    (lastImportMode === "imported_partial" || lastImportMode === "fallback_required")

  const analyzeDisabled = loading || !resolved.trim() || !hasUsableJd

  return (
    <Card>
      <CardHeader>
        <CardTitle>Step 1 — Resume and job relevance</CardTitle>
        <CardDescription>
          Add your resume, then paste or import job details — score matches here before tailoring. Job URL stays
          optional. Backend:&nbsp;
          <code className="bg-muted rounded px-1 py-0.5 text-xs">{apiBaseHint()}</code>
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-8">
        <section className="space-y-4" aria-labelledby="resume-section-label">
          <div className="flex flex-wrap items-center gap-2">
            <h3 id="resume-section-label" className="text-sm font-semibold tracking-tight">
              Resume for this run
            </h3>
          </div>
          <div
            className="bg-muted/40 inline-flex flex-wrap gap-2 rounded-lg border p-1"
            role="group"
            aria-label="Resume source"
          >
            {SOURCE_CHOICES.map(({ id, label }) => (
              <Button
                key={id}
                type="button"
                size="sm"
                variant={resumeSource === id ? "default" : "outline"}
                className={cn("shrink-0", resumeSource !== id && "bg-background")}
                disabled={uploadBusy || saveBusy}
                onClick={() => setResumeSource(id)}
              >
                {label}
              </Button>
            ))}
          </div>

          <input
            ref={fileInputRef}
            type="file"
            accept={RESUME_UPLOAD_ACCEPT}
            className="hidden"
            onChange={(e) => {
              const f = e.target.files?.[0]
              if (!f) return
              void extractFileIntoWorking(f)
            }}
          />

          {resumeSource === "saved" ? (
            <p className="text-muted-foreground max-w-xl text-xs">
              Text below is what we score against. Matches your saved profile snapshot until you upload, paste, or edit
              differently.
            </p>
          ) : null}

          {resumeSource === "upload" ? (
            <div className="space-y-2">
              <Button
                type="button"
                variant="secondary"
                size="sm"
                disabled={uploadBusy || saveBusy}
                onClick={() => fileInputRef.current?.click()}
              >
                {uploadBusy ? "Extracting…" : "Choose PDF, DOCX, or TXT"}
              </Button>
              <p className="text-muted-foreground text-xs">
                Simple text extraction only — skim the box below before Analyze.
              </p>
            </div>
          ) : null}

          {resumeSource === "paste" ? (
            <p className="text-muted-foreground max-w-xl text-xs">Paste plain text resume content into the box below.</p>
          ) : null}

          {uploadErrorFlag ? (
            <p className="text-destructive text-sm" role="alert">
              {uploadErrorFlag}
            </p>
          ) : null}

          <div className="space-y-2">
            <Label htmlFor="step-working-resume">Resume text (used for Analyze)</Label>
            <textarea
              id="step-working-resume"
              value={stepWorkingResume}
              onChange={(ev) => setStepWorkingResume(ev.target.value)}
              rows={16}
              className={cn(
                "flex min-h-[12rem] w-full rounded-lg border border-input bg-transparent px-2.5 py-2 font-mono text-sm transition-colors outline-none placeholder:text-muted-foreground focus-visible:border-ring focus-visible:ring-3 focus-visible:ring-ring/50 md:text-sm dark:bg-input/30",
              )}
              placeholder="Your resume plain text appears here…"
            />
          </div>

          {uploadWarnings.length ? (
            <ul className="text-muted-foreground list-disc space-y-1 border-l-2 border-amber-500/40 pl-4 text-xs">
              {uploadWarnings.map((w) => (
                <li key={w}>{w}</li>
              ))}
            </ul>
          ) : null}

          {profileDirty ? (
            <div className="flex flex-wrap items-center gap-3">
              <Button type="button" variant="outline" disabled={saveBusy || !stepWorkingResume.trim()} onClick={saveWorkingToProfile}>
                {saveBusy ? "Saving…" : "Save to profile"}
              </Button>
              <span className="text-muted-foreground text-xs">
                Saves your current resume text to your account (no auto-save on upload or paste).
              </span>
            </div>
          ) : null}

          <p className="text-muted-foreground text-xs">
            {savedResumeUpdatedAt
              ? `Last profile save: ${new Date(savedResumeUpdatedAt).toLocaleString()}`
              : "No profile save yet — optional after you are happy with the text above."}
          </p>

          {saveMessage ? <p className="text-sm text-green-700 dark:text-green-400">{saveMessage}</p> : null}
          {saveError ? <p className="text-destructive text-sm">{saveError}</p> : null}

          {!resolved.trim() ? (
            <p className="text-destructive text-sm">Add resume text above to enable scoring.</p>
          ) : null}
        </section>

        <form onSubmit={analyzeClick} className="space-y-4">
          <div className="grid gap-4 sm:grid-cols-2">
            <div className="space-y-2">
              <Label htmlFor="job-title">Job title</Label>
              <Input
                id="job-title"
                value={jobTitle}
                onChange={(ev) => setJobTitle(ev.target.value)}
                placeholder="e.g. Backend Engineer"
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="job-company">Company</Label>
              <Input
                id="job-company"
                value={jobCompany}
                onChange={(ev) => setJobCompany(ev.target.value)}
                placeholder="Optional"
              />
            </div>
          </div>

          <div className="space-y-2">
            <Label htmlFor="job-desc">Job description</Label>
            <Textarea
              id="job-desc"
              value={jobDescription}
              onChange={(ev) => setJobDesc(ev.target.value)}
              rows={10}
              className="font-mono text-sm"
              placeholder="Paste the full JD here first; URL import is optional below…"
            />
          </div>

          {showTitleOnlyBanner ? (
            <p className="border-amber-500/40 bg-amber-500/10 rounded-md border p-3 text-sm text-amber-950 dark:text-amber-100">
              <strong>Job description not imported.</strong> Paste the full JD in the Job description field above to
              continue.
            </p>
          ) : null}

          <div className="space-y-2">
            <div className="flex flex-wrap items-center gap-2">
              <Label htmlFor="job-url" className="text-muted-foreground">
                Job URL (optional)
              </Label>
              <ImportHealthBadge mode={lastImportMode} />
            </div>
            <div className="flex flex-wrap gap-2">
              <Input
                id="job-url"
                value={jobUrl}
                onChange={(ev) => {
                  setJobUrl(ev.target.value)
                  setLastImportMode(null)
                }}
                placeholder="https://…"
                className="max-w-xl min-w-[12rem] flex-1"
                autoComplete="off"
              />
              <Button type="button" variant="secondary" disabled={importBusy || !jobUrl.trim()} onClick={importFromUrl}>
                {importBusy ? "Importing…" : "Import from URL"}
              </Button>
            </div>
            <p className="text-muted-foreground text-xs">
              Optional helper — leave empty and keep the JD in the field above. Many job sites return title only.
            </p>
          </div>

          {importError ? (
            <p className="text-destructive text-sm font-medium" role="alert">
              {importError}
            </p>
          ) : null}
          {importNotes?.length ? (
            <div className="rounded-md border border-amber-500/25 bg-amber-500/5 p-3 text-xs">
              <p className="text-muted-foreground mb-1 font-semibold uppercase tracking-wide">Import notices</p>
              <ul className="text-muted-foreground list-disc space-y-1 pl-5">
                {importNotes.map((w) => (
                  <li key={w}>{w}</li>
                ))}
              </ul>
            </div>
          ) : null}

          <Button type="submit" disabled={analyzeDisabled}>
            {loading ? "Analyzing…" : "Analyze match"}
          </Button>
          {!hasUsableJd && resolved.trim() ? (
            <p className="text-muted-foreground text-xs">Paste job description text to enable Analyze.</p>
          ) : null}
        </form>

        {error ? (
          <div
            className="border-destructive/50 bg-destructive/5 text-destructive rounded-md border p-4 text-sm"
            role="alert"
          >
            <p className="font-medium">Could not score this pair</p>
            <p className="text-destructive/90 mt-1 font-mono text-xs">{error}</p>
          </div>
        ) : null}

        {lastSuccessfulBundle && canContinue ? (
          <>
            <MatchResultPanel key={matchFingerprintAtSuccess ?? "unset"} data={lastSuccessfulBundle.match} />
            <div className="mt-6">
              <Button type="button" onClick={() => setStep(2)}>
                Continue to Step 2
              </Button>
            </div>
          </>
        ) : null}
      </CardContent>
    </Card>
  )
}

function MatchResultPanel({ data }: { data: MatchPayload }) {
  const vm = useMemo(() => buildStep1ResultViewModel(data), [data])
  const [tab, setTab] = useState<Step1TabId>("overview")

  return (
    <div className="mt-6 space-y-6">
      <MatchResultSummaryStrip vm={vm} />

      <section className="space-y-3" aria-labelledby="top-actions-heading">
        <h3 id="top-actions-heading" className="text-sm font-semibold tracking-tight">
          Top 3 next actions
        </h3>
        <ol className="bg-primary/5 border-primary/20 dark:bg-primary/10 list-decimal space-y-2 rounded-xl border p-4 pl-8 text-sm">
          {vm.topThreeActions.length ? (
            vm.topThreeActions.map((a) => <li key={a}>{a}</li>)
          ) : (
            <li className="text-muted-foreground list-none -ml-4 pl-0">
              Open the Improve tab for concrete next steps — no ranked actions returned for this score.
            </li>
          )}
        </ol>
      </section>

      {vm.blockersTeaser.some(Boolean) ? (
        <div className="rounded-lg border bg-muted/20 p-4">
          <h3 className="text-sm font-semibold">Key blockers</h3>
          <ul className="text-muted-foreground mt-2 list-disc space-y-1 pl-5 text-sm">
            {vm.blockersTeaser.map((b) =>
              b ? (
                <li key={b} className="leading-snug">
                  {b}
                </li>
              ) : null,
            )}
          </ul>
        </div>
      ) : null}

      <MatchResultTabs vm={vm} tab={tab} onTabChange={setTab} />
    </div>
  )
}
