import * as React from "react"

const MOBILE_BREAKPOINT = 768
const QUERY = `(max-width: ${MOBILE_BREAKPOINT - 1}px)`

function getMql(): MediaQueryList | null {
  if (typeof window === "undefined") return null
  return window.matchMedia(QUERY)
}

function subscribe(onChange: () => void) {
  const mql = getMql()
  if (!mql) return () => {}
  mql.addEventListener("change", onChange)
  return () => mql.removeEventListener("change", onChange)
}

function getSnapshot() {
  return getMql()?.matches ?? false
}

function getServerSnapshot() {
  return false
}

export function useIsMobile() {
  return React.useSyncExternalStore(subscribe, getSnapshot, getServerSnapshot)
}
