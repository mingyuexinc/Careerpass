import { useEffect } from "react";
import { useDemoStore } from "../../stores/demo-store";

export function useDemoRefresh() {
  const initialized = useDemoStore((state) => state.initialized);
  const refresh = useDemoStore((state) => state.refresh);
  useEffect(() => {
    if (!initialized) void refresh();
  }, [initialized, refresh]);
}
