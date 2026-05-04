import { cleanup, render, screen, waitFor } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { afterEach, describe, expect, it, vi } from "vitest"

import { ApiError } from "@/lib/api"
import ResetPasswordForm from "@/app/(auth)/reset-password/reset-password-form"

const replace = vi.fn()

vi.mock("next/navigation", () => ({
  useRouter: () => ({ replace }),
  useSearchParams: () => new URLSearchParams("token=test-token-reset-123456789"),
}))

describe("ResetPasswordForm", () => {
  afterEach(() => {
    cleanup()
    replace.mockReset()
    vi.restoreAllMocks()
  })

  it("redirects to login after successful reset", async () => {
    const user = userEvent.setup()
    const auth = await import("@/services/auth.service")
    const postResetPassword = vi.spyOn(auth, "postResetPassword").mockResolvedValue({
      version: "v1",
      message: "ok",
    })

    render(<ResetPasswordForm />)
    await user.type(screen.getByLabelText(/^new password/i), "goodpass999")
    await user.type(screen.getByLabelText(/confirm new password/i), "goodpass999")
    await user.click(screen.getByRole("button", { name: /update password/i }))

    await waitFor(() => {
      expect(replace).toHaveBeenCalledWith("/login?reset=1")
    })
    expect(postResetPassword).toHaveBeenCalled()
  })

  it("surfaces invalid-token message from API", async () => {
    const user = userEvent.setup()
    const auth = await import("@/services/auth.service")
    vi.spyOn(auth, "postResetPassword").mockRejectedValue(
      new ApiError("RESET_TOKEN_INVALID", "bad token"),
    )

    render(<ResetPasswordForm />)
    await user.type(screen.getByLabelText(/^new password/i), "goodpass888")
    await user.type(screen.getByLabelText(/confirm new password/i), "goodpass888")
    await user.click(screen.getByRole("button", { name: /update password/i }))

    await waitFor(() => {
      expect(screen.getByText(/invalid or has expired/i)).toBeTruthy()
    })
    expect(replace).not.toHaveBeenCalled()
  })
})
