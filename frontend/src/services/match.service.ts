import { apiFetch } from "@/lib/api"
import type { MatchApiV1, MatchApiV2, MatchRequest } from "@/types/match"

/** Match v2 loads embeddings + may cold-start the transformer; 15s default is too tight. */
const MATCH_V2_TIMEOUT_MS = 120_000

export function postMatch(body: MatchRequest): Promise<MatchApiV1> {
  return apiFetch<MatchApiV1>("/api/match", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  })
}

export function postMatchV2(body: MatchRequest): Promise<MatchApiV2> {
  return apiFetch<MatchApiV2>("/api/match/v2", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
    timeoutMs: MATCH_V2_TIMEOUT_MS,
  })
}
