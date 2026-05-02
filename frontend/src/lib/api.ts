import { useAuthStore } from "@/store/useAuthStore"

const DEFAULT_TIMEOUT_MS = 15_000

export class ApiError extends Error {
  readonly code: string

  constructor(code: string, message: string) {
    super(message)
    this.name = "ApiError"
    this.code = code
  }
}

function sessionExpiredThrow(): never {
  useAuthStore.getState().logout({ sessionExpired: true })
  throw new ApiError("SESSION_EXPIRED", "Your session has expired. Please sign in again.")
}

function apiBase(): string {
  const base =
    process.env.NEXT_PUBLIC_API_BASE ||
    process.env.NEXT_PUBLIC_API_URL ||
    "http://localhost:8000"
  return base.replace(/\/$/, "")
}

function isLikelyNetworkFailure(e: unknown): boolean {
  if (e instanceof TypeError) return true
  if (e instanceof Error && e.message === "Failed to fetch") return true
  return false
}

function networkApiError(): ApiError {
  const base = apiBase()
  const local = base.includes("localhost") || base.includes("127.0.0.1")
  const hint = local
    ? "Redeploy the frontend after setting GitHub Actions variable PUBLIC_API_BASE_URL to your live API (HTTPS)."
    : "Most often the API base URL is wrong or there is no running web service on that host (requests fail before CORS). In Render, open the service and copy its exact URL. Use HTTPS when this site uses HTTPS. GitHub Pages https://<user>.github.io is allowed by current API CORS settings; add it to CORS_ORIGINS only if you run an older backend."
  return new ApiError("NETWORK_ERROR", `Could not reach the API (${base}). ${hint}`)
}

function isRecord(v: unknown): v is Record<string, unknown> {
  return typeof v === "object" && v !== null
}

function extractError(v: unknown): ApiError | null {
  if (!isRecord(v) || !isRecord(v.error)) return null
  const code = v.error.code
  const message = v.error.message
  if (typeof code !== "string" || typeof message !== "string") return null
  return new ApiError(code, message)
}

export async function apiFetch<T>(
  path: string,
  init: RequestInit & { timeoutMs?: number; token?: string | null } = {},
): Promise<T> {
  const { timeoutMs = DEFAULT_TIMEOUT_MS, signal: outerSignal, token, ...rest } = init
  const headers = new Headers(rest.headers)
  if (token) headers.set("Authorization", `Bearer ${token}`)
  const controller = new AbortController()
  const tid = setTimeout(() => controller.abort(), timeoutMs)

  if (outerSignal) {
    if (outerSignal.aborted) controller.abort()
    outerSignal.addEventListener("abort", () => controller.abort(), { once: true })
  }

  try {
    const url = `${apiBase()}${path.startsWith("/") ? path : `/${path}`}`
    const res = await fetch(url, {
      ...rest,
      headers,
      signal: controller.signal,
    })

    let json: unknown
    try {
      json = await res.json()
    } catch {
      if (!res.ok && res.status === 401 && token) {
        sessionExpiredThrow()
      }
      throw new ApiError(
        "INVALID_RESPONSE",
        res.ok ? "Success body was not valid JSON" : "Error body was not valid JSON",
      )
    }

    const apiErr = extractError(json)
    if (apiErr) {
      if (token && apiErr.code === "UNAUTHORIZED") {
        sessionExpiredThrow()
      }
      throw apiErr
    }

    if (!res.ok) {
      if (token && res.status === 401) {
        sessionExpiredThrow()
      }
      throw new ApiError("HTTP_ERROR", `Request failed (${res.status})`)
    }

    return json as T
  } catch (e) {
    if (e instanceof ApiError) throw e
    if (e instanceof DOMException && e.name === "AbortError") {
      throw new ApiError("TIMEOUT", `Request timed out after ${timeoutMs}ms`)
    }
    if (isLikelyNetworkFailure(e)) throw networkApiError()
    throw e
  } finally {
    clearTimeout(tid)
  }
}

/** Authenticated fetch that returns the raw `Response` (e.g. CSV/blob). Parses JSON error bodies when `!res.ok`. */
export async function apiFetchRaw(
  path: string,
  init: RequestInit & { timeoutMs?: number; token?: string | null } = {},
): Promise<Response> {
  const { timeoutMs = DEFAULT_TIMEOUT_MS, signal: outerSignal, token, ...rest } = init
  const headers = new Headers(rest.headers)
  if (token) headers.set("Authorization", `Bearer ${token}`)
  const controller = new AbortController()
  const tid = setTimeout(() => controller.abort(), timeoutMs)

  if (outerSignal) {
    if (outerSignal.aborted) controller.abort()
    outerSignal.addEventListener("abort", () => controller.abort(), { once: true })
  }

  try {
    const url = `${apiBase()}${path.startsWith("/") ? path : `/${path}`}`
    const res = await fetch(url, {
      ...rest,
      headers,
      signal: controller.signal,
    })

    if (!res.ok) {
      let json: unknown
      try {
        json = await res.json()
      } catch {
        if (token && res.status === 401) {
          sessionExpiredThrow()
        }
        throw new ApiError("HTTP_ERROR", `Request failed (${res.status})`)
      }
      const apiErr = extractError(json)
      if (apiErr) {
        if (token && apiErr.code === "UNAUTHORIZED") {
          sessionExpiredThrow()
        }
        throw apiErr
      }
      if (token && res.status === 401) {
        sessionExpiredThrow()
      }
      throw new ApiError("HTTP_ERROR", `Request failed (${res.status})`)
    }

    return res
  } catch (e) {
    if (e instanceof ApiError) throw e
    if (e instanceof DOMException && e.name === "AbortError") {
      throw new ApiError("TIMEOUT", `Request timed out after ${timeoutMs}ms`)
    }
    if (isLikelyNetworkFailure(e)) throw networkApiError()
    throw e
  } finally {
    clearTimeout(tid)
  }
}
