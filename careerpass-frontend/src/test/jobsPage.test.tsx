import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { JobsPage } from "../pages/hr/JobsPage";
import { useAuthStore } from "../stores/auth-store";

describe("JobsPage", () => {
  beforeEach(() => {
    useAuthStore.setState({ accessToken: "hr-access-token", error: null });
    vi.restoreAllMocks();
  });

  it("uploads multiple files through the S-02 API and shows per-file success", async () => {
    const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(
        JSON.stringify({
          code: 200,
          msg: "job upload processed",
          data: {
            results: [
              { index: 1, outcome: "created", job_id: "job-002", task_status: "queued" },
              { index: 0, outcome: "created", job_id: "job-001", task_status: "queued" },
            ],
          },
        }),
        { status: 200, headers: { "Content-Type": "application/json" } },
      ),
    );
    render(<JobsPage />);

    const input = document.querySelector('input[type="file"]') as HTMLInputElement;
    const files = [
      new File(["# first job"], "first-job.md", { type: "text/markdown" }),
      new File(["# second job"], "second-job.md", { type: "text/markdown" }),
    ];
    expect(input.multiple).toBe(true);
    expect(input.accept).toBe(".md");
    fireEvent.change(input, { target: { files } });

    await waitFor(() => expect(screen.getAllByText("上传成功")).toHaveLength(4));
    expect(fetchMock).toHaveBeenCalledTimes(1);
    const [url, request] = fetchMock.mock.calls[0];
    expect(url).toBe("/api/v1/jobs");
    expect(request).toEqual(expect.objectContaining({
      method: "POST",
      headers: { Authorization: "Bearer hr-access-token" },
    }));
    expect(request?.body).toBeInstanceOf(FormData);
    expect((request?.body as FormData).getAll("files")).toHaveLength(2);
    const resultItems = screen.getAllByRole("listitem");
    expect(resultItems[0]).toHaveTextContent("first-job.md");
    expect(resultItems[1]).toHaveTextContent("second-job.md");
    expect(screen.getByRole("region", { name: "岗位 JD 上传结果" })).toHaveClass("file-list-scroll");
    expect(screen.queryByRole("button", { name: "确认上传" })).not.toBeInTheDocument();

    expect(screen.queryByText(/AI 产品前端工程师/)).not.toBeInTheDocument();
    expect(screen.queryByText(/界面实验室/)).not.toBeInTheDocument();
    expect(screen.queryByText(/版本/)).not.toBeInTheDocument();
    expect(screen.queryByText("解析中")).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /删除/ })).not.toBeInTheDocument();
  });

  it("maps a failed Contract result to 上传失败", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(
        JSON.stringify({
          code: 200,
          msg: "job upload processed",
          data: { results: [{ index: 0, outcome: "failed", error_code: "invalid_file" }] },
        }),
        { status: 200, headers: { "Content-Type": "application/json" } },
      ),
    );
    render(<JobsPage />);
    const input = document.querySelector('input[type="file"]') as HTMLInputElement;
    fireEvent.change(input, {
      target: { files: [new File(["# bad"], "bad.md", { type: "text/markdown" })] },
    });

    await waitFor(() => expect(screen.getAllByText("上传失败")).toHaveLength(2));
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
      target: { files: [new File(["# pending"], "pending.md", { type: "text/markdown" })] },
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
});
