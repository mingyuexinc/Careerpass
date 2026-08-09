import { useWorkspaceStore } from "../stores/workspace-store";

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
});
