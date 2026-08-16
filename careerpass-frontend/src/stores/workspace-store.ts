import { create } from "zustand";
import { mockRepository } from "../api/mock/mockRepository";
import { listResumes, uploadResume as uploadResumeRequest } from "../api/resumeApi";
import {
  createReadyDocumentResult,
  listCandidateDocuments,
  uploadCandidateDocuments,
} from "../api/candidateDocumentApi";
import { useAuthStore } from "./auth-store";
import { getCurrentJobGoal, saveCurrentJobGoal } from "../api/jobGoalApi";
import type {
  DeliveryProgress,
  JobGoalInput,
  SupportingDocumentUploadResult,
  WorkspaceSnapshot,
} from "../domain/types";

interface WorkspaceState extends WorkspaceSnapshot {
  initialized: boolean;
  loading: boolean;
  resumeLoading: boolean;
  supportingDocumentsLoading: boolean;
  error: string | null;
  refresh: () => Promise<void>;
  uploadResume: (file: File) => Promise<void>;
  setParseResult: (result: "succeeded" | "failed") => Promise<void>;
  uploadDocuments: (files: File[]) => Promise<SupportingDocumentUploadResult[]>;
  uploadJobs: (files: File[]) => Promise<void>;
  uploadJob: (file: File) => Promise<void>;
  deleteJob: (id: string) => Promise<void>;
  saveGoal: (input: JobGoalInput) => Promise<void>;
  startAgent: () => Promise<void>;
  updateApplicationStatus: (id: string, status: DeliveryProgress) => Promise<void>;
  sendMessage: (id: string, content: string) => Promise<void>;
  resetData: () => Promise<void>;
  clearLocalState: () => Promise<void>;
  clearError: () => void;
}

const emptySnapshot: WorkspaceSnapshot = {
  resume: null,
  supportingDocuments: [],
  supportingDocumentUploads: [],
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
      const snapshot = await mockRepository.getSnapshot();
      snapshot.supportingDocumentUploads = [];
      const accessToken = useAuthStore.getState().accessToken;
      const activeRole = useAuthStore.getState().user?.role;
      if (accessToken && activeRole === "candidate") {
        const resumes = await listResumes(accessToken);
        snapshot.resume = resumes[0] ?? null;
        snapshot.supportingDocuments = await listCandidateDocuments(accessToken);
        snapshot.jobGoal = await getCurrentJobGoal(accessToken);
        snapshot.supportingDocumentUploads = [];
      }
      set({ ...snapshot, loading: false, initialized: true });
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
        const accessToken = useAuthStore.getState().accessToken;
        if (accessToken) {
          await uploadResumeRequest(file, accessToken);
        } else {
          await mockRepository.uploadResume(file);
        }
        const snapshot = await mockRepository.getSnapshot();
        if (accessToken) {
          const resumes = await listResumes(accessToken);
          snapshot.resume = resumes[0] ?? null;
        }
        return snapshot;
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
  uploadDocuments: async (files) => {
    set({
      loading: true,
      error: null,
      supportingDocumentsLoading: true,
      supportingDocumentUploads: files.map(createReadyDocumentResult),
    });
    try {
      const accessToken = useAuthStore.getState().accessToken;
      if (accessToken) {
        const results = await uploadCandidateDocuments(files, accessToken);
        const snapshot = await mockRepository.getSnapshot();
        snapshot.supportingDocuments = await listCandidateDocuments(accessToken);
        snapshot.supportingDocumentUploads = results;
        set({
          ...snapshot,
          loading: false,
          initialized: true,
          supportingDocumentsLoading: false,
        });
        return results;
      } else {
        const results = await mockRepository.uploadDocuments(files);
        const snapshot = await mockRepository.getSnapshot();
        snapshot.supportingDocumentUploads = results;
        set({
          ...snapshot,
          loading: false,
          initialized: true,
          supportingDocumentsLoading: false,
        });
        return results;
      }
    } catch (error) {
      set({
        loading: false,
        supportingDocumentsLoading: false,
        error: error instanceof Error ? error.message : "其它资料上传失败，请稍后重试。",
      });
      throw error;
    }
  },
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
      if (
        !Number.isInteger(input.offerTarget) ||
        input.offerTarget < 1 ||
        input.offerTarget > 10 ||
        !input.title.trim()
      )
        throw new Error("请填写有效的目标 Offer 数量和岗位名称。");
      const normalizedInput = {
        ...input,
        title: input.title.trim(),
        filters: input.filters.trim(),
      };
      const accessToken = useAuthStore.getState().accessToken;
      const snapshot = await mockRepository.getSnapshot();
      snapshot.jobGoal = accessToken
        ? await saveCurrentJobGoal(normalizedInput, accessToken)
        : await mockRepository.saveGoal(normalizedInput);
      return snapshot;
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
  clearLocalState: async () => {
    set({
      ...emptySnapshot,
      initialized: false,
      loading: false,
      resumeLoading: false,
      supportingDocumentsLoading: false,
      error: null,
    });
  },
  clearError: () => set({ error: null }),
}));

export function useWorkspaceInitialized(): boolean {
  return useWorkspaceStore((state) => state.initialized);
}

export function getWorkspaceState(): WorkspaceState {
  return useWorkspaceStore.getState();
}
