import { useState } from "react";
import type { Message, MessageAttachment } from "../../domain/types";

function formatSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function formatDateTime(value: string): string {
  return new Intl.DateTimeFormat("zh-CN", {
    month: "numeric",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
    hourCycle: "h23",
  }).format(new Date(value));
}

function getFileType(fileName: string, fileType: string): string {
  const extension = fileName.split(".").pop() || fileType;
  return extension.toUpperCase().slice(0, 4) || "FILE";
}

function getAttachmentActionLabel(
  attachment: MessageAttachment,
  downloading: boolean,
  downloaded: boolean,
  failedAfterDownload: boolean,
): string {
  if (downloading) return "下载中";
  if (attachment.status === "preparing") return "准备中";
  if (attachment.status === "expired") return "已过期";
  if (downloaded) return "已下载";
  if (attachment.status === "failed" || failedAfterDownload) return "重试下载";
  return "下载附件";
}

function AttachmentCard({
  message,
  attachment,
  downloading,
  downloaded,
  failedAfterDownload,
  onDownload,
}: {
  message: Message;
  attachment: MessageAttachment;
  downloading: boolean;
  downloaded: boolean;
  failedAfterDownload: boolean;
  onDownload?: (message: Message, attachment: MessageAttachment) => Promise<void>;
}) {
  const isUnavailable = attachment.status === "expired" || attachment.status === "preparing";
  const actionLabel = getAttachmentActionLabel(
    attachment,
    downloading,
    downloaded,
    failedAfterDownload,
  );
  return (
    <article
      className={`message-attachment-card is-${failedAfterDownload ? "failed" : attachment.status}`}
      aria-label={`附件 ${attachment.fileName}`}
    >
      <div className="message-attachment-main">
        <span className="message-attachment-icon" aria-hidden="true">
          {getFileType(attachment.fileName, attachment.fileType)}
        </span>
        <div className="message-attachment-copy">
          <strong className="message-attachment-name" title={attachment.fileName}>
            {attachment.fileName}
          </strong>
          <span className="message-attachment-meta">
            {attachment.fileType.toUpperCase()} · {formatSize(attachment.fileSizeBytes)}
          </span>
        </div>
        <span className="message-attachment-status">
          {attachment.status === "expired"
            ? "已过期"
            : attachment.status === "preparing"
              ? "准备中"
            : attachment.status === "failed" || failedAfterDownload
                ? "下载失败"
                : downloaded
                  ? "已下载"
                  : "可下载"}
        </span>
      </div>
      <div className="message-attachment-details">
        <span>接收于 {formatDateTime(attachment.createdAt)}</span>
        <span>有效期至 {formatDateTime(attachment.expiresAt)}</span>
      </div>
      <div className="message-attachment-actions">
        <button
          type="button"
          className="button button-secondary message-attachment-download"
          aria-label={`${actionLabel} ${attachment.fileName}`}
          disabled={!onDownload || downloading || isUnavailable}
          onClick={() => onDownload?.(message, attachment)}
        >
          {actionLabel}
        </button>
      </div>
    </article>
  );
}

export function MessageList({
  messages,
  agentName,
  onDownload,
}: {
  messages: Message[];
  agentName: string;
  onDownload?: (message: Message, attachment: MessageAttachment) => Promise<void>;
}) {
  const [downloadingId, setDownloadingId] = useState<string | null>(null);
  const [downloadedIds, setDownloadedIds] = useState<Set<string>>(() => new Set());
  const [failedDownloadIds, setFailedDownloadIds] = useState<Set<string>>(() => new Set());
  const [downloadError, setDownloadError] = useState<string | null>(null);

  async function handleDownload(message: Message, attachment: MessageAttachment) {
    if (
      !onDownload ||
      downloadingId === attachment.id ||
      attachment.status === "expired" ||
      attachment.status === "preparing"
    ) {
      return;
    }
    setDownloadingId(attachment.id);
    setDownloadError(null);
    try {
      await onDownload(message, attachment);
      setDownloadedIds((current) => new Set(current).add(attachment.id));
      setFailedDownloadIds((current) => {
        const next = new Set(current);
        next.delete(attachment.id);
        return next;
      });
    } catch (error) {
      setFailedDownloadIds((current) => new Set(current).add(attachment.id));
      setDownloadError(error instanceof Error ? error.message : "附件下载失败，请稍后重试。");
    } finally {
      setDownloadingId(null);
    }
  }

  return (
    <div className="message-list">
      {messages.map((message) => {
        const attachments = message.attachments ?? [];
        // An Agent attachment message is attachment-only even when a legacy
        // API response still contains the old success prompt in `text`.
        const attachmentOnly = message.sender === "agent" && attachments.length > 0;
        return (
          <div
            className={`message-row ${message.sender === "hr" ? "is-hr" : "is-agent"}${
              attachmentOnly ? " is-attachment-only" : ""
            }`}
            key={message.id}
          >
            {attachmentOnly ? (
              <div className="message-attachment-stack">
                {attachments.map((attachment) => (
                  <AttachmentCard
                    key={attachment.id}
                    message={message}
                    attachment={attachment}
                    downloading={downloadingId === attachment.id}
                    downloaded={downloadedIds.has(attachment.id)}
                    failedAfterDownload={failedDownloadIds.has(attachment.id)}
                    onDownload={
                      onDownload
                        ? (currentMessage, currentAttachment) =>
                            handleDownload(currentMessage, currentAttachment)
                        : undefined
                    }
                  />
                ))}
              </div>
            ) : (
              <div className="message-bubble">
                <strong>{message.sender === "hr" ? "HR" : agentName}</strong>
                {message.text ? <span>{message.text}</span> : null}
                {attachments.map((attachment) => (
                  <AttachmentCard
                    key={attachment.id}
                    message={message}
                    attachment={attachment}
                    downloading={downloadingId === attachment.id}
                    downloaded={downloadedIds.has(attachment.id)}
                    failedAfterDownload={failedDownloadIds.has(attachment.id)}
                    onDownload={
                      onDownload
                        ? (currentMessage, currentAttachment) =>
                            handleDownload(currentMessage, currentAttachment)
                        : undefined
                    }
                  />
                ))}
                <time>
                  {new Date(message.createdAt).toLocaleTimeString("zh-CN", {
                    hour: "2-digit",
                    minute: "2-digit",
                  })}
                </time>
              </div>
            )}
          </div>
        );
      })}
      {downloadError ? <div className="message-attachment-error">{downloadError}</div> : null}
    </div>
  );
}
