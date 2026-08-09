import type { Application } from "../../../domain/types";

export const applicationFixtures: Application[] = [
  {
    id: "application-001",
    jobId: "job-001",
    candidateId: "candidate-001",
    jobTitle: "AI 产品前端工程师",
    company: "界面实验室",
    location: "深圳",
    salary: "16-28K",
    status: "screening",
    appliedAt: "2026-08-08T09:00:00+08:00",
    lastContactAt: "2026-08-08T09:18:00+08:00",
  },
  {
    id: "application-002",
    jobId: "job-002",
    candidateId: "candidate-001",
    jobTitle: "React 应用开发工程师",
    company: "星河科技",
    location: "上海",
    salary: "18-30K",
    status: "submitted",
    appliedAt: "2026-08-08T09:02:00+08:00",
    lastContactAt: null,
  },
];
