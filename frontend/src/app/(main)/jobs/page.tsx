import { DashboardShell } from "@/components/dashboard/dashboard-shell"
import { JobsDashboard } from "@/components/jobs/jobs-dashboard"
import { JobsShell } from "@/components/jobs/jobs-shell"

export default function JobsPage() {
  return (
    <DashboardShell>
      <div className="space-y-2">
        <h1 className="text-2xl font-semibold tracking-tight">Jobs</h1>
        <p className="text-muted-foreground text-sm">
          Save search profiles, run multi-portal collectors, export CSV, and track applications on your board.
        </p>
      </div>
      <JobsShell>
        <JobsDashboard />
      </JobsShell>
    </DashboardShell>
  )
}
