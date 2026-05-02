import type { JobSearchRunApi } from "@/types/jobs"

const PORTAL_DISPLAY: Record<string, string> = {
  linkedin: "LinkedIn",
  indeed: "Indeed",
  glassdoor: "Glassdoor",
  naukri: "Naukri",
  zip_recruiter: "ZipRecruiter",
}

/** Pretty name for portal keys in run summaries (e.g. zip_recruiter → ZipRecruiter). */
export function portalLabel(portalKey: string): string {
  const k = portalKey.toLowerCase()
  if (PORTAL_DISPLAY[k]) return PORTAL_DISPLAY[k]
  if (!portalKey) return portalKey
  return portalKey.charAt(0).toUpperCase() + portalKey.slice(1)
}

type PortalSummary = { rows: number; state: string }

function portalSummaries(run: JobSearchRunApi): Record<string, PortalSummary> | null {
  const raw = run.summary_json?.portals
  if (!raw || typeof raw !== "object") return null
  return raw as Record<string, PortalSummary>
}

/** User-facing line for the last job search run (no collector internals). */
export function friendlyRunSummaryLine(run: JobSearchRunApi | null): string {
  if (!run) return ""
  const outcome = run.summary_json?.outcome
  const portals = portalSummaries(run)
  const collectorNote = run.summary_json?.collector_note

  const note = typeof collectorNote === "string" ? collectorNote.trim() : ""
  const collectorExplainsFailure =
    /^Job search failed:/i.test(note) ||
    /^Some job boards failed/i.test(note) ||
    /Indeed is not queried unless JOBSPY_RUN_INDEED/i.test(note) ||
    /ZipRecruiter is not queried unless JOBSPY_RUN_ZIP_RECRUITER/i.test(note) ||
    /No boards left to scrape/i.test(note)

  const parts: string[] = []

  if (typeof collectorNote === "string" && collectorNote.trim()) {
    parts.push(collectorNote.trim())
  }

  if (run.status === "failed") {
    parts.push("Search failed.")
    return parts.join(" ")
  }

  if (run.status === "running" || run.status === "queued") {
    parts.push(`Search ${run.status}…`)
    return parts.join(" ")
  }

  if (outcome === "no_results") {
    if (!collectorExplainsFailure) {
      parts.push("No results matched your search.")
    }
  } else if (run.status === "completed") {
    parts.push("Search completed.")
  } else if (run.status === "partial") {
    parts.push("Search partially completed — some sources were unavailable.")
  }

  if (portals) {
    const unavailable = Object.entries(portals).filter(([, v]) => v.state === "unavailable")
    if (unavailable.length) {
      const names = unavailable.map(([name]) => portalLabel(name))
      parts.push(`Unavailable: ${names.join(", ")}.`)
    }
    const noHits = Object.entries(portals).filter(([, v]) => v.state === "no_results")
    if (noHits.length && outcome !== "no_results") {
      const names = noHits.map(([name]) => portalLabel(name))
      parts.push(`No listings from: ${names.join(", ")}.`)
    }
  }

  return parts.join(" ").trim() || `Status: ${run.status}.`
}
