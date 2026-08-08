import { create } from "zustand";
import { mockRepository } from "../api/mock/mockRepository";
import type { DemoSnapshot, DeliveryProgress, JobGoalInput } from "../domain/types";

interface DemoState extends DemoSnapshot {
  initialized: boolean;
  loading: boolean;
  error: string | null;
  refresh: () => Promise<void>;
  uploadResume: (file: File) => Promise<void>;
  simulateParse: (result: "succeeded" | "failed") => Promise<void>;
  uploadDocuments: (files: File[]) => Promise<void>;
  uploadJob: (file: File) => Promise<void>;
  saveGoal: (input: JobGoalInput) => Promise<void>;
  startAgent: () => Promise<void>;
  updateApplicationStatus: (id: string, status: DeliveryProgress) => Promise<void>;
  sendMessage: (id: string, content: string) => Promise<void>;
  resetDemo: () => Promise<void>;
  clearError: () => void;
}

const emptySnapshot: DemoSnapshot = {
  resume: null,
  supportingDocuments: [],
  currentJob: null,
  jobGoal: null,
  agentStatus: "not_started",
  round: 0,
  applications: [],
  conversations: [],
};

async function runAction(
  set: (partial: Partial<DemoState>) => void,
  action: () => Promise<DemoSnapshot>,
): Promise<void> {
  set({ loading: true, error: null });
  try {
    set(await action());
    set({ loading: false, initialized: true });
  } catch (error) {
    set({
      loading: false,
      error: error instanceof Error ? error.message : "操作失败，请稍后重试。",
    });
    throw error;
  }
}

export const useDemoStore = create<DemoState>((set) => ({
  ...emptySnapshot,
  initialized: false,
  loading: false,
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
    runAction(set, async () => {
      await mockRepository.uploadResume(file);
      return mockRepository.getSnapshot();
    }),
  simulateParse: async (result) =>
    runAction(set, async () => {
      await mockRepository.simulateParseResult(result);
      return mockRepository.getSnapshot();
    }),
  uploadDocuments: async (files) =>
    runAction(set, async () => {
      await mockRepository.uploadDocuments(files);
      return mockRepository.getSnapshot();
    }),
  uploadJob: async (file) =>
    runAction(set, async () => {
      await mockRepository.uploadJob(file);
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
  resetDemo: async () => runAction(set, () => mockRepository.resetDemo()),
  clearError: () => set({ error: null }),
}));

export function useDemoInitialized(): boolean {
  return useDemoStore((state) => state.initialized);
}

export function getDemoState(): DemoState {
  return useDemoStore.getState();
}
