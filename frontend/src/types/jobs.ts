/** Types for `/api/jobs/*` aggregator + board (distinct from `/api/jobs/import-preview`). */

export type JobsPortalId = "linkedin" | "indeed" | "glassdoor" | "naukri"

export type JobSearchTriggerMode = string
export type JobSearchRunStatus = "queued" | "running" | "completed" | "partial" | "failed"

export interface SearchProfileApi {
  id: number
  user_id: number
  name: string
  keywords: string
  locations: string
  experience_levels: string
  employment_types: string
  remote_only: boolean
  selected_portals: string[]
  schedule_enabled: boolean
  schedule_frequency: string | null
  schedule_time: string | null
  schedule_timezone: string | null
  created_at?: string | null
  updated_at?: string | null
}

export interface SearchProfileCreateBody {
  name: string
  keywords?: string
  locations?: string
  experience_levels?: string
  employment_types?: string
  remote_only?: boolean
  selected_portals?: string[]
  schedule_enabled?: boolean
  schedule_frequency?: string | null
  schedule_time?: string | null
  schedule_timezone?: string | null
}

export interface SearchProfilePatchBody {
  name?: string | null
  keywords?: string | null
  locations?: string | null
  experience_levels?: string | null
  employment_types?: string | null
  remote_only?: boolean | null
  selected_portals?: string[] | null
  schedule_enabled?: boolean | null
  schedule_frequency?: string | null
  schedule_time?: string | null
  schedule_timezone?: string | null
}

export interface JobSearchRunApi {
  id: number
  user_id: number
  search_profile_id: number
  trigger_mode: JobSearchTriggerMode
  status: JobSearchRunStatus
  started_at?: string | null
  finished_at?: string | null
  summary_json: Record<string, unknown>
  scheduled_fire_at?: string | null
}

export interface AggregatedJobRowApi {
  id: number
  portal: string
  title: string
  company: string
  location: string
  posted_at: string | null
  salary_text: string
  apply_url: string
  duplicate_count: number
  board_status?: string | null
  source_count: number
}

export interface BoardEntryApi {
  id: number
  user_id: number
  job_id: number
  status: string
  notes: string
  follow_up_date: string | null
  recruiter_name: string
  recruiter_email: string
  applied_at?: string | null
  updated_at?: string | null
  title: string
  company: string
  portal: string
  apply_url: string
}

export interface BoardEntryPatchBody {
  status?: string | null
  notes?: string | null
  follow_up_date?: string | null
  recruiter_name?: string | null
  recruiter_email?: string | null
  applied_at?: string | null
}
