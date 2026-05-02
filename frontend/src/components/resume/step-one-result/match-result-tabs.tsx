"use client"

import type { ReactNode } from "react"
import { useId } from "react"

import { cn } from "@/lib/utils"
import type { Step1ResultViewModel, Step1TabId } from "@/lib/match-verdict-ui"

import { ScoreMeterRow } from "./score-meter-row"

const TAB_DEFS: { id: Step1TabId; label: string }[] = [
  { id: "overview", label: "Overview" },
  { id: "gaps", label: "Gaps" },
  { id: "improve", label: "Improve" },
  { id: "breakdown", label: "Score breakdown" },
]

type Props = {
  vm: Step1ResultViewModel
  tab: Step1TabId
  onTabChange: (t: Step1TabId) => void
}

export function MatchResultTabs({ vm, tab, onTabChange }: Props) {
  const baseId = useId().replace(/:/g, "")

  return (
    <div className="rounded-xl border bg-card shadow-sm">
      <div className="bg-muted/35 border-b p-1">
        <div
          role="tablist"
          aria-orientation="horizontal"
          aria-label="Match detail sections"
          className="flex flex-wrap gap-1"
        >
          {TAB_DEFS.map((t, i) => {
            const selected = tab === t.id
            return (
              <button
                key={t.id}
                type="button"
                role="tab"
                id={`${baseId}-tab-${t.id}`}
                aria-selected={selected}
                aria-controls={`${baseId}-panel-${t.id}`}
                tabIndex={selected ? 0 : -1}
                onClick={() => onTabChange(t.id)}
                onKeyDown={(ev) => {
                  if (ev.key !== "ArrowRight" && ev.key !== "ArrowLeft") return
                  ev.preventDefault()
                  const next = TAB_DEFS[(i + (ev.key === "ArrowRight" ? 1 : -1) + TAB_DEFS.length) % TAB_DEFS.length].id
                  onTabChange(next)
                }}
                className={cn(
                  "min-h-9 shrink-0 rounded-md px-3 py-2 text-xs font-medium sm:text-sm",
                  selected ? "bg-background text-foreground shadow-sm" : "text-muted-foreground hover:bg-muted/60",
                )}
              >
                {t.label}
              </button>
            )
          })}
        </div>
      </div>

      <div className="p-4 sm:p-5">
        {tab === "overview" ? (
          <div role="tabpanel" id={`${baseId}-panel-overview`} aria-labelledby={`${baseId}-tab-overview`}>
            <OverviewPanel vm={vm} />
          </div>
        ) : null}

        {tab === "gaps" ? (
          <div role="tabpanel" id={`${baseId}-panel-gaps`} aria-labelledby={`${baseId}-tab-gaps`}>
            <GapsPanel vm={vm} />
          </div>
        ) : null}

        {tab === "improve" ? (
          <div role="tabpanel" id={`${baseId}-panel-improve`} aria-labelledby={`${baseId}-tab-improve`}>
            <ImprovePanel vm={vm} />
          </div>
        ) : null}

        {tab === "breakdown" ? (
          <div role="tabpanel" id={`${baseId}-panel-breakdown`} aria-labelledby={`${baseId}-tab-breakdown`}>
            <BreakdownPanel vm={vm} />
          </div>
        ) : null}
      </div>
    </div>
  )
}

function PanelHeading({ children }: { children: ReactNode }) {
  return <h4 className="mb-4 text-sm font-semibold tracking-tight">{children}</h4>
}

function OverviewPanel({ vm }: { vm: Step1ResultViewModel }) {
  return (
    <div className="space-y-6">
      <div>
        <PanelHeading>Job match summary</PanelHeading>
        <p className="text-muted-foreground text-sm leading-relaxed">{vm.jobMatchSummarySentence}</p>
      </div>

      <div>
        <PanelHeading>ATS summary</PanelHeading>
        <p className="text-muted-foreground text-sm leading-relaxed">{vm.atsSummarySentence}</p>
        {vm.atsScore != null ? (
          <div className="mt-3 grid gap-4 sm:grid-cols-2">
            <div>
              <p className="text-muted-foreground mb-2 text-xs font-medium">What helps</p>
              <ul className="space-y-1 text-sm">
                {vm.atsHelpSignals.length ? (
                  vm.atsHelpSignals.map((s) => <li key={s}>{s}</li>)
                ) : (
                  <li className="text-muted-foreground text-xs">No standout positive signals extracted.</li>
                )}
              </ul>
            </div>
            <div>
              <p className="text-muted-foreground mb-2 text-xs font-medium">What hurts</p>
              <ul className="space-y-1 text-sm">
                {vm.atsHurtSignals.length ? (
                  vm.atsHurtSignals.map((s) => <li key={s}>{s}</li>)
                ) : (
                  <li className="text-muted-foreground text-xs">No ATS-style penalties flagged.</li>
                )}
              </ul>
            </div>
          </div>
        ) : null}
      </div>

      <div>
        <PanelHeading>Top strengths</PanelHeading>
        {vm.strengths.length ? (
          <ul className="list-disc space-y-1 pl-5 text-sm">
            {vm.strengths.map((s) => (
              <li key={s}>{s}</li>
            ))}
          </ul>
        ) : (
          <p className="text-muted-foreground text-sm">Strengths summary will deepen as overlap improves.</p>
        )}
      </div>

      <div>
        <PanelHeading>Key blockers</PanelHeading>
        {vm.overviewBlockers.length ? (
          <ul className="list-disc space-y-1 pl-5 text-sm">
            {vm.overviewBlockers.map((s) => (
              <li key={s}>{s}</li>
            ))}
          </ul>
        ) : (
          <p className="text-muted-foreground text-sm">Major blockers are minor—prioritize Next actions instead.</p>
        )}
      </div>

      {vm.whySentence ? (
        <div className="bg-muted/30 rounded-lg border p-3">
          <p className="text-muted-foreground mb-1 text-xs font-medium">Why this score happened</p>
          <p className="text-sm leading-relaxed">{vm.whySentence}</p>
        </div>
      ) : null}
    </div>
  )
}

function GapsPanel({ vm }: { vm: Step1ResultViewModel }) {
  return (
    <div className="space-y-6">
      <div>
        <PanelHeading>Gaps versus the posting</PanelHeading>
        {vm.gapRows.length ? (
          <div className="flex flex-wrap gap-2">
            {vm.gapRows.map(({ skill, priority }) => (
              <span
                key={skill}
                className={cn(
                  "inline-flex items-center rounded-full border px-3 py-1 text-xs font-medium",
                  priority === "must"
                    ? "border-destructive/40 bg-destructive/10 text-destructive"
                    : "border-muted bg-muted/40 text-muted-foreground",
                )}
              >
                <span className="sr-only">{priority === "must" ? "Must address" : "Optional"}:</span>
                <span aria-hidden>{priority === "must" ? "★ " : "○ "}</span>
                {skill}
              </span>
            ))}
          </div>
        ) : (
          <p className="text-muted-foreground text-sm">
            No major hard-skill gaps flagged—stay honest if wording still needs tuning.
          </p>
        )}
        <p className="text-muted-foreground mt-2 text-xs">★ Must address · ○ Optional refinement</p>
      </div>

      {vm.semanticMatches.length ? (
        <div>
          <PanelHeading>Near matches (meaning, not wording)</PanelHeading>
          <ul className="list-disc space-y-1 pl-5 text-sm">
            {vm.semanticMatches.slice(0, 20).map((s) => (
              <li key={s}>{s}</li>
            ))}
          </ul>
        </div>
      ) : null}
    </div>
  )
}

function ImprovePanel({ vm }: { vm: Step1ResultViewModel }) {
  const b = vm.improveBuckets
  const groups: { heading: string; items: string[] }[] = [
    { heading: "Resume wording", items: b.resumeWording },
    { heading: "Missing skills / evidence", items: b.missingSkills },
    { heading: "Experience & title alignment", items: b.experienceTitle },
  ]
  const hasGrouped = groups.some((g) => g.items.length > 0)

  return (
    <div className="space-y-6">
      <PanelHeading>Prioritized checklist</PanelHeading>
      <p className="text-muted-foreground -mt-3 mb-2 text-xs">
        Sorted from your scorer output—tick off what you genuinely can support.
      </p>
      {hasGrouped ? (
        <div className="space-y-5">
          {groups.map(({ heading, items }) =>
            items.length ? (
              <div key={heading}>
                <p className="text-muted-foreground mb-2 text-xs font-semibold">{heading}</p>
                <ol className="list-decimal space-y-2 pl-5 text-sm">
                  {items.slice(0, 12).map((line) => (
                    <li key={line}>{line}</li>
                  ))}
                </ol>
              </div>
            ) : null,
          )}
        </div>
      ) : null}
      {!hasGrouped && vm.improvementOrdered.length ? (
        <ol className="list-decimal space-y-2 pl-5 text-sm">
          {vm.improvementOrdered.slice(0, 16).map((line) => (
            <li key={line}>{line}</li>
          ))}
        </ol>
      ) : null}
      {!hasGrouped && !vm.improvementOrdered.length ? (
        <p className="text-muted-foreground text-sm">No improvement lines—nothing to reorder yet.</p>
      ) : null}
    </div>
  )
}

function BreakdownPanel({ vm }: { vm: Step1ResultViewModel }) {
  return (
    <div className="space-y-6">
      <PanelHeading>Component scores</PanelHeading>
      <div className="flex flex-col gap-6">
        {vm.meterRows.map((row) => (
          <ScoreMeterRow key={row.label} label={row.label} value={row.value} helperCopy={row.helperCopy} />
        ))}
      </div>
    </div>
  )
}
