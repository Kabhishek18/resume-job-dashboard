import { cleanup, render, screen, waitFor } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { afterEach, describe, expect, it } from "vitest"

import { THEME_STORAGE_KEY, ThemeProvider, useThemeChoice } from "@/components/theme-provider"

function ThemeConsumer() {
  const { mode, setMode } = useThemeChoice()
  return (
    <div>
      <span data-testid="mode">{mode}</span>
      <button type="button" onClick={() => setMode("dark")}>
        force-dark
      </button>
      <button type="button" onClick={() => setMode("light")}>
        force-light
      </button>
    </div>
  )
}

describe("ThemeProvider", () => {
  afterEach(() => {
    cleanup()
    localStorage.removeItem(THEME_STORAGE_KEY)
    document.documentElement.classList.remove("dark")
  })

  it("persists dark preference to localStorage", async () => {
    const user = userEvent.setup()
    render(
      <ThemeProvider>
        <ThemeConsumer />
      </ThemeProvider>,
    )
    await waitFor(() => {
      expect(screen.getByTestId("mode").textContent).toBeTruthy()
    })
    await user.click(screen.getByRole("button", { name: /force-dark/i }))
    expect(localStorage.getItem(THEME_STORAGE_KEY)).toBe("dark")
    expect(document.documentElement.classList.contains("dark")).toBe(true)
    await user.click(screen.getByRole("button", { name: /force-light/i }))
    expect(localStorage.getItem(THEME_STORAGE_KEY)).toBe("light")
    expect(document.documentElement.classList.contains("dark")).toBe(false)
  })
})
