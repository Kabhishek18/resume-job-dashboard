"use client"

import { useMemo } from "react"

import { listJobsStub } from "@/services/job.service"

/** Scaffold: wire to real API when job persistence exists. */
export function useJobs() {
  const jobs = useMemo(() => listJobsStub(), [])
  return { jobs, isLoading: false }
}
