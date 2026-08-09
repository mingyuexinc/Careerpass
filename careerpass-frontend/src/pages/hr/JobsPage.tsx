import { useState } from "react";
import { PageHeader } from "../../components/PageHeader";
import {
  ErrorState,
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
  async function upload(file: File) {
    try {
      await state.uploadJob(file);
      setToast("岗位 JD 已准备完成。");
    } catch {
      /* controlled by store */
    }
  }
  return (
    <div className="page-view">
      <PageHeader
        eyebrow="HR / JOBS"
        title="准备岗位 JD"
        description="上传一份岗位资料，为求职者 Agent 准备可以匹配和投递的岗位。"
      />
      {state.error ? (
        <ErrorState description={state.error} onRetry={state.clearError} />
      ) : null}
      <section className="upload-grid">
        <article className="panel upload-panel">
          <div className="panel-heading">
            <div>
              <h2>岗位 JD 上传</h2>
              <p className="muted-text">当前版本支持维护一份岗位 JD。</p>
            </div>
            <StatusBadge tone={state.currentJob ? "success" : "neutral"}>
              {state.currentJob ? "已准备" : "待上传"}
            </StatusBadge>
          </div>
          <FileUpload
            label={state.currentJob ? "重新上传岗位 JD" : "选择岗位 JD"}
            description="支持 PDF、DOCX 等常见格式。"
            accept=".pdf,.doc,.docx"
            disabled={state.loading}
            onFiles={(files) => void upload(files[0])}
          />
          {state.currentJob ? (
            <div className="job-summary">
              <div className="job-symbol">⌁</div>
              <div>
                <h2>{state.currentJob.title}</h2>
                <p>
                  {state.currentJob.company} · {state.currentJob.location} ·{" "}
                  {state.currentJob.salary}
                </p>
                <span>{state.currentJob.summary}</span>
              </div>
            </div>
          ) : null}
        </article>
        <article className="panel">
          <div className="panel-heading">
            <h2>当前版本范围</h2>
            <StatusBadge>当前版本</StatusBadge>
          </div>
          <div className="notice-list">
            <div className="notice-row">
              <span>1</span>
              <div>
                <strong>一份岗位</strong>
                <p>上传新的 JD 会替换当前岗位。</p>
              </div>
            </div>
            <div className="notice-row">
              <span>2</span>
              <div>
                <strong>不做复杂管理</strong>
                <p>当前版本不包含岗位编辑、删除和岗位目录。</p>
              </div>
            </div>
            <div className="notice-row">
              <span>3</span>
              <div>
                <strong>服务 Agent</strong>
                <p>岗位准备后可查看沟通和投递进度。</p>
              </div>
            </div>
          </div>
        </article>
      </section>
      {toast ? <Toast message={toast} onClose={() => setToast(null)} /> : null}
    </div>
  );
}
