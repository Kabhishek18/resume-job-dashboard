"use client"

import type { ReactNode } from "react"

import { AuthGuard } from "@/components/auth/auth-guard"
import { AppShell } from "@/components/dashboard/app-shell"

export default function MainLayout({ children }: { children: ReactNode }) {
  return (
    <AuthGuard>
      <AppShell>{children}</AppShell>
    </AuthGuard>
  )
}
