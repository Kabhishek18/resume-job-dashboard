"use client"

import { useCallback, useEffect, useMemo, useRef, useState } from "react"

import { Trash2 } from "lucide-react"

import { Button, buttonVariants } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { ApiError } from "@/lib/api"
import { friendlyRunSummaryLine } from "@/lib/jobs-run-summary"
import { aggregatedJobsToCsv, aggregatedJobsToTsv, triggerDownloadCsv } from "@/lib/jobs-results-export"
import { cn } from "@/lib/utils"
import { postMatchV2 } from "@/services/match.service"
import { getProfile } from "@/services/profile.service"
import {
  addJobToBoard,
  createSearchProfile,
  deleteBoardEntry,
  getRun,
  getRunResults,
  listBoard,
  listSearchProfiles,
  patchBoardEntry,
  patchSearchProfile,
  runSearchProfile,
} from "@/services/jobs.service"
import { useAuthStore } from "@/store/useAuthStore"
import type { AggregatedJobRowApi, BoardEntryApi, BoardEntryPatchBody, JobsPortalId, JobSearchRunApi, SearchProfileApi } from "@/types/jobs"

export const JOBS_RESULTS_TAB = "results"
export const JOBS_BOARD_TAB = "board"

export { aggregatedJobsToTsv } from "@/lib/jobs-results-export"

const PAGE_SIZE_STORAGE_KEY = "jobs-results-page-size"
const PAGE_SIZE_OPTIONS = [10, 25, 50, 100] as const

function readStoredPageSize(): number {
  if (typeof window === "undefined") return 25
  const raw = window.localStorage.getItem(PAGE_SIZE_STORAGE_KEY)
  const n = raw ? Number.parseInt(raw, 10) : 25
  return PAGE_SIZE_OPTIONS.includes(n as (typeof PAGE_SIZE_OPTIONS)[number]) ? n : 25
}

const RESULTS_WANTED_OPTIONS = ["", "15", "30", "50", "75", "100", "150", "200"] as const

const PORTALS: { id: JobsPortalId; label: string }[] = [
  { id: "linkedin", label: "LinkedIn" },
  { id: "indeed", label: "Indeed" },
  { id: "zip_recruiter", label: "ZipRecruiter" },
  { id: "glassdoor", label: "Glassdoor" },
  { id: "google", label: "Google jobs (JobSpy)" },
  { id: "bayt", label: "Bayt" },
  { id: "bdjobs", label: "BDJobs" },
  { id: "naukri", label: "Naukri" },
]

const BOARD_STATUSES = ["saved", "applied", "pending", "rejected", "interviewing", "offer", "new"] as const

type SortKey = "title" | "company" | "portal" | "board_status" | "match_score"

function boardStatusChipClass(status: string): string {
  const s = status.toLowerCase()
  if (s === "applied") return "bg-emerald-500/15 text-emerald-800 dark:text-emerald-200 border-emerald-500/30"
  if (s === "interviewing") return "bg-violet-500/15 text-violet-800 dark:text-violet-200 border-violet-500/30"
  if (s === "offer") return "bg-amber-500/15 text-amber-900 dark:text-amber-200 border-amber-500/30"
  if (s === "rejected") return "bg-red-500/10 text-red-800 dark:text-red-200 border-red-500/25"
  if (s === "pending" || s === "saved" || s === "new") {
    return "bg-slate-500/10 text-slate-800 dark:text-slate-200 border-slate-500/25"
  }
  return "bg-muted text-foreground border-border"
}

async function pollUntilRunTerminal(token: string, runId: number): Promise<void> {
  const done = new Set(["completed", "partial", "failed"])
  for (let i = 0; i < 240; i++) {
    const r = await getRun(token, runId)
    if (done.has(r.status)) return
    await new Promise((res) => setTimeout(res, 500))
  }
  throw new ApiError("TIMEOUT", "The search run did not finish in time.")
}

function compareRows(a: AggregatedJobRowApi, b: AggregatedJobRowApi, key: SortKey, dir: "asc" | "desc"): number {
  if (key === "match_score") {
    return 0
  }
  const va = (key === "board_status" ? a.board_status ?? "" : String(a[key as keyof AggregatedJobRowApi] ?? "")).toLowerCase()
  const vb = (key === "board_status" ? b.board_status ?? "" : String(b[key as keyof AggregatedJobRowApi] ?? "")).toLowerCase()
  const c = va.localeCompare(vb)
  return dir === "asc" ? c : -c
}

function jobRowRawTextForMatch(r: AggregatedJobRowApi): string {
  const parts = [r.title, r.company, r.location, r.salary_text, r.description_snippet].filter((x) => String(x ?? "").trim())
  return parts.length ? parts.join("\n\n") : r.title || "Job"
}

export function JobsDashboard() {
  const token = useAuthStore((s) => s.token)
  const [tab, setTab] = useState<typeof JOBS_RESULTS_TAB | typeof JOBS_BOARD_TAB>(JOBS_RESULTS_TAB)

  const [profiles, setProfiles] = useState<SearchProfileApi[]>([])
  const [selectedProfileId, setSelectedProfileId] = useState<number | null>(null)

  const [name, setName] = useState("")
  const [keywords, setKeywords] = useState("")
  const [locations, setLocations] = useState("")
  const [pickedPortals, setPickedPortals] = useState<JobsPortalId[]>(() => ["linkedin"])
  const [resultsWantedStr, setResultsWantedStr] = useState<string>("")

  const [message, setMessage] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  const [lastRunId, setLastRunId] = useState<number | null>(null)
  const [lastRun, setLastRun] = useState<JobSearchRunApi | null>(null)
  const [results, setResults] = useState<AggregatedJobRowApi[]>([])

  const [filterText, setFilterText] = useState("")
  const [sortKey, setSortKey] = useState<SortKey>("title")
  const [sortDir, setSortDir] = useState<"asc" | "desc">("asc")
  const [resultsPage, setResultsPage] = useState(1)
  const [pageSize, setPageSize] = useState(() => readStoredPageSize())

  const [boardEntries, setBoardEntries] = useState<BoardEntryApi[]>([])
  const [boardEntryDeletingId, setBoardEntryDeletingId] = useState<number | null>(null)

  const [savedResumeText, setSavedResumeText] = useState<string | null>(null)
  /** Completed scores only (-1 = error). Missing key = still loading. */
  const [matchScores, setMatchScores] = useState<Record<number, number>>({})
  const matchInflightRef = useRef(new Set<number>())
  /** Mirrors completed scores for queueing (sync cleared with reset; avoids stale closure vs effects). */
  const matchScoresWorkRef = useRef<Record<number, number>>({})

  const hasResume = Boolean((savedResumeText ?? "").trim())
  const showMatchColumn = hasResume
  const resultsTableColSpan = 5 + (showMatchColumn ? 1 : 0)

  const filteredSorted = useMemo(() => {
    const q = filterText.trim().toLowerCase()
    let rows = results
    if (q) {
      rows = rows.filter((r) => {
        const blob = [r.title, r.company, r.location, r.portal, r.board_status ?? ""].join(" ").toLowerCase()
        return blob.includes(q)
      })
    }
    const sortMatchValue = (id: number) => {
      const s = matchScores[id]
      if (typeof s === "number" && s >= 0) return s
      return -1
    }
    if (sortKey === "match_score") {
      return [...rows].sort((a, b) => {
        const c = sortMatchValue(a.id) - sortMatchValue(b.id)
        return sortDir === "asc" ? c : -c
      })
    }
    return [...rows].sort((a, b) => compareRows(a, b, sortKey, sortDir))
  }, [results, filterText, sortKey, sortDir, matchScores])

  const totalPages = Math.max(1, Math.ceil(filteredSorted.length / pageSize))
  const pageSlice = useMemo(() => {
    const p = Math.min(resultsPage, totalPages)
    const start = (p - 1) * pageSize
    return filteredSorted.slice(start, start + pageSize)
  }, [filteredSorted, resultsPage, totalPages, pageSize])

  const safePage = Math.min(resultsPage, totalPages)
  const pageSliceIds = useMemo(() => pageSlice.map((r) => r.id).join(","), [pageSlice])

  const googleJobsSearchUrl = useMemo(() => {
    const q = ["jobs", keywords.trim(), locations.trim()].filter((s) => s.length > 0).join(" ")
    return `https://www.google.com/search?q=${encodeURIComponent(q)}`
  }, [keywords, locations])

  const refreshProfiles = useCallback(async () => {
    if (!token) return
    try {
      const rows = await listSearchProfiles(token)
      setProfiles(rows)
    } catch (e) {
      setMessage(e instanceof ApiError ? e.message : "Could not load saved searches.")
    }
  }, [token])

  const refreshBoard = useCallback(async () => {
    if (!token) return
    try {
      setBoardEntries(await listBoard(token))
    } catch (e) {
      setMessage(e instanceof ApiError ? e.message : "Could not load board.")
    }
  }, [token])

  useEffect(() => {
    let cancelled = false
    ;(async () => {
      if (!token) return
      try {
        const rows = await listSearchProfiles(token)
        if (!cancelled) setProfiles(rows)
      } catch (e) {
        if (!cancelled) setMessage(e instanceof ApiError ? e.message : "Could not load saved searches.")
      }
    })()
    return () => {
      cancelled = true
    }
  }, [token])

  useEffect(() => {
    if (tab !== JOBS_BOARD_TAB) return
    let cancelled = false
    ;(async () => {
      if (!token) return
      try {
        const entries = await listBoard(token)
        if (!cancelled) setBoardEntries(entries)
      } catch (e) {
        if (!cancelled) setMessage(e instanceof ApiError ? e.message : "Could not load board.")
      }
    })()
    return () => {
      cancelled = true
    }
  }, [tab, token])

  useEffect(() => {
    let cancelled = false
    ;(async () => {
      if (!token) return
      try {
        const prof = await getProfile(token)
        if (!cancelled) setSavedResumeText(prof.resume_text ?? null)
      } catch {
        if (!cancelled) setSavedResumeText(null)
      }
    })()
    return () => {
      cancelled = true
    }
  }, [token])

  useEffect(() => {
    if (!hasResume && sortKey === "match_score") {
      queueMicrotask(() => setSortKey("title"))
    }
  }, [hasResume, sortKey])

  useEffect(() => {
    matchInflightRef.current.clear()
    matchScoresWorkRef.current = {}
    /* Sync clear: async defer races with scoring effect and can wipe freshly written scores. */
    // eslint-disable-next-line react-hooks/set-state-in-effect -- reset client cache when run/resume identity changes
    setMatchScores({})
  }, [lastRunId, savedResumeText])

  useEffect(() => {
    const resume = (savedResumeText ?? "").trim()
    if (!resume || !pageSlice.length) return
    let cancelled = false

    async function scoreOne(r: AggregatedJobRowApi): Promise<void> {
      if (matchInflightRef.current.has(r.id)) return
      matchInflightRef.current.add(r.id)
      try {
        const m = await postMatchV2({
          raw_resume_text: resume,
          job: {
            title: r.title,
            company: r.company,
            raw_text: jobRowRawTextForMatch(r),
            url: r.apply_url || null,
          },
        })
        if (cancelled) return
        matchScoresWorkRef.current[r.id] = m.job_match.score
        setMatchScores((prev) => ({ ...prev, [r.id]: m.job_match.score }))
      } catch {
        if (!cancelled) {
          matchScoresWorkRef.current[r.id] = -1
          setMatchScores((prev) => ({ ...prev, [r.id]: -1 }))
        }
      } finally {
        matchInflightRef.current.delete(r.id)
      }
    }

    const pending = pageSlice.filter((r) => !(r.id in matchScoresWorkRef.current))
    const q = [...pending]
    const workers = [0, 1].map(async () => {
      while (q.length && !cancelled) {
        const row = q.shift()
        if (row) await scoreOne(row)
      }
    })

    void Promise.all(workers)
    return () => {
      cancelled = true
    }
  },
  // pageSlice omitted: pageSliceIds + length track the page; `pageSlice` is a new [] when unrelated state updates.
  // eslint-disable-next-line react-hooks/exhaustive-deps
  [savedResumeText, pageSliceIds, pageSlice.length],
  )

  const fillFromProfile = (p: SearchProfileApi) => {
    setName(p.name)
    setKeywords(p.keywords ?? "")
    setLocations(p.locations ?? "")
    setResultsWantedStr(p.results_wanted != null && p.results_wanted >= 1 ? String(p.results_wanted) : "")
    const allowed = new Set(PORTALS.map((x) => x.id))
    const next = (p.selected_portals ?? []).filter((x): x is JobsPortalId => allowed.has(x as JobsPortalId))
    setPickedPortals(next.length ? next : ["linkedin"])
  }

  const togglePortal = (id: JobsPortalId) => {
    setPickedPortals((prev) => {
      if (prev.includes(id)) return prev.filter((x) => x !== id)
      return [...prev, id]
    })
  }

  const onSelectProfileOption = (v: string) => {
    setMessage(null)
    if (v === "new") {
      setSelectedProfileId(null)
      setName("")
      setKeywords("")
      setLocations("")
      setResultsWantedStr("")
      setPickedPortals(["linkedin"])
      return
    }
    const id = Number(v)
    const p = profiles.find((x) => x.id === id)
    setSelectedProfileId(id)
    if (p) fillFromProfile(p)
  }

  const saveProfile = async () => {
    if (!token) return
    const trimmed = name.trim()
    if (!trimmed) {
      setMessage("Please enter a name for this search.")
      return
    }
    if (!pickedPortals.length) {
      setMessage("Select at least one jobs portal.")
      return
    }
    const parsedRw = Number.parseInt(resultsWantedStr, 10)
    const results_wanted =
      resultsWantedStr.trim() === "" || Number.isNaN(parsedRw) ? null : Math.min(200, Math.max(1, parsedRw))
    setBusy(true)
    setMessage(null)
    try {
      if (selectedProfileId !== null) {
        await patchSearchProfile(token, selectedProfileId, {
          name: trimmed,
          keywords,
          locations,
          selected_portals: pickedPortals,
          results_wanted,
        })
        setMessage("Search profile updated.")
      } else {
        const created = await createSearchProfile(token, {
          name: trimmed,
          keywords,
          locations,
          selected_portals: pickedPortals,
          results_wanted,
        })
        setSelectedProfileId(created.id)
        fillFromProfile(created)
        setMessage("Search profile saved.")
      }
      await refreshProfiles()
    } catch (e) {
      setMessage(e instanceof ApiError ? e.message : "Could not save search profile.")
    } finally {
      setBusy(false)
    }
  }

  const runSearch = async () => {
    if (!token || selectedProfileId === null) {
      setMessage("Save a search profile first, then select it before running.")
      return
    }
    setBusy(true)
    setMessage(null)
    setResults([])
    setLastRun(null)
    setResultsPage(1)
    try {
      const run = await runSearchProfile(token, selectedProfileId)
      setLastRunId(run.id)
      await pollUntilRunTerminal(token, run.id)
      const finished = await getRun(token, run.id)
      setLastRun(finished)
      setResults(await getRunResults(token, run.id))
      setMessage("Run finished.")
    } catch (e) {
      setMessage(e instanceof ApiError ? e.message : "Search run failed.")
    } finally {
      setBusy(false)
    }
  }

  const copyText = async (text: string, okMsg: string) => {
    setMessage(null)
    try {
      await navigator.clipboard.writeText(text)
      setMessage(okMsg)
    } catch {
      setMessage("Clipboard copy failed.")
    }
  }

  const trackRow = async (jobId: number) => {
    if (!token) return
    setMessage(null)
    try {
      await addJobToBoard(token, jobId)
      await refreshBoard()
      setMessage("Added to board.")
      if (lastRunId !== null) {
        setResults(await getRunResults(token, lastRunId))
      }
    } catch (e) {
      setMessage(e instanceof ApiError ? e.message : "Could not add to board.")
    }
  }

  const patchBoardRow = async (entryId: number, jobId: number, body: BoardEntryPatchBody) => {
    if (!token) return
    try {
      const next = await patchBoardEntry(token, entryId, body)
      setBoardEntries((prev) => prev.map((e) => (e.id === entryId ? next : e)))
      if (body.status != null) {
        setResults((prev) => prev.map((r) => (r.id === jobId ? { ...r, board_status: body.status! } : r)))
      }
    } catch (e) {
      setMessage(e instanceof ApiError ? e.message : "Board update failed.")
    }
  }

  const removeBoardRow = async (entryId: number, jobId: number, title: string) => {
    if (!token) return
    const label = title.trim() || "this job"
    const confirmed =
      typeof window === "undefined" ||
      window.confirm(
        `Remove “${label.slice(0, 80)}${label.length > 80 ? "…" : ""}” from your board? You can track it again from Results.`,
      )
    if (!confirmed) return
    setMessage(null)
    setBoardEntryDeletingId(entryId)
    try {
      await deleteBoardEntry(token, entryId)
      setBoardEntries((prev) => prev.filter((e) => e.id !== entryId))
      setResults((prev) => prev.map((r) => (r.id === jobId ? { ...r, board_status: null } : r)))
      setMessage("Removed from board.")
    } catch (e) {
      setMessage(e instanceof ApiError ? e.message : "Could not remove from board.")
    } finally {
      setBoardEntryDeletingId(null)
    }
  }

  const runSummary = friendlyRunSummaryLine(lastRun)

  return (
    <div className="space-y-6">
      {message ? (
        <p className="text-muted-foreground border-border bg-muted/40 rounded-lg border px-3 py-2 text-sm">{message}</p>
      ) : null}

      <div className="bg-muted inline-flex gap-1 rounded-lg p-1">
        <Button
          type="button"
          variant={tab === JOBS_RESULTS_TAB ? "default" : "ghost"}
          size="sm"
          className="rounded-md"
          onClick={() => setTab(JOBS_RESULTS_TAB)}
          data-testid="jobs-tab-results"
        >
          Results
        </Button>
        <Button
          type="button"
          variant={tab === JOBS_BOARD_TAB ? "default" : "ghost"}
          size="sm"
          className="rounded-md"
          onClick={() => setTab(JOBS_BOARD_TAB)}
          data-testid="jobs-tab-board"
        >
          Board
        </Button>
      </div>

      {tab === JOBS_RESULTS_TAB ? (
        <Card className="shadow-sm">
          <CardHeader className="space-y-1 border-b pb-4">
            <CardTitle className="text-lg">Job search</CardTitle>
            <CardDescription>
              Run a saved search across LinkedIn, Indeed, ZipRecruiter, Glassdoor, Google jobs, Bayt, BDJobs, and Naukri
              (JobSpy-supported sites depend on your installed python-jobspy). Results are deduped by apply link; export
              matches what you filter and sort below.
            </CardDescription>
            {lastRun ? (
              <p className="text-foreground pt-2 text-sm font-medium leading-snug">{runSummary}</p>
            ) : (
              <p className="text-muted-foreground pt-1 text-xs">Run a search to see status and counts per source.</p>
            )}
          </CardHeader>
          <CardContent className="space-y-4 pt-6">
            <div className="space-y-2">
              <Label htmlFor="profile-pick">Search profile</Label>
              <select
                id="profile-pick"
                data-testid="jobs-profile-select"
                className="border-input bg-background focus-visible:ring-ring h-9 w-full rounded-md border px-2 text-sm shadow-xs outline-none focus-visible:ring-2"
                value={selectedProfileId === null ? "new" : String(selectedProfileId)}
                disabled={busy}
                onChange={(e) => onSelectProfileOption(e.target.value)}
              >
                <option value="new">New search profile…</option>
                {profiles.map((p) => (
                  <option key={p.id} value={p.id}>
                    {p.name}
                  </option>
                ))}
              </select>
            </div>

            <div className="grid gap-3 sm:grid-cols-2">
              <div className="space-y-2 sm:col-span-2">
                <Label htmlFor="sp-name">Name</Label>
                <Input id="sp-name" value={name} onChange={(e) => setName(e.target.value)} disabled={busy} />
              </div>
              <div className="space-y-2 sm:col-span-2">
                <Label htmlFor="sp-keys">Keywords</Label>
                <Input
                  id="sp-keys"
                  placeholder="e.g. backend engineer python"
                  value={keywords}
                  onChange={(e) => setKeywords(e.target.value)}
                  disabled={busy}
                />
              </div>
              <div className="space-y-2 sm:col-span-2">
                <Label htmlFor="sp-loc">Locations</Label>
                <Input
                  id="sp-loc"
                  placeholder="e.g. Berlin, Remote"
                  value={locations}
                  onChange={(e) => setLocations(e.target.value)}
                  disabled={busy}
                />
              </div>
              <div className="space-y-2 sm:col-span-2">
                <Label htmlFor="sp-max">Max jobs per run</Label>
                <select
                  id="sp-max"
                  data-testid="jobs-results-wanted-select"
                  className="border-input bg-background focus-visible:ring-ring h-9 w-full rounded-md border px-2 text-sm shadow-xs outline-none focus-visible:ring-2"
                  value={resultsWantedStr}
                  onChange={(e) => setResultsWantedStr(e.target.value)}
                  disabled={busy}
                >
                  {RESULTS_WANTED_OPTIONS.map((opt) => (
                    <option key={opt || "default"} value={opt}>
                      {opt === "" ? "Server default" : opt}
                    </option>
                  ))}
                </select>
              </div>
            </div>

            <div className="space-y-2">
              <span className="text-sm font-medium">Portals</span>
              <div className="flex flex-wrap gap-3">
                {PORTALS.map((p) => (
                  <label key={p.id} className="flex cursor-pointer items-center gap-2 text-sm">
                    <input
                      type="checkbox"
                      className="size-4 rounded border"
                      checked={pickedPortals.includes(p.id)}
                      onChange={() => togglePortal(p.id)}
                      disabled={busy}
                    />
                    {p.label}
                  </label>
                ))}
              </div>
              {pickedPortals.includes("indeed") ? (
                <p className="text-muted-foreground text-xs leading-snug">
                  Indeed is queried only when <code className="text-foreground rounded bg-muted px-1">JOBSPY_RUN_INDEED=true</code>{" "}
                  is set in the backend <code className="text-foreground rounded bg-muted px-1">.env</code> (many networks get HTTP
                  403; a <code className="text-foreground rounded bg-muted px-1">JOBSPY_PROXY</code> often helps).
                </p>
              ) : null}
              {pickedPortals.includes("zip_recruiter") ? (
                <p className="text-muted-foreground text-xs leading-snug">
                  ZipRecruiter is queried only when{" "}
                  <code className="text-foreground rounded bg-muted px-1">JOBSPY_RUN_ZIP_RECRUITER=true</code> is set in the backend{" "}
                  <code className="text-foreground rounded bg-muted px-1">.env</code> (many networks get 403;{" "}
                  <code className="text-foreground rounded bg-muted px-1">JOBSPY_PROXY</code> often helps).
                </p>
              ) : null}
              {pickedPortals.includes("google") || pickedPortals.includes("bayt") || pickedPortals.includes("bdjobs") ? (
                <p className="text-muted-foreground text-xs leading-snug">
                  Google jobs, Bayt, and BDJobs are passed to python-jobspy only if your installed build supports them
                  (upgrade with <code className="text-foreground rounded bg-muted px-1">pip install -U python-jobspy</code>
                  ). Bayt/BDJobs are region-specific.
                </p>
              ) : null}
            </div>

            <div className="flex flex-wrap gap-2">
              <Button type="button" variant="secondary" onClick={() => void saveProfile()} disabled={busy} data-testid="jobs-save-profile">
                Save profile
              </Button>
              <Button type="button" onClick={() => void runSearch()} disabled={busy || selectedProfileId === null} data-testid="jobs-run-search">
                {busy ? "Working…" : "Run search"}
              </Button>
              <a
                href={googleJobsSearchUrl}
                target="_blank"
                rel="noopener noreferrer"
                className={cn(buttonVariants({ variant: "outline", size: "sm" }), "no-underline")}
                data-testid="jobs-google-search"
              >
                Search on Google
              </a>
            </div>

            <div className="grid gap-3 border-t pt-4 sm:grid-cols-2 lg:grid-cols-3">
              <div className="space-y-2 sm:col-span-2 lg:col-span-1">
                <Label htmlFor="jobs-filter">Filter results</Label>
                <Input
                  id="jobs-filter"
                  data-testid="jobs-results-filter"
                  placeholder="Title, company, location, portal…"
                  value={filterText}
                  onChange={(e) => {
                    setFilterText(e.target.value)
                    setResultsPage(1)
                  }}
                  disabled={!results.length}
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="jobs-sort">Sort by</Label>
                <select
                  id="jobs-sort"
                  data-testid="jobs-results-sort-key"
                  className="border-input bg-background focus-visible:ring-ring h-9 w-full rounded-md border px-2 text-sm shadow-xs outline-none focus-visible:ring-2"
                  value={sortKey}
                  onChange={(e) => {
                    setSortKey(e.target.value as SortKey)
                    setResultsPage(1)
                  }}
                  disabled={!results.length}
                >
                  <option value="title">Title</option>
                  <option value="company">Company</option>
                  <option value="portal">Portal</option>
                  <option value="board_status">Board status</option>
                  {showMatchColumn ? <option value="match_score">Match score</option> : null}
                </select>
              </div>
              <div className="space-y-2">
                <Label htmlFor="jobs-sort-dir">Direction</Label>
                <select
                  id="jobs-sort-dir"
                  data-testid="jobs-results-sort-dir"
                  className="border-input bg-background focus-visible:ring-ring h-9 w-full rounded-md border px-2 text-sm shadow-xs outline-none focus-visible:ring-2"
                  value={sortDir}
                  onChange={(e) => {
                    setSortDir(e.target.value as "asc" | "desc")
                    setResultsPage(1)
                  }}
                  disabled={!results.length}
                >
                  <option value="asc">A → Z</option>
                  <option value="desc">Z → A</option>
                </select>
              </div>
            </div>

            <div className="flex flex-col gap-3 sm:flex-row sm:flex-wrap sm:items-center sm:justify-between">
              <div className="flex flex-wrap items-center gap-2 text-muted-foreground text-xs">
                <span>
                  Showing {filteredSorted.length} row{filteredSorted.length === 1 ? "" : "s"}
                  {filteredSorted.length !== results.length ? ` (of ${results.length} from run)` : ""}
                  {filteredSorted.length > pageSize ? ` · Page ${safePage} of ${totalPages}` : ""}
                </span>
                <div className="flex items-center gap-1.5">
                  <Label htmlFor="jobs-page-size" className="text-muted-foreground whitespace-nowrap text-xs font-normal">
                    Rows per page
                  </Label>
                  <select
                    id="jobs-page-size"
                    data-testid="jobs-page-size-select"
                    className="border-input bg-background h-8 rounded-md border px-2 text-xs shadow-xs"
                    value={pageSize}
                    onChange={(e) => {
                      const n = Number.parseInt(e.target.value, 10)
                      setPageSize(n)
                      try {
                        window.localStorage.setItem(PAGE_SIZE_STORAGE_KEY, String(n))
                      } catch {
                        /* ignore */
                      }
                      setResultsPage(1)
                    }}
                  >
                    {PAGE_SIZE_OPTIONS.map((n) => (
                      <option key={n} value={n}>
                        {n}
                      </option>
                    ))}
                  </select>
                </div>
              </div>
              <div className="flex flex-wrap gap-2">
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  data-testid="jobs-copy-page"
                  onClick={() => void copyText(aggregatedJobsToTsv(pageSlice), "Copied current page (TSV).")}
                  disabled={!pageSlice.length}
                >
                  Copy current page
                </Button>
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  data-testid="jobs-copy-all"
                  onClick={() => void copyText(aggregatedJobsToTsv(filteredSorted), "Copied all filtered rows (TSV).")}
                  disabled={!filteredSorted.length}
                >
                  Copy all
                </Button>
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  data-testid="jobs-download-page-csv"
                  onClick={() => {
                    if (!lastRunId || !pageSlice.length) return
                    triggerDownloadCsv(`run-${lastRunId}-page-${safePage}.csv`, aggregatedJobsToCsv(pageSlice))
                    setMessage("Downloaded current page CSV.")
                  }}
                  disabled={lastRunId === null || !pageSlice.length}
                >
                  Download page CSV
                </Button>
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  data-testid="jobs-download-all-csv"
                  onClick={() => {
                    if (!lastRunId || !filteredSorted.length) return
                    triggerDownloadCsv(`run-${lastRunId}-filtered-all.csv`, aggregatedJobsToCsv(filteredSorted))
                    setMessage("Downloaded all filtered CSV.")
                  }}
                  disabled={lastRunId === null || !filteredSorted.length}
                >
                  Download all CSV
                </Button>
              </div>
            </div>

            {filteredSorted.length > pageSize ? (
              <div className="flex items-center gap-2">
                <Button
                  type="button"
                  variant="secondary"
                  size="sm"
                  data-testid="jobs-page-prev"
                  disabled={safePage <= 1}
                  onClick={() => setResultsPage((p) => Math.max(1, p - 1))}
                >
                  Previous
                </Button>
                <Button
                  type="button"
                  variant="secondary"
                  size="sm"
                  data-testid="jobs-page-next"
                  disabled={safePage >= totalPages}
                  onClick={() => setResultsPage((p) => Math.min(totalPages, p + 1))}
                >
                  Next
                </Button>
              </div>
            ) : null}

            <div className="overflow-x-auto rounded-lg border">
              <table className="w-full min-w-[760px] text-left text-sm">
                <thead className="bg-muted/50">
                  <tr>
                    <th className="p-2.5 text-xs font-semibold tracking-wide">Title</th>
                    <th className="p-2.5 text-xs font-semibold tracking-wide">Company</th>
                    <th className="p-2.5 text-xs font-semibold tracking-wide">Portal</th>
                    {showMatchColumn ? (
                      <th className="p-2.5 text-xs font-semibold tracking-wide">Match</th>
                    ) : null}
                    <th className="p-2.5 text-xs font-semibold tracking-wide">Board</th>
                    <th className="w-28 p-2.5 text-xs font-semibold tracking-wide" />
                  </tr>
                </thead>
                <tbody>
                  {!results.length ? (
                    <tr>
                      <td colSpan={resultsTableColSpan} className="text-muted-foreground p-8 text-center text-sm">
                        <div className="mx-auto max-w-sm space-y-1">
                          <p className="text-foreground font-medium">No results yet</p>
                          <p>Save a profile, pick portals, and run a search. Deduped listings and board status appear here.</p>
                        </div>
                      </td>
                    </tr>
                  ) : !filteredSorted.length ? (
                    <tr>
                      <td colSpan={resultsTableColSpan} className="text-muted-foreground p-6 text-center text-sm">
                        No rows match your filter. Clear the filter to see all results.
                      </td>
                    </tr>
                  ) : (
                    pageSlice.map((r) => (
                      <tr key={r.id} className="odd:bg-muted/15 border-t">
                        <td className="max-w-[220px] p-2.5 align-middle">
                          {r.apply_url ? (
                            <a className="text-primary font-medium underline underline-offset-2" href={r.apply_url} target="_blank" rel="noreferrer">
                              {r.title || "Untitled"}
                            </a>
                          ) : (
                            <span className="font-medium">{r.title || "Untitled"}</span>
                          )}
                          {r.duplicate_count > 1 ? (
                            <span className="text-muted-foreground ml-2 text-xs tabular-nums">×{r.duplicate_count}</span>
                          ) : null}
                        </td>
                        <td className="p-2.5 align-middle">{r.company}</td>
                        <td className="text-muted-foreground p-2.5 align-middle capitalize">{r.portal}</td>
                        {showMatchColumn ? (
                          <td className="text-foreground p-2.5 align-middle tabular-nums text-xs font-medium">
                            {!(r.id in matchScores)
                              ? "…"
                              : matchScores[r.id] === -1
                                ? "—"
                                : String(matchScores[r.id])}
                          </td>
                        ) : null}
                        <td className="p-2.5 align-middle">
                          {r.board_status ? (
                            <span
                              className={cn(
                                "inline-flex rounded-full border px-2 py-0.5 text-xs font-medium capitalize",
                                boardStatusChipClass(r.board_status),
                              )}
                            >
                              {r.board_status}
                            </span>
                          ) : (
                            <span className="text-muted-foreground text-xs">—</span>
                          )}
                        </td>
                        <td className="p-2.5 align-middle">
                          <Button type="button" size="sm" variant="outline" className="h-8 px-2" onClick={() => void trackRow(r.id)}>
                            Track
                          </Button>
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          </CardContent>
        </Card>
      ) : (
        <Card className="shadow-sm">
          <CardHeader className="border-b pb-4">
            <CardTitle className="text-lg">Application board</CardTitle>
            <CardDescription>
              Track applications from Results. Status chips update live; edits sync back to the Results tab. Use{" "}
              <strong>Remove</strong> to delete a saved job from your board (listings stay in Results).
            </CardDescription>
          </CardHeader>
          <CardContent className="pt-6">
            <div className="space-y-4 lg:hidden">
              {boardEntries.length === 0 ? (
                <p className="text-muted-foreground rounded-lg border border-dashed p-8 text-center text-sm">
                  Nothing on the board yet — use <strong>Track</strong> in Results after a search.
                </p>
              ) : (
                boardEntries.map((row) => (
                  <BoardCard
                    key={`${row.id}-${row.updated_at ?? ""}`}
                    row={row}
                    disabled={busy || boardEntryDeletingId === row.id}
                    onPatch={patchBoardRow}
                    onRemove={removeBoardRow}
                  />
                ))
              )}
            </div>
            <div className="hidden overflow-x-auto rounded-lg border lg:block">
              <table className="w-full min-w-[920px] text-left text-sm">
                <thead className="bg-muted/50">
                  <tr>
                    <th className="p-2.5 text-xs font-semibold tracking-wide">Role</th>
                    <th className="p-2.5 text-xs font-semibold tracking-wide">Company</th>
                    <th className="p-2.5 text-xs font-semibold tracking-wide">Status</th>
                    <th className="p-2.5 text-xs font-semibold tracking-wide">Follow-up</th>
                    <th className="p-2.5 text-xs font-semibold tracking-wide">Recruiter</th>
                    <th className="p-2.5 text-xs font-semibold tracking-wide">Notes</th>
                    <th className="p-2.5 text-xs font-semibold tracking-wide">Updated</th>
                    <th className="p-2.5 text-right text-xs font-semibold tracking-wide">Remove</th>
                  </tr>
                </thead>
                <tbody>
                  {boardEntries.length === 0 ? (
                    <tr>
                      <td colSpan={8} className="text-muted-foreground p-8 text-center text-sm">
                        Nothing on the board yet — use Track in Results after a search.
                      </td>
                    </tr>
                  ) : (
                    boardEntries.map((row) => (
                      <BoardRowEditable
                        key={`${row.id}-${row.updated_at ?? ""}`}
                        row={row}
                        disabled={busy || boardEntryDeletingId === row.id}
                        onPatch={patchBoardRow}
                        onRemove={removeBoardRow}
                      />
                    ))
                  )}
                </tbody>
              </table>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  )
}

function BoardRowEditable({
  row,
  disabled,
  onPatch,
  onRemove,
}: {
  row: BoardEntryApi
  disabled: boolean
  onPatch: (entryId: number, jobId: number, body: BoardEntryPatchBody) => void
  onRemove: (entryId: number, jobId: number, title: string) => void | Promise<void>
}) {
  const statuses = Array.from(new Set([row.status, ...BOARD_STATUSES]))
  const updated = row.updated_at ? new Date(row.updated_at).toLocaleString(undefined, { dateStyle: "short", timeStyle: "short" }) : "—"
  return (
    <tr className="odd:bg-muted/15 border-t align-top">
      <td className="max-w-[200px] p-2.5">
        {row.apply_url ? (
          <a className="text-primary font-medium underline underline-offset-2" href={row.apply_url} target="_blank" rel="noreferrer">
            {row.title}
          </a>
        ) : (
          row.title
        )}
        <div className="text-muted-foreground mt-1 text-xs capitalize">{row.portal}</div>
      </td>
      <td className="p-2.5">{row.company}</td>
      <td className="p-2.5">
        <div className="flex flex-col gap-1">
          <select
            className="border-input bg-background h-9 max-w-[12rem] rounded-md border px-2 text-sm font-medium capitalize"
            disabled={disabled}
            value={row.status}
            onChange={(e) => onPatch(row.id, row.job_id, { status: e.target.value })}
          >
            {statuses.map((s) => (
              <option key={s} value={s}>
                {s}
              </option>
            ))}
          </select>
        </div>
      </td>
      <td className="p-2.5">
        <Input
          className="h-9 font-mono text-xs"
          defaultValue={row.follow_up_date ?? ""}
          placeholder="YYYY-MM-DD"
          disabled={disabled}
          onBlur={(e) => {
            const v = e.target.value.trim()
            onPatch(row.id, row.job_id, { follow_up_date: v })
          }}
        />
      </td>
      <td className="max-w-[200px] p-2.5">
        <div className="space-y-1">
          <Input
            className="h-8 text-xs"
            defaultValue={row.recruiter_name}
            placeholder="Name"
            disabled={disabled}
            onBlur={(e) => {
              const v = e.target.value
              if (v !== row.recruiter_name) onPatch(row.id, row.job_id, { recruiter_name: v })
            }}
          />
          <Input
            className="h-8 text-xs"
            type="email"
            defaultValue={row.recruiter_email}
            placeholder="Email"
            disabled={disabled}
            onBlur={(e) => {
              const v = e.target.value
              if (v !== row.recruiter_email) onPatch(row.id, row.job_id, { recruiter_email: v })
            }}
          />
        </div>
      </td>
      <td className="max-w-[260px] p-2.5">
        <textarea
          className="border-input bg-background focus-visible:ring-ring min-h-[72px] w-full rounded-md border px-2 py-1 text-xs shadow-xs outline-none focus-visible:ring-2"
          defaultValue={row.notes}
          disabled={disabled}
          onBlur={(e) => {
            const v = e.target.value
            if (v !== row.notes) onPatch(row.id, row.job_id, { notes: v })
          }}
        />
      </td>
      <td className="text-muted-foreground whitespace-nowrap p-2.5 text-xs">{updated}</td>
      <td className="p-2.5 align-middle">
        <Button
          type="button"
          variant="outline"
          size="sm"
          className="text-destructive hover:bg-destructive/10 h-8 gap-1 px-2"
          disabled={disabled}
          aria-label={`Remove ${row.title} from board`}
          onClick={() => void onRemove(row.id, row.job_id, row.title)}
        >
          <Trash2 className="size-3.5 shrink-0" aria-hidden />
          <span className="hidden sm:inline">Remove</span>
        </Button>
      </td>
    </tr>
  )
}

function BoardCard({
  row,
  disabled,
  onPatch,
  onRemove,
}: {
  row: BoardEntryApi
  disabled: boolean
  onPatch: (entryId: number, jobId: number, body: BoardEntryPatchBody) => void
  onRemove: (entryId: number, jobId: number, title: string) => void | Promise<void>
}) {
  const statuses = Array.from(new Set([row.status, ...BOARD_STATUSES]))
  const updated = row.updated_at ? new Date(row.updated_at).toLocaleString(undefined, { dateStyle: "short", timeStyle: "short" }) : "—"
  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="text-base">
          {row.apply_url ? (
            <a className="text-primary underline underline-offset-2" href={row.apply_url} target="_blank" rel="noreferrer">
              {row.title}
            </a>
          ) : (
            row.title
          )}
        </CardTitle>
        <CardDescription>
          {row.company} · <span className="capitalize">{row.portal}</span>
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-3">
        <div>
          <Label className="text-xs">Status</Label>
          <select
            className="border-input bg-background mt-1 h-9 w-full rounded-md border px-2 text-sm"
            disabled={disabled}
            value={row.status}
            onChange={(e) => onPatch(row.id, row.job_id, { status: e.target.value })}
          >
            {statuses.map((s) => (
              <option key={s} value={s}>
                {s}
              </option>
            ))}
          </select>
        </div>
        <div>
          <Label className="text-xs">Follow-up</Label>
          <Input
            className="mt-1 h-9 font-mono text-xs"
            defaultValue={row.follow_up_date ?? ""}
            disabled={disabled}
            onBlur={(e) => onPatch(row.id, row.job_id, { follow_up_date: e.target.value.trim() })}
          />
        </div>
        <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
          <div>
            <Label className="text-xs">Recruiter</Label>
            <Input className="mt-1 h-9 text-xs" defaultValue={row.recruiter_name} disabled={disabled} onBlur={(e) => onPatch(row.id, row.job_id, { recruiter_name: e.target.value })} />
          </div>
          <div>
            <Label className="text-xs">Email</Label>
            <Input className="mt-1 h-9 text-xs" defaultValue={row.recruiter_email} disabled={disabled} onBlur={(e) => onPatch(row.id, row.job_id, { recruiter_email: e.target.value })} />
          </div>
        </div>
        <div>
          <Label className="text-xs">Notes</Label>
          <textarea
            className="border-input bg-background mt-1 min-h-[64px] w-full rounded-md border px-2 py-1 text-xs"
            defaultValue={row.notes}
            disabled={disabled}
            onBlur={(e) => onPatch(row.id, row.job_id, { notes: e.target.value })}
          />
        </div>
        <p className="text-muted-foreground text-xs">Updated {updated}</p>
        <Button
          type="button"
          variant="outline"
          size="sm"
          className="text-destructive hover:bg-destructive/10 w-full gap-1.5 sm:w-auto"
          disabled={disabled}
          aria-label={`Remove ${row.title} from board`}
          onClick={() => void onRemove(row.id, row.job_id, row.title)}
        >
          <Trash2 className="size-3.5 shrink-0" aria-hidden />
          Remove from board
        </Button>
      </CardContent>
    </Card>
  )
}
