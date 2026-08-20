import { useState } from "react";
import type { Message, MessageAttachment } from "../../domain/types";

function formatSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  return `${(bytes / 1024).toFixed(1)} KB`;
}

export function MessageList({
  messages,
  onDownload,
}: {
  messages: Message[];
  onDownload?: (message: Message, attachment: MessageAttachment) => Promise<void>;
}) {
  const [downloadingId, setDownloadingId] = useState<string | null>(null);
  const [downloadError, setDownloadError] = useState<string | null>(null);

  async function handleDownload(message: Message, attachment: MessageAttachment) {
    if (!onDownload || attachment.status === "expired") return;
    setDownloadingId(attachment.id);
    setDownloadError(null);
    try {
      await onDownload(message, attachment);
    } catch (error) {
      setDownloadError(error instanceof Error ? error.message : "附件下载失败，请稍后重试。");
    } finally {
      setDownloadingId(null);
    }
  }

  return (
    <div className="message-list">
      {messages.map((message) => (
        <div
          className={`message-row ${message.sender === "hr" ? "is-hr" : "is-agent"}`}
          key={message.id}
        >
          <div className="message-bubble">
            <strong>{message.sender === "hr" ? "HR" : "求职 Agent"}</strong>
            <span>{message.text}</span>
            {message.attachments?.map((attachment) => (
              <div className="message-attachment" key={attachment.id}>
                <div>
                  <strong>{attachment.fileName}</strong>
                  <small>
                    {attachment.fileType.toUpperCase()} · {formatSize(attachment.fileSizeBytes)}
                  </small>
                </div>
                <button
                  type="button"
                  disabled={downloadingId === attachment.id || attachment.status === "expired"}
                  onClick={() => void handleDownload(message, attachment)}
                >
                  {downloadingId === attachment.id
                    ? "下载中"
                    : attachment.status === "expired"
                      ? "已过期"
                      : "下载"}
                </button>
                <small>有效期至 {new Date(attachment.expiresAt).toLocaleString("zh-CN")}</small>
              </div>
            ))}
            <time>
              {new Date(message.createdAt).toLocaleTimeString("zh-CN", {
                hour: "2-digit",
                minute: "2-digit",
              })}
            </time>
          </div>
        </div>
      ))}
      {downloadError ? <div className="message-attachment-error">{downloadError}</div> : null}
    </div>
  );
}
