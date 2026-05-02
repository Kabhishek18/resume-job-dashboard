const STORAGE_KEY = "resumeJobDashboard:lastPath"

const ALLOWED_PREFIXES = ["/dashboard", "/jobs", "/resume"] as const

export function isStorableAppPath(pathname: string): boolean {
  if (!pathname || pathname === "/") return false
  if (pathname.startsWith("/login") || pathname.startsWith("/signup")) return false
  return ALLOWED_PREFIXES.some((p) => pathname === p || pathname.startsWith(`${p}/`))
}

export function readLastVisitedPath(): string | null {
  if (typeof window === "undefined") return null
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    if (!raw) return null
    if (!raw.startsWith("/") || raw.startsWith("//")) return null
    if (!isStorableAppPath(raw)) return null
    return raw
  } catch {
    return null
  }
}

export function writeLastVisitedPath(pathname: string): void {
  if (typeof window === "undefined") return
  try {
    if (!isStorableAppPath(pathname)) return
    localStorage.setItem(STORAGE_KEY, pathname)
  } catch {
    /* ignore */
  }
}

export function resolvePostAuthPath(nextParam: string | null): string {
  const raw = nextParam?.trim() ?? ""
  if (raw.startsWith("/") && !raw.startsWith("//")) {
    return raw
  }
  return readLastVisitedPath() ?? "/dashboard"
}
