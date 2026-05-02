import { apiFetch } from "@/lib/api"
import type { DashboardSummaryApi } from "@/types/dashboard"

const jsonHeaders = { "Content-Type": "application/json" }

export async function getDashboardSummary(token: string): Promise<DashboardSummaryApi> {
  return apiFetch<DashboardSummaryApi>("/api/dashboard/summary", {
    headers: jsonHeaders,
    token,
  })
}
