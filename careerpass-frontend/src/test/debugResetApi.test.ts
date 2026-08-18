import { resetCurrentAccount } from "../api/debugResetApi";

describe("S-DBG reset API", () => {
  afterEach(() => vi.restoreAllMocks());

  it("posts without a client-owned account identifier", async () => {
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

    await expect(resetCurrentAccount("token")).resolves.toEqual({
      reset: true,
      scope: "current_account",
    });
    expect(fetchMock).toHaveBeenCalledWith(
      "/api/v1/debug/reset/current-account",
      expect.objectContaining({
        method: "POST",
        headers: { Authorization: "Bearer token" },
      }),
    );
  });

  it("maps an active-task conflict to a user-safe message", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(
        JSON.stringify({
          code: 409,
          msg: "reset is unavailable while account tasks are running",
          data: null,
        }),
        {
          status: 409,
          headers: { "Content-Type": "application/json" },
        },
      ),
    );

    await expect(resetCurrentAccount("token")).rejects.toThrow("任务处理中");
  });

  it("does not describe dependent data as an active task", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(
        JSON.stringify({
          code: 409,
          msg: "account reset is blocked by dependent data",
          data: null,
        }),
        { status: 409, headers: { "Content-Type": "application/json" } },
      ),
    );

    await expect(resetCurrentAccount("token")).rejects.toThrow("历史联调数据");
    await expect(resetCurrentAccount("token")).rejects.not.toThrow("任务处理中");
  });
});
