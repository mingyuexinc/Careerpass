import {
  listCurrentHrApplications,
  updateCurrentHrApplicationStatus,
} from "../api/applicationApi";

describe("HR application API", () => {
  afterEach(() => vi.restoreAllMocks());

  it("maps the restricted HR projection without candidate-side fields", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(
        JSON.stringify({
          code: 0,
          msg: "success",
          data: {
            total: 1,
            applications: [
              {
                id: "application-001",
                job_id: "job-001",
                job_title: "AI 应用开发工程师",
                company_name: "示例公司",
                candidate_name: "Alex Chen",
                status: "submitted",
              },
            ],
          },
        }),
        { status: 200, headers: { "Content-Type": "application/json" } },
      ),
    );

    await expect(listCurrentHrApplications("hr-token")).resolves.toEqual([
      {
        id: "application-001",
        jobId: "job-001",
        jobTitle: "AI 应用开发工程师",
        companyName: "示例公司",
        candidateName: "Alex Chen",
        status: "submitted",
      },
    ]);
    expect(fetch).toHaveBeenCalledWith(
      "/api/v1/applications/hr/current",
      expect.objectContaining({
        headers: { Authorization: "Bearer hr-token" },
      }),
    );
  });

  it("sends a status patch and maps conflict responses to safe feedback", async () => {
    const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValueOnce(
      new Response(
        JSON.stringify({
          code: 409,
          msg: "application status transition is not allowed",
          data: null,
        }),
        { status: 409, headers: { "Content-Type": "application/json" } },
      ),
    );

    await expect(
      updateCurrentHrApplicationStatus("application-001", "submitted", "hr-token"),
    ).rejects.toMatchObject({
      status: 409,
      message: "该投递状态不能回退或修改终态。",
    });
    expect(fetchMock).toHaveBeenCalledWith(
      "/api/v1/applications/application-001/status",
      expect.objectContaining({
        method: "PATCH",
        body: JSON.stringify({ status: "submitted" }),
      }),
    );
  });
});
