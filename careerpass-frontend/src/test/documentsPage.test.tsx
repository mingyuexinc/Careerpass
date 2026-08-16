import { fireEvent, render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { DocumentsPage } from "../pages/candidate/DocumentsPage";
import { useAuthStore } from "../stores/auth-store";
import { useWorkspaceStore } from "../stores/workspace-store";

describe("DocumentsPage supporting document upload feedback", () => {
  beforeEach(async () => {
    useAuthStore.getState().signOut();
    await useWorkspaceStore.getState().resetData();
    useWorkspaceStore.setState({
      initialized: true,
      loading: false,
      error: null,
      supportingDocuments: [
        {
          id: "document-success",
          fileName: "portfolio.pdf",
          fileType: "pdf",
          uploadedAt: "2026-08-16T06:26:00.000Z",
          status: "success",
        },
      ],
      supportingDocumentUploads: [
        {
          fileName: "unsupported.docx",
          status: "failed",
          result: "failed",
          document: null,
          failureCode: "unsupported_file",
        },
      ],
    });
  });

  it("does not render historical failures from workspace state", () => {
    const { container } = render(
      <MemoryRouter>
        <DocumentsPage />
      </MemoryRouter>,
    );

    expect(screen.getByText("portfolio.pdf")).toBeInTheDocument();
    expect(
      screen.getByRole("region", { name: "其它求职资料成功上传列表" }),
    ).toBeInTheDocument();
    expect(container.querySelector(".file-upload-results")).not.toBeInTheDocument();
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
  });

  it("shows a transient batch error snackbar without a retry action", async () => {
    const uploadDocuments = vi.fn().mockResolvedValue([
      {
        fileName: "unsupported.docx",
        status: "failed",
        result: "failed",
        document: null,
        failureCode: "unsupported_file",
      },
    ]);
    useWorkspaceStore.setState({ uploadDocuments });
    const { container } = render(
      <MemoryRouter>
        <DocumentsPage />
      </MemoryRouter>,
    );

    const input = container.querySelector('input[type="file"]:not([accept=".pdf"])');
    expect(input).toBeInTheDocument();
    fireEvent.change(input!, {
      target: { files: [new File(["not supported"], "unsupported.docx")] },
    });

    const alert = await screen.findByRole("alert");
    expect(alert).toHaveTextContent("unsupported.docx 上传失败：请检查文件格式或大小。");
    expect(screen.queryByRole("button", { name: "重试" })).not.toBeInTheDocument();
    expect(useWorkspaceStore.getState().supportingDocumentUploads).toEqual([]);
  });
});
