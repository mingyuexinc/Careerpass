import { deliveryProgressMeta, deliveryProgressOrder } from "../../domain/mappings";
import type { DeliveryProgress } from "../../domain/types";

export function ProgressTimeline({ current }: { current: DeliveryProgress }) {
  const currentIndex =
    current === "terminated" ? -1 : deliveryProgressOrder.indexOf(current);
  return (
    <div
      className="timeline"
      aria-label={`当前进度：${deliveryProgressMeta[current].label}`}
    >
      {deliveryProgressOrder.map((status, index) => (
        <div
          key={status}
          className={`timeline-step ${current === "terminated" ? "is-terminated" : index < currentIndex ? "is-done" : index === currentIndex ? "is-current" : ""}`}
        >
          <span className="timeline-dot" />
          <span>{deliveryProgressMeta[status].label}</span>
        </div>
      ))}
    </div>
  );
}
