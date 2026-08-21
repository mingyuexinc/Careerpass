import { useState } from "react";
import { PageHeader } from "../../components/PageHeader";
import { ErrorState, FileInfoCard, FileUpload, StatusBadge } from "../../components/ui";
import { uploadJobsWithApi } from "../../api/jobUploadApi";
import { useWorkspaceRefresh } from "../../features/workspace/useWorkspaceRefresh";
import { useWorkspaceStore } from "../../stores/workspace-store";

export function JobsPage() {
  useWorkspaceRefresh();
  const { hrJobs, refresh, deleteJob } = useWorkspaceStore((state) => state);
  const [uploading, setUploading] = useState(false);
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
                {hrJobs.map((job) => (
                  <FileInfoCard
                    key={job.id}
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
                  />
                ))}
              </div>
            </div>
          ) : null}
        </article>
      </section>
    </div>
  );
}
