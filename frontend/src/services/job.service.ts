/**
 * Placeholder for future job CRUD / ingestion. Use postMatch from match.service for scoring.
 */
export type JobListItem = {
  id: string
  title: string
  company: string
  location?: string
  matchScore?: number
}

export function listJobsStub(): JobListItem[] {
  return []
}
