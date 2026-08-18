import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter, Navigate, Route, Routes } from "react-router-dom";
import { JobGoalCreatePage } from "../pages/candidate/JobGoalCreatePage";
import { JobGoalPage } from "../pages/candidate/JobGoalPage";
import { JobGoalViewPage } from "../pages/candidate/JobGoalViewPage";
import { useWorkspaceStore } from "../stores/workspace-store";

vi.mock("../features/workspace/useWorkspaceRefresh", () => ({
  useWorkspaceRefresh: vi.fn(),
}));

const goal = {
  id: "goal-001",
  offerTarget: 3,
  title: "后端开发工程师",
  filters: "优先 AI 应用和数据产品",
  status: "active" as const,
  createdAt: "2026-08-16T01:00:00Z",
  updatedAt: "2026-08-16T01:01:00Z",
};

function renderGoalRoute(initialEntry: string) {
  return render(
    <MemoryRouter initialEntries={[initialEntry]}>
      <Routes>
        <Route path="/candidate/job-goal" element={<JobGoalPage />}>
          <Route index element={<Navigate to="create" replace />} />
          <Route path="create" element={<JobGoalCreatePage />} />
          <Route path="view" element={<JobGoalViewPage />} />
        </Route>
      </Routes>
    </MemoryRouter>,
  );
}

describe("S-07 job goal page split", () => {
  beforeEach(() => {
    useWorkspaceStore.setState({
      initialized: true,
      loading: false,
      error: null,
      jobGoal: goal,
      resume: {
        id: "resume-001",
        fileName: "resume.pdf",
        uploadedAt: "2026-08-16T00:00:00Z",
        parseStatus: "succeeded",
        version: 1,
      },
      agentStatus: "ready",
      agentRunCanStart: true,
      startAgent: vi.fn().mockResolvedValue(undefined),
      clearError: vi.fn(),
    });
  });

  it("redirects the legacy route to the creation subpage", async () => {
    renderGoalRoute("/candidate/job-goal");

    expect(
      await screen.findByRole("heading", { name: "求职目标配置" }),
    ).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "求职目标创建" })).toHaveClass("is-active");
    expect(screen.getByRole("link", { name: "求职目标查看" })).toBeInTheDocument();
  });

  it("keeps creation and viewing content on separate pages", () => {
    renderGoalRoute("/candidate/job-goal/create");

    expect(screen.getByRole("heading", { name: "求职目标配置" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "启动条件" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "启动求职 Agent" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "启动求职 Agent" })).toHaveTextContent("→");
    expect(
      screen.queryByRole("heading", { name: "已创建的求职目标" }),
    ).not.toBeInTheDocument();

    cleanup();
    renderGoalRoute("/candidate/job-goal/view");
    expect(screen.getByRole("heading", { name: "已创建的求职目标" })).toBeInTheDocument();
    expect(
      screen.queryByRole("textbox", { name: "目标岗位名称" }),
    ).not.toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: /创建求职目标|保存修改|启动求职 Agent/ }),
    ).not.toBeInTheDocument();
  });

  it("renders the current goal as one read-only list row", () => {
    renderGoalRoute("/candidate/job-goal/view");

    expect(screen.getByRole("list", { name: "求职目标记录列表" })).toBeInTheDocument();
    expect(screen.getAllByRole("listitem")).toHaveLength(1);
    expect(screen.getByText("后端开发工程师")).toBeInTheDocument();
    expect(screen.getByText("3 个")).toBeInTheDocument();
    expect(screen.getByText(/2026/)).toBeInTheDocument();
    expect(screen.queryByText("优先 AI 应用和数据产品")).not.toBeInTheDocument();
    expect(screen.queryByText("最近更新")).not.toBeInTheDocument();
    expect(document.querySelectorAll(".job-goal-record > *")).toHaveLength(3);
    expect(screen.getByText("1 条")).toBeInTheDocument();
  });

  it("shows an empty view with a link to creation", () => {
    useWorkspaceStore.setState({ jobGoal: null });
    renderGoalRoute("/candidate/job-goal/view");

    expect(screen.getByText("还没有求职目标")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "去创建求职目标" })).toHaveAttribute(
      "href",
      "/candidate/job-goal/create",
    );
  });

  it("keeps the start action disabled until the server-derived state is ready", () => {
    useWorkspaceStore.setState({ agentStatus: "not_started", agentRunCanStart: false });
    renderGoalRoute("/candidate/job-goal/create");

    expect(screen.getByRole("button", { name: "启动求职 Agent" })).toBeDisabled();
  });

  it("keeps the save action stable and restores focus after saving", async () => {
    let resolveSave!: () => void;
    const saveFinished = new Promise<void>((resolve) => {
      resolveSave = resolve;
    });
    const saveGoal = vi.fn(async () => {
      useWorkspaceStore.setState({ savingGoal: true });
      await saveFinished;
      useWorkspaceStore.setState({ jobGoal: goal, savingGoal: false });
    });
    useWorkspaceStore.setState({ jobGoal: null, saveGoal });
    renderGoalRoute("/candidate/job-goal/create");

    const saveButton = screen.getByRole("button", { name: "创建求职目标" });
    saveButton.focus();
    fireEvent.click(saveButton);

    expect(saveButton).toBeDisabled();
    expect(saveButton).toHaveTextContent("保存中…");
    expect(screen.getByRole("button", { name: "启动求职 Agent" })).toBeDisabled();

    resolveSave();
    await waitFor(() => expect(saveButton).toHaveTextContent("保存修改"));
    await waitFor(() => expect(saveButton).toHaveFocus());
    expect(saveGoal).toHaveBeenCalledTimes(1);
  });

  it("shows the locked success message after starting", async () => {
    const startAgent = vi.fn().mockImplementation(async () => {
      useWorkspaceStore.setState({ agentStatus: "running", agentRunCanStart: false });
    });
    useWorkspaceStore.setState({ startAgent });
    renderGoalRoute("/candidate/job-goal/create");

    fireEvent.click(screen.getByRole("button", { name: "启动求职 Agent" }));

    await waitFor(() =>
      expect(
        screen.getByText("求职目标已锁定，请前往求职进度查看本轮投递结果。"),
      ).toBeInTheDocument(),
    );
    expect(document.querySelector(".agent-state")).toHaveClass("running");
    expect(startAgent).toHaveBeenCalledTimes(1);
  });
});
