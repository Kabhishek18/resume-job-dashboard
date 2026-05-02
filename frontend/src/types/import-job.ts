/** POST /api/jobs/import-preview */
export type ImportPreviewMode = "imported_full" | "imported_partial" | "fallback_required"

export type ImportPreviewApiV1 = {
  version: "v1"
  mode: ImportPreviewMode
  title?: string | null
  company?: string | null
  raw_text?: string | null
  warnings: string[]
}
