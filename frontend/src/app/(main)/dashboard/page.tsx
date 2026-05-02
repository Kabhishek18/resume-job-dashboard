import { DashboardShell } from "@/components/dashboard/dashboard-shell"

import { DashboardHomeContent } from "./dashboard-home"

export default function DashboardPage() {
  return (
    <DashboardShell>
      <div className="space-y-1">
        <h1 className="text-2xl font-semibold tracking-tight">Dashboard</h1>
        <p className="text-muted-foreground text-sm">Board activity, recent jobs, and quick links.</p>
      </div>
      <div className="space-y-6">
        <DashboardHomeContent />
      </div>
    </DashboardShell>
  )
}
