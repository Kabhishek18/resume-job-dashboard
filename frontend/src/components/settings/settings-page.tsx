"use client"

import { useCallback, useEffect, useRef, useState } from "react"

import { useRouter } from "next/navigation"

import { useThemeChoice, type ThemeMode } from "@/components/theme-provider"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Textarea } from "@/components/ui/textarea"
import { ApiError } from "@/lib/api"
import { cn } from "@/lib/utils"
import { postChangePassword } from "@/services/auth.service"
import { getProfile, patchProfileName, putSavedResume } from "@/services/profile.service"
import { postExtractResumeFile } from "@/services/resume-extract.service"
import { useAuthStore } from "@/store/useAuthStore"

function formatResumeUpdated(iso: string | null): string {
  if (!iso) return "Never saved"
  try {
    return new Date(iso).toLocaleString()
  } catch {
    return iso
  }
}

export function SettingsPage() {
  const router = useRouter()
  const token = useAuthStore((s) => s.token)
  const patchUser = useAuthStore((s) => s.patchUser)
  const logout = useAuthStore((s) => s.logout)
  const { mode: themeMode, setMode: setThemeMode } = useThemeChoice()

  const fileRef = useRef<HTMLInputElement>(null)

  const [loadingProfile, setLoadingProfile] = useState(true)
  const [profileError, setProfileError] = useState<string | null>(null)
  const [email, setEmail] = useState("")
  const [name, setName] = useState("")
  const [nameSaved, setNameSaved] = useState<string | null>(null)
  const [nameError, setNameError] = useState<string | null>(null)
  const [nameBusy, setNameBusy] = useState(false)

  const [currentPw, setCurrentPw] = useState("")
  const [newPw, setNewPw] = useState("")
  const [confirmPw, setConfirmPw] = useState("")
  const [pwError, setPwError] = useState<string | null>(null)
  const [pwSuccess, setPwSuccess] = useState<string | null>(null)
  const [pwBusy, setPwBusy] = useState(false)

  const [resumeText, setResumeText] = useState("")
  const [resumeUpdatedAt, setResumeUpdatedAt] = useState<string | null>(null)
  const [resumeBusy, setResumeBusy] = useState(false)
  const [resumeError, setResumeError] = useState<string | null>(null)
  const [resumeMessage, setResumeMessage] = useState<string | null>(null)
  const [extractWarnings, setExtractWarnings] = useState<string[]>([])

  useEffect(() => {
    let cancelled = false
    ;(async () => {
      if (!token) return
      setLoadingProfile(true)
      setProfileError(null)
      try {
        const p = await getProfile(token)
        if (cancelled) return
        setEmail(p.email)
        setName(p.name)
        setResumeText(p.resume_text ?? "")
        setResumeUpdatedAt(p.resume_updated_at)
      } catch (e) {
        if (!cancelled)
          setProfileError(e instanceof ApiError ? e.message : "Could not load your profile.")
      } finally {
        if (!cancelled) setLoadingProfile(false)
      }
    })()
    return () => {
      cancelled = true
    }
  }, [token])

  async function submitName(ev: React.FormEvent) {
    ev.preventDefault()
    if (!token) return
    const trimmed = name.trim()
    if (!trimmed) {
      setNameError("Name is required.")
      return
    }
    setNameBusy(true)
    setNameError(null)
    setNameSaved(null)
    try {
      const p = await patchProfileName(token, { name: trimmed })
      setNameSaved("Display name saved.")
      patchUser({ name: p.name })
    } catch (e) {
      setNameError(e instanceof ApiError ? e.message : "Could not save name.")
    } finally {
      setNameBusy(false)
    }
  }

  async function submitPassword(ev: React.FormEvent) {
    ev.preventDefault()
    if (!token) return
    setPwError(null)
    setPwSuccess(null)
    if (newPw.length < 8) {
      setPwError("New password must be at least 8 characters.")
      return
    }
    if (newPw !== confirmPw) {
      setPwError("New password and confirmation do not match.")
      return
    }
    setPwBusy(true)
    try {
      const res = await postChangePassword(token, {
        current_password: currentPw,
        new_password: newPw,
        confirm_password: confirmPw,
      })
      setPwSuccess(res.message)
      setCurrentPw("")
      setNewPw("")
      setConfirmPw("")
    } catch (e) {
      if (e instanceof ApiError) {
        if (e.code === "WRONG_CURRENT_PASSWORD") {
          setPwError("Current password is incorrect.")
        } else if (e.code === "VALIDATION_ERROR") {
          setPwError(e.message)
        } else {
          setPwError(e.message)
        }
      } else setPwError("Could not update password.")
    } finally {
      setPwBusy(false)
    }
  }

  async function saveResume() {
    if (!token) return
    const t = resumeText.trim()
    if (!t) {
      setResumeError("Resume text cannot be empty.")
      return
    }
    setResumeBusy(true)
    setResumeError(null)
    setResumeMessage(null)
    try {
      const p = await putSavedResume(token, t)
      setResumeUpdatedAt(p.resume_updated_at)
      setResumeMessage("Saved to your profile.")
    } catch (e) {
      setResumeError(e instanceof ApiError ? e.message : "Save failed.")
    } finally {
      setResumeBusy(false)
    }
  }

  const onPickFile = useCallback(
    async (file: File) => {
      if (!token) return
      setResumeError(null)
      setResumeMessage(null)
      setExtractWarnings([])
      setResumeBusy(true)
      try {
        const res = await postExtractResumeFile(token, file)
        setResumeText(res.plain_text)
        setExtractWarnings(res.warnings ?? [])
        setResumeMessage("Extracted text loaded — review below, then save to update your profile.")
      } catch (e) {
        setResumeError(
          e instanceof ApiError ? `${e.code}: ${e.message}` : e instanceof Error ? e.message : "Extract failed.",
        )
      } finally {
        setResumeBusy(false)
        if (fileRef.current) fileRef.current.value = ""
      }
    },
    [token],
  )

  function themeButton(mode: ThemeMode, label: string) {
    const active = themeMode === mode
    return (
      <Button
        type="button"
        variant={active ? "default" : "outline"}
        size="sm"
        className={cn("flex-1", active && "pointer-events-none")}
        onClick={() => setThemeMode(mode)}
      >
        {label}
      </Button>
    )
  }

  if (!token) {
    return null
  }

  if (loadingProfile) {
    return <p className="text-muted-foreground px-4 py-10 text-sm">Loading settings…</p>
  }

  return (
    <div className="mx-auto flex w-full max-w-3xl flex-col gap-6 px-4 py-8">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Settings</h1>
        <p className="text-muted-foreground mt-1 text-sm">Manage your account, appearance, and saved resume.</p>
      </div>

      {profileError ? (
        <p className="text-destructive text-sm" role="alert">
          {profileError}
        </p>
      ) : null}

      <Card>
        <CardHeader>
          <CardTitle>Account</CardTitle>
          <CardDescription>Your email stays fixed while you&apos;re signed in.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="settings-email">Email</Label>
            <Input id="settings-email" value={email} readOnly disabled className="bg-muted/50" />
          </div>
          <form onSubmit={submitName} className="space-y-2">
            <Label htmlFor="settings-name">Display name</Label>
            <div className="flex flex-col gap-2 sm:flex-row sm:items-end">
              <Input
                id="settings-name"
                value={name}
                onChange={(e) => setName(e.target.value)}
                maxLength={120}
                autoComplete="name"
                className="sm:flex-1"
              />
              <Button type="submit" disabled={nameBusy}>
                {nameBusy ? "Saving…" : "Save name"}
              </Button>
            </div>
            {nameSaved ? <p className="text-muted-foreground text-sm">{nameSaved}</p> : null}
            {nameError ? (
              <p className="text-destructive text-sm" role="alert">
                {nameError}
              </p>
            ) : null}
          </form>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Security</CardTitle>
          <CardDescription>Password must be at least 8 characters. You can sign out from here or from the header.</CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={submitPassword} className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="settings-current-pw">Current password</Label>
              <Input
                id="settings-current-pw"
                type="password"
                autoComplete="current-password"
                value={currentPw}
                onChange={(e) => setCurrentPw(e.target.value)}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="settings-new-pw">New password</Label>
              <Input
                id="settings-new-pw"
                type="password"
                autoComplete="new-password"
                value={newPw}
                onChange={(e) => setNewPw(e.target.value)}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="settings-confirm-pw">Confirm new password</Label>
              <Input
                id="settings-confirm-pw"
                type="password"
                autoComplete="new-password"
                value={confirmPw}
                onChange={(e) => setConfirmPw(e.target.value)}
              />
            </div>
            {pwSuccess ? (
              <p className="text-muted-foreground text-sm" role="status">
                {pwSuccess}
              </p>
            ) : null}
            {pwError ? (
              <p className="text-destructive text-sm" role="alert">
                {pwError}
              </p>
            ) : null}
            <div className="flex flex-wrap gap-2">
              <Button type="submit" disabled={pwBusy}>
                {pwBusy ? "Updating…" : "Change password"}
              </Button>
              <Button
                type="button"
                variant="outline"
                onClick={() => {
                  logout()
                  router.replace("/login")
                }}
              >
                Sign out
              </Button>
            </div>
          </form>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Appearance</CardTitle>
          <CardDescription>Stored only in this browser. &quot;System&quot; follows your OS light/dark mode.</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex flex-wrap gap-2">
            {themeButton("light", "Light")}
            {themeButton("dark", "Dark")}
            {themeButton("system", "System")}
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Saved resume</CardTitle>
          <CardDescription>
            Last updated: {formatResumeUpdated(resumeUpdatedAt)}. Paste or upload PDF, DOCX, or TXT — then save to sync with
            the resume flow.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-3">
          <input
            ref={fileRef}
            type="file"
            accept=".pdf,.docx,.txt,application/pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document,text/plain"
            className="hidden"
            onChange={(e) => {
              const f = e.target.files?.[0]
              if (f) void onPickFile(f)
            }}
          />
          <div className="flex flex-wrap gap-2">
            <Button type="button" variant="outline" size="sm" disabled={resumeBusy} onClick={() => fileRef.current?.click()}>
              Upload to replace…
            </Button>
          </div>
          {extractWarnings.length > 0 ? (
            <ul className="text-muted-foreground list-inside list-disc text-sm">
              {extractWarnings.map((w) => (
                <li key={w}>{w}</li>
              ))}
            </ul>
          ) : null}
          <Textarea
            id="settings-resume"
            rows={6}
            value={resumeText}
            onChange={(e) => setResumeText(e.target.value)}
            placeholder="Paste your resume as plain text…"
            className="font-mono max-h-[min(40vh,14rem)] min-h-[6.5rem] resize-y overflow-y-auto text-xs sm:text-sm"
          />
          {resumeMessage ? (
            <p className="text-muted-foreground text-sm" role="status">
              {resumeMessage}
            </p>
          ) : null}
          {resumeError ? (
            <p className="text-destructive text-sm" role="alert">
              {resumeError}
            </p>
          ) : null}
        </CardContent>
        <CardFooter>
          <Button type="button" onClick={() => void saveResume()} disabled={resumeBusy}>
            {resumeBusy ? "Working…" : "Save resume to profile"}
          </Button>
        </CardFooter>
      </Card>
    </div>
  )
}
