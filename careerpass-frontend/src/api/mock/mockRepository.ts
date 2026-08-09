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
    const uploaded = files.map((file, index): SupportingDocument => ({
      id: `document-${Date.now()}-${index}`,
      fileName: file.name || `supporting-document-${index + 1}.pdf`,
      kind: "other",
      uploadedAt: now(),
      status: "ready",
    }));
    this.snapshot.supportingDocuments = [
      ...this.snapshot.supportingDocuments,
      ...uploaded,
    ];
    return clone(uploaded);
  }

  async getCurrentJob(): Promise<Job | null> {
    return clone(this.snapshot.currentJob);
  }

  async uploadJob(file: File): Promise<Job> {
    await delay(430);
    const job = clone(jobFixtures[0]);
    job.uploaded = true;
    job.summary = file.name ? `${job.summary} 已上传文件：${file.name}` : job.summary;
    this.snapshot.currentJob = job;
    return clone(job);
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
      this.snapshot.currentJob ??= { ...clone(jobFixtures[0]), uploaded: true };
      this.snapshot.conversations = [
        {
          id: "conversation-001",
          applicationId: "application-001",
          jobTitle: "AI 产品前端工程师",
          candidateName: "Alex Chen",
          messages: [
            {
              id: "message-001",
              sender: "agent",
              text: "您好，我是 Alex 的求职 Agent，感谢您查看这份投递。",
              createdAt: "2026-08-08T09:18:00+08:00",
            },
          ],
        },
      ];
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
