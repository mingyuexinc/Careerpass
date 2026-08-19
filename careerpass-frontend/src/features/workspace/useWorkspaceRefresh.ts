import { useEffect } from "react";
import { useWorkspaceStore } from "../../stores/workspace-store";
import { useAuthStore } from "../../stores/auth-store";

export function useWorkspaceRefresh() {
  const resumeStatus = useWorkspaceStore((state) => state.resume?.parseStatus);
  const refresh = useWorkspaceStore((state) => state.refresh);
  const accessToken = useAuthStore((state) => state.accessToken);
  const activeRole = useAuthStore((state) => state.user?.role);
  useEffect(() => {
    if (!accessToken) return;
    void refresh();
  }, [accessToken, activeRole, refresh]);

  useEffect(() => {
    if (!accessToken || resumeStatus !== "processing") return;
    const timer = window.setInterval(() => void refresh(), 1500);
    return () => window.clearInterval(timer);
  }, [accessToken, refresh, resumeStatus]);
}
