import type { ReactNode } from "react";

interface StatusBadgeProps {
  tone?: "neutral" | "info" | "success" | "danger";
  children: ReactNode;
}

export function StatusBadge({ tone = "neutral", children }: StatusBadgeProps) {
  return <span className={`status-badge status-${tone}`}>{children}</span>;
}
