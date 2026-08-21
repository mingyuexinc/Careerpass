import type {
  Application,
  AgentRunSummary,
  Conversation,
  WorkspaceSnapshot,
  DeliveryProgress,
  HrJob,
  Job,
  JobGoal,
  JobGoalInput,
  Resume,
  SupportingDocument,
  SupportingDocumentUploadResult,
} from "../../domain/types";
import { createReadyDocumentResult, getDocumentFileType } from "../candidateDocumentApi";
import { getOfferCount, isValidDeliveryTransition } from "../../domain/mappings";
import { jobFixtures } from "./fixtures/jobs";
import { createInitialSnapshot, createRunningSnapshot } from "./fixtures/scenarios";
import type { WorkspaceRepository } from "../repositories/interfaces";

const delay = (milliseconds = 180) =>
  new Promise((resolve) => window.setTimeout(resolve, milliseconds));

function clone<T>(value: T): T {
  return structuredClone(value);
}

function now(): string {
  return new Date().toISOString();
}

function toHrJob(job: Job): HrJob {
  return {
    id: job.id,
    fileName: job.fileName,
    jobTitle: job.title,
    companyName: job.company,
    createdAt: job.uploadedAt,
    parseStatus: "succeeded",
    matchStarted: false,
  };
}

function contentFingerprint(bytes: Uint8Array): string {
  let hash = 2166136261;
  for (const byte of bytes) {
    hash ^= byte;
    hash = Math.imul(hash, 16777619);
  }
  return `${bytes.length}:${hash >>> 0}`;
}

async function readFileBytes(file: File): Promise<Uint8Array> {
  if (typeof file.arrayBuffer === "function") {
    return new Uint8Array(await file.arrayBuffer());
  }
  if (typeof FileReader !== "undefined") {
    return new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.onload = () => resolve(new Uint8Array(reader.result as ArrayBuffer));
      reader.onerror = () => reject(reader.error ?? new Error("无法读取文件。"));
      reader.readAsArrayBuffer(file);
    });
  }
  return new TextEncoder().encode(await file.text());
}

class MockRepository implements WorkspaceRepository {
  private snapshot: WorkspaceSnapshot = createInitialSnapshot();
  private documentFingerprints = new Map<string, string>();

  async getSnapshot(): Promise<WorkspaceSnapshot> {
    await delay(80);
    return clone(this.snapshot);
  }

  async loadRunningScenario(): Promise<WorkspaceSnapshot> {
    this.snapshot = createRunningSnapshot();
    return clone(this.snapshot);
  }

  async resetData(): Promise<WorkspaceSnapshot> {
    await delay(120);
    this.snapshot = createInitialSnapshot();
    this.documentFingerprints.clear();
    return clone(this.snapshot);
  }

  async getCurrentResume(): Promise<Resume | null> {
    return clone(this.snapshot.resume);
  }

  async uploadResume(file: File): Promise<Resume> {
    await delay(420);
    const current = this.snapshot.resume;
    if (
      this.snapshot.agentStatus === "running" ||
      this.snapshot.agentStatus === "finished"
    ) {
      throw new Error("当前投递轮次已绑定简历，暂不能替换。");
    }
    const resume: Resume = {
      id: `resume-${Date.now()}`,
      fileName: file.name || "resume.pdf",
      uploadedAt: now(),
      parseStatus: "processing",
      version: (current?.version ?? 0) + 1,
    };
    this.snapshot.resume = resume;
    this.snapshot.agentStatus = "not_started";
    return clone(resume);
  }

  async deleteResume(id: string): Promise<Resume | null> {
    await delay(180);
    const current = this.snapshot.resume;
    if (!current || current.id !== id) throw new Error("当前简历不存在或已不可用。");
    if (
      !["not_started", "ready"].includes(this.snapshot.agentStatus) ||
      !["succeeded", "failed"].includes(current.parseStatus)
    ) {
      throw new Error("当前状态不能删除简历。");
    }
    this.snapshot.resume = null;
    return null;
  }

  async setParseResult(result: "succeeded" | "failed"): Promise<Resume> {
    await delay(520);
    if (!this.snapshot.resume) throw new Error("请先上传简历。");
    this.snapshot.resume.parseStatus = result;
    if (result === "failed") this.snapshot.agentStatus = "not_started";
    return clone(this.snapshot.resume);
  }

  async listDocuments(): Promise<SupportingDocument[]> {
    return clone(this.snapshot.supportingDocuments);
  }

  async deleteDocument(id: string): Promise<SupportingDocument[]> {
    await delay(180);
    if (!this.snapshot.supportingDocuments.some((item) => item.id === id)) {
      throw new Error("其它资料不存在或已不可用。");
    }
    this.snapshot.supportingDocuments = this.snapshot.supportingDocuments.filter(
      (item) => item.id !== id,
    );
    for (const [fingerprint, documentId] of this.documentFingerprints.entries()) {
      if (documentId === id) this.documentFingerprints.delete(fingerprint);
    }
    return clone(this.snapshot.supportingDocuments);
  }

  async uploadDocuments(files: File[]): Promise<SupportingDocumentUploadResult[]> {
    const readyResults = files.map(createReadyDocumentResult);
    this.snapshot.supportingDocumentUploads = readyResults;
    await delay(360);
    const results = await Promise.all(
      files.map(async (file, index) => {
        const fileName = file.name || `supporting-document-${index + 1}.pdf`;
        const extension = fileName.split(".").at(-1)?.toLowerCase();
        const allowed =
          extension === "pdf" ||
          extension === "md" ||
          extension === "jpg" ||
          extension === "png";
        if (!allowed || file.size === 0) {
          return {
            fileName,
            status: "failed",
            result: "failed",
            document: null,
            failureCode: file.size === 0 ? "empty_file" : "unsupported_file",
          } satisfies SupportingDocumentUploadResult;
        }
        if (file.size > 10_000_000) {
          return {
            fileName,
            status: "failed",
            result: "failed",
            document: null,
            failureCode: "file_too_large",
          } satisfies SupportingDocumentUploadResult;
        }
        const bytes = await readFileBytes(file);
        const fingerprint = contentFingerprint(bytes);
        const existingId = this.documentFingerprints.get(fingerprint);
        if (existingId) {
          const existing = this.snapshot.supportingDocuments.find(
            (item) => item.id === existingId,
          );
          if (existing) {
            return {
              fileName,
              status: "success",
              result: "duplicate",
              document: clone(existing),
              failureCode: null,
            } satisfies SupportingDocumentUploadResult;
          }
        }
        const document: SupportingDocument = {
          id: `document-${Date.now()}-${index}`,
          fileName,
          fileType: getDocumentFileType(fileName),
          uploadedAt: now(),
          status: "success",
        };
        this.documentFingerprints.set(fingerprint, document.id);
        this.snapshot.supportingDocuments = [
          ...this.snapshot.supportingDocuments,
          document,
        ];
        return {
          fileName,
          status: "success",
          result: "created",
          document: clone(document),
          failureCode: null,
        } satisfies SupportingDocumentUploadResult;
      }),
    );
    this.snapshot.supportingDocumentUploads = results;
    return clone(results);
  }

  async getCurrentJob(): Promise<Job | null> {
    return clone(this.snapshot.currentJob);
  }

  async listJobs(): Promise<Job[]> {
    return clone(this.snapshot.jobs);
  }

  async uploadJobs(files: File[]): Promise<Job[]> {
    await delay(430);
    const current = this.snapshot.currentJob;
    const existingCount = this.snapshot.jobs.length;
    const uploadBatchId = Date.now();
    const uploaded = files.map((file, index) => {
      const job = clone(jobFixtures[(existingCount + index) % jobFixtures.length]);
      job.id = `job-upload-${uploadBatchId}-${existingCount + index + 1}`;
      job.fileName = file.name || `job-description-${index + 1}.pdf`;
      job.uploadedAt = now();
      job.version = (current?.version ?? 0) + index + 1;
      job.uploaded = true;
      return job;
    });
    this.snapshot.jobs = [...this.snapshot.jobs, ...uploaded];
    this.snapshot.currentJob = uploaded.at(-1) ?? current;
    this.snapshot.hrJobs = this.snapshot.jobs.map(toHrJob);
    this.snapshot.currentHrJob = this.snapshot.currentJob
      ? toHrJob(this.snapshot.currentJob)
      : null;
    return clone(uploaded);
  }

  async uploadJob(file: File): Promise<Job> {
    const uploaded = await this.uploadJobs([file]);
    return uploaded[0];
  }

  async deleteJob(id: string): Promise<Job[]> {
    await delay(240);
    const exists = this.snapshot.jobs.some((job) => job.id === id);
    if (!exists) throw new Error("没有找到对应的岗位 JD。");
    this.snapshot.jobs = this.snapshot.jobs.filter((job) => job.id !== id);
    this.snapshot.currentJob = this.snapshot.jobs.at(-1) ?? null;
    this.snapshot.hrJobs = this.snapshot.jobs.map(toHrJob);
    this.snapshot.currentHrJob = this.snapshot.currentJob
      ? toHrJob(this.snapshot.currentJob)
      : null;
    return clone(this.snapshot.jobs);
  }

  async getCurrentGoal(): Promise<JobGoal | null> {
    return clone(this.snapshot.jobGoal);
  }

  async saveGoal(input: JobGoalInput): Promise<JobGoal> {
    await delay(260);
    const goal: JobGoal = {
      id: this.snapshot.jobGoal?.id ?? `goal-${Date.now()}`,
      ...input,
      status: this.snapshot.jobGoal?.status ?? "active",
      createdAt: this.snapshot.jobGoal?.createdAt ?? now(),
      updatedAt: now(),
    };
    this.snapshot.jobGoal = goal;
    if (
      this.snapshot.resume?.parseStatus === "succeeded" &&
      this.snapshot.agentStatus === "not_started"
    ) {
      this.snapshot.agentStatus = "ready";
    }
    return clone(goal);
  }

  async startAgent(): Promise<AgentRunSummary> {
    await delay(520);
    if (!this.snapshot.resume || this.snapshot.resume.parseStatus !== "succeeded") {
      throw new Error("简历解析成功后才能启动 Agent。");
    }
    if (!this.snapshot.jobGoal) throw new Error("请先创建求职目标。");
    if (this.snapshot.agentStatus === "finished")
      throw new Error("Agent 已结束，不能重复启动。");
    if (this.snapshot.agentStatus === "running") {
      return {
        id: "mock-agent-run-001",
        status: "running",
        startedAt: "2026-08-17T00:00:00.000Z",
        finishedAt: null,
        finishReason: null,
      };
    }
    this.snapshot.agentStatus = "running";
    this.snapshot.round = 1;
    return {
      id: "mock-agent-run-001",
      status: "running",
      startedAt: "2026-08-17T00:00:00.000Z",
      finishedAt: null,
      finishReason: null,
    };
  }

  async listApplications(): Promise<Application[]> {
    await delay(120);
    return clone(this.snapshot.applications);
  }

  async listHrApplications() {
    await delay(120);
    return clone(this.snapshot.hrApplications);
  }

  async updateHrApplicationStatus(
    id: string,
    status: DeliveryProgress,
  ) {
    await delay(280);
    const hrApplication = this.snapshot.hrApplications.find((item) => item.id === id);
    if (!hrApplication) throw new Error("没有找到对应的投递记录。");
    if (!isValidDeliveryTransition(hrApplication.status, status)) {
      throw new Error("该投递状态不能直接跳转到目标阶段。");
    }
    hrApplication.status = status;
    const candidateApplication = this.snapshot.applications.find((item) => item.id === id);
    if (candidateApplication) {
      candidateApplication.status = status;
      candidateApplication.lastContactAt = now();
    }
    const offerCount = getOfferCount(
      this.snapshot.applications.map((item) => item.status),
    );
    if (this.snapshot.jobGoal && offerCount >= this.snapshot.jobGoal.offerTarget) {
      this.snapshot.agentStatus = "finished";
      this.snapshot.jobGoal.status = "achieved";
    }
    return clone(hrApplication);
  }

  async updateApplicationStatus(
    id: string,
    status: DeliveryProgress,
  ): Promise<Application> {
    await delay(280);
    const application = this.snapshot.applications.find((item) => item.id === id);
    if (!application) throw new Error("没有找到对应的投递记录。");
    if (!isValidDeliveryTransition(application.status, status)) {
      throw new Error("该投递状态不能直接跳转到目标阶段。");
    }
    application.status = status;
    application.lastContactAt = now();
    const offerCount = getOfferCount(
      this.snapshot.applications.map((item) => item.status),
    );
    if (this.snapshot.jobGoal && offerCount >= this.snapshot.jobGoal.offerTarget) {
      this.snapshot.agentStatus = "finished";
    }
    return clone(application);
  }

  async listConversations(): Promise<Conversation[]> {
    await delay(120);
    return clone(this.snapshot.conversations);
  }

  async sendConversationMessage(id: string, content: string, clientMessageId?: string): Promise<Conversation> {
    await delay(480);
    void clientMessageId;
    const conversation = this.snapshot.conversations.find((item) => item.id === id);
    if (!conversation) throw new Error("没有找到对应会话。");
    const trimmed = content.trim();
    if (!trimmed) throw new Error("请输入消息内容。");
    const timestamp = now();
    conversation.messages.push({
      id: `message-${Date.now()}`,
      sender: "hr",
      text: trimmed,
      createdAt: timestamp,
    });
    conversation.messages.push({
      id: `message-${Date.now()}-reply`,
      sender: "agent",
      text: "感谢您的沟通，我会补充说明候选人的相关项目经验。",
      createdAt: now(),
    });
    return clone(conversation);
  }
}

export const mockRepository = new MockRepository();
