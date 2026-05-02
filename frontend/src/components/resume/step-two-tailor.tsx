"use client"

import { useCallback, useEffect, useId, useMemo, useState } from "react"

import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Label } from "@/components/ui/label"
import { Textarea } from "@/components/ui/textarea"
import { cn } from "@/lib/utils"
import { ApiError } from "@/lib/api"
import { buildStep1ResultViewModel } from "@/lib/match-verdict-ui"
import { buildDoTheseFirst } from "@/lib/tailor-step2-utils"
import { postTailor } from "@/services/tailor.service"
import {
  type ActiveTailorTab,
  isStep2UnlockedFromState,
  useResumeWizardStore,
} from "@/store/useResumeWizardStore"
import { matchBundleToSnapshots, type TailorApiV1 } from "@/types/tailor"
import { isMatchV2 } from "@/types/match"

const TAB_IDS: { id: ActiveTailorTab; label: string }[] = [
  { id: "overview", label: "Overview" },
  { id: "resume", label: "Tailored resume" },
]

function useCopyFeedback() {
  const [label, setLabel] = useState<string | null>(null)
  useEffect(() => {
    if (!label) return
    const t = window.setTimeout(() => setLabel(null), 2000)
    return () => window.clearTimeout(t)
  }, [label])
  const copy = useCallback(async (text: string, successMessage: string) => {
    try {
      await navigator.clipboard.writeText(text)
      setLabel(successMessage)
    } catch {
      setLabel("Copy failed")
    }
  }, [])
  return { copyLabel: label, copy }
}

function fullResumeDraftBlock(summary: string, bulletsText: string): string {
  const lines = bulletsText
    .split("\n")
    .map((l) => l.trim())
    .filter(Boolean)
  const bullets = lines.map((l) => `• ${l}`).join("\n")
  return [summary.trim(), bullets].filter(Boolean).join("\n\n")
}

export function StepTwoTailorCard() {
  const bundle = useResumeWizardStore((s) => s.lastSuccessfulBundle)
  const includeCoverLetter = useResumeWizardStore((s) => s.includeCoverLetter)
  const setCover = useResumeWizardStore((s) => s.setIncludeCoverLetter)
  const lastTailoring = useResumeWizardStore((s) => s.lastTailoring)
  const setLastTailoring = useResumeWizardStore((s) => s.setLastTailoring)
  const activeTailorTab = useResumeWizardStore((s) => s.activeTailorTab)
  const setActiveTailorTab = useResumeWizardStore((s) => s.setActiveTailorTab)
  const editedSummary = useResumeWizardStore((s) => s.editedSummary)
  const editedBullets = useResumeWizardStore((s) => s.editedBullets)
  const editedCoverLetter = useResumeWizardStore((s) => s.editedCoverLetter)
  const setEditedSummary = useResumeWizardStore((s) => s.setTailorEditedSummary)
  const setEditedBullets = useResumeWizardStore((s) => s.setTailorEditedBullets)
  const setEditedCoverLetter = useResumeWizardStore((s) => s.setTailorEditedCoverLetter)
  const jobTitle = useResumeWizardStore((s) => s.jobTitle)
  const jobCompany = useResumeWizardStore((s) => s.jobCompany)
  const state = useResumeWizardStore()

  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const { copyLabel, copy } = useCopyFeedback()
  const baseId = useId().replace(/:/g, "")

  const unlocked = isStep2UnlockedFromState(state)
  const hasGenerated = Boolean(lastTailoring)

  /** When bundle is present and inputs still match analyze, tailoring is allowed */
  const canGenerate = bundle && unlocked && !busy

  const coverTabVisible =
    includeCoverLetter || Boolean(lastTailoring?.includeCoverLetterRequested)

  const tabs = useMemo(() => {
    const t = [...TAB_IDS]
    if (coverTabVisible) t.push({ id: "cover_letter", label: "Cover letter" } as const)
    return t
  }, [coverTabVisible])

  useEffect(() => {
    if (activeTailorTab === "cover_letter" && !coverTabVisible) {
      setActiveTailorTab("overview")
    }
  }, [activeTailorTab, coverTabVisible, setActiveTailorTab])

  const stepOneVm = bundle ? buildStep1ResultViewModel(bundle.match) : null
  const stepOneActions = useMemo(() => {
    if (!bundle) return [] as string[]
    return bundle.match.version === "v2" ? bundle.match.actions : bundle.match.suggestions
  }, [bundle])

  const doTheseFirst = useMemo(() => {
    if (!lastTailoring?.result?.review) return []
    return buildDoTheseFirst(lastTailoring.result.review, stepOneActions)
  }, [lastTailoring, stepOneActions])

  const optimizingLine = useMemo(() => {
    if (!bundle) return ""
    const m = bundle.match
    if (isMatchV2(m) && m.missing_hard_skills.length) {
      return `Closer alignment on: ${m.missing_hard_skills.slice(0, 4).join(", ")}.`
    }
    if (!isMatchV2(m) && m.missing_skills.length) {
      return `Closer alignment on: ${m.missing_skills.slice(0, 4).join(", ")}.`
    }
    return "Stronger wording and JD-relevant bullets without inventing facts."
  }, [bundle])

  async function generate() {
    if (!bundle || !unlocked) return
    setBusy(true)
    setError(null)
    try {
      const { match_snapshot, match_snapshot_v2 } = matchBundleToSnapshots(bundle.match)
      const res = await postTailor({
        resume_text: bundle.resolvedResumeText,
        job: bundle.job,
        include_cover_letter: includeCoverLetter,
        ...(match_snapshot ? { match_snapshot } : {}),
        ...(match_snapshot_v2 ? { match_snapshot_v2 } : {}),
      })
      setLastTailoring({
        result: res,
        includeCoverLetterRequested: includeCoverLetter,
      })
      setActiveTailorTab("overview")
    } catch (e) {
      setError(
        e instanceof ApiError
          ? `${e.code}: ${e.message}`
          : e instanceof Error
            ? e.message
            : "Tailoring failed",
      )
    } finally {
      setBusy(false)
    }
  }

  if (!bundle && !lastTailoring) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Step 2 — Tailoring</CardTitle>
          <CardDescription>Complete Step&nbsp;1 with a successful analyze first.</CardDescription>
        </CardHeader>
      </Card>
    )
  }

  /** Stale: prior tailoring retained but Step 1 analysis no longer valid */
  if (!bundle && lastTailoring) {
    return (
      <StaleTailoringCard
        lastTailoring={lastTailoring}
        tabs={tabs}
        activeTailorTab={activeTailorTab}
        baseId={baseId}
        onTab={(t) => setActiveTailorTab(t)}
        editedSummary={editedSummary}
        editedBullets={editedBullets}
        editedCoverLetter={editedCoverLetter}
        onEditedSummary={setEditedSummary}
        onEditedBullets={setEditedBullets}
        onEditedCoverLetter={setEditedCoverLetter}
        coverTabVisible={coverTabVisible}
        copy={copy}
        copyLabel={copyLabel}
        doTheseFirst={doTheseFirst}
      />
    )
  }

  if (!bundle) {
    return null
  }

  if (!unlocked) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Step 2 — Tailoring</CardTitle>
          <CardDescription>Inputs changed — return to Step&nbsp;1 and analyze again.</CardDescription>
        </CardHeader>
      </Card>
    )
  }

  const displayTitle = jobTitle.trim() || bundle.job.title?.trim() || "Target role"
  const displayCompany = jobCompany.trim() || bundle.job.company?.trim() || ""

  return (
    <div className="space-y-4">
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-lg">Tailor for this job</CardTitle>
          <CardDescription className="space-y-1">
            <span className="text-foreground block font-medium">
              {displayTitle}
              {displayCompany ? ` · ${displayCompany}` : ""}
            </span>
            {stepOneVm ? (
              <span className="text-muted-foreground block text-sm">
                Step 1: {stepOneVm.jobVerdictHeadline} ({Math.round(stepOneVm.jobMatchScore)}/100 job match
                {stepOneVm.atsScore != null ? `, ${Math.round(stepOneVm.atsScore)}/100 ATS` : ""}).
              </span>
            ) : null}
            <span className="text-muted-foreground block text-sm">{optimizingLine}</span>
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4 border-t pt-4">
          <div className="flex flex-wrap items-center gap-3">
            <input
              id="cover-toggle"
              type="checkbox"
              checked={includeCoverLetter}
              onChange={(ev) => setCover(ev.target.checked)}
              className="size-4 shrink-0"
            />
            <Label htmlFor="cover-toggle" className="cursor-pointer font-normal leading-snug">
              Include cover letter in this run
            </Label>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <Button type="button" onClick={() => void generate()} disabled={!canGenerate}>
              {busy ? "Generating…" : hasGenerated ? "Regenerate tailored draft" : "Generate tailored draft"}
            </Button>
            {hasGenerated ? (
              <Button type="button" variant="secondary" onClick={() => setActiveTailorTab("overview")}>
                Refine
              </Button>
            ) : null}
            {copyLabel ? <span className="text-muted-foreground text-xs">{copyLabel}</span> : null}
          </div>
          {error ? (
            <div className="border-destructive/50 bg-destructive/5 text-destructive rounded-md border p-3 text-sm">
              {error}
            </div>
          ) : null}
          <p className="text-muted-foreground text-xs">
            Stub provider by default; nothing here updates your saved profile. Review all generated text for
            factual accuracy.
          </p>
        </CardContent>
      </Card>

      {lastTailoring ? (
        <Card>
          <div className="border-b bg-muted/35 p-1">
            <div
              role="tablist"
              aria-orientation="horizontal"
              aria-label="Tailoring workspace"
              className="flex flex-wrap gap-1"
            >
              {tabs.map((tab, i) => {
                const selected = activeTailorTab === tab.id
                return (
                  <button
                    key={tab.id}
                    type="button"
                    role="tab"
                    id={`${baseId}-t2-${tab.id}`}
                    aria-selected={selected}
                    aria-controls={`${baseId}-t2p-${tab.id}`}
                    tabIndex={selected ? 0 : -1}
                    onClick={() => setActiveTailorTab(tab.id)}
                    onKeyDown={(ev) => {
                      if (ev.key !== "ArrowRight" && ev.key !== "ArrowLeft") return
                      ev.preventDefault()
                      const next = tabs[(i + (ev.key === "ArrowRight" ? 1 : -1) + tabs.length) % tabs.length]
                      if (next) setActiveTailorTab(next.id)
                    }}
                    className={cn(
                      "min-h-9 shrink-0 rounded-md px-3 py-2 text-xs font-medium sm:text-sm",
                      selected ? "bg-background text-foreground shadow-sm" : "text-muted-foreground hover:bg-muted/60",
                    )}
                  >
                    {tab.label}
                  </button>
                )
              })}
            </div>
          </div>
          <CardContent className="p-4 sm:p-5">
            {activeTailorTab === "overview" ? (
              <OverviewWorkspace
                review={lastTailoring.result.review}
                doTheseFirst={doTheseFirst}
                stepOneSnapshot={stepOneVm}
                panelId={`${baseId}-t2p-overview`}
                labelledBy={`${baseId}-t2-overview`}
              />
            ) : null}
            {activeTailorTab === "resume" ? (
              <ResumeEditWorkspace
                summary={editedSummary}
                bullets={editedBullets}
                onSummary={setEditedSummary}
                onBullets={setEditedBullets}
                onCopySummary={() => void copy(editedSummary, "Copied summary")}
                onCopyBullets={() => void copy(editedBullets, "Copied bullets")}
                onCopyFull={() =>
                  void copy(fullResumeDraftBlock(editedSummary, editedBullets), "Copied full draft")
                }
                panelId={`${baseId}-t2p-resume`}
                labelledBy={`${baseId}-t2-resume`}
              />
            ) : null}
            {activeTailorTab === "cover_letter" && coverTabVisible ? (
              <CoverLetterWorkspace
                enabled={includeCoverLetter || Boolean(lastTailoring.includeCoverLetterRequested)}
                text={editedCoverLetter}
                onChange={setEditedCoverLetter}
                onCopy={() => void copy(editedCoverLetter, "Copied cover letter")}
                hasGenerated={hasGenerated}
                panelId={`${baseId}-t2p-cover`}
                labelledBy={`${baseId}-t2-cover_letter`}
              />
            ) : null}
          </CardContent>
        </Card>
      ) : (
        <p className="text-muted-foreground text-sm">
          After you generate, review suggestions in Overview and edit the draft in Tailored resume.
        </p>
      )}
    </div>
  )
}

function OverviewWorkspace({
  review,
  doTheseFirst,
  stepOneSnapshot,
  panelId,
  labelledBy,
}: {
  review: { add: string[]; remove: string[]; improve: string[] }
  doTheseFirst: string[]
  stepOneSnapshot: ReturnType<typeof buildStep1ResultViewModel> | null
  panelId: string
  labelledBy: string
}) {
  return (
    <div role="tabpanel" id={panelId} aria-labelledby={labelledBy} className="space-y-6">
      <div className="grid gap-4 sm:grid-cols-3">
        <ReviewCard title="What to add" items={review.add} />
        <ReviewCard title="What to trim" items={review.remove} />
        <ReviewCard title="What to strengthen" items={review.improve} />
      </div>
      {doTheseFirst.length ? (
        <div className="rounded-lg border bg-muted/20 p-4">
          <h4 className="text-sm font-semibold tracking-tight">Do these first</h4>
          <ol className="text-muted-foreground mt-2 list-decimal space-y-1 pl-5 text-sm">
            {doTheseFirst.map((x) => (
              <li key={x}>{x}</li>
            ))}
          </ol>
        </div>
      ) : null}
      <div className="rounded-lg border p-4">
        <h4 className="text-sm font-semibold tracking-tight">Based on Step 1</h4>
        {stepOneSnapshot ? (
          <ul className="text-muted-foreground mt-2 list-disc space-y-1 pl-5 text-sm">
            <li>{stepOneSnapshot.applyGuidanceLine}</li>
            {stepOneSnapshot.topThreeActions.slice(0, 3).map((a) => (
              <li key={a}>{a}</li>
            ))}
          </ul>
        ) : (
          <p className="text-muted-foreground mt-2 text-sm">Match context not loaded.</p>
        )}
      </div>
    </div>
  )
}

function ReviewCard({ title, items }: { title: string; items: string[] }) {
  return (
    <div className="rounded-lg border p-4">
      <h4 className="text-sm font-semibold tracking-tight">{title}</h4>
      <ul className="text-muted-foreground mt-2 list-disc space-y-1 pl-5 text-sm">
        {items.length ? (
          items.map((x) => <li key={`${title}-${x}`}>{x}</li>)
        ) : (
          <li className="list-none pl-0 text-xs">No items in this bucket.</li>
        )}
      </ul>
    </div>
  )
}

function ResumeEditWorkspace({
  summary,
  bullets,
  onSummary,
  onBullets,
  onCopySummary,
  onCopyBullets,
  onCopyFull,
  panelId,
  labelledBy,
}: {
  summary: string
  bullets: string
  onSummary: (v: string) => void
  onBullets: (v: string) => void
  onCopySummary: () => void
  onCopyBullets: () => void
  onCopyFull: () => void
  panelId: string
  labelledBy: string
}) {
  return (
    <div role="tabpanel" id={panelId} aria-labelledby={labelledBy} className="space-y-4">
      <p className="text-amber-900 dark:text-amber-100 bg-amber-500/10 border-amber-500/25 rounded-md border px-3 py-2 text-xs">
        Edit freely, but keep claims truthful — generated text is a starting point only.
      </p>
      <div className="flex flex-wrap gap-2">
        <Button type="button" variant="secondary" size="sm" onClick={onCopySummary}>
          Copy summary
        </Button>
        <Button type="button" variant="secondary" size="sm" onClick={onCopyBullets}>
          Copy bullets
        </Button>
        <Button type="button" variant="secondary" size="sm" onClick={onCopyFull}>
          Copy full tailored block
        </Button>
      </div>
      <div>
        <Label htmlFor="tailor-summary" className="text-sm font-medium">
          Professional summary
        </Label>
        <Textarea
          id="tailor-summary"
          className="mt-1.5 min-h-[120px]"
          value={summary}
          onChange={(e) => onSummary(e.target.value)}
        />
      </div>
      <div>
        <Label htmlFor="tailor-bullets" className="text-sm font-medium">
          Tailored experience bullets
        </Label>
        <p className="text-muted-foreground mt-0.5 text-xs">One bullet per line.</p>
        <Textarea
          id="tailor-bullets"
          className="mt-1.5 min-h-[180px] font-mono text-sm"
          value={bullets}
          onChange={(e) => onBullets(e.target.value)}
        />
      </div>
    </div>
  )
}

function CoverLetterWorkspace({
  enabled,
  text,
  onChange,
  onCopy,
  hasGenerated,
  panelId,
  labelledBy,
}: {
  enabled: boolean
  text: string
  onChange: (v: string) => void
  onCopy: () => void
  hasGenerated: boolean
  panelId: string
  labelledBy: string
}) {
  return (
    <div role="tabpanel" id={panelId} aria-labelledby={labelledBy} className="space-y-4">
      {!enabled ? (
        <div className="rounded-lg border border-dashed p-6 text-center">
          <p className="text-muted-foreground text-sm">Enable cover letter generation in the summary card above.</p>
        </div>
      ) : !hasGenerated ? (
        <div className="rounded-lg border border-dashed p-6 text-center">
          <p className="text-muted-foreground text-sm">
            Run <strong>Generate tailored draft</strong> to create a cover letter you can edit here.
          </p>
        </div>
      ) : (
        <>
          <Button type="button" variant="secondary" size="sm" onClick={onCopy}>
            Copy cover letter
          </Button>
          <Textarea
            className="min-h-[240px] text-sm"
            value={text}
            onChange={(e) => onChange(e.target.value)}
            placeholder="Cover letter draft"
          />
        </>
      )}
    </div>
  )
}

function StaleTailoringCard({
  lastTailoring,
  tabs,
  activeTailorTab,
  baseId,
  onTab,
  editedSummary,
  editedBullets,
  editedCoverLetter,
  onEditedSummary,
  onEditedBullets,
  onEditedCoverLetter,
  coverTabVisible,
  copy,
  copyLabel,
  doTheseFirst,
}: {
  lastTailoring: { result: TailorApiV1; includeCoverLetterRequested: boolean }
  tabs: { id: ActiveTailorTab; label: string }[]
  activeTailorTab: ActiveTailorTab
  baseId: string
  onTab: (t: ActiveTailorTab) => void
  editedSummary: string
  editedBullets: string
  editedCoverLetter: string
  onEditedSummary: (v: string) => void
  onEditedBullets: (v: string) => void
  onEditedCoverLetter: (v: string) => void
  coverTabVisible: boolean
  copy: (t: string, m: string) => Promise<void>
  copyLabel: string | null
  doTheseFirst: string[]
}) {
  return (
    <div className="space-y-4">
      <Card className="border-amber-500/40">
        <CardHeader>
          <CardTitle className="text-lg">Step 2 — Drafts may be outdated</CardTitle>
          <CardDescription>
            Your resume or job description no longer matches the last Step&nbsp;1 analysis. Go back to Step&nbsp;1,
            run <strong>Analyze match</strong>, then return here to regenerate. You can still copy text below if
            useful.
          </CardDescription>
        </CardHeader>
      </Card>
      {copyLabel ? <p className="text-muted-foreground text-xs">{copyLabel}</p> : null}
      <Card>
        <div className="border-b bg-muted/35 p-1">
          <div role="tablist" aria-label="Tailoring workspace" className="flex flex-wrap gap-1">
            {tabs.map((tab, i) => {
              const selected = activeTailorTab === tab.id
              return (
                <button
                  key={tab.id}
                  type="button"
                  role="tab"
                  aria-selected={selected}
                  tabIndex={selected ? 0 : -1}
                  onClick={() => onTab(tab.id)}
                  onKeyDown={(ev) => {
                    if (ev.key !== "ArrowRight" && ev.key !== "ArrowLeft") return
                    ev.preventDefault()
                    const next = tabs[(i + (ev.key === "ArrowRight" ? 1 : -1) + tabs.length) % tabs.length]
                    if (next) onTab(next.id)
                  }}
                  className={cn(
                    "min-h-9 shrink-0 rounded-md px-3 py-2 text-xs font-medium sm:text-sm",
                    selected ? "bg-background text-foreground shadow-sm" : "text-muted-foreground hover:bg-muted/60",
                  )}
                >
                  {tab.label}
                </button>
              )
            })}
          </div>
        </div>
        <CardContent className="p-4 sm:p-5">
          {activeTailorTab === "overview" ? (
            <div className="space-y-4">
              <OverviewWorkspace
                review={lastTailoring.result.review}
                doTheseFirst={doTheseFirst}
                stepOneSnapshot={null}
                panelId={`${baseId}-stale-overview`}
                labelledBy=""
              />
            </div>
          ) : null}
          {activeTailorTab === "resume" ? (
            <ResumeEditWorkspace
              summary={editedSummary}
              bullets={editedBullets}
              onSummary={onEditedSummary}
              onBullets={onEditedBullets}
              onCopySummary={() => void copy(editedSummary, "Copied summary")}
              onCopyBullets={() => void copy(editedBullets, "Copied bullets")}
              onCopyFull={() => void copy(fullResumeDraftBlock(editedSummary, editedBullets), "Copied full draft")}
              panelId={`${baseId}-stale-resume`}
              labelledBy=""
            />
          ) : null}
          {activeTailorTab === "cover_letter" && coverTabVisible ? (
            <CoverLetterWorkspace
              enabled={lastTailoring.includeCoverLetterRequested}
              text={editedCoverLetter}
              onChange={onEditedCoverLetter}
              onCopy={() => void copy(editedCoverLetter, "Copied cover letter")}
              hasGenerated
              panelId={`${baseId}-stale-cover`}
              labelledBy=""
            />
          ) : null}
        </CardContent>
      </Card>
    </div>
  )
}
