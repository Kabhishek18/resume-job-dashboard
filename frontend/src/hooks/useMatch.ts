"use client"

import { useCallback, useState } from "react"

import { ApiError } from "@/lib/api"
import { postMatchV2 } from "@/services/match.service"
import type { MatchPayload, MatchRequest } from "@/types/match"

export function useMatch() {
  const [data, setData] = useState<MatchPayload | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)

  const runMatch = useCallback(async (body: MatchRequest) => {
    setLoading(true)
    setError(null)
    setData(null)
    try {
      const result = await postMatchV2(body)
      setData(result)
      return result
    } catch (e) {
      const message =
        e instanceof ApiError
          ? `${e.code}: ${e.message}`
          : e instanceof Error
            ? e.message
            : "Match failed"
      setError(message)
      throw e
    } finally {
      setLoading(false)
    }
  }, [])

  return { data, error, loading, runMatch }
}
