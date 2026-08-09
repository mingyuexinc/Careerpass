import { StepMarker, type StepMarkerStatus } from "./StepMarker";

interface StepListItemProps {
  step: number;
  status: StepMarkerStatus;
  title: string;
  description: string;
  activeSymbol?: string;
}

export function StepListItem({
  step,
  status,
  title,
  description,
  activeSymbol,
}: StepListItemProps) {
  return (
    <div className="step-list-item">
      <StepMarker step={step} status={status} activeSymbol={activeSymbol} />
      <div className="step-list-copy">
        <strong>{title}</strong>
        <span>{description}</span>
      </div>
    </div>
  );
}
