export type StepMarkerStatus = "waiting" | "active" | "completed";

interface StepMarkerProps {
  step: number;
  status?: StepMarkerStatus;
  activeSymbol?: string;
}

export function StepMarker({ step, status = "waiting", activeSymbol }: StepMarkerProps) {
  const content = status === "completed" ? "✓" : (activeSymbol ?? step);

  return (
    <span className={`step-marker step-marker-${status}`} aria-hidden="true">
      {content}
    </span>
  );
}
