import type { Job } from "../../../domain/types";

export const jobFixtures: Job[] = [
  {
    id: "job-001",
    title: "AI 产品前端工程师",
    company: "界面实验室",
    location: "深圳",
    salary: "16-28K",
    summary: "负责数据产品和 AI 应用前端界面的设计实现。",
    uploaded: false,
  },
  {
    id: "job-002",
    title: "React 应用开发工程师",
    company: "星河科技",
    location: "上海",
    salary: "18-30K",
    summary: "参与企业级工作台、组件系统和前端工程质量建设。",
    uploaded: false,
  },
];
