import { cleanup, render, screen } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { afterEach, describe, expect, it, vi } from "vitest"

import { ResumeWizardTabs } from "./resume-wizard-tabs"

afterEach(() => cleanup())

describe("ResumeWizardTabs", () => {
  it("exposes a horizontal tablist", () => {
    render(<ResumeWizardTabs currentStep={1} canAccessStep2={false} onSelectStep={vi.fn()} />)
    const list = screen.getByRole("tablist")
    expect(list.getAttribute("aria-orientation")).toBe("horizontal")
  })

  it("uses stable tab ids for assistive flows", () => {
    render(<ResumeWizardTabs currentStep={2} canAccessStep2={true} onSelectStep={vi.fn()} />)
    expect(document.getElementById("wizard-tab-1")).not.toBeNull()
    expect(document.getElementById("wizard-tab-2")).not.toBeNull()
  })

  it("allows selecting tailoring tab when unlocked", async () => {
    const spy = vi.fn()
    render(<ResumeWizardTabs currentStep={1} canAccessStep2={true} onSelectStep={spy} />)
    await userEvent.click(screen.getByRole("tab", { name: /step 2\. tailoring/i }))
    expect(spy).toHaveBeenCalledWith(2)
  })

  it("disables tailoring tab until Step1 unlocks", async () => {
    const spy = vi.fn()
    render(<ResumeWizardTabs currentStep={1} canAccessStep2={false} onSelectStep={spy} />)
    const tabTwo = screen.getByRole("tab", { name: /step 2\. tailoring/i })
    expect((tabTwo as HTMLButtonElement).disabled).toBe(true)
    expect(tabTwo.getAttribute("aria-describedby")).toBe("wizard-step2-help")
    await userEvent.click(tabTwo)
    expect(spy).not.toHaveBeenCalled()
  })

  it("shows step 2 help until tailoring unlocks", () => {
    render(<ResumeWizardTabs currentStep={1} canAccessStep2={false} onSelectStep={vi.fn()} />)
    expect(document.getElementById("wizard-step2-help")).not.toBeNull()
  })
})
