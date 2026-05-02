import { DashboardShell } from "@/components/dashboard/dashboard-shell"
import { ResumeWizard } from "@/components/resume/resume-wizard"

export default function ResumePage() {
  return (
    <DashboardShell>
      <div className="space-y-2">
        <h1 className="text-2xl font-semibold tracking-tight">Resume</h1>
        <p className="text-muted-foreground text-sm">
          ATS-style relevance scoring (Step&nbsp;1) and tailoring with an LLM-ready contract (stub provider by default).
        </p>
      </div>
      <div className="mt-8">
        <ResumeWizard />
      </div>
    </DashboardShell>
  )
}
