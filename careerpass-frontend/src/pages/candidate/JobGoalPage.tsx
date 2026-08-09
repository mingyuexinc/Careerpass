import { useEffect, useState } from "react";
import { PageHeader } from "../../components/PageHeader";
import {
  Button,
  ConditionChecklist,
  ErrorState,
  LoadingState,
  StatusBadge,
  Toast,
} from "../../components/ui";
import { agentStatusMeta } from "../../domain/mappings";
import { useWorkspaceRefresh } from "../../features/workspace/useWorkspaceRefresh";
import { useWorkspaceStore } from "../../stores/workspace-store";

export function JobGoalPage() {
  useWorkspaceRefresh();
  const state = useWorkspaceStore((store) => store);
  const [offerTarget, setOfferTarget] = useState("1");
  const [title, setTitle] = useState("前端工程师");
  const [filters, setFilters] = useState("优先 AI 应用和数据产品，不考虑长期出差岗位。");
  const [toast, setToast] = useState<string | null>(null);
  useEffect(() => {
    if (state.jobGoal) {
      setOfferTarget(String(state.jobGoal.offerTarget));
      setTitle(state.jobGoal.title);
      setFilters(state.jobGoal.filters);
    }
  }, [state.jobGoal]);
  if (!state.initialized) return <LoadingState />;
  const canStart =
    state.resume?.parseStatus === "succeeded" &&
    Boolean(state.jobGoal) &&
    state.agentStatus === "ready";
  async function saveGoal() {
    try {
      await state.saveGoal({ offerTarget: Number(offerTarget), title, filters });
      setToast("求职目标已保存。");
    } catch {
      /* controlled by store */
    }
  }
  async function startAgent() {
    try {
      await state.startAgent();
      setToast("求职 Agent 已启动，首轮投递结果已就绪。");
    } catch {
      /* controlled by store */
    }
  }
  return (
    <div className="page-view">
      <PageHeader
        eyebrow="CANDIDATE / JOB GOAL"
        title="配置你的求职任务"
        description="设置目标 Offer 数量和岗位条件，满足启动条件后即可开始求职 Agent。"
      />
      {state.error ? (
        <ErrorState description={state.error} onRetry={state.clearError} />
      ) : null}
      <section className="panel">
        <div className="panel-heading">
          <div>
            <h2>求职目标配置</h2>
            <p className="muted-text">当前版本每位用户维护一个求职目标。</p>
          </div>
          {state.jobGoal ? (
            <StatusBadge tone="success">已保存</StatusBadge>
          ) : (
            <StatusBadge>待创建</StatusBadge>
          )}
        </div>
        <div className="form-grid">
          <label>
            目标 Offer 数量
            <input
              type="number"
              min="1"
              value={offerTarget}
              onChange={(event) => setOfferTarget(event.target.value)}
              disabled={
                state.agentStatus === "running" || state.agentStatus === "finished"
              }
            />
          </label>
          <label>
            目标岗位名称
            <input
              value={title}
              onChange={(event) => setTitle(event.target.value)}
              disabled={
                state.agentStatus === "running" || state.agentStatus === "finished"
              }
            />
          </label>
          <label className="field-wide">
            岗位过滤条件
            <textarea
              rows={4}
              value={filters}
              onChange={(event) => setFilters(event.target.value)}
              disabled={
                state.agentStatus === "running" || state.agentStatus === "finished"
              }
            />
          </label>
          <div className="field-wide">
            <Button
              type="button"
              disabled={
                state.loading ||
                state.agentStatus === "running" ||
                state.agentStatus === "finished" ||
                !title.trim()
              }
              onClick={() => void saveGoal()}
            >
              {state.loading ? "保存中…" : state.jobGoal ? "保存修改" : "创建求职目标"}
            </Button>
          </div>
        </div>
      </section>
      <section className="panel">
        <div className="panel-heading">
          <div>
            <h2>启动条件</h2>
            <p className="muted-text">所有条件满足后，启动按钮才会开放。</p>
          </div>
          <StatusBadge tone={agentStatusMeta[state.agentStatus].tone}>
            {agentStatusMeta[state.agentStatus].label}
          </StatusBadge>
        </div>
        <ConditionChecklist
          items={[
            { label: "已登录求职者工作台", done: true },
            {
              label: "简历上传并解析成功",
              done: state.resume?.parseStatus === "succeeded",
            },
            { label: "求职目标创建完成", done: Boolean(state.jobGoal) },
          ]}
        />
        <div className="agent-card">
          <div>
            <div className="agent-state">
              <span className="pulse" />
              {agentStatusMeta[state.agentStatus].label}
            </div>
            <p>{agentStatusMeta[state.agentStatus].description}</p>
          </div>
          <Button
            type="button"
            disabled={!canStart || state.loading}
            onClick={() => void startAgent()}
          >
            {state.agentStatus === "finished"
              ? "运行已结束"
              : state.agentStatus === "running"
                ? "已启动"
                : "启动求职 Agent"}
          </Button>
        </div>
      </section>
      {toast ? <Toast message={toast} onClose={() => setToast(null)} /> : null}
    </div>
  );
}
