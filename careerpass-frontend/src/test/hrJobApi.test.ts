import { listCurrentHrJobs } from "../api/hrJobApi";

describe("HR Job API", () => {
  afterEach(() => vi.restoreAllMocks());

  it("maps the minimal persisted HR Job projection", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(
        JSON.stringify({
          code: 200,
          msg: "current HR jobs",
          data: {
            total: 1,
            jobs: [
              {
                id: "job-001",
                file_name: "001-ai-engineer.md",
                job_title: "AI 应用开发工程师",
                company_name: "示例公司",
                created_at: "2026-08-19T00:00:00Z",
                parse_status: "succeeded",
              },
            ],
          },
        }),
        { status: 200, headers: { "Content-Type": "application/json" } },
      ),
    );

    await expect(listCurrentHrJobs("hr-token")).resolves.toEqual([
      {
        id: "job-001",
        fileName: "001-ai-engineer.md",
        jobTitle: "AI 应用开发工程师",
        companyName: "示例公司",
        createdAt: "2026-08-19T00:00:00Z",
        parseStatus: "succeeded",
      },
    ]);
    expect(fetch).toHaveBeenCalledWith(
      "/api/v1/jobs/hr/current",
      expect.objectContaining({
        headers: { Authorization: "Bearer hr-token" },
      }),
    );
  });

  it("turns an unauthorized response into a typed request error", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(
        JSON.stringify({ code: 401, msg: "authentication required", data: null }),
        { status: 401, headers: { "Content-Type": "application/json" } },
      ),
    );

    await expect(listCurrentHrJobs("expired-token")).rejects.toMatchObject({
      status: 401,
      message: "authentication required",
    });
  });
});
