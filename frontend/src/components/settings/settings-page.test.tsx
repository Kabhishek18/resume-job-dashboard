import type { ReactElement } from "react"
import { cleanup, render, screen, waitFor } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest"

import { ThemeProvider } from "@/components/theme-provider"
import * as authService from "@/services/auth.service"
import * as profileService from "@/services/profile.service"

const patchUser = vi.fn()
const logout = vi.fn()

vi.mock("@/store/useAuthStore", () => ({
  useAuthStore: (sel: (s: unknown) => unknown) =>
    (sel as (s: Record<string, unknown>) => unknown)({
      token: "fake-token",
      patchUser,
      logout,
    }),
}))

vi.mock("next/navigation", () => ({
  useRouter: () => ({ replace: vi.fn(), push: vi.fn() }),
}))

function Shell({ children }: { children: ReactElement }) {
  return <ThemeProvider>{children}</ThemeProvider>
}

describe("SettingsPage", () => {
  beforeEach(() => {
    vi.spyOn(profileService, "getProfile").mockResolvedValue({
      version: "v1",
      id: 1,
      email: "j@example.com",
      name: "Jane",
      resume_text: null,
      resume_updated_at: null,
    })
    vi.spyOn(profileService, "patchProfileName").mockImplementation(async (_, body) => ({
      version: "v1",
      id: 1,
      email: "j@example.com",
      name: body.name,
      resume_text: null,
      resume_updated_at: null,
    }))
    vi.spyOn(authService, "postChangePassword").mockRejectedValue(new Error("unused unless called"))
  })

  afterEach(() => {
    cleanup()
    vi.clearAllMocks()
  })

  it("loads profile and submits name change", async () => {
    const { SettingsPage } = await import("@/components/settings/settings-page")
    const user = userEvent.setup()
    render(
      <Shell>
        <SettingsPage />
      </Shell>,
    )

    await waitFor(() => {
      const el = document.getElementById("settings-name") as HTMLInputElement | null
      expect(el).not.toBeNull()
      expect(el?.value).toBe("Jane")
    })

    await user.clear(document.getElementById("settings-name") as HTMLInputElement)
    await user.type(document.getElementById("settings-name") as HTMLInputElement, "Janet")
    await user.click(screen.getByRole("button", { name: /save name/i }))

    await waitFor(() => {
      expect(profileService.patchProfileName).toHaveBeenCalledWith("fake-token", { name: "Janet" })
    })
    await waitFor(() => {
      expect(screen.getByText(/display name saved/i)).toBeTruthy()
    })
    expect(patchUser).toHaveBeenCalledWith({ name: "Janet" })
  })

  it("validates password mismatch before calling API", async () => {
    const { SettingsPage } = await import("@/components/settings/settings-page")
    const user = userEvent.setup()

    render(
      <Shell>
        <SettingsPage />
      </Shell>,
    )

    await waitFor(() => {
      expect(document.getElementById("settings-name")).toBeTruthy()
    })

    await user.type(screen.getByLabelText(/^current password$/i), "currentpass")
    await user.type(screen.getByLabelText(/^new password$/i), "newpass999")
    await user.type(screen.getByLabelText(/confirm new password/i), "newpass111")
    await user.click(screen.getByRole("button", { name: /change password/i }))
    expect(screen.getByText(/do not match/i)).toBeTruthy()
    expect(authService.postChangePassword).not.toHaveBeenCalled()
  })
})
