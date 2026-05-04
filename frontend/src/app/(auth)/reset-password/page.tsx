import { Suspense } from "react"

import ResetPasswordForm from "./reset-password-form"

export default function ResetPasswordPage() {
  return (
    <Suspense fallback={<p className="text-muted-foreground text-sm">Loading…</p>}>
      <ResetPasswordForm />
    </Suspense>
  )
}
