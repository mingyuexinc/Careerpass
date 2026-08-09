import { render, screen } from "@testing-library/react";
import { JobsPage } from "../pages/hr/JobsPage";
import { useWorkspaceStore } from "../stores/workspace-store";

describe("JobsPage", () => {
  it("combines the JD identity and job summary in one upload card", () => {
    useWorkspaceStore.setState({
      initialized: true,
      loading: false,
      error: null,
      jobs: [
        {
          id: "job-001",
          fileName: "frontend-job.pdf",
          uploadedAt: "2026-08-09T09:30:00+08:00",
          version: 2,
          title: "AI 产品前端工程师",
          company: "界面实验室",
          location: "深圳",
          salary: "16-28K",
          summary: "负责 AI 应用前端界面的设计实现。",
          uploaded: true,
        },
      ],
      currentJob: {
        id: "job-001",
        fileName: "frontend-job.pdf",
        uploadedAt: "2026-08-09T09:30:00+08:00",
        version: 2,
        title: "AI 产品前端工程师",
        company: "界面实验室",
        location: "深圳",
        salary: "16-28K",
        summary: "负责 AI 应用前端界面的设计实现。",
        uploaded: true,
      },
    });

    render(<JobsPage />);

    expect(screen.getByText("JD")).toBeInTheDocument();
    expect(screen.queryByText("当前版本范围")).not.toBeInTheDocument();
    expect(screen.queryByText("不做复杂管理")).not.toBeInTheDocument();
    expect(screen.queryByText("frontend-job.pdf")).not.toBeInTheDocument();
    expect(screen.getByText(/版本 2 · 上传于/)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "删除 岗位 JD" })).toBeInTheDocument();
    expect(
      screen.getByText("AI 产品前端工程师 · 界面实验室 · 深圳 · 16-28K"),
    ).toBeInTheDocument();
    expect(document.querySelectorAll(".file-info-card")).toHaveLength(1);
    expect(document.querySelector(".file-list-scroll")).toBeInTheDocument();
    expect(
      (document.querySelector('input[type="file"]') as HTMLInputElement).multiple,
    ).toBe(true);
  });
});
