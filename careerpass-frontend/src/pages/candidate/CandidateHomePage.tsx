import { Link } from "react-router-dom";
import { PageHeader } from "../../components/PageHeader";
import { LoadingState, StatusBadge } from "../../components/ui";
import { agentStatusMeta, resumeStatusMeta } from "../../domain/mappings";
import { useDemoRefresh } from "../../features/demo/useDemoRefresh";
import { useDemoStore } from "../../stores/demo-store";

export function CandidateHomePage() {
  useDemoRefresh();
  const { initialized, resume, jobGoal, agentStatus, applications } = useDemoStore(
    (state) => state,
  );
  if (!initialized) return <LoadingState />;
  const status = agentStatusMeta[agentStatus];
  return (
    <div className="page-view">
      <PageHeader
        eyebrow="CANDIDATE WORKSPACE"
        title="准备好开始你的求职旅程了吗？"
        description="Careerpass 将陪你完成资料准备、目标设定和求职 Agent 启动，让每一步都更清晰。"
      />
      <section className="hero-card">
        <div>
          <h2>你的下一步</h2>
          <p>
            {agentStatus === "finished"
              ? "目标已达成，查看进度了解完整投递结果。"
              : resume?.parseStatus === "succeeded"
                ? "简历已准备好，可以创建求职目标。"
                : "先上传一份简历，开始准备求职资料。"}
          </p>
          <Link
            className="button button-primary inline-button"
            to={
              resume?.parseStatus === "succeeded"
                ? "/candidate/job-goal"
                : "/candidate/documents"
            }
          >
            {resume?.parseStatus === "succeeded" ? "进入求职任务" : "上传求职资料"}{" "}
            <span>→</span>
          </Link>
        </div>
        <div className="hero-orb">✦</div>
      </section>
      <section className="panel-grid">
        <article className="panel">
          <div className="panel-heading">
            <h2>当前准备状态</h2>
            <StatusBadge tone={status.tone}>{status.label}</StatusBadge>
          </div>
          <div className="state-list">
            <div className="state-row">
              <span className="state-marker">
                {resume?.parseStatus === "succeeded" ? "✓" : "1"}
              </span>
              <div>
                <strong>简历解析</strong>
                <span>
                  {resume ? resumeStatusMeta[resume.parseStatus].label : "尚未开始"}
                </span>
              </div>
            </div>
            <div className="state-row">
              <span className="state-marker">{jobGoal ? "✓" : "2"}</span>
              <div>
                <strong>求职目标</strong>
                <span>{jobGoal ? "已创建" : "等待创建"}</span>
              </div>
            </div>
            <div className="state-row">
              <span className="state-marker">
                {agentStatus === "finished" ? "✓" : "3"}
              </span>
              <div>
                <strong>Agent 状态</strong>
                <span>{status.label}</span>
              </div>
            </div>
          </div>
        </article>
        <article className="panel">
          <div className="panel-heading">
            <h2>快速入口</h2>
            <span className="muted-text">{applications.length} 条投递</span>
          </div>
          <div className="quick-links">
            <Link to="/candidate/documents">
              管理求职资料 <span>→</span>
            </Link>
            <Link to="/candidate/job-goal">
              配置求职任务 <span>→</span>
            </Link>
            <Link to="/candidate/progress">
              查看求职进度 <span>→</span>
            </Link>
          </div>
        </article>
      </section>
    </div>
  );
}
