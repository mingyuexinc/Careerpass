import { Link } from "react-router-dom";
import { EmptyState, LoadingState } from "../../components/ui";
import type { JobGoal } from "../../domain/types";
import { useWorkspaceStore } from "../../stores/workspace-store";

function formatDate(value: string) {
  return new Date(value).toLocaleString("zh-CN", {
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function GoalRecord({ goal }: { goal: JobGoal }) {
  return (
    <li className="job-goal-record">
      <strong className="job-goal-record-title" title={goal.title}>
        {goal.title}
      </strong>
      <span className="job-goal-record-offer">{goal.offerTarget} 个</span>
      <time className="job-goal-record-created" dateTime={goal.createdAt}>
        {formatDate(goal.createdAt)}
      </time>
    </li>
  );
}

export function JobGoalViewPage() {
  const state = useWorkspaceStore((store) => store);
  if (!state.initialized) return <LoadingState />;

  const records = state.jobGoal ? [state.jobGoal] : [];

  return (
    <section className="panel job-goal-list-panel" aria-labelledby="job-goal-view-title">
      <div className="panel-heading">
        <div>
          <h2 id="job-goal-view-title">已创建的求职目标</h2>
          <p className="muted-text">当前用户已创建的求职目标</p>
        </div>
        <span className="job-goal-record-count">{records.length} 条</span>
      </div>
      {records.length ? (
        <div className="job-goal-table">
          <div className="job-goal-table-head">
            <span>目标岗位</span>
            <span>目标 Offer</span>
            <span>创建时间</span>
          </div>
          <ol className="job-goal-record-list" aria-label="求职目标记录列表">
            {records.map((goal) => (
              <GoalRecord key={goal.id} goal={goal} />
            ))}
          </ol>
        </div>
      ) : (
        <EmptyState
          title="还没有求职目标"
          description="完成求职目标创建后，这里会显示你的目标记录。"
        />
      )}
      {!records.length ? (
        <Link className="button button-secondary inline-button" to="../create">
          去创建求职目标
        </Link>
      ) : null}
    </section>
  );
}
