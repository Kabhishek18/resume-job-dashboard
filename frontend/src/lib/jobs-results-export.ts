import type { AggregatedJobRowApi } from "@/types/jobs"

/** Column order for clipboard and CSV exports (matches on-screen relevance). */
export const RESULTS_EXPORT_HEADERS = [
  "portal",
  "title",
  "company",
  "location",
  "posted_at",
  "salary_text",
  "apply_url",
  "description_snippet",
  "duplicate_count",
  "board_status",
  "source_count",
] as const

function escapeCsvCell(value: string): string {
  const needsQuote = /[",\n\r]/.test(value)
  const v = value.replace(/"/g, '""')
  return needsQuote ? `"${v}"` : v
}

export function rowToExportCells(r: AggregatedJobRowApi): string[] {
  return [
    r.portal,
    r.title,
    r.company,
    r.location,
    r.posted_at ?? "",
    r.salary_text,
    r.apply_url,
    r.description_snippet ?? "",
    String(r.duplicate_count),
    r.board_status ?? "",
    String(r.source_count),
  ]
}

/** TSV for clipboard: tabs/newlines escaped in cells. */
export function aggregatedJobsToTsv(rows: AggregatedJobRowApi[]): string {
  const header = [...RESULTS_EXPORT_HEADERS]
  const lines = [header.join("\t")]
  for (const r of rows) {
    const cells = rowToExportCells(r).map((c) => c.replace(/\t/g, " ").replace(/\r?\n/g, " "))
    lines.push(cells.join("\t"))
  }
  return lines.join("\n")
}

export function aggregatedJobsToCsv(rows: AggregatedJobRowApi[]): string {
  const header = [...RESULTS_EXPORT_HEADERS].map(escapeCsvCell).join(",")
  const lines = [header]
  for (const r of rows) {
    const line = rowToExportCells(r).map(escapeCsvCell).join(",")
    lines.push(line)
  }
  return lines.join("\r\n")
}

export function triggerDownloadCsv(filename: string, csvBody: string): void {
  const blob = new Blob([csvBody], { type: "text/csv;charset=utf-8" })
  const url = URL.createObjectURL(blob)
  const a = document.createElement("a")
  a.href = url
  a.download = filename
  a.click()
  URL.revokeObjectURL(url)
}
