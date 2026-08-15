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
import { agentStatusMeta, resumeStatusMeta } from "../../domain/mappings";
import { useWorkspaceRefresh } from "../../features/workspace/useWorkspaceRefresh";
import { useWorkspaceStore } from "../../stores/workspace-store";

export function DocumentsPage() {
  useWorkspaceRefresh();
  const state = useWorkspaceStore((store) => store);
  const [toast, setToast] = useState<string | null>(null);
  if (!state.initialized) return <LoadingState />;
  const resumeLocked =
    state.agentStatus === "running" || state.agentStatus === "finished";
  const resumeStatus = state.resume
    ? resumeStatusMeta[state.resume.parseStatus]
    : resumeStatusMeta.not_uploaded;
  async function uploadResume(file: File) {
    try {
      await state.uploadResume(file);
      setToast("简历已上传，正在进行解析。");
    } catch {
      /* Store exposes the controlled error below. */
    }
  }
  async function uploadDocuments(files: File[]) {
    try {
      await state.uploadDocuments(files);
      setToast("其它资料已就绪。");
    } catch {
      /* controlled by store */
    }
  }
  async function removeDocument(id: string) {
    try {
      await state.deleteDocument(id);
      setToast("求职资料已删除。");
    } catch {
      /* controlled by store */
    }
  }
  return (
    <div className="page-view">
      <PageHeader
        eyebrow="CANDIDATE / DOCUMENTS"
        title="准备你的求职资料"
        description="上传简历和补充资料，系统将处理文件并更新资料状态。"
      />
      {state.error ? (
        <ErrorState description={state.error} onRetry={state.clearError} />
      ) : null}
      <section className="upload-grid">
        <article className="panel upload-panel">
          <div className="panel-heading">
            <div>
              <h2>正式简历</h2>
              <p className="muted-text">简历解析成功后才能创建求职目标。</p>
            </div>
            {state.resume ? (
              <StatusBadge tone={resumeStatus.tone}>{resumeStatus.label}</StatusBadge>
            ) : null}
          </div>
          <FileUpload
            label={state.resume ? "重新选择简历" : "上传一份简历"}
            description={
              resumeLocked ? "当前投递轮次已绑定简历。" : "仅支持文本型 PDF 简历。"
            }
            accept=".pdf"
            disabled={resumeLocked || state.resumeLoading}
            onFiles={(files) => void uploadResume(files[0])}
          />
          {state.resume ? (
            <FileInfoCard
              fileName={state.resume.fileName}
              version={state.resume.version}
              uploadedAt={state.resume.uploadedAt}
            />
          ) : null}
        </article>
        <article className="panel upload-panel">
          <div className="panel-heading">
            <div>
              <h2>其它求职资料</h2>
              <p className="muted-text">证书、作品集等资料只保存就绪状态。</p>
            </div>
            <StatusBadge tone="neutral">
              {state.supportingDocuments.length
                ? `${state.supportingDocuments.length} 份已就绪`
                : "可选"}
            </StatusBadge>
          </div>
          <FileUpload
            label="上传其它资料"
            description="可以一次选择多份文件，后续分批追加。"
            accept=".pdf,.doc,.docx,.png,.jpg"
            multiple
            disabled={state.supportingDocumentsLoading}
            disabledLabel="正在处理…"
            onFiles={(files) => void uploadDocuments(files)}
          />
          {state.supportingDocuments.length ? (
            <div className="file-list-scroll" aria-label="其它求职资料列表" role="region">
              <div className="file-list">
                {state.supportingDocuments.map((document) => (
                  <FileInfoCard
                    key={document.id}
                    fileName={document.fileName}
                    version={document.version}
                    uploadedAt={document.uploadedAt}
                    deleteLabel={document.fileName}
                    deleteDisabled={state.supportingDocumentsLoading}
                    onDelete={() => void removeDocument(document.id)}
                  />
                ))}
              </div>
            </div>
          ) : (
            <div className="inline-empty">还没有其它资料，可稍后补充。</div>
          )}
        </article>
      </section>
      <section className="notice-card">
        <div className="notice-icon">i</div>
        <div>
          <strong>{agentStatusMeta[state.agentStatus].label}</strong>
          <p>
            {resumeLocked
              ? "当前轮次已经绑定这份简历，历史投递记录会继续保留。"
              : "在 Agent 启动前，你可以重新上传简历并重新解析。"}
          </p>
        </div>
      </section>
      {toast ? <Toast message={toast} onClose={() => setToast(null)} /> : null}
    </div>
  );
}
