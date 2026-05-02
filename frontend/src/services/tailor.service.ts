import { apiFetch } from "@/lib/api"
import type { TailorApiV1, TailorRequest } from "@/types/tailor"

export function postTailor(body: TailorRequest): Promise<TailorApiV1> {
  return apiFetch<TailorApiV1>("/api/resume/tailor", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  })
}
