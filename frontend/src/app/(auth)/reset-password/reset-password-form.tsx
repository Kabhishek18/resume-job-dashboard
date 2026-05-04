"use client"

import Link from "next/link"
import { useRouter, useSearchParams } from "next/navigation"
import { useState } from "react"

import { ApiError } from "@/lib/api"
import { postResetPassword } from "@/services/auth.service"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"

export default function ResetPasswordForm() {
  const router = useRouter()
  const searchParams = useSearchParams()
  const rawToken = (searchParams.get("token") || "").trim()

  const [pw, setPw] = useState("")
  const [confirm, setConfirm] = useState("")
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault()
    setError(null)
    if (!rawToken) {
      setError("This reset link is missing a token. Open the link from your email.")
      return
    }
    if (pw.length < 8) {
      setError("Password must be at least 8 characters.")
      return
    }
    if (pw !== confirm) {
      setError("Passwords do not match.")
      return
    }
    setLoading(true)
    try {
      await postResetPassword({ token: rawToken, new_password: pw, confirm_password: confirm })
      router.replace("/login?reset=1")
    } catch (err) {
      if (err instanceof ApiError) {
        if (err.code === "RESET_TOKEN_INVALID") {
          setError("This reset link is invalid or has expired. Request a new one from “Forgot password”.")
        } else if (err.code === "VALIDATION_ERROR") {
          setError(err.message)
        } else {
          setError(err.message)
        }
      } else setError("Could not reset password.")
    } finally {
      setLoading(false)
    }
  }

  const missingToken = !rawToken

  return (
    <Card className="w-full max-w-md">
      <CardHeader className="space-y-1">
        <CardTitle className="text-xl">Choose a new password</CardTitle>
        <CardDescription>After resetting, sign in again with your new password.</CardDescription>
      </CardHeader>
      <CardContent>
        {missingToken ? (
          <p className="text-destructive text-sm" role="alert">
            This page needs a reset link from your email. Copy the full URL or tap the link again.
          </p>
        ) : (
          <form onSubmit={(e) => void onSubmit(e)} className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="reset-pw">New password</Label>
              <Input
                id="reset-pw"
                type="password"
                autoComplete="new-password"
                required
                value={pw}
                onChange={(e) => setPw(e.target.value)}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="reset-confirm">Confirm new password</Label>
              <Input
                id="reset-confirm"
                type="password"
                autoComplete="new-password"
                required
                value={confirm}
                onChange={(e) => setConfirm(e.target.value)}
              />
            </div>
            {error ? (
              <p className="text-destructive text-sm" role="alert">
                {error}
              </p>
            ) : null}
            <Button type="submit" className="w-full" disabled={loading}>
              {loading ? "Updating…" : "Update password"}
            </Button>
          </form>
        )}
      </CardContent>
      <CardFooter className="border-t pt-6">
        <p className="text-muted-foreground w-full text-center text-sm">
          <Link href="/login" className="text-foreground underline-offset-4 hover:underline">
            Sign in
          </Link>
        </p>
      </CardFooter>
    </Card>
  )
}
