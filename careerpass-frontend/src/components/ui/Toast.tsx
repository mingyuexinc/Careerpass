import { useEffect } from "react";

export type ToastTone = "success" | "error" | "info";

interface ToastProps {
  message: string;
  tone?: ToastTone;
  onClose?: () => void;
  duration?: number;
}

export function Toast({
  message,
  tone = "success",
  onClose,
  duration = 4500,
}: ToastProps) {
  useEffect(() => {
    if (!onClose || duration <= 0) return;
    const timer = window.setTimeout(onClose, duration);
    return () => window.clearTimeout(timer);
  }, [duration, message, onClose]);

  return (
    <div className={`toast toast-${tone}`} role={tone === "error" ? "alert" : "status"}>
      <span>{message}</span>
      {onClose ? (
        <button type="button" aria-label="关闭提示" onClick={onClose}>
          ×
        </button>
      ) : null}
    </div>
  );
}
