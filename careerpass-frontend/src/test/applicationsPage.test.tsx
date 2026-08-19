import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { ApplicationsPage } from "../pages/hr/ApplicationsPage";
import { useAuthStore } from "../stores/auth-store";
import { useWorkspaceStore } from "../stores/workspace-store";

const hrApplication = {
  id: "application-001",
  jobId: "job-001",
  jobTitle: "AI 应用开发工程师",
  companyName: "示例公司",
  candidateName: "候选人甲",
  status: "screening" as const,
};

describe("HR ApplicationsPage", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    useAuthStore.getState().signOut();
    useWorkspaceStore.setState({
      initialized: true,
      loading: false,
      error: null,
      hrApplications: [hrApplication],
    });
  });

  it("shows only the four HR projection fields and only forward choices", () => {
    render(<ApplicationsPage />);

    expect(screen.getByRole("heading", { name: "AI 应用开发工程师" })).toBeInTheDocument();
    expect(screen.getByText("示例公司 · 候选人甲")).toBeInTheDocument();
    expect(screen.getAllByText("初筛中").length).toBeGreaterThan(0);
    expect(screen.queryByText(/匹配|推荐|简历|联系方式|沟通/)).not.toBeInTheDocument();

    const select = screen.getByRole("combobox");
    expect(select).toHaveValue("screening");
    expect(screen.queryByRole("option", { name: "已投递" })).not.toBeInTheDocument();
    expect(screen.getByRole("option", { name: "笔试" })).toBeInTheDocument();
    expect(screen.getByRole("option", { name: "流程终止" })).toBeInTheDocument();
  });

  it("updates an HR application through the real API branch", async () => {
    useAuthStore.setState({
      user: { id: "hr-001", role: "hr", displayName: "Mia Wang", title: "HR 工作台" },
      accessToken: "hr-token",
    });
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(JSON.stringify({ code: 200, msg: "success", data: { jobs: [], total: 0 } }), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      }),
    );
    vi.mocked(globalThis.fetch).mockImplementation(async (input, init) => {
      const url = String(input);
      if (url.endsWith("/jobs/hr/current")) {
        return new Response(
          JSON.stringify({ code: 200, msg: "current HR jobs", data: { jobs: [], total: 0 } }),
          { status: 200, headers: { "Content-Type": "application/json" } },
        );
      }
      if (url.endsWith("/applications/hr/current") && !init?.method) {
        return new Response(
          JSON.stringify({
            code: 200,
            msg: "current HR applications",
            data: {
              applications: [
                {
                  id: hrApplication.id,
                  job_id: hrApplication.jobId,
                  job_title: hrApplication.jobTitle,
                  company_name: hrApplication.companyName,
                  candidate_name: hrApplication.candidateName,
                  status: hrApplication.status,
                },
              ],
              total: 1,
            },
          }),
          { status: 200, headers: { "Content-Type": "application/json" } },
        );
      }
      return new Response(
        JSON.stringify({
          code: 200,
          msg: "success",
          data: {
            id: hrApplication.id,
            job_id: hrApplication.jobId,
            job_title: hrApplication.jobTitle,
            company_name: hrApplication.companyName,
            candidate_name: hrApplication.candidateName,
            status: "written_test",
          },
        }),
        { status: 200, headers: { "Content-Type": "application/json" } },
      );
    });
    render(<ApplicationsPage />);

    const select = await screen.findByRole("combobox");
    fireEvent.change(select, { target: { value: "written_test" } });

    await waitFor(() => expect(useWorkspaceStore.getState().hrApplications[0].status).toBe("written_test"));
    expect(screen.getByText("投递进度已更新。")).toBeInTheDocument();
  });

  it("disables controls for terminal applications", () => {
    useWorkspaceStore.setState({
      hrApplications: [{ ...hrApplication, status: "terminated" }],
    });
    render(<ApplicationsPage />);

    expect(screen.getByRole("combobox")).toBeDisabled();
    expect(screen.getByRole("button", { name: "标记流程终止" })).toBeDisabled();
    expect(screen.getAllByText("流程终止").length).toBeGreaterThan(0);
  });
});
