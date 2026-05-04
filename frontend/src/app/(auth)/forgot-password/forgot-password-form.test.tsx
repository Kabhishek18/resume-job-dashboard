import { cleanup, render, screen, waitFor } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { afterEach, describe, expect, it, vi } from "vitest"

import ForgotPasswordForm from "@/app/(auth)/forgot-password/forgot-password-form"
import { FORGOT_PASSWORD_SUCCESS_MESSAGE } from "@/constants/password-reset"
import * as authService from "@/services/auth.service"

describe("ForgotPasswordForm", () => {
  afterEach(() => cleanup())

  it("shows generic success state after submit", async () => {
    const user = userEvent.setup()
    vi.spyOn(authService, "postForgotPassword").mockResolvedValue({
      version: "v1",
      message: FORGOT_PASSWORD_SUCCESS_MESSAGE,
    })
    render(<ForgotPasswordForm />)
    await user.type(screen.getByLabelText(/email/i), "someone@example.com")
    await user.click(screen.getByRole("button", { name: /send reset link/i }))
    await waitFor(() => {
      expect(screen.getByText(/check your email/i)).toBeTruthy()
    })
    expect(screen.getByText(FORGOT_PASSWORD_SUCCESS_MESSAGE)).toBeTruthy()
    vi.restoreAllMocks()
  })
})
