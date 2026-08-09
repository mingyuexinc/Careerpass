import type {
  Application,
  Conversation,
  WorkspaceSnapshot,
  DeliveryProgress,
  Job,
  JobGoal,
  JobGoalInput,
  Resume,
  SupportingDocument,
} from "../../domain/types";
import { getOfferCount, isValidDeliveryTransition } from "../../domain/mappings";
import { applicationFixtures } from "./fixtures/applications";
import { conversationFixtures } from "./fixtures/conversations";
import { jobFixtures } from "./fixtures/jobs";
import { createInitialSnapshot } from "./fixtures/scenarios";
import type { WorkspaceRepository } from "../repositories/interfaces";

const delay = (milliseconds = 180) =>
  new Promise((resolve) => window.setTimeout(resolve, milliseconds));

function clone<T>(value: T): T {
  return structuredClone(value);
}

function now(): string {
  return new Date().toISOString();
}

class MockRepository implements WorkspaceRepository {
  private snapshot: WorkspaceSnapshot = createInitialSnapshot();

  async getSnapshot(): Promise<WorkspaceSnapshot> {
    await delay(80);
    return clone(this.snapshot);
  }

  async resetData(): Promise<WorkspaceSnapshot> {
    await delay(120);
    this.snapshot = createInitialSnapshot();
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

  async uploadDocuments(files: File[]): Promise<SupportingDocument[]> {
    await delay(360);
    const versions = new Map<string, number>();
    this.snapshot.supportingDocuments.forEach((document) => {
      versions.set(
        document.fileName,
        Math.max(versions.get(document.fileName) ?? 0, document.version),
      );
    });
    const uploaded = files.map((file, index): SupportingDocument => {
      const fileName = file.name || `supporting-document-${index + 1}.pdf`;
      const version = (versions.get(fileName) ?? 0) + 1;
      versions.set(fileName, version);
      return {
        id: `document-${Date.now()}-${index}`,
        fileName,
        kind: "other",
        uploadedAt: now(),
        version,
        status: "ready",
      };
    });
    this.snapshot.supportingDocuments = [
      ...this.snapshot.supportingDocuments,
      ...uploaded,
    ];
    return clone(uploaded);
  }

  async deleteDocument(id: string): Promise<SupportingDocument[]> {
    await delay(220);
    const exists = this.snapshot.supportingDocuments.some(
      (document) => document.id === id,
    );
    if (!exists) throw new Error("没有找到对应的求职资料。");
    this.snapshot.supportingDocuments = this.snapshot.supportingDocuments.filter(
      (document) => document.id !== id,
    );
    return clone(this.snapshot.supportingDocuments);
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
      createdAt: this.snapshot.jobGoal?.createdAt ?? now(),
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

  async startAgent(): Promise<WorkspaceSnapshot> {
    await delay(520);
    if (!this.snapshot.resume || this.snapshot.resume.parseStatus !== "succeeded") {
      throw new Error("简历解析成功后才能启动 Agent。");
    }
    if (!this.snapshot.jobGoal) throw new Error("请先创建求职目标。");
    if (this.snapshot.agentStatus === "finished")
      throw new Error("Agent 已结束，不能重复启动。");
    if (this.snapshot.agentStatus === "running") return clone(this.snapshot);
    this.snapshot.agentStatus = "running";
    this.snapshot.round = 1;
    if (this.snapshot.applications.length === 0) {
      this.snapshot.applications = clone(applicationFixtures);
      if (!this.snapshot.currentJob) {
        this.snapshot.currentJob = { ...clone(jobFixtures[0]), uploaded: true };
        this.snapshot.jobs = [this.snapshot.currentJob];
      }
      this.snapshot.conversations = clone(conversationFixtures);
    }
    return clone(this.snapshot);
  }

  async listApplications(): Promise<Application[]> {
    await delay(120);
    return clone(this.snapshot.applications);
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

  async sendConversationMessage(id: string, content: string): Promise<Conversation> {
    await delay(480);
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
