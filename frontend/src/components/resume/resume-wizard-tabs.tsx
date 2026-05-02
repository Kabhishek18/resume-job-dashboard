"use client"

import type { JSX } from "react"

import { Button } from "@/components/ui/button"
import { cn } from "@/lib/utils"

type Props = {
  currentStep: 1 | 2
  canAccessStep2: boolean
  onSelectStep: (step: 1 | 2) => void
}

const STEPS = [
  { id: 1 as const, ariaLabel: "Step 1. Relevance Score", label: "Step 1. Relevance Score" },
  { id: 2 as const, ariaLabel: "Step 2. Tailoring", label: "Step 2. Tailoring" },
]

export function ResumeWizardTabs({ currentStep, canAccessStep2, onSelectStep }: Props): JSX.Element {
  return (
    <div className="w-full space-y-2">
      <div
        role="tablist"
        aria-label="Resume workflow steps"
        aria-orientation="horizontal"
        className="bg-muted/40 flex w-full flex-wrap gap-1 rounded-lg border p-1"
      >
        {STEPS.map((t) => {
          const selected = currentStep === t.id
          const disabled = t.id === 2 && !canAccessStep2
          return (
            <Button
              key={t.id}
              type="button"
              variant={selected ? "default" : "ghost"}
              size="sm"
              role="tab"
              aria-selected={selected}
              aria-disabled={disabled}
              disabled={disabled}
              className={cn(
                "min-h-9 flex-1 px-3 text-xs sm:text-sm",
                selected && "shadow-sm",
                disabled && "cursor-not-allowed opacity-50",
              )}
              id={`wizard-tab-${t.id}`}
              tabIndex={selected ? 0 : -1}
              aria-label={t.ariaLabel}
              aria-describedby={t.id === 2 && !canAccessStep2 ? "wizard-step2-help" : undefined}
              onClick={() => {
                if (t.id === 2 && !canAccessStep2) return
                onSelectStep(t.id)
              }}
            >
              <span className="font-medium">{t.label}</span>
            </Button>
          )
        })}
      </div>
      {!canAccessStep2 ? (
        <p id="wizard-step2-help" className="text-muted-foreground text-xs">
          Complete relevance scoring first to open tailoring.
        </p>
      ) : null}
    </div>
  )
}
