import type { Application } from "../../../domain/types";

export const demoApplications: Application[] = [
  {
    id: "application-demo-001",
    jobId: "job-demo-001",
    candidateId: "candidate-demo",
    jobTitle: "AI 产品前端工程师",
    company: "界面实验室",
    location: "深圳",
    salary: "16-28K",
    status: "screening",
    appliedAt: "2026-08-08T09:00:00+08:00",
    lastContactAt: "2026-08-08T09:18:00+08:00",
  },
  {
    id: "application-demo-002",
    jobId: "job-demo-002",
    candidateId: "candidate-demo",
    jobTitle: "React 应用开发工程师",
    company: "星河科技",
    location: "上海",
    salary: "18-30K",
    status: "submitted",
    appliedAt: "2026-08-08T09:02:00+08:00",
    lastContactAt: null,
  },
];
