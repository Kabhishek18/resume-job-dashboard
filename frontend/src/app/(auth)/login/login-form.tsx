"use client"

import { useRouter, useSearchParams } from "next/navigation"
import Link from "next/link"
import { useState } from "react"

import { ApiError } from "@/lib/api"
import { resolvePostAuthPath } from "@/lib/last-visited-path"
import { postLogin } from "@/services/auth.service"
import { useAuthStore } from "@/store/useAuthStore"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"

export default function LoginForm() {
  const router = useRouter()
  const searchParams = useSearchParams()
  const setAuth = useAuthStore((s) => s.setAuth)

  const sessionExpired = searchParams.get("expired") === "1"
  const passwordReset = searchParams.get("reset") === "1"

  const [email, setEmail] = useState("")
  const [password, setPassword] = useState("")
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault()
    setError(null)
    setLoading(true)
    try {
      const res = await postLogin({ email: email.trim(), password })
      setAuth(res.access_token, res.user)
      router.replace(resolvePostAuthPath(searchParams.get("next")))
    } catch (err) {
      const message =
        err instanceof ApiError ? err.message : err instanceof Error ? err.message : "Sign in failed"
      setError(message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <Card className="w-full max-w-md">
      <CardHeader className="space-y-1">
        <CardTitle className="text-xl">Sign in</CardTitle>
        <CardDescription>Use your email and password to continue.</CardDescription>
      </CardHeader>
      <CardContent>
        <form onSubmit={onSubmit} className="space-y-4">
          {passwordReset ? (
            <p className="rounded-md border border-emerald-500/40 bg-emerald-500/10 px-3 py-2 text-sm text-emerald-950 dark:text-emerald-100">
              Password updated. Sign in again with your new password.
            </p>
          ) : null}
          {sessionExpired ? (
            <p className="border-amber-500/40 bg-amber-500/10 text-amber-950 dark:text-amber-100 rounded-md border px-3 py-2 text-sm">
              Session expired. Please sign in again.
            </p>
          ) : null}
          <div className="space-y-2">
            <Label htmlFor="login-email">Email</Label>
            <Input
              id="login-email"
              type="email"
              autoComplete="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="login-password">Password</Label>
            <Input
              id="login-password"
              type="password"
              autoComplete="current-password"
              required
              value={password}
              onChange={(e) => setPassword(e.target.value)}
            />
          </div>
          {error ? <p className="text-destructive text-sm">{error}</p> : null}
          <Button type="submit" className="w-full" disabled={loading}>
            {loading ? "Signing in…" : "Sign in"}
          </Button>
          <p className="text-muted-foreground text-center text-sm">
            <Link href="/forgot-password" className="text-foreground underline-offset-4 hover:underline">
              Forgot password?
            </Link>
          </p>
          <p className="text-muted-foreground text-center text-sm">
            No account?{" "}
            <Link href="/signup" className="text-foreground underline-offset-4 hover:underline">
              Sign up
            </Link>
          </p>
        </form>
      </CardContent>
    </Card>
  )
}
