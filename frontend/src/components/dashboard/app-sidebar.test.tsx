import type { ReactElement } from "react"
import { cleanup, render, screen } from "@testing-library/react"
import { afterEach, describe, expect, it, vi } from "vitest"

import { AppSidebar } from "@/components/dashboard/app-sidebar"
import { SidebarProvider } from "@/components/ui/sidebar"

vi.mock("next/navigation", () => ({
  usePathname: () => "/dashboard",
}))

function shell(ui: ReactElement) {
  return <SidebarProvider>{ui}</SidebarProvider>
}

describe("AppSidebar", () => {
  afterEach(() => cleanup())

  it("does not render Home in navigation", () => {
    render(shell(<AppSidebar />))
    expect(screen.queryByText("Home")).toBeNull()
    expect(screen.getByText("Dashboard")).toBeTruthy()
    expect(screen.getByText("Jobs")).toBeTruthy()
    expect(screen.getByText("Resume")).toBeTruthy()
    expect(screen.getByText("Settings")).toBeTruthy()
  })
})
