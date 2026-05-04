import { apiFetch, apiFetchRaw } from "@/lib/api"
import type {
  AggregatedJobRowApi,
  BoardEntryApi,
  BoardEntryPatchBody,
  JobSearchRunApi,
  SearchProfileApi,
  SearchProfileCreateBody,
  SearchProfilePatchBody,
} from "@/types/jobs"

const jsonHeaders = { "Content-Type": "application/json" }

export async function listSearchProfiles(token: string): Promise<SearchProfileApi[]> {
  return apiFetch<SearchProfileApi[]>("/api/jobs/searches", {
    headers: jsonHeaders,
    token,
  })
}

export async function createSearchProfile(
  token: string,
  body: SearchProfileCreateBody,
): Promise<SearchProfileApi> {
  return apiFetch<SearchProfileApi>("/api/jobs/searches", {
    method: "POST",
    headers: jsonHeaders,
    token,
    body: JSON.stringify(body),
  })
}

export async function patchSearchProfile(
  token: string,
  searchId: number,
  body: SearchProfilePatchBody,
): Promise<SearchProfileApi> {
  return apiFetch<SearchProfileApi>(`/api/jobs/searches/${searchId}`, {
    method: "PATCH",
    headers: jsonHeaders,
    token,
    body: JSON.stringify(body),
  })
}

export async function runSearchProfile(token: string, searchId: number): Promise<JobSearchRunApi> {
  return apiFetch<JobSearchRunApi>(`/api/jobs/searches/${searchId}/run`, {
    method: "POST",
    headers: jsonHeaders,
    token,
  })
}

export async function getRun(token: string, runId: number): Promise<JobSearchRunApi> {
  return apiFetch<JobSearchRunApi>(`/api/jobs/runs/${runId}`, {
    headers: jsonHeaders,
    token,
  })
}

export async function getRunResults(token: string, runId: number): Promise<AggregatedJobRowApi[]> {
  return apiFetch<AggregatedJobRowApi[]>(`/api/jobs/runs/${runId}/results`, {
    headers: jsonHeaders,
    token,
  })
}

export async function downloadRunResultsCsv(token: string, runId: number): Promise<Blob> {
  const res = await apiFetchRaw(`/api/jobs/runs/${runId}/results.csv`, { token })
  return res.blob()
}

export async function listBoard(token: string): Promise<BoardEntryApi[]> {
  return apiFetch<BoardEntryApi[]>("/api/jobs/board", {
    headers: jsonHeaders,
    token,
  })
}

export async function addJobToBoard(token: string, jobId: number): Promise<BoardEntryApi> {
  return apiFetch<BoardEntryApi>("/api/jobs/board", {
    method: "POST",
    headers: jsonHeaders,
    token,
    body: JSON.stringify({ job_id: jobId }),
  })
}

export async function patchBoardEntry(
  token: string,
  entryId: number,
  body: BoardEntryPatchBody,
): Promise<BoardEntryApi> {
  return apiFetch<BoardEntryApi>(`/api/jobs/board/${entryId}`, {
    method: "PATCH",
    headers: jsonHeaders,
    token,
    body: JSON.stringify(body),
  })
}

export async function deleteBoardEntry(token: string, entryId: number): Promise<{ ok: string }> {
  return apiFetch<{ ok: string }>(`/api/jobs/board/${entryId}`, {
    method: "DELETE",
    headers: jsonHeaders,
    token,
  })
}
