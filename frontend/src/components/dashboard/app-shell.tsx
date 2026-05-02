"use client"

import { usePathname } from "next/navigation"
import type { ReactNode } from "react"
import { useEffect } from "react"

import { AppSidebar } from "@/components/dashboard/app-sidebar"
import { SiteHeader } from "@/components/dashboard/site-header"
import { SidebarInset, SidebarProvider } from "@/components/ui/sidebar"
import { TooltipProvider } from "@/components/ui/tooltip"
import { writeLastVisitedPath } from "@/lib/last-visited-path"

export function AppShell({ children }: { children: ReactNode }) {
  const pathname = usePathname()

  useEffect(() => {
    if (!pathname) return
    writeLastVisitedPath(pathname)
  }, [pathname])

  return (
    <TooltipProvider delay={0}>
      <SidebarProvider>
        <AppSidebar />
        <SidebarInset>
          <SiteHeader />
          <div className="flex flex-1 flex-col">{children}</div>
        </SidebarInset>
      </SidebarProvider>
    </TooltipProvider>
  )
}
