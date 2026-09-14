import { useCallback, useEffect, useRef } from "react";
import { listCurrentHrJobs } from "../../api/hrJobApi";
import { getResumeStatus } from "../../api/resumeApi";
import { ApiRequestError } from "../../api/applicationApi";
import { useWorkspaceStore, isMockMode } from "../../stores/workspace-store";
import { useAuthStore } from "../../stores/auth-store";

const BACKOFF_INTERVALS_MS = [1500, 3000, 6000];
const BACKOFF_CAP_MS = 10_000;
const MAX_TOTAL_POLL_MS = 210_000;
const MAX_CONSECUTIVE_FAILURES = 3;

function pollDelayMs(attempt: number): number {
  return attempt < BACKOFF_INTERVALS_MS.length
    ? BACKOFF_INTERVALS_MS[attempt]
    : BACKOFF_CAP_MS;
}

export function useWorkspaceRefresh() {
  const resumeStatus = useWorkspaceStore((state) => state.resume?.parseStatus);
  const resumeId = useWorkspaceStore((state) => state.resume?.id);
  const hrJobs = useWorkspaceStore((state) => state.hrJobs);
  const refresh = useWorkspaceStore((state) => state.refresh);
  const accessToken = useAuthStore((state) => state.accessToken);
  const user = useAuthStore((state) => state.user);
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
    if (!accessToken && !user) return;
    void runRefresh();
  }, [accessToken, activeRole, runRefresh, user]);

  // Pending parse states are observed through lightweight status reads with
  // exponential backoff; a full workspace refresh runs only once, after the
  // observed state leaves the pending range.
  const pendingResume = activeRole === "candidate" && resumeStatus === "processing";
  const hasPendingHrJobs = hrJobs.some(
    (job) => job.parseStatus === "queued" || job.parseStatus === "running",
  );
  const shouldPoll = Boolean(accessToken) && (pendingResume || hasPendingHrJobs);

  useEffect(() => {
    if (!shouldPoll) return;
    let cancelled = false;
    let timer = 0;
    let attempt = 0;
    let totalDelayMs = 0;
    let failures = 0;

    const finishWithFullRefresh = () => {
      void runRefresh({ preserveView: true });
    };

    const tick = async () => {
      if (cancelled) return;
      const token = useAuthStore.getState().accessToken;
      if (!token) return;
      try {
        if (isMockMode()) {
          await runRefresh({ preserveView: true });
        } else if (pendingResume && resumeId) {
          const status = await getResumeStatus(resumeId, token);
          failures = 0;
          if (status !== "processing") {
            finishWithFullRefresh();
            return;
          }
        } else if (hasPendingHrJobs) {
          const jobs = await listCurrentHrJobs(token);
          failures = 0;
          useWorkspaceStore.getState().updateHrJobs(jobs);
          if (!jobs.some((job) => job.parseStatus === "queued" || job.parseStatus === "running")) {
            finishWithFullRefresh();
            return;
          }
        }
      } catch (error) {
        failures += 1;
        if (error instanceof ApiRequestError && error.status === 404) {
          finishWithFullRefresh();
          return;
        }
        if (error instanceof ApiRequestError && error.status === 401) {
          return;
        }
        if (failures >= MAX_CONSECUTIVE_FAILURES) {
          finishWithFullRefresh();
          return;
        }
      }
      const delay = pollDelayMs(attempt);
      attempt += 1;
      totalDelayMs += delay;
      if (totalDelayMs >= MAX_TOTAL_POLL_MS) {
        useWorkspaceStore.getState().markResumePollingTimedOut();
        return;
      }
      timer = window.setTimeout(() => void tick(), delay);
    };

    timer = window.setTimeout(() => void tick(), pollDelayMs(0));
    totalDelayMs = pollDelayMs(0);
    attempt = 1;
    return () => {
      cancelled = true;
      window.clearTimeout(timer);
    };
  }, [shouldPoll, pendingResume, resumeId, hasPendingHrJobs, runRefresh]);
}
