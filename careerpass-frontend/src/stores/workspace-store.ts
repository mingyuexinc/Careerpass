import { create } from "zustand";
import { mockRepository } from "../api/mock/mockRepository";
import type { DeliveryProgress, JobGoalInput, WorkspaceSnapshot } from "../domain/types";

interface WorkspaceState extends WorkspaceSnapshot {
  initialized: boolean;
  loading: boolean;
  resumeLoading: boolean;
  supportingDocumentsLoading: boolean;
  error: string | null;
  refresh: () => Promise<void>;
  uploadResume: (file: File) => Promise<void>;
  setParseResult: (result: "succeeded" | "failed") => Promise<void>;
  uploadDocuments: (files: File[]) => Promise<void>;
  deleteDocument: (id: string) => Promise<void>;
  uploadJobs: (files: File[]) => Promise<void>;
  uploadJob: (file: File) => Promise<void>;
  deleteJob: (id: string) => Promise<void>;
  saveGoal: (input: JobGoalInput) => Promise<void>;
  startAgent: () => Promise<void>;
  updateApplicationStatus: (id: string, status: DeliveryProgress) => Promise<void>;
  sendMessage: (id: string, content: string) => Promise<void>;
  resetData: () => Promise<void>;
  clearError: () => void;
}

const emptySnapshot: WorkspaceSnapshot = {
  resume: null,
  supportingDocuments: [],
  jobs: [],
  currentJob: null,
  jobGoal: null,
  agentStatus: "not_started",
  round: 0,
  applications: [],
  conversations: [],
};

async function runAction(
  set: (partial: Partial<WorkspaceState>) => void,
  action: () => Promise<WorkspaceSnapshot>,
  loadingKey?: "resumeLoading" | "supportingDocumentsLoading",
): Promise<void> {
  const startedState: Partial<WorkspaceState> = loadingKey ? { [loadingKey]: true } : {};
  set({ loading: true, error: null, ...startedState });
  try {
    set(await action());
    const completedState: Partial<WorkspaceState> = loadingKey
      ? { [loadingKey]: false }
      : {};
    set({ loading: false, initialized: true, ...completedState });
  } catch (error) {
    const failedState: Partial<WorkspaceState> = loadingKey
      ? { [loadingKey]: false }
      : {};
    set({
      loading: false,
      error: error instanceof Error ? error.message : "操作失败，请稍后重试。",
      ...failedState,
    });
    throw error;
  }
}

export const useWorkspaceStore = create<WorkspaceState>((set) => ({
  ...emptySnapshot,
  initialized: false,
  loading: false,
  resumeLoading: false,
  supportingDocumentsLoading: false,
  error: null,
  refresh: async () => {
    set({ loading: true, error: null });
    try {
      set({ ...(await mockRepository.getSnapshot()), loading: false, initialized: true });
    } catch (error) {
      set({
        loading: false,
        error: error instanceof Error ? error.message : "数据加载失败。",
      });
    }
  },
  uploadResume: async (file) =>
    runAction(
      set,
      async () => {
        await mockRepository.uploadResume(file);
        return mockRepository.getSnapshot();
      },
      "resumeLoading",
    ),
  setParseResult: async (result) =>
    runAction(
      set,
      async () => {
        await mockRepository.setParseResult(result);
        return mockRepository.getSnapshot();
      },
      "resumeLoading",
    ),
  uploadDocuments: async (files) =>
    runAction(
      set,
      async () => {
        await mockRepository.uploadDocuments(files);
        return mockRepository.getSnapshot();
      },
      "supportingDocumentsLoading",
    ),
  deleteDocument: async (id) =>
    runAction(
      set,
      async () => {
        await mockRepository.deleteDocument(id);
        return mockRepository.getSnapshot();
      },
      "supportingDocumentsLoading",
    ),
  uploadJobs: async (files) =>
    runAction(set, async () => {
      await mockRepository.uploadJobs(files);
      return mockRepository.getSnapshot();
    }),
  uploadJob: async (file) =>
    runAction(set, async () => {
      await mockRepository.uploadJob(file);
      return mockRepository.getSnapshot();
    }),
  deleteJob: async (id) =>
    runAction(set, async () => {
      await mockRepository.deleteJob(id);
      return mockRepository.getSnapshot();
    }),
  saveGoal: async (input) =>
    runAction(set, async () => {
      if (input.offerTarget < 1 || !input.title.trim())
        throw new Error("请填写有效的目标 Offer 数量和岗位名称。");
      await mockRepository.saveGoal({
        ...input,
        title: input.title.trim(),
        filters: input.filters.trim(),
      });
      return mockRepository.getSnapshot();
    }),
  startAgent: async () => runAction(set, () => mockRepository.startAgent()),
  updateApplicationStatus: async (id, status) =>
    runAction(set, async () => {
      await mockRepository.updateApplicationStatus(id, status);
      return mockRepository.getSnapshot();
    }),
  sendMessage: async (id, content) =>
    runAction(set, async () => {
      await mockRepository.sendConversationMessage(id, content);
      return mockRepository.getSnapshot();
    }),
  resetData: async () => runAction(set, () => mockRepository.resetData()),
  clearError: () => set({ error: null }),
}));

export function useWorkspaceInitialized(): boolean {
  return useWorkspaceStore((state) => state.initialized);
}

export function getWorkspaceState(): WorkspaceState {
  return useWorkspaceStore.getState();
}
