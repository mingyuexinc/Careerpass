import { useState } from "react";
import { PageHeader } from "../../components/PageHeader";
import { ErrorState, FileUpload, StatusBadge } from "../../components/ui";
import { uploadJobsWithApi, type JobUploadResult } from "../../api/jobUploadApi";

export function JobsPage() {
  const [uploadResults, setUploadResults] = useState<JobUploadResult[]>([]);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function upload(files: File[]) {
    if (!files.length) return;
    setUploading(true);
    setError(null);
    setUploadResults([]);
    try {
      const results = await uploadJobsWithApi(files);
      setUploadResults(results);
    } catch (uploadError) {
      setError(
        uploadError instanceof Error ? uploadError.message : "岗位 JD 上传失败，请稍后重试。",
      );
    } finally {
      setUploading(false);
    }
  }

  return (
    <div className="page-view">
      <PageHeader
        eyebrow="HR / JOBS"
        title="准备岗位 JD"
        description="上传岗位 JD，建立后续流程可使用的岗位输入资源。"
      />
      {error ? (
        <ErrorState description={error} onRetry={() => setError(null)} />
      ) : null}
      <section className="upload-grid">
        <article className="panel upload-panel">
          <div className="panel-heading">
            <div>
              <h2>岗位 JD 上传</h2>
              <p className="muted-text">选择一份或多份 Markdown（.md）文件后自动上传。</p>
            </div>
            <StatusBadge tone={uploading ? "info" : uploadResults.length ? "success" : "neutral"}>
              {uploading ? "上传中" : uploadResults.length ? `${uploadResults.length} 份已处理` : "待上传"}
            </StatusBadge>
          </div>
          <FileUpload
            label="选择岗位 JD"
            description="仅支持 Markdown（.md）文件，选择后自动上传。"
            accept=".md"
            multiple
            disabled={uploading}
            onFiles={(files) => void upload(files)}
          />
          {uploadResults.length ? (
            <div className="file-list-scroll" aria-label="岗位 JD 上传结果" role="region">
              <div className="file-list" role="list">
                {uploadResults.map((result) => {
                  const succeeded = result.outcome !== "failed";
                  return (
                    <div className="file-info-card" key={`${result.fileName}-${result.jobId ?? result.errorCode}`} role="listitem">
                      <span className="file-type-icon" aria-hidden="true">JD</span>
                      <div className="file-info-copy">
                        <strong className="file-info-name">{result.fileName}</strong>
                        <span className="file-info-meta">
                          {succeeded ? "上传成功" : "上传失败"}
                        </span>
                      </div>
                      <StatusBadge tone={succeeded ? "success" : "danger"}>
                        {succeeded ? "上传成功" : "上传失败"}
                      </StatusBadge>
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
