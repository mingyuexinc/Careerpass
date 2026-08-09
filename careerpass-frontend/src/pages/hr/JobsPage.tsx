import { useState } from "react";
import { PageHeader } from "../../components/PageHeader";
import {
  ErrorState,
  FileInfoCard,
  FileUpload,
  LoadingState,
  StatusBadge,
  Toast,
} from "../../components/ui";
import { useWorkspaceRefresh } from "../../features/workspace/useWorkspaceRefresh";
import { useWorkspaceStore } from "../../stores/workspace-store";

export function JobsPage() {
  useWorkspaceRefresh();
  const state = useWorkspaceStore((store) => store);
  const [toast, setToast] = useState<string | null>(null);
  if (!state.initialized) return <LoadingState />;
  async function upload(files: File[]) {
    try {
      await state.uploadJobs(files);
      setToast(`${files.length} 份岗位 JD 已准备完成。`);
    } catch {
      /* controlled by store */
    }
  }
  async function removeJob(id: string) {
    try {
      await state.deleteJob(id);
      setToast("岗位 JD 已删除。");
    } catch {
      /* controlled by store */
    }
  }
  return (
    <div className="page-view">
      <PageHeader
        eyebrow="HR / JOBS"
        title="准备岗位 JD"
        description="上传岗位资料，为求职者 Agent 准备可以匹配和投递的岗位。"
      />
      {state.error ? (
        <ErrorState description={state.error} onRetry={state.clearError} />
      ) : null}
      <section className="upload-grid">
        <article className="panel upload-panel">
          <div className="panel-heading">
            <div>
              <h2>岗位 JD 上传</h2>
              <p className="muted-text">当前版本支持分批维护多份岗位 JD。</p>
            </div>
            <StatusBadge tone={state.currentJob ? "success" : "neutral"}>
              {state.jobs.length ? `${state.jobs.length} 份已准备` : "待上传"}
            </StatusBadge>
          </div>
          <FileUpload
            label={state.currentJob ? "继续上传岗位 JD" : "选择岗位 JD"}
            description="支持 PDF、DOCX 等常见格式，可分批追加。"
            accept=".pdf,.doc,.docx"
            multiple
            disabled={state.loading}
            onFiles={(files) => void upload(files)}
          />
          {state.jobs.length || state.currentJob ? (
            <div className="file-list-scroll" aria-label="岗位 JD 列表" role="region">
              <div className="file-list">
                {(state.jobs.length ? state.jobs : [state.currentJob]).map((job) => (
                  <FileInfoCard
                    key={job.id}
                    fileName={job.fileName}
                    iconLabel="JD"
                    primaryText={`${job.title} · ${job.company} · ${job.location} · ${job.salary}`}
                    version={job.version}
                    uploadedAt={job.uploadedAt}
                    deleteLabel="岗位 JD"
                    deleteDisabled={state.loading}
                    onDelete={() => void removeJob(job.id)}
                  />
                ))}
              </div>
            </div>
          ) : null}
        </article>
      </section>
      {toast ? <Toast message={toast} onClose={() => setToast(null)} /> : null}
    </div>
  );
}
