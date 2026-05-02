"use client"

import { LogOut, Settings, User } from "lucide-react"
import { useRouter } from "next/navigation"

import { Button } from "@/components/ui/button"
import { SidebarTrigger } from "@/components/ui/sidebar"
import { useAuthStore } from "@/store/useAuthStore"

export function SiteHeader() {
  const router = useRouter()
  const user = useAuthStore((s) => s.user)
  const logout = useAuthStore((s) => s.logout)

  function handleLogout() {
    logout()
    router.replace("/login")
  }

  return (
    <header className="bg-background flex h-14 shrink-0 items-center gap-2 border-b border-border px-4">
      <SidebarTrigger />
      <div className="flex flex-1 items-center justify-end gap-1">
        <Button variant="ghost" size="sm" type="button" className="text-muted-foreground gap-2">
          <User className="size-4 shrink-0" />
          <span className="hidden sm:inline">{user?.name ?? "Profile"}</span>
        </Button>
        <Button variant="ghost" size="icon-sm" type="button" aria-label="Settings">
          <Settings className="size-4" />
        </Button>
        <Button
          variant="ghost"
          size="icon-sm"
          type="button"
          aria-label="Sign out"
          onClick={handleLogout}
        >
          <LogOut className="size-4" />
        </Button>
      </div>
    </header>
  )
}
