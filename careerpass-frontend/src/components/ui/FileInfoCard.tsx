import type { ReactNode } from "react";

interface FileInfoCardProps {
  fileName: string;
  version?: number;
  uploadedAt: string;
  iconLabel?: string;
  primaryText?: string;
  deleteLabel?: string;
  onDelete?: () => void;
  deleteDisabled?: boolean;
  trailingContent?: ReactNode;
}

function getFileType(fileName: string): string {
  const separatorIndex = fileName.lastIndexOf(".");
  if (separatorIndex < 0 || separatorIndex === fileName.length - 1) return "FILE";
  const extension = fileName.slice(separatorIndex + 1).toUpperCase();
  return extension.length <= 4 ? extension : "FILE";
}

function formatUploadTime(uploadedAt: string): string {
  return new Intl.DateTimeFormat("zh-CN", {
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    hourCycle: "h23",
  }).format(new Date(uploadedAt));
}

export function FileInfoCard({
  fileName,
  version,
  uploadedAt,
  iconLabel,
  primaryText,
  deleteLabel,
  onDelete,
  deleteDisabled = false,
  trailingContent,
}: FileInfoCardProps) {
  const displayText = primaryText ?? fileName;
  return (
    <div className={`file-info-card${onDelete ? " has-delete" : ""}`}>
      <span className="file-type-icon" aria-hidden="true">
        {iconLabel ?? getFileType(fileName)}
      </span>
      <div className="file-info-copy">
        <strong className="file-info-name" title={displayText}>
          {displayText}
        </strong>
        <span className="file-info-meta">
          {version === undefined ? "上传于" : `版本 ${version} · 上传于`}{" "}
          {formatUploadTime(uploadedAt)}
        </span>
      </div>
      {trailingContent ? (
        <div className="file-info-trailing">{trailingContent}</div>
      ) : null}
      {onDelete ? (
        <button
          type="button"
          className="file-info-delete"
          aria-label={`删除 ${deleteLabel ?? displayText}`}
          title="删除资料"
          disabled={deleteDisabled}
          onClick={onDelete}
        >
          ×
        </button>
      ) : null}
    </div>
  );
}
