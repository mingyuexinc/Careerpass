import { render, screen } from "@testing-library/react";
import { StepListItem } from "../components/ui";

describe("StepListItem", () => {
  it("renders the shared marker, title, and description structure", () => {
    const { container } = render(
      <StepListItem
        step={1}
        status="active"
        title="上传岗位 JD"
        description="准备岗位信息"
      />,
    );

    expect(container.querySelector(".step-list-item")).toBeInTheDocument();
    expect(screen.getByText("1")).toHaveClass("step-marker-active");
    expect(screen.getByText("上传岗位 JD")).toBeInTheDocument();
    expect(screen.getByText("准备岗位信息")).toBeInTheDocument();
  });
});
