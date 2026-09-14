import { renderHook } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { ApiRequestError } from "../api/applicationApi";
import { getResumeStatus } from "../api/resumeApi";
import { listCurrentHrJobs } from "../api/hrJobApi";
import { useWorkspaceRefresh } from "../features/workspace/useWorkspaceRefresh";
import { useAuthStore } from "../stores/auth-store";
import { useWorkspaceStore } from "../stores/workspace-store";
import type { HrJob, UserProfile } from "../domain/types";

vi.mock("../api/resumeApi", () => ({ getResumeStatus: vi.fn() }));
vi.mock("../api/hrJobApi", () => ({ listCurrentHrJobs: vi.fn() }));

const candidateUser: UserProfile = {
  id: "user-1",
  role: "candidate",
  displayName: "Candidate",
  title: "Candidate",
};

const hrUser: UserProfile = {
  id: "user-2",
  role: "hr",
  displayName: "HR",
  title: "HR",
};

function processingResume() {
  return {
    id: "resume-1",
    fileName: "resume.pdf",
    uploadedAt: "2026-09-14T00:00:00Z",
    parseStatus: "processing" as const,
    version: 1,
    isCurrent: true,
  };
}

function queuedHrJob(): HrJob {
  return {
    id: "job-1",
    fileName: "role.md",
    jobTitle: null,
    companyName: null,
    createdAt: "2026-09-14T00:00:00Z",
    parseStatus: "queued",
  };
}

function currentRefreshSpy() {
  return useWorkspaceStore.getState().refresh as unknown as ReturnType<typeof vi.fn>;
}

describe("useWorkspaceRefresh status polling", () => {
  beforeEach(() => {
    vi.useFakeTimers();
    useWorkspaceStore.setState({
      initialized: true,
      loading: false,
      resumeLoading: false,
      supportingDocumentsLoading: false,
      error: null,
      resumePollingNotice: null,
      resume: processingResume(),
      hrJobs: [],
      refresh: vi.fn().mockResolvedValue(undefined),
    });
    useAuthStore.setState({ user: candidateUser, accessToken: "token" });
  });

  afterEach(async () => {
    vi.useRealTimers();
    vi.clearAllMocks();
    useAuthStore.setState({ user: null, accessToken: null });
    await useWorkspaceStore.getState().clearLocalState();
  });

  it("polls with exponential backoff and refreshes once after the terminal status", async () => {
    vi.mocked(getResumeStatus)
      .mockResolvedValueOnce("processing")
      .mockResolvedValueOnce("processing")
      .mockResolvedValueOnce("succeeded");

    renderHook(() => useWorkspaceRefresh());
    const refresh = currentRefreshSpy();
    expect(refresh).toHaveBeenCalledTimes(1);

    await vi.advanceTimersByTimeAsync(1499);
    expect(getResumeStatus).toHaveBeenCalledTimes(0);
    await vi.advanceTimersByTimeAsync(1);
    expect(getResumeStatus).toHaveBeenCalledTimes(1);

    await vi.advanceTimersByTimeAsync(2999);
    expect(getResumeStatus).toHaveBeenCalledTimes(1);
    await vi.advanceTimersByTimeAsync(1);
    expect(getResumeStatus).toHaveBeenCalledTimes(2);

    await vi.advanceTimersByTimeAsync(5999);
    expect(getResumeStatus).toHaveBeenCalledTimes(2);
    await vi.advanceTimersByTimeAsync(1);
    expect(getResumeStatus).toHaveBeenCalledTimes(3);

    expect(refresh).toHaveBeenCalledTimes(2);
    expect(refresh).toHaveBeenLastCalledWith({ preserveView: true });

    await vi.advanceTimersByTimeAsync(30_000);
    expect(getResumeStatus).toHaveBeenCalledTimes(3);
  });

  it("stops polling with one full refresh when the resume is missing", async () => {
    vi.mocked(getResumeStatus).mockRejectedValue(new ApiRequestError("missing", 404));

    renderHook(() => useWorkspaceRefresh());

    await vi.advanceTimersByTimeAsync(1500);
    expect(getResumeStatus).toHaveBeenCalledTimes(1);
    expect(currentRefreshSpy()).toHaveBeenLastCalledWith({ preserveView: true });

    await vi.advanceTimersByTimeAsync(30_000);
    expect(getResumeStatus).toHaveBeenCalledTimes(1);
  });

  it("stops with a notice after the polling budget is exhausted", async () => {
    vi.mocked(getResumeStatus).mockResolvedValue("processing");

    renderHook(() => useWorkspaceRefresh());

    await vi.advanceTimersByTimeAsync(215_000);
    expect(useWorkspaceStore.getState().resumePollingNotice).toContain("解析耗时较长");
    const calls = vi.mocked(getResumeStatus).mock.calls.length;
    expect(calls).toBeGreaterThan(5);

    await vi.advanceTimersByTimeAsync(60_000);
    expect(vi.mocked(getResumeStatus).mock.calls.length).toBe(calls);
  });

  it("polls hr job parse status through the job list without resume calls", async () => {
    useAuthStore.setState({ user: hrUser, accessToken: "token" });
    useWorkspaceStore.setState({ resume: null, hrJobs: [queuedHrJob()] });
    const finishedJob: HrJob = { ...queuedHrJob(), parseStatus: "succeeded" };
    vi.mocked(listCurrentHrJobs).mockResolvedValue([finishedJob]);

    renderHook(() => useWorkspaceRefresh());

    await vi.advanceTimersByTimeAsync(1500);
    expect(listCurrentHrJobs).toHaveBeenCalledTimes(1);
    expect(getResumeStatus).not.toHaveBeenCalled();
    expect(useWorkspaceStore.getState().hrJobs[0]?.parseStatus).toBe("succeeded");
    expect(currentRefreshSpy()).toHaveBeenLastCalledWith({ preserveView: true });

    await vi.advanceTimersByTimeAsync(30_000);
    expect(listCurrentHrJobs).toHaveBeenCalledTimes(1);
  });

  it("does not poll when no parse work is pending", async () => {
    useWorkspaceStore.setState({
      resume: { ...processingResume(), parseStatus: "succeeded" },
    });

    renderHook(() => useWorkspaceRefresh());

    await vi.advanceTimersByTimeAsync(30_000);
    expect(getResumeStatus).not.toHaveBeenCalled();
    expect(currentRefreshSpy()).toHaveBeenCalledTimes(1);
  });
});
