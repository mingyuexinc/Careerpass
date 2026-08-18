import { useWorkspaceStore } from "../stores/workspace-store";
import { useAuthStore } from "../stores/auth-store";

describe("workspace upload loading scopes", () => {
  beforeEach(async () => {
    await useWorkspaceStore.getState().resetData();
    useWorkspaceStore.setState({
      initialized: true,
      loading: false,
      resumeLoading: false,
      supportingDocumentsLoading: false,
      error: null,
    });
  });

  it("keeps resume controls independent while supporting documents upload", async () => {
    const upload = useWorkspaceStore
      .getState()
      .uploadDocuments([new File(["portfolio"], "portfolio.pdf")]);

    expect(useWorkspaceStore.getState().supportingDocumentsLoading).toBe(true);
    expect(useWorkspaceStore.getState().resumeLoading).toBe(false);

    await upload;

    expect(useWorkspaceStore.getState().supportingDocumentsLoading).toBe(false);
    expect(useWorkspaceStore.getState().resumeLoading).toBe(false);
  });

  it("keeps supporting document controls independent while resume upload runs", async () => {
    const upload = useWorkspaceStore
      .getState()
      .uploadResume(new File(["resume"], "resume.pdf"));

    expect(useWorkspaceStore.getState().resumeLoading).toBe(true);
    expect(useWorkspaceStore.getState().supportingDocumentsLoading).toBe(false);

    await upload;

    expect(useWorkspaceStore.getState().resumeLoading).toBe(false);
    expect(useWorkspaceStore.getState().supportingDocumentsLoading).toBe(false);
  });

  it("does not call candidate APIs while refreshing an authenticated HR workspace", async () => {
    const fetchMock = vi.spyOn(globalThis, "fetch");
    useAuthStore.setState({
      user: {
        id: "hr-001",
        role: "hr",
        displayName: "Demo HR",
        title: "HR 工作台",
      },
      accessToken: "hr-token",
      error: null,
      submitting: false,
    });

    await useWorkspaceStore.getState().refresh();

    expect(fetchMock).not.toHaveBeenCalled();
    expect(useWorkspaceStore.getState().initialized).toBe(true);
    useAuthStore.getState().signOut();
    fetchMock.mockRestore();
  });

  it("preserves the real resume when saving a real job goal", async () => {
    const resume = {
      id: "resume-real-001",
      fileName: "resume.pdf",
      uploadedAt: "2026-08-18T00:00:00Z",
      parseStatus: "succeeded" as const,
      version: 1,
    };
    const goal = {
      id: "goal-real-001",
      offerTarget: 1,
      title: "AI 应用开发工程师",
      filters: "",
      status: "active" as const,
      createdAt: "2026-08-18T00:01:00Z",
      updatedAt: "2026-08-18T00:01:00Z",
    };
    const goalResponse = {
      id: goal.id,
      offer_target: goal.offerTarget,
      title: goal.title,
      filters: goal.filters,
      status: goal.status,
      created_at: goal.createdAt,
      updated_at: goal.updatedAt,
    };
    useAuthStore.setState({
      user: {
        id: "candidate-001",
        role: "candidate",
        displayName: "Demo Candidate",
        title: "求职者工作台",
      },
      accessToken: "candidate-token",
      error: null,
      submitting: false,
    });
    useWorkspaceStore.setState({
      resume,
      jobGoal: null,
      agentStatus: "not_started",
      agentRunCanStart: false,
    });
    const fetchMock = vi.spyOn(globalThis, "fetch").mockImplementation(async (input, init) => {
      const url = String(input);
      if (url.endsWith("/job_goals/current") && init?.method === "PUT") {
        return new Response(
          JSON.stringify({ code: 200, msg: "job goal saved", data: { goal: goalResponse } }),
          { status: 200, headers: { "Content-Type": "application/json" } },
        );
      }
      if (url.endsWith("/agent_runs/current")) {
        return new Response(
          JSON.stringify({
            code: 200,
            msg: "success",
            data: { state: "not_started", can_start: true, run: null },
          }),
          { status: 200, headers: { "Content-Type": "application/json" } },
        );
      }
      throw new Error(`unexpected request: ${url}`);
    });

    await useWorkspaceStore.getState().saveGoal({
      offerTarget: 1,
      title: goal.title,
      filters: goal.filters,
    });

    expect(useWorkspaceStore.getState().resume).toEqual(resume);
    expect(useWorkspaceStore.getState().jobGoal).toEqual(goal);
    expect(fetchMock).toHaveBeenCalledTimes(2);
    fetchMock.mockRestore();
    useAuthStore.getState().signOut();
  });
});
