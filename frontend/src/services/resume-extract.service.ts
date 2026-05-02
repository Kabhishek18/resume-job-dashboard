import { apiFetch } from "@/lib/api"
import type { ExtractResumeFileApiV1 } from "@/types/resume-extract"

export async function postExtractResumeFile(token: string, file: File): Promise<ExtractResumeFileApiV1> {
  const form = new FormData()
  form.append("file", file)
  return apiFetch<ExtractResumeFileApiV1>("/api/profile/resume-upload", {
    method: "POST",
    body: form,
    token,
  })
}
