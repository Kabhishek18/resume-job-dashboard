import { apiFetch } from "@/lib/api"
import type { ParseResumeApiV1 } from "@/types/resume"

export function postParse(rawText: string): Promise<ParseResumeApiV1> {
  return apiFetch<ParseResumeApiV1>("/api/parse", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ raw_text: rawText }),
  })
}
