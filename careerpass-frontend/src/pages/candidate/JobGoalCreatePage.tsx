import { useEffect, useRef, useState } from "react";
import {
  Button,
  ErrorState,
  LoadingState,
  StatusBadge,
  Toast,
} from "../../components/ui";
import { agentStatusMeta } from "../../domain/mappings";
import { useWorkspaceStore } from "../../stores/workspace-store";

export function JobGoalCreatePage() {
  const state = useWorkspaceStore((store) => store);
  const [offerTarget, setOfferTarget] = useState("1");
  const [title, setTitle] = useState("前端工程师");
  const [filters, setFilters] = useState("优先 AI 应用和数据产品，不考虑长期出差岗位。");
  const [toast, setToast] = useState<string | null>(null);
  const saveButtonRef = useRef<HTMLButtonElement>(null);

  useEffect(() => {
    if (!state.jobGoal) return;
    setOfferTarget(String(state.jobGoal.offerTarget));
    setTitle(state.jobGoal.title);
    setFilters(state.jobGoal.filters);
  }, [state.jobGoal]);

  if (!state.initialized) return <LoadingState />;

  const locked = state.agentStatus === "running" || state.agentStatus === "finished";
  const canStart =
    state.resume?.parseStatus === "succeeded" &&
    Boolean(state.jobGoal) &&
    state.agentStatus === "ready" &&
    state.agentRunCanStart;

  async function saveGoal() {
    const shouldRestoreFocus = document.activeElement === saveButtonRef.current;
    try {
      await state.saveGoal({ offerTarget: Number(offerTarget), title, filters });
      setToast("求职目标已保存。");
      if (shouldRestoreFocus) {
        requestAnimationFrame(() => saveButtonRef.current?.focus());
      }
    } catch {
      // The store exposes the controlled user-facing error.
    }
  }

  async function startAgent() {
    try {
      await state.startAgent();
      setToast("求职 Agent 已启动，正在准备首轮匹配");
    } catch {
      // The store exposes the controlled user-facing error.
    }
  }

  return (
    <div className="job-goal-create-page">
      {state.error ? (
        <ErrorState description={state.error} onRetry={state.clearError} />
      ) : null}
      <article className="panel job-goal-form-panel">
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
              disabled={locked}
            />
          </label>
          <label>
            目标岗位名称
            <input
              value={title}
              onChange={(event) => setTitle(event.target.value)}
              disabled={locked}
            />
          </label>
          <label className="field-wide">
            岗位过滤条件
            <textarea
              rows={4}
              value={filters}
              onChange={(event) => setFilters(event.target.value)}
              disabled={locked}
            />
          </label>
          <div className="field-wide form-action-row">
            <Button
              ref={saveButtonRef}
              id="save-job-goal"
              type="button"
              disabled={state.savingGoal || locked || !title.trim()}
              onClick={() => void saveGoal()}
            >
              {state.savingGoal ? "保存中…" : state.jobGoal ? "保存修改" : "创建求职目标"}
            </Button>
          </div>
        </div>
      </article>

      <section className="panel agent-start-panel">
        <div className="panel-heading">
          <div>
            <h2>启动条件</h2>
            <p className="muted-text">完成必要准备后，启动按钮才会开放。</p>
          </div>
          <StatusBadge tone={agentStatusMeta[state.agentStatus].tone}>
            {agentStatusMeta[state.agentStatus].label}
          </StatusBadge>
        </div>
      </section>
      <section className="agent-card" aria-labelledby="agent-start-title">
        <div className="agent-card-content">
          <h3 id="agent-start-title">
            {state.agentStatus === "finished"
              ? "Agent 运行结束"
              : state.agentStatus === "running"
                ? "Agent 正在运行"
                : "启动求职 Agent"}
          </h3>
          <p>
            {locked
              ? "求职目标已锁定，请前往求职进度查看本轮投递结果。"
              : "启动后，Agent 将完成本轮岗位筛选与系统内投递记录创建。前端不展示中间过程。"}
          </p>
          <div
            className={`agent-state ${
              state.agentStatus === "finished"
                ? "finished"
                : state.agentStatus === "running"
                  ? "running"
                  : ""
            }`}
          >
            <span className="pulse" />
            {state.agentStatus === "finished"
              ? "Agent 运行结束"
              : state.agentStatus === "running"
                ? "Agent 运行中"
                : "尚未启动"}
          </div>
        </div>
        <div className="agent-card-action">
          <Button
            type="button"
            className="agent-start-button"
            disabled={!canStart || state.startingAgent || state.savingGoal}
            aria-label="启动求职 Agent"
            onClick={() => void startAgent()}
          >
            {state.startingAgent
              ? "启动中…"
              : state.agentStatus === "finished"
                ? "运行已结束"
                : state.agentStatus === "running"
                  ? "已启动"
                  : "启动求职 Agent"}
            <span aria-hidden="true">→</span>
          </Button>
        </div>
      </section>

      {toast ? <Toast message={toast} onClose={() => setToast(null)} /> : null}
    </div>
  );
}
