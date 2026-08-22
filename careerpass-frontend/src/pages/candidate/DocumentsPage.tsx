import { useState } from "react";
import { PageHeader } from "../../components/PageHeader";
import {
  ErrorState,
  FileInfoCard,
  FileUpload,
  LoadingState,
  StatusBadge,
  Toast,
  type ToastTone,
} from "../../components/ui";
import { agentStatusMeta, resumeStatusMeta } from "../../domain/mappings";
import { useWorkspaceRefresh } from "../../features/workspace/useWorkspaceRefresh";
import { useWorkspaceStore } from "../../stores/workspace-store";

export function DocumentsPage() {
  useWorkspaceRefresh();
  const state = useWorkspaceStore((store) => store);
  const [toast, setToast] = useState<{
    message: string;
    tone: ToastTone;
  } | null>(null);
  const [documentUploadRequestFailed, setDocumentUploadRequestFailed] = useState(false);
  if (!state.initialized) return <LoadingState />;
  const resumeLocked =
    state.agentStatus === "running" || state.agentStatus === "finished";
  const resumeExists = Boolean(state.resume);
  const resumeDeleteAllowed = Boolean(
    state.resume &&
      ["not_started", "ready"].includes(state.agentStatus) &&
      ["succeeded", "failed"].includes(state.resume.parseStatus),
  );
  const resumeStatus = state.resume
    ? resumeStatusMeta[state.resume.parseStatus]
    : resumeStatusMeta.not_uploaded;
  async function uploadResume(file: File) {
    try {
      await state.uploadResume(file);
      setToast({ message: "简历已上传，正在进行解析。", tone: "success" });
    } catch {
      /* Store exposes the controlled error below. */
    }
  }
  async function uploadDocuments(files: File[]) {
    setToast(null);
    setDocumentUploadRequestFailed(false);
    try {
      const results = await state.uploadDocuments(files);
      const failedUploads = results.filter((item) => item.status === "failed");
      useWorkspaceStore.setState({ supportingDocumentUploads: [] });
      if (failedUploads.length === 0) {
        setToast({ message: "其它资料已就绪。", tone: "success" });
        return;
      }
      const failedFileNames = failedUploads.map((item) => item.fileName).join("、");
      const message =
        failedUploads.length === 1
          ? `${failedFileNames} 上传失败：请检查文件格式或大小。`
          : `${failedUploads.length} 个文件上传失败：${failedFileNames}。请检查文件格式或大小。`;
      setToast({ message, tone: "error" });
    } catch {
      useWorkspaceStore.setState({ supportingDocumentUploads: [] });
      setDocumentUploadRequestFailed(true);
      /* controlled by store */
    }
  }
  async function deleteResume() {
    if (!state.resume || !resumeDeleteAllowed) return;
    if (!window.confirm(`确认删除当前简历“${state.resume.fileName}”吗？`)) return;
    try {
      await state.deleteResume();
      setToast({ message: "当前简历已删除。", tone: "success" });
    } catch {
      /* Store exposes the controlled error below. */
    }
  }
  async function deleteDocument(id: string, fileName: string) {
    if (!window.confirm(`确认删除资料“${fileName}”吗？`)) return;
    try {
      await state.deleteDocument(id);
      setToast({ message: "资料已删除。", tone: "success" });
    } catch {
      /* Store exposes the controlled error below. */
    }
  }
  const pendingUploads = state.supportingDocumentUploads.filter(
    (item) => item.status === "ready",
  );
  return (
    <div className="page-view">
      <PageHeader
        eyebrow="CANDIDATE / DOCUMENTS"
        title="准备你的求职资料"
        description="上传简历和补充资料，系统将处理文件并更新资料状态。"
      />
      {state.error ? (
        <ErrorState
          description={state.error}
          onRetry={documentUploadRequestFailed ? undefined : state.clearError}
        />
      ) : null}
      <section className="upload-grid">
        <article className="panel upload-panel">
          <div className="panel-heading">
            <div>
              <h2>个人简历</h2>
              <p className="muted-text">简历解析成功后才能创建求职目标。</p>
            </div>
            {state.resume ? (
              <StatusBadge tone={resumeStatus.tone}>{resumeStatus.label}</StatusBadge>
            ) : null}
          </div>
          <FileUpload
            label={state.resume ? "上传新简历并设为当前" : "上传一份简历"}
            description={
              resumeLocked ? "当前投递轮次已绑定简历。" : "简历仅支持PDF格式。"
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
              deleteLabel={state.resume.fileName}
              deleteDisabled={!resumeDeleteAllowed || state.resumeLoading}
              onDelete={() => void deleteResume()}
            />
          ) : null}
        </article>
        <article className="panel upload-panel">
          <div className="panel-heading">
            <div>
              <h2>其它求职资料</h2>
              <p className="muted-text">上传你的其它求职材料或证明</p>
            </div>
            <StatusBadge tone="neutral">
              {state.supportingDocuments.length
                ? `${state.supportingDocuments.length} 份已保存`
                : "可选"}
            </StatusBadge>
          </div>
          <FileUpload
            label="上传其它资料"
            description="支持 PDF、Markdown、JPG、PNG，单文件不超过 10MB。"
            accept=".pdf,.md,.jpg,.png"
            multiple
            disabled={state.supportingDocumentsLoading}
            disabledLabel="正在处理…"
            onFiles={(files) => void uploadDocuments(files)}
          />
          {pendingUploads.length ? (
            <LoadingState
              title="正在上传其它资料"
              description={`正在处理：${pendingUploads.map((item) => item.fileName).join("、")}`}
            />
          ) : null}
          {state.supportingDocuments.length ? (
            <div
              className="file-list-scroll"
              aria-label="其它求职资料成功上传列表"
              role="region"
            >
              <div className="file-list">
                {state.supportingDocuments.map((document) => (
                  <FileInfoCard
                    key={document.id}
                    fileName={document.fileName}
                    uploadedAt={document.uploadedAt}
                    deleteLabel={document.fileName}
                    deleteDisabled={state.supportingDocumentsLoading}
                    onDelete={() => void deleteDocument(document.id, document.fileName)}
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
              : resumeExists
                ? "可以上传新简历；新形成的简历会自动成为当前简历。"
                : "上传并解析一份简历后，才能创建求职目标。"}
          </p>
        </div>
      </section>
      {toast ? (
        <Toast message={toast.message} tone={toast.tone} onClose={() => setToast(null)} />
      ) : null}
    </div>
  );
}
