import { useState } from "react";
import { PageHeader } from "../../components/PageHeader";
import { Button, ErrorState, FileInfoCard, FileUpload, StatusBadge } from "../../components/ui";
import { uploadJobsWithApi } from "../../api/jobUploadApi";
import { useWorkspaceRefresh } from "../../features/workspace/useWorkspaceRefresh";
import { useWorkspaceStore } from "../../stores/workspace-store";

export function JobsPage() {
  useWorkspaceRefresh();
  const { hrJobs, refresh, deleteJob, retryJobParse } = useWorkspaceStore((state) => state);
  const [uploading, setUploading] = useState(false);
  const [retryingJobId, setRetryingJobId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function upload(files: File[]) {
    if (!files.length) return;
    setUploading(true);
    setError(null);
    try {
      const results = await uploadJobsWithApi(files);
      const failedUploads = results.filter((result) => result.outcome === "failed");
      if (failedUploads.length) {
        const failedFileNames = failedUploads.map((result) => result.fileName).join("、");
        setError(
          failedUploads.length === 1
            ? `${failedFileNames} 上传失败，请检查文件格式或大小。`
            : `${failedUploads.length} 个岗位 JD 上传失败：${failedFileNames}。`,
        );
      }
      await refresh();
    } catch (uploadError) {
      setError(
        uploadError instanceof Error
          ? uploadError.message
          : "岗位 JD 上传失败，请稍后重试。",
      );
    } finally {
      setUploading(false);
    }
  }

  async function removeJob(id: string) {
    try {
      await deleteJob(id);
    } catch {
      // The workspace store exposes the controlled error state.
    }
  }

  async function retry(id: string) {
    setRetryingJobId(id);
    try {
      await retryJobParse(id);
      await refresh({ preserveView: true });
    } catch {
      // The workspace store exposes the controlled user-facing error.
    } finally {
      setRetryingJobId(null);
    }
  }

  function parseStatus(job: (typeof hrJobs)[number]) {
    if (job.parseStatus === "succeeded") return { label: "已解析", tone: "success" as const };
    if (job.parseStatus === "queued" || job.parseStatus === "running") {
      return { label: "解析中", tone: "info" as const };
    }
    if (job.parseStatus === "failed") {
      const reason = job.parseFailureKind === "missing_core_fields"
        ? "缺少核心字段"
        : job.parseFailureKind === "invalid_content"
          ? "内容不可读"
          : "暂时不可用或重试耗尽";
      return { label: `解析失败：${reason}`, tone: "danger" as const };
    }
    return { label: "等待解析", tone: "neutral" as const };
  }

  return (
    <div className="page-view">
      <PageHeader
        eyebrow="HR / JOBS"
        title="准备岗位 JD"
        description="上传岗位 JD，建立后续流程可使用的岗位输入资源。"
      />
      {error ? <ErrorState description={error} onRetry={() => setError(null)} /> : null}
      <section className="upload-grid">
        <article className="panel upload-panel">
          <div className="panel-heading">
            <div>
              <h2>岗位 JD 上传</h2>
              <p className="muted-text">选择一份或多份 Markdown（.md）文件后自动上传。</p>
            </div>
            <StatusBadge
              tone={uploading ? "info" : hrJobs.length ? "success" : "neutral"}
            >
              {uploading
                ? "上传中"
                : hrJobs.length
                  ? `${hrJobs.length} 份已保存`
                  : "待上传"}
            </StatusBadge>
          </div>
          <FileUpload
            label="上传岗位 JD"
            description="支持 Markdown（.md），选择后自动上传。"
            accept=".md"
            multiple
            disabled={uploading}
            onFiles={(files) => void upload(files)}
          />
          {hrJobs.length ? (
            <div className="file-list-scroll" aria-label="已上传岗位列表" role="region">
              <div className="file-list" role="list">
                {hrJobs.map((job) => {
                  const status = parseStatus(job);
                  return (
                    <div key={job.id} className="job-upload-item">
                      <FileInfoCard
                        fileName={job.fileName ?? job.jobTitle ?? "岗位 JD"}
                        uploadedAt={job.createdAt}
                        iconLabel="MD"
                        deleteLabel={job.fileName ?? job.jobTitle ?? "岗位 JD"}
                        deleteDisabled={
                          job.parseStatus !== "succeeded" && job.parseStatus !== "failed"
                            ? true
                            : job.matchStarted
                        }
                        onDelete={() => void removeJob(job.id)}
                        trailingContent={
                          <>
                            <StatusBadge tone={status.tone}>{status.label}</StatusBadge>
                            {job.parseStatus === "failed" && job.parseCanRetry && !job.matchStarted ? (
                              <Button
                                type="button"
                                disabled={retryingJobId === job.id}
                                onClick={() => void retry(job.id)}
                              >
                                {retryingJobId === job.id ? "重新解析中…" : "重新解析"}
                              </Button>
                            ) : null}
                          </>
                        }
                      />
                    </div>
                  );
                })}
              </div>
            </div>
          ) : null}
        </article>
      </section>
    </div>
  );
}
