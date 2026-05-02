"use client"

import Link from "next/link"
import { useRouter } from "next/navigation"
import { useEffect, useState } from "react"

import { DashboardShell } from "@/components/dashboard/dashboard-shell"
import { buttonVariants } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { cn } from "@/lib/utils"
import { readLastVisitedPath } from "@/lib/last-visited-path"
import { useAuthStore } from "@/store/useAuthStore"

export default function MarketingHomePage() {
  const router = useRouter()
  const token = useAuthStore((s) => s.token)
  const [hydrated, setHydrated] = useState(false)

  useEffect(() => {
    const unsub = useAuthStore.persist.onFinishHydration(() => setHydrated(true))
    void useAuthStore.persist.rehydrate()
    return unsub
  }, [])

  useEffect(() => {
    if (!hydrated || !token) return
    const dest = readLastVisitedPath() ?? "/dashboard"
    router.replace(dest)
  }, [hydrated, token, router])

  if (hydrated && token) {
    return (
      <DashboardShell>
        <p className="text-muted-foreground text-sm">Opening your workspace…</p>
      </DashboardShell>
    )
  }

  return (
    <DashboardShell>
      <div className="space-y-2">
        <h1 className="text-2xl font-semibold tracking-tight">Welcome</h1>
        <p className="text-muted-foreground text-sm">
          Sign in to open your workspace, or create an account to get started.
        </p>
      </div>
      <div className="grid gap-4 sm:grid-cols-3">
        <Card className="h-full">
          <CardHeader>
            <CardTitle className="text-base">Dashboard</CardTitle>
            <CardDescription>Overview of tracked applications and recent activity.</CardDescription>
          </CardHeader>
          <CardContent>
            <Link
              href="/login?next=/dashboard"
              className={cn(buttonVariants({ variant: "secondary", size: "sm" }), "w-full sm:w-auto")}
            >
              Sign in for dashboard
            </Link>
          </CardContent>
        </Card>
        <Card className="h-full">
          <CardHeader>
            <CardTitle className="text-base">Jobs</CardTitle>
            <CardDescription>Search boards and track applications.</CardDescription>
          </CardHeader>
          <CardContent>
            <Link
              href="/login?next=/jobs"
              className={cn(buttonVariants({ variant: "secondary", size: "sm" }), "w-full sm:w-auto")}
            >
              Sign in for jobs
            </Link>
          </CardContent>
        </Card>
        <Card className="h-full">
          <CardHeader>
            <CardTitle className="text-base">Resume</CardTitle>
            <CardDescription>Match and tailor your resume to roles.</CardDescription>
          </CardHeader>
          <CardContent>
            <Link
              href="/login?next=/resume"
              className={cn(buttonVariants({ variant: "secondary", size: "sm" }), "w-full sm:w-auto")}
            >
              Sign in for resume
            </Link>
          </CardContent>
        </Card>
      </div>
    </DashboardShell>
  )
}
