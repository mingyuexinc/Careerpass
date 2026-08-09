import { useEffect } from "react";
import { useWorkspaceStore } from "../../stores/workspace-store";

export function useWorkspaceRefresh() {
  const initialized = useWorkspaceStore((state) => state.initialized);
  const refresh = useWorkspaceStore((state) => state.refresh);
  useEffect(() => {
    if (!initialized) void refresh();
  }, [initialized, refresh]);
}
