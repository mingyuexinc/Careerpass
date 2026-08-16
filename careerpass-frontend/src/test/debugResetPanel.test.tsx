import { act, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter, useLocation } from "react-router-dom";
import { DebugResetPanel } from "../components/DebugResetPanel";
import { useAuthStore } from "../stores/auth-store";
import { useWorkspaceStore } from "../stores/workspace-store";

function LocationProbe() {
  return <span data-testid="location">{useLocation().pathname}</span>;
}

function renderPanel() {
  return render(
    <MemoryRouter initialEntries={["/candidate"]}>
      <DebugResetPanel />
      <LocationProbe />
    </MemoryRouter>,
  );
}

describe("DebugResetPanel", () => {
  beforeEach(async () => {
    vi.stubEnv("VITE_DEBUG_RESET_ENABLED", "true");
    useAuthStore.setState({
      user: {
        id: "candidate-001",
        role: "candidate",
        displayName: "Demo Candidate",
        title: "求职者工作台",
      },
      accessToken: "candidate-token",
      error: null,
      submitting: false,
    });
    await act(async () => {
      await useWorkspaceStore.getState().clearLocalState();
    });
  });

  afterEach(() => {
    act(() => useAuthStore.getState().signOut());
    vi.unstubAllEnvs();
    vi.restoreAllMocks();
  });

  it("resets the current account and navigates to login", async () => {
    const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(
        JSON.stringify({
          code: 200,
          msg: "debug data reset",
          data: { reset: true, scope: "current_account" },
        }),
        { status: 200, headers: { "Content-Type": "application/json" } },
      ),
    );

    renderPanel();
    fireEvent.click(screen.getByRole("button", { name: "一键恢复初始状态" }));

    await waitFor(() =>
      expect(screen.getByTestId("location")).toHaveTextContent("/login"),
    );
    expect(fetchMock).toHaveBeenCalledWith(
      "/api/v1/debug/reset/current-account",
      expect.objectContaining({ method: "POST" }),
    );
    expect(useAuthStore.getState().accessToken).toBeNull();
  });

  it("keeps the current session when reset is rejected", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(JSON.stringify({ code: 409, msg: "busy", data: null }), {
        status: 409,
        headers: { "Content-Type": "application/json" },
      }),
    );

    renderPanel();
    fireEvent.click(screen.getByRole("button", { name: "一键恢复初始状态" }));

    expect(await screen.findByRole("alert")).toHaveTextContent("任务处理中");
    expect(useAuthStore.getState().accessToken).toBe("candidate-token");
    expect(screen.getByTestId("location")).toHaveTextContent("/candidate");
  });

  it("is hidden when the frontend debug flag is disabled", () => {
    vi.stubEnv("VITE_DEBUG_RESET_ENABLED", "false");
    renderPanel();
    expect(
      screen.queryByRole("button", { name: "一键恢复初始状态" }),
    ).not.toBeInTheDocument();
  });
});
