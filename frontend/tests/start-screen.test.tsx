// Phase 5 failure case: starting an audit with the API down shows the exact message.
import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { API_DOWN_MESSAGE, ApiUnreachableError } from "@/lib/data/errors";

vi.mock("next/navigation", () => ({ useRouter: () => ({ push: vi.fn() }), useSearchParams: () => new URLSearchParams() }));
vi.mock("@/lib/data", async () => {
  const errors = await vi.importActual<typeof import("@/lib/data/errors")>("@/lib/data/errors");
  return {
    ...errors,
    data: {
      mode: "live",
      getConfig: () => Promise.resolve({ tester_model: "t", skeptic_model: "s", variants: ["base"], spend_usd: 0,
        project_cap_usd: 9.5, run_cap_usd: 1, busy: false }),
      listAudits: () => Promise.resolve([]),
      startAudit: () => Promise.reject(new errors.ApiUnreachableError()),
    },
  };
});

describe("Start screen", () => {
  it("shows the API-down message when starting fails to connect", async () => {
    const { StartScreen } = await import("@/components/StartScreen");
    render(<StartScreen />);
    fireEvent.click(await screen.findByRole("button", { name: "Start audit" }));
    expect((await screen.findByRole("alert")).textContent).toBe(API_DOWN_MESSAGE);
    expect(new ApiUnreachableError().message).toBe(API_DOWN_MESSAGE);
  });
});
