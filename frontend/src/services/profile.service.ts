import { apiFetch } from "@/lib/api"
import type { ProfileApiV1 } from "@/types/profile"

export async function getProfile(token: string): Promise<ProfileApiV1> {
  return apiFetch<ProfileApiV1>("/api/profile", {
    headers: { "Content-Type": "application/json" },
    token,
  })
}

export async function putSavedResume(token: string, resume_text: string): Promise<ProfileApiV1> {
  return apiFetch<ProfileApiV1>("/api/profile/resume", {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    token,
    body: JSON.stringify({ resume_text }),
  })
}
