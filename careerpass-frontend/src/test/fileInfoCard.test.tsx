import { fireEvent, render, screen } from "@testing-library/react";
import { FileInfoCard } from "../components/ui";

describe("FileInfoCard", () => {
  it("renders a centered file type and unified upload metadata", () => {
    const { container } = render(
      <FileInfoCard
        fileName="candidate-resume.pdf"
        version={2}
        uploadedAt="2026-08-08T09:00:00+08:00"
      />,
    );

    expect(container.querySelector(".file-type-icon")).toHaveTextContent("PDF");
    expect(screen.getByText("candidate-resume.pdf")).toBeInTheDocument();
    expect(screen.getByText(/版本 2 · 上传于/)).toBeInTheDocument();
  });

  it("supports a business identity variant without exposing the file name", () => {
    render(
      <FileInfoCard
        fileName="internal-job-file.pdf"
        iconLabel="JD"
        primaryText="前端工程师 · 星河科技 · 深圳 · 20-30K"
        version={2}
        uploadedAt="2026-08-09T09:30:00+08:00"
      />,
    );

    expect(screen.getByText("JD")).toBeInTheDocument();
    expect(screen.getByText("前端工程师 · 星河科技 · 深圳 · 20-30K")).toBeInTheDocument();
    expect(screen.queryByText("internal-job-file.pdf")).not.toBeInTheDocument();
    expect(screen.getByText(/版本 2 · 上传于/)).toBeInTheDocument();
  });

  it("renders an accessible delete action when requested", () => {
    const onDelete = vi.fn();
    render(
      <FileInfoCard
        fileName="portfolio.pdf"
        version={1}
        uploadedAt="2026-08-09T09:30:00+08:00"
        onDelete={onDelete}
        deleteLabel="portfolio.pdf"
      />,
    );

    fireEvent.click(screen.getByRole("button", { name: "删除 portfolio.pdf" }));
    expect(onDelete).toHaveBeenCalledOnce();
  });
});
