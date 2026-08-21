import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { JobsPage } from "../pages/hr/JobsPage";
import { useAuthStore } from "../stores/auth-store";
import { useWorkspaceStore } from "../stores/workspace-store";

describe("JobsPage", () => {
  beforeEach(() => {
    useAuthStore.setState({ user: null, accessToken: "hr-access-token", error: null });
    useWorkspaceStore.setState({
      initialized: false,
      loading: false,
      error: null,
      hrJobs: [],
      currentHrJob: null,
      hrApplications: [],
    });
    vi.restoreAllMocks();
  });

  it("uploads multiple files through the S-02 API and shows persisted file cards", async () => {
    useAuthStore.setState({
      user: {
        id: "hr-001",
        role: "hr",
        displayName: "Demo HR",
        title: "HR 工作台",
      },
    });
    const fetchMock = vi.spyOn(globalThis, "fetch").mockImplementation(async (input) => {
      const url = String(input);
      if (url.endsWith("/jobs")) {
        return new Response(
          JSON.stringify({
            code: 200,
            msg: "job upload processed",
            data: {
              results: [
                {
                  index: 1,
                  outcome: "created",
                  job_id: "job-002",
                  task_status: "queued",
                },
                {
                  index: 0,
                  outcome: "created",
                  job_id: "job-001",
                  task_status: "queued",
                },
              ],
            },
          }),
          { status: 200, headers: { "Content-Type": "application/json" } },
        );
      }
      if (url.endsWith("/jobs/hr/current")) {
        return new Response(
          JSON.stringify({
            code: 200,
            msg: "current HR jobs",
            data: {
              jobs: [
                {
                  id: "job-001",
                  file_name: "first-job.md",
                  job_title: "AI 应用开发工程师",
                  company_name: "示例科技",
                  created_at: "2026-08-19T00:00:00Z",
                  parse_status: "succeeded",
                },
                {
                  id: "job-002",
                  file_name: "second-job.md",
                  job_title: "智能平台工程师",
                  company_name: "示例科技",
                  created_at: "2026-08-19T00:01:00Z",
                  parse_status: "succeeded",
                },
              ],
              total: 2,
            },
          }),
          { status: 200, headers: { "Content-Type": "application/json" } },
        );
      }
      if (url.endsWith("/applications/hr/current")) {
        return new Response(
          JSON.stringify({
            code: 200,
            msg: "current HR applications",
            data: { applications: [], total: 0 },
          }),
          { status: 200, headers: { "Content-Type": "application/json" } },
        );
      }
      throw new Error(`unexpected request: ${url}`);
    });
    render(<JobsPage />);

    const input = document.querySelector('input[type="file"]') as HTMLInputElement;
    const files = [
      new File(["# first job"], "first-job.md", { type: "text/markdown" }),
      new File(["# second job"], "second-job.md", { type: "text/markdown" }),
    ];
    expect(input.multiple).toBe(true);
    expect(input.accept).toBe(".md");
    fireEvent.change(input, { target: { files } });

    await waitFor(() => expect(screen.getByText("first-job.md")).toBeInTheDocument());
    const uploadCall = fetchMock.mock.calls.find(([input]) =>
      String(input).endsWith("/jobs"),
    );
    expect(uploadCall).toBeDefined();
    const [url, request] = uploadCall!;
    expect(url).toBe("/api/v1/jobs");
    expect(request).toEqual(
      expect.objectContaining({
        method: "POST",
        headers: { Authorization: "Bearer hr-access-token" },
      }),
    );
    expect(request?.body).toBeInstanceOf(FormData);
    expect((request?.body as FormData).getAll("files")).toHaveLength(2);
    expect(screen.getByRole("region", { name: "已上传岗位列表" })).toHaveClass(
      "file-list-scroll",
    );
    expect(screen.getByText("second-job.md")).toBeInTheDocument();
    expect(screen.getByText("2 份已保存")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "确认上传" })).not.toBeInTheDocument();

    expect(screen.queryByText(/AI 产品前端工程师/)).not.toBeInTheDocument();
    expect(screen.queryByText(/界面实验室/)).not.toBeInTheDocument();
    expect(screen.getAllByRole("button", { name: /删除/ })).toHaveLength(2);
  });

  it("keeps restored HR jobs inside the JD upload card", async () => {
    useAuthStore.setState({
      user: {
        id: "hr-001",
        role: "hr",
        displayName: "Demo HR",
        title: "HR 工作台",
      },
      accessToken: "hr-access-token",
    });
    vi.spyOn(globalThis, "fetch").mockImplementation(async (input) => {
      const url = String(input);
      if (url.endsWith("/jobs/hr/current")) {
        return new Response(
          JSON.stringify({
            code: 200,
            msg: "current HR jobs",
            data: {
              jobs: [
                {
                  id: "job-restored",
                  file_name: "restored-job.md",
                  job_title: "AI 应用开发工程师",
                  company_name: "示例科技",
                  created_at: "2026-08-19T00:00:00Z",
                  parse_status: "succeeded",
                },
              ],
              total: 1,
            },
          }),
          { status: 200, headers: { "Content-Type": "application/json" } },
        );
      }
      if (url.endsWith("/applications/hr/current")) {
        return new Response(
          JSON.stringify({
            code: 200,
            msg: "current HR applications",
            data: { applications: [], total: 0 },
          }),
          { status: 200, headers: { "Content-Type": "application/json" } },
        );
      }
      throw new Error(`unexpected request: ${url}`);
    });

    render(<JobsPage />);

    const uploadPanel = screen
      .getByRole("heading", { name: "岗位 JD 上传" })
      .closest("article");
    await waitFor(() => expect(screen.getByText("restored-job.md")).toBeInTheDocument());
    const jobList = screen.getByRole("region", { name: "已上传岗位列表" });
    expect(uploadPanel).toContainElement(jobList);
    expect(jobList).toContainElement(screen.getByText("restored-job.md"));
    expect(jobList).toContainElement(screen.getByText(/上传于/));
    expect(jobList).toContainElement(screen.getByText("MD"));
    expect(screen.getByText("1 份已保存")).toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: "已上传岗位" })).not.toBeInTheDocument();
    expect(screen.queryByRole("region", { name: "已保存岗位" })).not.toBeInTheDocument();
  });

  it("maps a failed Contract result to 上传失败", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(
        JSON.stringify({
          code: 200,
          msg: "job upload processed",
          data: {
            results: [{ index: 0, outcome: "failed", error_code: "invalid_file" }],
          },
        }),
        { status: 200, headers: { "Content-Type": "application/json" } },
      ),
    );
    render(<JobsPage />);
    const input = document.querySelector('input[type="file"]') as HTMLInputElement;
    fireEvent.change(input, {
      target: { files: [new File(["# bad"], "bad.md", { type: "text/markdown" })] },
    });

    await waitFor(() =>
      expect(
        screen.getByText("bad.md 上传失败，请检查文件格式或大小。"),
      ).toBeInTheDocument(),
    );
  });

  it("disables file selection while the automatic upload is pending", async () => {
    let resolveUpload!: (response: Response) => void;
    vi.spyOn(globalThis, "fetch").mockReturnValue(
      new Promise((resolve) => {
        resolveUpload = resolve;
      }),
    );
    render(<JobsPage />);
    const input = document.querySelector('input[type="file"]') as HTMLInputElement;
    fireEvent.change(input, {
      target: {
        files: [new File(["# pending"], "pending.md", { type: "text/markdown" })],
      },
    });

    await waitFor(() => expect(input).toBeDisabled());
    expect(screen.getByRole("button", { name: "当前不可替换" })).toBeDisabled();
    resolveUpload(
      new Response(
        JSON.stringify({ code: 200, msg: "job upload processed", data: { results: [] } }),
        { status: 200, headers: { "Content-Type": "application/json" } },
      ),
    );
    await waitFor(() => expect(input).not.toBeDisabled());
  });

  it("deletes a parsed job immediately without a confirmation dialog", async () => {
    useAuthStore.setState({
      user: {
        id: "hr-001",
        role: "hr",
        displayName: "Demo HR",
        title: "HR 工作台",
      },
    });
    const fetchMock = vi.spyOn(globalThis, "fetch").mockImplementation(async (input, init) => {
      const url = String(input);
      if (url.endsWith("/jobs/hr/current")) {
        return new Response(
          JSON.stringify({
            code: 200,
            msg: "current HR jobs",
            data: {
              jobs: init?.method === "DELETE" ? [] : [
                {
                  id: "job-delete-001",
                  file_name: "001-天创机器人-Agent开发工程师.md",
                  job_title: "Agent 开发工程师",
                  company_name: "天创机器人",
                  created_at: "2026-08-19T00:00:00Z",
                  parse_status: "succeeded",
                  match_started: false,
                },
              ],
              total: init?.method === "DELETE" ? 0 : 1,
            },
          }),
          { status: 200, headers: { "Content-Type": "application/json" } },
        );
      }
      if (url.endsWith("/applications/hr/current")) {
        return new Response(
          JSON.stringify({ code: 200, msg: "current HR applications", data: { applications: [], total: 0 } }),
          { status: 200, headers: { "Content-Type": "application/json" } },
        );
      }
      if (url.endsWith("/jobs/job-delete-001") && init?.method === "DELETE") {
        return new Response(
          JSON.stringify({
            code: 200,
            msg: "success",
            data: {
              resource_type: "job",
              resource_id: "job-delete-001",
              deleted: true,
            },
          }),
          { status: 200, headers: { "Content-Type": "application/json" } },
        );
      }
      throw new Error(`unexpected request: ${url}`);
    });
    const confirmSpy = vi.spyOn(window, "confirm");
    render(<JobsPage />);

    await waitFor(() => expect(screen.getByText("001-天创机器人-Agent开发工程师.md")).toBeInTheDocument());
    fireEvent.click(screen.getByRole("button", { name: /删除 001-天创机器人-Agent开发工程师\.md/ }));

    await waitFor(() => expect(screen.queryByText("001-天创机器人-Agent开发工程师.md")).not.toBeInTheDocument());
    expect(confirmSpy).not.toHaveBeenCalled();
    expect(
      fetchMock.mock.calls.some(
        ([input, init]) => String(input).endsWith("/jobs/job-delete-001") && init?.method === "DELETE",
      ),
    ).toBe(true);
  });
});
