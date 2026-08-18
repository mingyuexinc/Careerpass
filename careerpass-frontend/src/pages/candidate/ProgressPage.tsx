import { PageHeader } from "../../components/PageHeader";
import {
  EmptyState,
  LoadingState,
  ProgressTimeline,
  StatusBadge,
} from "../../components/ui";
import {
  agentStatusMeta,
  deliveryProgressMeta,
  getOfferCount,
} from "../../domain/mappings";
import { useWorkspaceRefresh } from "../../features/workspace/useWorkspaceRefresh";
import { useWorkspaceStore } from "../../stores/workspace-store";

export function ProgressPage() {
  useWorkspaceRefresh();
  const state = useWorkspaceStore((store) => store);
  if (!state.initialized) return <LoadingState />;
  const offerCount = getOfferCount(
    state.applications.map((application) => application.status),
  );
  const activeCount = state.applications.filter(
    (application) => !deliveryProgressMeta[application.status].terminal,
  ).length;
  const terminatedCount = state.applications.filter(
    (application) => application.status === "terminated",
  ).length;
  return (
    <div className="page-view">
      <PageHeader
        eyebrow="CANDIDATE / PROGRESS"
        title="查看求职进度"
        description="这里会持续展示当前投递轮次、岗位阶段和 Offer 目标完成情况。"
        action={
          <StatusBadge tone={agentStatusMeta[state.agentStatus].tone}>
            {agentStatusMeta[state.agentStatus].label}
          </StatusBadge>
        }
      />
      {!state.applications.length ? (
        <EmptyState
          title={
            state.agentStatus === "not_started"
              ? "求职进程尚未开始"
              : "当前没有可供匹配的岗位"
          }
          description={
            state.agentStatus === "not_started"
              ? "完成简历解析和求职目标创建后，启动 Agent 即可开始首轮求职。"
              : "本轮岗位均已筛选完成，暂未产生投递记录。"
          }
        />
      ) : (
        <>
          <section className="offer-progress-panel">
            <div
              className="offer-ring"
              style={
                {
                  "--offer-progress": `${state.jobGoal ? Math.min(offerCount / state.jobGoal.offerTarget, 1) * 100 : 0}%`,
                } as React.CSSProperties
              }
            >
              <div>
                <strong>
                  {offerCount}/{state.jobGoal?.offerTarget ?? 0}
                </strong>
                <span>Offer 达成</span>
              </div>
            </div>
            <div>
              <h2>目标 Offer 达成进度</h2>
              <p>
                {state.agentStatus === "finished" && state.agentRun?.finishReason === "no_match"
                  ? "本轮岗位已筛选完成，暂未产生投递结果。"
                  : state.agentStatus === "finished"
                    ? "目标已达成，系统已判定 Agent 运行结束。"
                    : "继续推进求职沟通，当前状态会在 HR 更新后同步。"}
              </p>
            </div>
          </section>
          <section className="metric-grid">
            <div className="metric">
              <span>本轮投递</span>
              <strong>{state.applications.length}</strong>
              <small>第 {state.round} 轮</small>
            </div>
            <div className="metric">
              <span>累计投递</span>
              <strong>{state.applications.length}</strong>
              <small>历史总数</small>
            </div>
            <div className="metric">
              <span>进行中岗位</span>
              <strong>{activeCount}</strong>
              <small>尚未结束</small>
            </div>
            <div className="metric">
              <span>流程终止</span>
              <strong>{terminatedCount}</strong>
              <small>已结束岗位</small>
            </div>
          </section>
          <section className="application-list">
            {state.applications.map((application) => (
              <article className="application-card" key={application.id}>
                <div className="application-top">
                  <div className="application-heading">
                    <h2>{application.jobTitle}</h2>
                    <p>
                      {application.company} · {application.location} · 最近沟通：
                      {application.lastContactAt
                        ? new Date(application.lastContactAt).toLocaleString("zh-CN")
                        : "暂无"}
                    </p>
                  </div>
                  <div className="application-match-summary">
                    <strong>推荐匹配得分 {application.matchScore}</strong>
                    <p>{application.recommendationReason}</p>
                  </div>
                  <StatusBadge tone={deliveryProgressMeta[application.status].tone}>
                    {deliveryProgressMeta[application.status].label}
                  </StatusBadge>
                </div>
                <ProgressTimeline current={application.status} />
              </article>
            ))}
          </section>
        </>
      )}
    </div>
  );
}
