"use client"

import { verdictHueClasses } from "@/lib/match-verdict"
import type { Step1ResultViewModel } from "@/lib/match-verdict-ui"
import { cn } from "@/lib/utils"
import type { MatchScoreBand } from "@/types/match"

type Props = {
  vm: Step1ResultViewModel
}

function ScoreChip({
  title,
  score,
  band,
  supporting,
}: {
  title: string
  score: number
  band: MatchScoreBand
  supporting?: string
}) {
  const hue = verdictHueClasses(band)
  return (
    <div className={cn("rounded-xl border p-4", hue.card)}>
      <div className="flex items-start gap-3">
        <span
          className={cn(
            "inline-flex shrink-0 items-center rounded-full border px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide",
            hue.badge,
          )}
          aria-hidden
        >
          {band === "weak" ? "Low" : band === "needs_work" ? "Mid" : "High"}
        </span>
        <div className="min-w-0 flex-1 space-y-1">
          <p className="text-sm font-semibold">{title}</p>
          {supporting ? <p className="text-muted-foreground text-xs leading-snug">{supporting}</p> : null}
          <p className="tabular-nums text-2xl font-semibold">{Math.round(score)}</p>
          <p className="text-muted-foreground text-xs font-medium uppercase tracking-wide">out of 100</p>
        </div>
      </div>
    </div>
  )
}

export function MatchResultSummaryStrip({ vm }: Props) {
  const jobHue = verdictHueClasses(vm.jobBand)

  return (
    <div className="grid gap-4 lg:grid-cols-[minmax(0,1.2fr)_minmax(0,0.95fr)]">
      <section
        className={cn("rounded-xl border p-5 lg:p-6", jobHue.card)}
        aria-labelledby="step1-job-match-heading"
      >
        <div className="flex flex-wrap items-start gap-3">
          <span
            className={cn(
              "inline-flex shrink-0 items-center rounded-full border px-2.5 py-0.5 text-xs font-semibold",
              jobHue.badge,
            )}
            aria-hidden
          >
            Primary
          </span>
          <div className="min-w-0 flex-1 space-y-3">
            <div>
              <h3 id="step1-job-match-heading" className="text-lg font-semibold tracking-tight">
                Job match
              </h3>
              <p className="text-muted-foreground mt-0.5 text-2xl font-semibold tabular-nums lg:text-3xl">
                {Math.round(vm.jobMatchScore)} <span className="text-muted-foreground text-lg font-normal">/ 100</span>
              </p>
              <p className="mt-2 text-lg font-semibold">{vm.jobVerdictHeadline}</p>
              <p className="text-muted-foreground mt-2 text-sm leading-relaxed">{vm.applyGuidanceLine}</p>
            </div>
          </div>
        </div>
      </section>

      <aside className="flex flex-col gap-3">
        {vm.atsScore != null && vm.atsBand != null ? (
          <ScoreChip
            title="ATS Compatibility"
            score={vm.atsScore}
            band={vm.atsBand}
            supporting="How parseable your plain-text resume is for typical ATS-style pipelines—not layout."
          />
        ) : (
          <div className="bg-muted/30 rounded-xl border p-4">
            <p className="text-sm font-semibold">ATS Compatibility</p>
            <p className="text-muted-foreground mt-1 text-xs leading-relaxed">{vm.atsSummarySentence}</p>
          </div>
        )}
        <p className="text-muted-foreground text-xs font-medium" aria-label="Match API version">
          {vm.apiLabel}
        </p>
      </aside>
    </div>
  )
}
