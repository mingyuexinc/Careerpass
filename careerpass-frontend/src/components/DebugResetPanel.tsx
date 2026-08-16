import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { resetCurrentAccount } from "../api/debugResetApi";
import { Button } from "./ui";
import { useAuthStore } from "../stores/auth-store";
import { useWorkspaceStore } from "../stores/workspace-store";

function isDebugResetEnabled(): boolean {
  const configured = import.meta.env.VITE_DEBUG_RESET_ENABLED;
  return configured === "true" || (configured === undefined && import.meta.env.DEV);
}

export function DebugResetPanel() {
  const navigate = useNavigate();
  const accessToken = useAuthStore((state) => state.accessToken);
  const signOut = useAuthStore((state) => state.signOut);
  const clearLocalState = useWorkspaceStore((state) => state.clearLocalState);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  if (!isDebugResetEnabled()) return null;

  async function handleReset() {
    if (!accessToken || submitting) return;
    setSubmitting(true);
    setError(null);
    try {
      await resetCurrentAccount(accessToken);
      await clearLocalState();
      signOut();
      navigate("/login", { replace: true });
    } catch (reason) {
      setError(
        reason instanceof Error
          ? reason.message.trim()
          : "恢复初始状态失败，请稍后重试。",
      );
      setSubmitting(false);
    }
  }

  return (
    <section className="panel debug-reset-panel" aria-label="调试数据恢复">
      <div>
        <div className="eyebrow">DEVELOPMENT TOOL</div>
        <h2>调试：恢复当前账号初始状态</h2>
        <p className="page-subtitle">
          仅清理当前账号产生的联调数据，账号本身不会删除。存在处理中任务时，请稍后再试。
        </p>
        {error ? (
          <p className="debug-reset-error" role="alert">
            {error}
          </p>
        ) : null}
      </div>
      <Button type="button" variant="danger" disabled={submitting} onClick={handleReset}>
        {submitting ? "恢复中…" : "一键恢复初始状态"}
      </Button>
    </section>
  );
}
