"use client"

import Link from "next/link"
import { useEffect, useState } from "react"

import { buttonVariants } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { ApiError } from "@/lib/api"
import { cn } from "@/lib/utils"
import { getDashboardSummary } from "@/services/dashboard.service"
import { useAuthStore } from "@/store/useAuthStore"
import type { DashboardSummaryApi } from "@/types/dashboard"

function DashboardHomeInner() {
  const token = useAuthStore((s) => s.token)
  const [data, setData] = useState<DashboardSummaryApi | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let cancelled = false
    ;(async () => {
      if (!token) return
      try {
        const d = await getDashboardSummary(token)
        if (!cancelled) setData(d)
      } catch (e) {
        if (!cancelled) setError(e instanceof ApiError ? e.message : "Could not load dashboard.")
      }
    })()
    return () => {
      cancelled = true
    }
  }, [token])

  if (error) {
    return <p className="text-destructive text-sm">{error}</p>
  }

  if (!data) {
    return <p className="text-muted-foreground text-sm">Loading overview…</p>
  }

  const statusEntries = Object.entries(data.board_counts_by_status).sort((a, b) => b[1] - a[1])
  const recent = data.recent_board_entries
  const run = data.most_recent_run

  return (
    <>
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <Card className="border-primary/20 shadow-sm">
          <CardHeader className="pb-2">
            <CardDescription>Tracked jobs</CardDescription>
            <CardTitle className="text-3xl tabular-nums">{data.total_tracked_jobs}</CardTitle>
          </CardHeader>
          <CardContent className="text-muted-foreground text-xs">Roles on your board</CardContent>
        </Card>
        {statusEntries.length === 0 ? (
          <Card className="sm:col-span-3">
            <CardHeader className="pb-2">
              <CardDescription>By status</CardDescription>
              <CardTitle className="text-lg font-medium">No board activity yet</CardTitle>
            </CardHeader>
            <CardContent className="text-muted-foreground text-sm">
              Run a search on the Jobs page and use <strong>Track</strong> to add roles here.
            </CardContent>
          </Card>
        ) : (
          statusEntries.map(([label, count]) => (
            <Card key={label} className="shadow-sm">
              <CardHeader className="pb-2">
                <CardDescription className="capitalize">{label}</CardDescription>
                <CardTitle className="text-3xl tabular-nums">{count}</CardTitle>
              </CardHeader>
              <CardContent className="text-muted-foreground text-xs">Board entries</CardContent>
            </Card>
          ))
        )}
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        <Card className="shadow-sm">
          <CardHeader>
            <CardTitle className="text-base">Recent tracked jobs</CardTitle>
            <CardDescription>Latest updates on your board</CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            {recent.length === 0 ? (
              <div className="text-muted-foreground rounded-lg border border-dashed p-6 text-center text-sm">
                <p className="text-foreground font-medium">Nothing here yet</p>
                <p className="mt-1">
                  <Link href="/jobs" className="text-primary underline-offset-4 hover:underline">
                    Open Jobs
                  </Link>{" "}
                  to search and track.
                </p>
              </div>
            ) : (
              <ul className="divide-border divide-y rounded-lg border">
                {recent.map((e) => (
                  <li key={e.id} className="flex flex-col gap-1 p-3 sm:flex-row sm:items-center sm:justify-between">
                    <div>
                      <p className="font-medium">
                        {e.apply_url ? (
                          <a className="text-primary underline-offset-4 hover:underline" href={e.apply_url} target="_blank" rel="noreferrer">
                            {e.title}
                          </a>
                        ) : (
                          e.title
                        )}
                      </p>
                      <p className="text-muted-foreground text-xs">
                        {e.company} · <span className="capitalize">{e.portal}</span> ·{" "}
                        <span className="capitalize">{e.status}</span>
                      </p>
                    </div>
                    <Link
                      href="/jobs"
                      className={cn(buttonVariants({ variant: "outline", size: "sm" }), "shrink-0 self-start sm:self-center")}
                    >
                      View in Jobs
                    </Link>
                  </li>
                ))}
              </ul>
            )}
          </CardContent>
        </Card>

        <Card className="shadow-sm">
          <CardHeader>
            <CardTitle className="text-base">Latest job search run</CardTitle>
            <CardDescription>Most recent search execution</CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            {!run ? (
              <div className="text-muted-foreground rounded-lg border border-dashed p-6 text-center text-sm">
                No runs yet. Start from{" "}
                <Link href="/jobs" className="text-primary underline-offset-4 hover:underline">
                  Jobs
                </Link>
                .
              </div>
            ) : (
              <div className="space-y-2 rounded-lg border p-4 text-sm">
                <p className="font-medium capitalize">
                  Status: <span className="text-foreground">{run.status}</span>
                </p>
                <p className="text-muted-foreground text-xs">Run #{run.id} · Profile #{run.search_profile_id}</p>
              </div>
            )}
            <div className="flex flex-wrap gap-2 pt-2">
              <Link href="/jobs" className={cn(buttonVariants({ variant: "default", size: "default" }))}>
                Jobs workspace
              </Link>
              <Link href="/resume" className={cn(buttonVariants({ variant: "secondary", size: "default" }))}>
                Resume wizard
              </Link>
            </div>
          </CardContent>
        </Card>
      </div>
    </>
  )
}

export function DashboardHomeContent() {
  return <DashboardHomeInner />
}
