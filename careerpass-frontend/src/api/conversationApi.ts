import type { Conversation, Message, MessageAttachment } from "../domain/types";
import { ApiRequestError } from "./applicationApi";

interface ApiEnvelope<T> {
  code: number;
  msg: string;
  data: T | null;
}

interface MessageResponse {
  id: string;
  sender: "hr" | "agent";
  message_type: "text";
  status: "pending" | "sent" | "failed";
  content: string;
  created_at: string;
  attachments?: AttachmentResponse[];
}

interface AttachmentResponse {
  id: string;
  file_name: string;
  file_type: string;
  file_size_bytes: number;
  created_at: string;
  expires_at: string;
  status: MessageAttachment["status"];
}

interface ConversationResponse {
  id: string;
  application_id: string;
  job_title: string;
  candidate_name: string;
  messages: MessageResponse[];
}

const apiBaseUrl = import.meta.env.VITE_API_BASE_URL ?? "/api/v1";

async function parseResponse<T>(response: Response): Promise<T> {
  const payload = (await response.json()) as ApiEnvelope<T>;
  if (!response.ok || payload.data === null) {
    throw new ApiRequestError(payload.msg || "沟通数据加载失败，请稍后重试。", response.status);
  }
  return payload.data;
}

function mapMessage(value: MessageResponse): Message {
  return {
    id: value.id,
    sender: value.sender,
    text: value.content,
    createdAt: value.created_at,
    status: value.status,
    messageType: value.message_type,
    attachments: (value.attachments ?? []).map(mapAttachment),
  };
}

function mapAttachment(value: AttachmentResponse): MessageAttachment {
  return {
    id: value.id,
    fileName: value.file_name,
    fileType: value.file_type,
    fileSizeBytes: value.file_size_bytes,
    createdAt: value.created_at,
    expiresAt: value.expires_at,
    status: value.status,
  };
}

function mapConversation(value: ConversationResponse): Conversation {
  return {
    id: value.id,
    applicationId: value.application_id,
    jobTitle: value.job_title,
    candidateName: value.candidate_name,
    messages: value.messages.map(mapMessage),
  };
}

export async function listCurrentConversations(accessToken: string): Promise<Conversation[]> {
  const response = await fetch(`${apiBaseUrl}/applications/hr/current/conversations`, {
    headers: { Authorization: `Bearer ${accessToken}` },
  });
  const data = await parseResponse<{ conversations: ConversationResponse[]; total: number }>(response);
  return data.conversations.map(mapConversation);
}

export async function sendConversationMessage(
  applicationId: string,
  conversationId: string,
  content: string,
  clientMessageId: string,
  accessToken: string,
): Promise<Conversation> {
  const response = await fetch(`${apiBaseUrl}/applications/${applicationId}/conversation/messages`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${accessToken}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      conversation_id: conversationId,
      client_message_id: clientMessageId,
      content,
    }),
  });
  const data = await parseResponse<{
    conversation_id: string;
    received_message: MessageResponse;
    new_messages: MessageResponse[];
  }>(response);
  const conversations = await listCurrentConversations(accessToken);
  return conversations.find((item) => item.id === data.conversation_id) ?? {
    id: data.conversation_id,
    applicationId,
    jobTitle: "受控岗位",
    candidateName: "候选人",
    messages: data.new_messages.map(mapMessage),
  };
}

export async function downloadConversationAttachment(
  applicationId: string,
  messageId: string,
  attachmentId: string,
  fileName: string,
  accessToken: string,
): Promise<void> {
  const response = await fetch(
    `${apiBaseUrl}/applications/${applicationId}/conversation/messages/${messageId}/attachments/${attachmentId}/download`,
    { headers: { Authorization: `Bearer ${accessToken}` } },
  );
  if (!response.ok) {
    let message = "附件下载失败，请稍后重试。";
    try {
      const payload = (await response.json()) as ApiEnvelope<unknown>;
      message = payload.msg || message;
    } catch {
      // Preserve the safe frontend fallback for non-JSON download errors.
    }
    throw new ApiRequestError(message, response.status);
  }
  const blob = await response.blob();
  const objectUrl = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = objectUrl;
  anchor.download = fileName;
  anchor.click();
  URL.revokeObjectURL(objectUrl);
}
