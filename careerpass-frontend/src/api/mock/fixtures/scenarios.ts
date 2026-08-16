import type { WorkspaceSnapshot } from "../../../domain/types";
import { applicationFixtures } from "./applications";
import { conversationFixtures } from "./conversations";
import { jobFixtures } from "./jobs";

export function createInitialSnapshot(): WorkspaceSnapshot {
  return {
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
}

export function createRunningSnapshot(): WorkspaceSnapshot {
  const applications = structuredClone(applicationFixtures);
  const job = structuredClone(jobFixtures[0]);
  job.uploaded = true;
  return {
    resume: {
      id: "resume-001",
      fileName: "Alex_Chen_Resume.pdf",
      uploadedAt: "2026-08-08T08:50:00+08:00",
      parseStatus: "succeeded",
      version: 1,
    },
    supportingDocuments: [],
    supportingDocumentUploads: [],
    jobs: [job],
    currentJob: job,
    jobGoal: {
      id: "goal-001",
      offerTarget: 1,
      title: "前端工程师",
      filters: "优先 AI 应用和数据产品，不考虑长期出差岗位。",
      status: "active",
      createdAt: "2026-08-08T08:55:00+08:00",
      updatedAt: "2026-08-08T08:55:00+08:00",
    },
    agentStatus: "running",
    round: 1,
    applications,
    conversations: structuredClone(conversationFixtures),
  };
}
