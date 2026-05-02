import type { ReactNode } from "react"

export function DashboardShell({ children }: { children: ReactNode }) {
  return <div className="mx-auto w-full max-w-5xl flex-1 space-y-6 px-4 py-8">{children}</div>
}
