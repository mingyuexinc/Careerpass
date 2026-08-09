import { render, screen } from "@testing-library/react";
import { StepMarker } from "../components/ui";

describe("StepMarker", () => {
  it("renders the numbered waiting state", () => {
    render(<StepMarker step={2} />);
    expect(screen.getByText("2")).toHaveClass("step-marker", "step-marker-waiting");
  });

  it("renders the active and completed state symbols", () => {
    const { rerender } = render(<StepMarker step={3} status="active" activeSymbol="…" />);
    expect(screen.getByText("…")).toHaveClass("step-marker-active");

    rerender(<StepMarker step={3} status="completed" />);
    expect(screen.getByText("✓")).toHaveClass("step-marker-completed");
  });
});
