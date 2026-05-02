"use client"

import type { ReactNode } from "react"
import { useEffect, useState } from "react"
import { usePathname, useRouter } from "next/navigation"

import { useAuthStore } from "@/store/useAuthStore"

export function AuthGuard({ children }: { children: ReactNode }) {
  const router = useRouter()
  const pathname = usePathname()
  const token = useAuthStore((s) => s.token)
  const [hydrated, setHydrated] = useState(false)

  useEffect(() => {
    const unsub = useAuthStore.persist.onFinishHydration(() => setHydrated(true))
    void useAuthStore.persist.rehydrate()
    return unsub
  }, [])

  useEffect(() => {
    if (!hydrated) return
    if (!token) {
      const sp = new URLSearchParams()
      if (pathname) sp.set("next", pathname)
      if (useAuthStore.getState().sessionExpiredRedirect) {
        sp.set("expired", "1")
        useAuthStore.getState().clearSessionExpiredRedirect()
      }
      const suffix = sp.toString() ? `?${sp.toString()}` : ""
      router.replace(`/login${suffix}`)
    }
  }, [hydrated, token, router, pathname])

  if (!hydrated || !token) {
    return (
      <div className="flex min-h-svh flex-col items-center justify-center gap-2">
        <p className="text-muted-foreground text-sm">Loading…</p>
      </div>
    )
  }

  return <>{children}</>
}
