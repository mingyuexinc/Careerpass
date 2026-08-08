import type { Conversation, DemoSnapshot } from "../../../domain/types";
import { demoApplications } from "./applications";
import { demoJobs } from "./jobs";

export const initialConversations: Conversation[] = [];

export function createInitialSnapshot(): DemoSnapshot {
  return {
    resume: null,
    supportingDocuments: [],
    currentJob: null,
    jobGoal: null,
    agentStatus: "not_started",
    round: 0,
    applications: [],
    conversations: [],
  };
}

export function createRunningSnapshot(): DemoSnapshot {
  const applications = structuredClone(demoApplications);
  const job = structuredClone(demoJobs[0]);
  job.uploaded = true;
  return {
    resume: {
      id: "resume-demo-001",
      fileName: "Alex_Chen_Resume.pdf",
      uploadedAt: "2026-08-08T08:50:00+08:00",
      parseStatus: "succeeded",
      version: 1,
    },
    supportingDocuments: [],
    currentJob: job,
    jobGoal: {
      id: "goal-demo-001",
      offerTarget: 1,
      title: "前端工程师",
      filters: "优先 AI 应用和数据产品，不考虑长期出差岗位。",
      createdAt: "2026-08-08T08:55:00+08:00",
    },
    agentStatus: "running",
    round: 1,
    applications,
    conversations: [],
  };
}
