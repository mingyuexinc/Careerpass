import { create } from "zustand";
import { mockRepository } from "../api/mock/mockRepository";
import { listCurrentHrJobs } from "../api/hrJobApi";
import { listResumes, uploadResume as uploadResumeRequest } from "../api/resumeApi";
import {
  createReadyDocumentResult,
  listCandidateDocuments,
  uploadCandidateDocuments,
} from "../api/candidateDocumentApi";
import { useAuthStore } from "./auth-store";
import { getCurrentJobGoal, saveCurrentJobGoal } from "../api/jobGoalApi";
import { getCurrentAgentRun, startCurrentAgentRun } from "../api/agentRunApi";
import {
  ApiRequestError,
  listCurrentApplications,
  listCurrentHrApplications,
  updateCurrentHrApplicationStatus,
} from "../api/applicationApi";
import {
  downloadConversationAttachment,
  listCurrentConversations,
  sendConversationMessage,
} from "../api/conversationApi";
import type {
  DeliveryProgress,
  AgentRunSummary,
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
  refresh: (options?: { preserveView?: boolean }) => Promise<void>;
  uploadResume: (file: File) => Promise<void>;
  setParseResult: (result: "succeeded" | "failed") => Promise<void>;
  uploadDocuments: (files: File[]) => Promise<SupportingDocumentUploadResult[]>;
  uploadJobs: (files: File[]) => Promise<void>;
  uploadJob: (file: File) => Promise<void>;
  deleteJob: (id: string) => Promise<void>;
  saveGoal: (input: JobGoalInput) => Promise<void>;
  startAgent: () => Promise<void>;
  updateApplicationStatus: (id: string, status: DeliveryProgress) => Promise<void>;
  sendMessage: (id: string, content: string, clientMessageId?: string) => Promise<void>;
  downloadAttachment: (applicationId: string, messageId: string, attachmentId: string, fileName: string) => Promise<void>;
  resetData: () => Promise<void>;
  clearLocalState: () => Promise<void>;
  clearError: () => void;
  agentRun: AgentRunSummary | null;
  agentRunCanStart: boolean;
  savingGoal: boolean;
  startingAgent: boolean;
}

function toWorkspaceSnapshot(state: WorkspaceState): WorkspaceSnapshot {
  return {
    resume: state.resume,
    supportingDocuments: state.supportingDocuments,
    supportingDocumentUploads: state.supportingDocumentUploads,
    jobs: state.jobs,
    currentJob: state.currentJob,
    hrJobs: state.hrJobs,
    currentHrJob: state.currentHrJob,
    jobGoal: state.jobGoal,
    agentStatus: state.agentStatus,
    round: state.round,
    applications: state.applications,
    hrApplications: state.hrApplications,
    conversations: state.conversations,
  };
}

const emptySnapshot: WorkspaceSnapshot = {
  resume: null,
  supportingDocuments: [],
  supportingDocumentUploads: [],
  jobs: [],
  currentJob: null,
  hrJobs: [],
  currentHrJob: null,
  jobGoal: null,
  agentStatus: "not_started",
  round: 0,
  applications: [],
  hrApplications: [],
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
    if (error instanceof ApiRequestError && error.status === 401) {
      useAuthStore.getState().signOut();
    }
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
  agentRun: null,
  agentRunCanStart: false,
  savingGoal: false,
  startingAgent: false,
  refresh: async (options = {}) => {
    const preserveView = options.preserveView ?? false;
    set({
      loading: true,
      ...(preserveView ? {} : { initialized: false }),
      error: null,
    });
    try {
      const snapshot: WorkspaceSnapshot = {
        ...emptySnapshot,
        supportingDocuments: [],
        supportingDocumentUploads: [],
        jobs: [],
        currentJob: null,
        hrJobs: [],
        currentHrJob: null,
        applications: [],
        hrApplications: [],
        conversations: [],
      };
      const accessToken = useAuthStore.getState().accessToken;
      const activeRole = useAuthStore.getState().user?.role;
      if (accessToken && activeRole === "candidate") {
        const resumes = await listResumes(accessToken);
        snapshot.resume = resumes[0] ?? null;
        snapshot.supportingDocuments = await listCandidateDocuments(accessToken);
        snapshot.jobGoal = await getCurrentJobGoal(accessToken);
        const agentRunStatus = await getCurrentAgentRun(accessToken);
        snapshot.applications = await listCurrentApplications(accessToken);
        snapshot.agentStatus =
          agentRunStatus.run?.status ??
          (agentRunStatus.canStart ? "ready" : "not_started");
        set({
          ...snapshot,
          agentRun: agentRunStatus.run,
          agentRunCanStart: agentRunStatus.canStart,
          loading: false,
          initialized: true,
        });
        return;
      }
      if (accessToken && activeRole === "hr") {
        snapshot.hrJobs = await listCurrentHrJobs(accessToken);
        snapshot.currentHrJob = snapshot.hrJobs.at(-1) ?? null;
        snapshot.hrApplications = await listCurrentHrApplications(accessToken);
        try {
          snapshot.conversations = await listCurrentConversations(accessToken);
        } catch {
          // Conversation loading is additive to the HR workspace.  Keep the
          // applications page usable while an older backend is being upgraded.
          snapshot.conversations = [];
        }
        set({
          ...snapshot,
          agentRun: null,
          agentRunCanStart: false,
          loading: false,
          initialized: true,
        });
        return;
      }
      set({
        ...snapshot,
        agentRun: null,
        agentRunCanStart: snapshot.agentStatus === "ready",
        loading: false,
        initialized: true,
      });
    } catch (error) {
      if (error instanceof ApiRequestError && error.status === 401) {
        useAuthStore.getState().signOut();
      }
      set({
        loading: false,
        ...(preserveView
          ? {}
          : { error: error instanceof Error ? error.message : "数据加载失败。" }),
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
        const snapshot = toWorkspaceSnapshot(useWorkspaceStore.getState());
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
        const snapshot = toWorkspaceSnapshot(useWorkspaceStore.getState());
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
  saveGoal: async (input) => {
    if (useWorkspaceStore.getState().savingGoal) return;
    const accessToken = useAuthStore.getState().accessToken;
    set({ savingGoal: true });
    try {
      await runAction(set, async () => {
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
        const snapshot = toWorkspaceSnapshot(useWorkspaceStore.getState());
        snapshot.jobGoal = accessToken
          ? await saveCurrentJobGoal(normalizedInput, accessToken)
          : await mockRepository.saveGoal(normalizedInput);
        return snapshot;
      });
      if (accessToken) {
        const agentRunStatus = await getCurrentAgentRun(accessToken);
        set({
          agentRun: agentRunStatus.run,
          agentRunCanStart: agentRunStatus.canStart,
          agentStatus:
            agentRunStatus.run?.status ??
            (agentRunStatus.canStart ? "ready" : "not_started"),
        });
      } else {
        const current = useWorkspaceStore.getState();
        set({ agentRunCanStart: current.agentStatus === "ready" });
      }
    } finally {
      set({ savingGoal: false });
    }
  },
  startAgent: async () => {
    const current = useWorkspaceStore.getState();
    if (current.startingAgent || current.savingGoal) return;
    set({ loading: true, error: null });
    set({ startingAgent: true });
    try {
      const accessToken = useAuthStore.getState().accessToken;
      const run = accessToken
        ? await startCurrentAgentRun(accessToken)
        : await mockRepository.startAgent();
      const applications = accessToken
        ? await listCurrentApplications(accessToken)
        : (await mockRepository.getSnapshot()).applications;
      set({
        agentRun: run,
        agentRunCanStart: false,
        agentStatus: run.status,
        applications,
        loading: false,
        startingAgent: false,
        initialized: true,
      });
    } catch (error) {
      set({
        loading: false,
        startingAgent: false,
        error: error instanceof Error ? error.message : "启动失败，请稍后重试。",
      });
      throw error;
    }
  },
  updateApplicationStatus: async (id, status) =>
    runAction(set, async () => {
      const accessToken = useAuthStore.getState().accessToken;
      const activeRole = useAuthStore.getState().user?.role;
      const snapshot = toWorkspaceSnapshot(useWorkspaceStore.getState());
      if (accessToken && activeRole === "hr") {
        const updated = await updateCurrentHrApplicationStatus(id, status, accessToken);
        snapshot.hrApplications = snapshot.hrApplications.map((item) =>
          item.id === updated.id ? updated : item,
        );
        return snapshot;
      }
      await mockRepository.updateHrApplicationStatus(id, status);
      return mockRepository.getSnapshot();
    }),
  sendMessage: async (id, content, clientMessageId) =>
    runAction(set, async () => {
      const accessToken = useAuthStore.getState().accessToken;
      if (accessToken && useAuthStore.getState().user?.role === "hr") {
        const current = useWorkspaceStore.getState().conversations.find((item) => item.id === id);
        if (!current) throw new Error("沟通会话不存在或已不可用。");
        const updated = await sendConversationMessage(
          current.applicationId,
          current.id,
          content,
          clientMessageId ?? crypto.randomUUID(),
          accessToken,
        );
        const snapshot = toWorkspaceSnapshot(useWorkspaceStore.getState());
        snapshot.conversations = snapshot.conversations.map((item) =>
          item.id === updated.id ? updated : item,
        );
        return snapshot;
      }
      await mockRepository.sendConversationMessage(id, content, clientMessageId);
      return mockRepository.getSnapshot();
    }),
  downloadAttachment: async (applicationId, messageId, attachmentId, fileName) => {
    const accessToken = useAuthStore.getState().accessToken;
    if (!accessToken || useAuthStore.getState().user?.role !== "hr") {
      throw new Error("当前身份无权下载附件。");
    }
    await downloadConversationAttachment(applicationId, messageId, attachmentId, fileName, accessToken);
  },
  resetData: async () => runAction(set, () => mockRepository.resetData()),
  clearLocalState: async () => {
    set({
      ...emptySnapshot,
      initialized: false,
      loading: false,
      resumeLoading: false,
      supportingDocumentsLoading: false,
      error: null,
      agentRun: null,
      agentRunCanStart: false,
      savingGoal: false,
      startingAgent: false,
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
