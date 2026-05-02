import { Suspense } from "react"

import LoginForm from "./login-form"

export default function LoginPage() {
  return (
    <Suspense fallback={<p className="text-muted-foreground text-sm">Loading…</p>}>
      <LoginForm />
    </Suspense>
  )
}
