import { useCallback, useEffect, useRef } from "react";
import { useWorkspaceStore } from "../../stores/workspace-store";
import { useAuthStore } from "../../stores/auth-store";

export function useWorkspaceRefresh() {
  const resumeStatus = useWorkspaceStore((state) => state.resume?.parseStatus);
  const refresh = useWorkspaceStore((state) => state.refresh);
  const accessToken = useAuthStore((state) => state.accessToken);
  const activeRole = useAuthStore((state) => state.user?.role);
  const refreshInFlight = useRef(false);
  const runRefresh = useCallback(
    async (options?: { preserveView?: boolean }) => {
      if (refreshInFlight.current) return;
      refreshInFlight.current = true;
      try {
        await refresh(options);
      } finally {
        refreshInFlight.current = false;
      }
    },
    [refresh],
  );

  useEffect(() => {
    if (!accessToken) return;
    void runRefresh();
  }, [accessToken, activeRole, runRefresh]);

  useEffect(() => {
    if (!accessToken || resumeStatus !== "processing") return;
    const timer = window.setInterval(
      () => void runRefresh({ preserveView: true }),
      1500,
    );
    return () => window.clearInterval(timer);
  }, [accessToken, resumeStatus, runRefresh]);
}
