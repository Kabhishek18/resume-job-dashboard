"use client"

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react"

export const THEME_STORAGE_KEY = "theme-mode"

export type ThemeMode = "light" | "dark" | "system"

type ThemeContextValue = {
  mode: ThemeMode
  /** Effective theme for UI (after resolving `system`). */
  resolved: "light" | "dark"
  setMode: (m: ThemeMode) => void
}

const ThemeContext = createContext<ThemeContextValue | null>(null)

function readStoredMode(): ThemeMode {
  if (typeof window === "undefined") return "system"
  try {
    const raw = localStorage.getItem(THEME_STORAGE_KEY)
    if (raw === "light" || raw === "dark" || raw === "system") return raw
  } catch {
    /* ignore */
  }
  return "system"
}

function systemPrefersDark(): boolean {
  if (typeof window === "undefined") return false
  return window.matchMedia("(prefers-color-scheme: dark)").matches
}

function applyResolved(resolved: "light" | "dark") {
  document.documentElement.classList.toggle("dark", resolved === "dark")
}

export function ThemeProvider({ children }: { children: ReactNode }) {
  const [mode, setModeState] = useState<ThemeMode>("system")
  const [mounted, setMounted] = useState(false)

  useEffect(() => {
    // Hydrate preference from storage once on mount (no SSR storage).
    // eslint-disable-next-line react-hooks/set-state-in-effect -- intentional post-mount sync
    setModeState(readStoredMode())
    setMounted(true)
  }, [])

  const resolved: "light" | "dark" = useMemo(() => {
    if (mode === "light") return "light"
    if (mode === "dark") return "dark"
    return systemPrefersDark() ? "dark" : "light"
  }, [mode])

  useEffect(() => {
    if (!mounted) return
    applyResolved(resolved)
  }, [mounted, resolved])

  useEffect(() => {
    if (!mounted || mode !== "system") return
    const mq = window.matchMedia("(prefers-color-scheme: dark)")
    const onChange = () => applyResolved(systemPrefersDark() ? "dark" : "light")
    mq.addEventListener("change", onChange)
    return () => mq.removeEventListener("change", onChange)
  }, [mounted, mode])

  const setMode = useCallback((next: ThemeMode) => {
    setModeState(next)
    try {
      localStorage.setItem(THEME_STORAGE_KEY, next)
    } catch {
      /* ignore */
    }
    if (next === "light") applyResolved("light")
    else if (next === "dark") applyResolved("dark")
    else applyResolved(systemPrefersDark() ? "dark" : "light")
  }, [])

  const value = useMemo(
    () => ({
      mode,
      resolved,
      setMode,
    }),
    [mode, resolved, setMode],
  )

  return <ThemeContext.Provider value={value}>{children}</ThemeContext.Provider>
}

export function useThemeChoice() {
  const ctx = useContext(ThemeContext)
  if (!ctx) throw new Error("useThemeChoice must be used within ThemeProvider")
  return ctx
}
