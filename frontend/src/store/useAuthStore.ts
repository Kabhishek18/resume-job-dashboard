import { create } from "zustand"
import { persist } from "zustand/middleware"

import type { AuthUser } from "@/types/auth"
import {
  clearWizardPersistBlobForUser,
  resetWizardMemoryOnly,
} from "@/store/resume-wizard-persistence"

type LogoutOptions = { sessionExpired?: boolean }

type AuthState = {
  token: string | null
  user: AuthUser | null
  /** When true, redirect to login with ?expired=1 (cleared after AuthGuard consumes it). Not persisted. */
  sessionExpiredRedirect: boolean
  setAuth: (token: string, user: AuthUser) => void
  patchUser: (partial: Partial<Pick<AuthUser, "name" | "email">>) => void
  logout: (opts?: LogoutOptions) => void
  clearSessionExpiredRedirect: () => void
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      token: null,
      user: null,
      sessionExpiredRedirect: false,
      setAuth: (token, user) =>
        set((s) => {
          const prev = s.user
          if (prev != null && prev.id !== user.id) {
            clearWizardPersistBlobForUser(prev.id)
          }
          return { token, user, sessionExpiredRedirect: false }
        }),
      patchUser: (partial) =>
        set((s) =>
          s.user ? { user: { ...s.user, ...partial } } : {},
        ),
      logout: (opts) => {
        const user = useAuthStore.getState().user
        if (user?.id != null) {
          clearWizardPersistBlobForUser(user.id)
        } else {
          resetWizardMemoryOnly()
        }
        set({
          token: null,
          user: null,
          sessionExpiredRedirect: Boolean(opts?.sessionExpired),
        })
      },
      clearSessionExpiredRedirect: () => set({ sessionExpiredRedirect: false }),
    }),
    {
      name: "auth-storage",
      partialize: (s) => ({ token: s.token, user: s.user }),
      skipHydration: true,
    },
  ),
)
