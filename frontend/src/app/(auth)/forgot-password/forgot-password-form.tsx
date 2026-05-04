"use client"

import Link from "next/link"
import { useState } from "react"

import { ApiError } from "@/lib/api"
import { FORGOT_PASSWORD_SUCCESS_MESSAGE } from "@/constants/password-reset"
import { cn } from "@/lib/utils"
import { postForgotPassword } from "@/services/auth.service"
import { Button, buttonVariants } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"

export default function ForgotPasswordForm() {
  const [email, setEmail] = useState("")
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)
  const [submitted, setSubmitted] = useState(false)

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault()
    setError(null)
    setLoading(true)
    try {
      await postForgotPassword(email.trim())
      setSubmitted(true)
    } catch (err) {
      const message =
        err instanceof ApiError ? err.message : err instanceof Error ? err.message : "Something went wrong"
      setError(message)
    } finally {
      setLoading(false)
    }
  }

  if (submitted) {
    return (
      <Card className="w-full max-w-md">
        <CardHeader>
          <CardTitle className="text-xl">Check your email</CardTitle>
          <CardDescription>{FORGOT_PASSWORD_SUCCESS_MESSAGE}</CardDescription>
        </CardHeader>
        <CardFooter>
          <Link href="/login" className={cn(buttonVariants({ variant: "outline" }), "w-full justify-center text-center")}>
            Back to sign in
          </Link>
        </CardFooter>
      </Card>
    )
  }

  return (
    <Card className="w-full max-w-md">
      <CardHeader className="space-y-1">
        <CardTitle className="text-xl">Forgot password</CardTitle>
        <CardDescription>We&apos;ll email you a link to choose a new password if an account exists.</CardDescription>
      </CardHeader>
      <CardContent>
        <form onSubmit={(e) => void onSubmit(e)} className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="forgot-email">Email</Label>
            <Input
              id="forgot-email"
              type="email"
              autoComplete="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
            />
          </div>
          {error ? <p className="text-destructive text-sm">{error}</p> : null}
          <Button type="submit" className="w-full" disabled={loading}>
            {loading ? "Sending…" : "Send reset link"}
          </Button>
        </form>
      </CardContent>
      <CardFooter className="flex flex-col gap-2 border-t pt-6">
        <p className="text-muted-foreground text-center text-sm">
          Remembered your password?{" "}
          <Link href="/login" className="text-foreground underline-offset-4 hover:underline">
            Sign in
          </Link>
        </p>
      </CardFooter>
    </Card>
  )
}
