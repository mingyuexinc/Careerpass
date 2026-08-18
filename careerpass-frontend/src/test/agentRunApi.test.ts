import { getCurrentAgentRun, startCurrentAgentRun } from "../api/agentRunApi";

describe("S-07 Agent run API", () => {
  beforeEach(() => vi.restoreAllMocks());

  it("maps a safe current status projection", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(JSON.stringify({ code: 200, msg: "success", data: { state: "not_started", can_start: true } }), { status: 200 }),
    );
    await expect(getCurrentAgentRun("candidate-token")).resolves.toEqual({
      state: "not_started",
      canStart: true,
      run: null,
    });
  });

  it("starts without sending client resource identifiers", async () => {
    const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(JSON.stringify({ code: 200, msg: "success", data: { run: { id: "run-001", status: "running", started_at: "2026-08-17T00:00:00Z" } } }), { status: 200 }),
    );
    await expect(startCurrentAgentRun("candidate-token")).resolves.toEqual({
      id: "run-001",
      status: "running",
      startedAt: "2026-08-17T00:00:00Z",
      finishedAt: null,
      finishReason: null,
    });
    expect(fetchMock).toHaveBeenCalledWith(
      "/api/v1/agent_runs/current/start",
      expect.objectContaining({ method: "POST", body: "{}" }),
    );
  });
});
