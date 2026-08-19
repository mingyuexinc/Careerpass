import type { AgentStatus, DeliveryProgress, ResumeParseStatus } from "./types";

export const resumeStatusMeta: Record<
  ResumeParseStatus,
  { label: string; tone: "neutral" | "info" | "success" | "danger" }
> = {
  not_uploaded: { label: "尚未上传", tone: "neutral" },
  uploading: { label: "上传中", tone: "info" },
  processing: { label: "解析中", tone: "info" },
  succeeded: { label: "解析成功", tone: "success" },
  failed: { label: "解析失败", tone: "danger" },
};

export const agentStatusMeta: Record<
  AgentStatus,
  { label: string; description: string; tone: "neutral" | "info" | "success" }
> = {
  not_started: {
    label: "尚未启动",
    description: "完成资料准备和求职目标后即可启动。",
    tone: "neutral",
  },
  ready: {
    label: "可以启动",
    description: "启动条件已满足，Agent 已准备就绪。",
    tone: "info",
  },
  running: {
    label: "Agent 运行中",
    description: "求职 Agent 已启动，正在准备首轮匹配。",
    tone: "info",
  },
  finished: {
    label: "Agent 已结束",
    description: "目标 Offer 数已达成，系统已停止新增投递。",
    tone: "success",
  },
};

export const deliveryProgressOrder: DeliveryProgress[] = [
  "submitted",
  "screening",
  "written_test",
  "interview_1",
  "interview_2",
  "interview_3",
  "hr_interview",
  "offer",
];

export const deliveryProgressMeta: Record<
  DeliveryProgress,
  { label: string; tone: "neutral" | "info" | "success" | "danger"; terminal: boolean }
> = {
  submitted: { label: "已投递", tone: "neutral", terminal: false },
  screening: { label: "初筛中", tone: "info", terminal: false },
  written_test: { label: "笔试", tone: "info", terminal: false },
  interview_1: { label: "一面", tone: "info", terminal: false },
  interview_2: { label: "二面", tone: "info", terminal: false },
  interview_3: { label: "三面", tone: "info", terminal: false },
  hr_interview: { label: "HR 面", tone: "info", terminal: false },
  offer: { label: "获得 Offer", tone: "success", terminal: true },
  terminated: { label: "流程终止", tone: "danger", terminal: true },
};

export function isValidDeliveryTransition(
  current: DeliveryProgress,
  next: DeliveryProgress,
): boolean {
  if (current === next) return true;
  if (deliveryProgressMeta[current].terminal) return false;
  if (next === "terminated") return true;
  const currentIndex = deliveryProgressOrder.indexOf(current);
  const nextIndex = deliveryProgressOrder.indexOf(next);
  return nextIndex > currentIndex;
}

export function getAllowedDeliveryTransitions(
  current: DeliveryProgress,
): DeliveryProgress[] {
  if (deliveryProgressMeta[current].terminal) return [];
  const currentIndex = deliveryProgressOrder.indexOf(current);
  return [
    ...deliveryProgressOrder.slice(currentIndex + 1),
    "terminated",
  ];
}

export function getOfferCount(statuses: DeliveryProgress[]): number {
  return statuses.filter((status) => status === "offer").length;
}
