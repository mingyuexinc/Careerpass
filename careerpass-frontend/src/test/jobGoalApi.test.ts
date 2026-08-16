import { getCurrentJobGoal, saveCurrentJobGoal } from "../api/jobGoalApi";

describe("S-06 job goal API", () => {
  beforeEach(() => vi.restoreAllMocks());

  it("maps the current goal response to the frontend type", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(
        JSON.stringify({
          code: 200,
          msg: "success",
          data: {
            goal: {
              id: "goal-001",
              offer_target: 3,
              title: "后端开发工程师",
              filters: "优先 AI",
              status: "active",
              created_at: "2026-08-16T01:00:00Z",
              updated_at: "2026-08-16T01:01:00Z",
            },
          },
        }),
        { status: 200, headers: { "Content-Type": "application/json" } },
      ),
    );

    await expect(getCurrentJobGoal("candidate-token")).resolves.toEqual({
      id: "goal-001",
      offerTarget: 3,
      title: "后端开发工程师",
      filters: "优先 AI",
      status: "active",
      createdAt: "2026-08-16T01:00:00Z",
      updatedAt: "2026-08-16T01:01:00Z",
    });
    expect(fetch).toHaveBeenCalledWith(
      "/api/v1/job_goals/current",
      expect.objectContaining({
        headers: { Authorization: "Bearer candidate-token" },
      }),
    );
  });

  it("sends snake_case fields through PUT and maps the saved goal", async () => {
    const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(
        JSON.stringify({
          code: 200,
          msg: "job goal saved",
          data: {
            goal: {
              id: "goal-001",
              offer_target: 2,
              title: "全栈开发工程师",
              filters: "",
              status: "active",
              created_at: "2026-08-16T01:00:00Z",
              updated_at: "2026-08-16T01:02:00Z",
            },
          },
        }),
        { status: 200, headers: { "Content-Type": "application/json" } },
      ),
    );

    await expect(
      saveCurrentJobGoal(
        { offerTarget: 2, title: "全栈开发工程师", filters: "" },
        "candidate-token",
      ),
    ).resolves.toMatchObject({ id: "goal-001", offerTarget: 2 });
    expect(fetchMock).toHaveBeenCalledWith(
      "/api/v1/job_goals/current",
      expect.objectContaining({
        method: "PUT",
        body: JSON.stringify({ offer_target: 2, title: "全栈开发工程师", filters: "" }),
      }),
    );
  });
});
