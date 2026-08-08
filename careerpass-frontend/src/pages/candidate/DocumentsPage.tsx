import { useState } from "react";
import { PageHeader } from "../../components/PageHeader";
import {
  Button,
  ErrorState,
  FileUpload,
  LoadingState,
  StatusBadge,
  Toast,
} from "../../components/ui";
import { agentStatusMeta, resumeStatusMeta } from "../../domain/mappings";
import { useDemoRefresh } from "../../features/demo/useDemoRefresh";
import { useDemoStore } from "../../stores/demo-store";

export function DocumentsPage() {
  useDemoRefresh();
  const state = useDemoStore((store) => store);
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
      window.setTimeout(
        () =>
          void state.simulateParse(
            file.name.toLowerCase().includes("fail") ? "failed" : "succeeded",
          ),
        700,
      );
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
  return (
    <div className="page-view">
      <PageHeader
        eyebrow="CANDIDATE / DOCUMENTS"
        title="准备你的求职资料"
        description="上传简历和补充资料，系统会模拟解析流程并展示可用状态。"
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
              resumeLocked ? "当前投递轮次已绑定简历。" : "支持 PDF、DOCX 等常见格式。"
            }
            accept=".pdf,.doc,.docx"
            disabled={resumeLocked || state.loading}
            onFiles={(files) => void uploadResume(files[0])}
          />
          {state.resume ? (
            <div className="file-card">
              <span className="file-icon">PDF</span>
              <div>
                <strong>{state.resume.fileName}</strong>
                <span>
                  版本 {state.resume.version} ·{" "}
                  {new Date(state.resume.uploadedAt).toLocaleDateString("zh-CN")}
                </span>
              </div>
            </div>
          ) : null}
          <div className="demo-actions">
            <Button
              variant="ghost"
              type="button"
              disabled={!state.resume || state.loading}
              onClick={() => void state.simulateParse("succeeded")}
            >
              模拟解析成功
            </Button>
            <Button
              variant="ghost"
              type="button"
              disabled={!state.resume || state.loading}
              onClick={() => void state.simulateParse("failed")}
            >
              演示解析失败
            </Button>
          </div>
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
            disabled={state.loading}
            onFiles={(files) => void uploadDocuments(files)}
          />
          {state.supportingDocuments.length ? (
            <div className="file-list">
              {state.supportingDocuments.map((document) => (
                <div className="file-card" key={document.id}>
                  <span className="file-icon">FILE</span>
                  <div>
                    <strong>{document.fileName}</strong>
                    <span>
                      已就绪 · {document.kind === "other" ? "其它资料" : document.kind}
                    </span>
                  </div>
                </div>
              ))}
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
