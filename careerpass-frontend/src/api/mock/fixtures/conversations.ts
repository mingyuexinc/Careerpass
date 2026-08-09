import type { Conversation } from "../../../domain/types";

export const conversationFixtures: Conversation[] = [
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
  {
    id: "conversation-002",
    applicationId: "application-002",
    jobTitle: "React 应用开发工程师",
    candidateName: "Alex Chen",
    messages: [
      {
        id: "message-002",
        sender: "agent",
        text: "您好，我是 Alex 的求职 Agent，感谢您查看这份投递。",
        createdAt: "2026-08-08T09:20:00+08:00",
      },
    ],
  },
];
