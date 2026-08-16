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
});
