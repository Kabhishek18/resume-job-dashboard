import { apiFetch } from "@/lib/api"
import type { ImportPreviewApiV1 } from "@/types/import-job"

export function postImportPreview(url: string): Promise<ImportPreviewApiV1> {
  return apiFetch<ImportPreviewApiV1>("/api/jobs/import-preview", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ url }),
  })
}
