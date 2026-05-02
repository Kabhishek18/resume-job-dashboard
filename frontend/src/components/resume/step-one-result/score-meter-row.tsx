"use client"

import { cn } from "@/lib/utils"

type Props = {
  label: string
  value: number
  helperCopy: string
}

export function ScoreMeterRow({ label, value, helperCopy }: Props) {
  const rounded = Math.round(value)
  const clamped = Math.max(0, Math.min(100, rounded))

  return (
    <div className="space-y-2">
      <div className="flex items-baseline justify-between gap-2">
        <span className="text-sm font-medium">{label}</span>
        <span className="text-muted-foreground tabular-nums text-sm">{clamped}</span>
      </div>
      <div
        className={cn(
          "bg-muted relative h-2 w-full overflow-hidden rounded-full border border-transparent",
          "focus-within:ring-ring/40",
        )}
        role="progressbar"
        aria-valuenow={clamped}
        aria-valuemin={0}
        aria-valuemax={100}
        aria-label={`${label} score`}
      >
        <div
          className="bg-primary h-full rounded-full transition-[width] duration-300"
          style={{ width: `${clamped}%` }}
        />
      </div>
      <p className="text-muted-foreground text-xs leading-relaxed">{helperCopy}</p>
    </div>
  )
}
