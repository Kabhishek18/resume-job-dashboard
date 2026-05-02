import type { BoardEntryApi, JobSearchRunApi } from "@/types/jobs"

export interface DashboardSummaryApi {
  board_counts_by_status: Record<string, number>
  total_tracked_jobs: number
  recent_board_entries: BoardEntryApi[]
  most_recent_run: JobSearchRunApi | null
}
