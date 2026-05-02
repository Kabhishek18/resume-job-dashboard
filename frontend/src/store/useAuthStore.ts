import { create } from "zustand"
import { persist } from "zustand/middleware"

import type { AuthUser } from "@/types/auth"

type LogoutOptions = { sessionExpired?: boolean }

type AuthState = {
  token: string | null
  user: AuthUser | null
  /** When true, redirect to login with ?expired=1 (cleared after AuthGuard consumes it). Not persisted. */
  sessionExpiredRedirect: boolean
  setAuth: (token: string, user: AuthUser) => void
  logout: (opts?: LogoutOptions) => void
  clearSessionExpiredRedirect: () => void
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      token: null,
      user: null,
      sessionExpiredRedirect: false,
      setAuth: (token, user) => set({ token, user, sessionExpiredRedirect: false }),
      logout: (opts) =>
        set({
          token: null,
          user: null,
          sessionExpiredRedirect: Boolean(opts?.sessionExpired),
        }),
      clearSessionExpiredRedirect: () => set({ sessionExpiredRedirect: false }),
    }),
    {
      name: "auth-storage",
      partialize: (s) => ({ token: s.token, user: s.user }),
      skipHydration: true,
    },
  ),
)
