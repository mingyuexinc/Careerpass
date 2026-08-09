import { Link } from "react-router-dom";
import { PageHeader } from "../../components/PageHeader";
import { LoadingState, StatusBadge } from "../../components/ui";
import { agentStatusMeta, resumeStatusMeta } from "../../domain/mappings";
import { useWorkspaceRefresh } from "../../features/workspace/useWorkspaceRefresh";
import { useAuthStore } from "../../stores/auth-store";
import { useWorkspaceStore } from "../../stores/workspace-store";

export function CandidateHomePage() {
  useWorkspaceRefresh();
  const user = useAuthStore((state) => state.user);
  const { initialized, resume, jobGoal, agentStatus, applications } = useWorkspaceStore(
    (state) => state,
  );
  if (!initialized) return <LoadingState />;
  const status = agentStatusMeta[agentStatus];
  const firstName = user?.displayName.split(" ")[0] ?? "求职者";
  const resumeParsed = resume?.parseStatus === "succeeded";
  const agentStarted = agentStatus === "running" || agentStatus === "finished";
  const nextStep =
    agentStatus === "finished"
      ? { to: "/candidate/progress", label: "查看求职进度" }
      : resumeParsed
        ? { to: "/candidate/job-goal", label: "进入求职任务" }
        : { to: "/candidate/documents", label: "上传求职资料" };
  const flowSteps = [
    {
      title: "上传求职资料",
      description: resumeParsed
        ? "简历解析成功，画像已就绪"
        : resume?.parseStatus === "processing" || resume?.parseStatus === "uploading"
          ? "简历正在解析，请稍候"
          : resume?.parseStatus === "failed"
            ? "简历解析未完成，请重新上传"
            : "上传一份简历，完成资料准备",
      done: resumeParsed,
    },
    {
      title: "创建求职目标",
      description: jobGoal ? "求职目标已创建" : "设置目标岗位与筛选条件",
      done: Boolean(jobGoal),
    },
    {
      title: "启动求职 Agent",
      description:
        agentStatus === "finished"
          ? "目标 Offer 已达成，系统已结束本轮运行"
          : agentStatus === "running"
            ? "Agent 正在持续推进求职"
            : agentStatus === "ready"
              ? "启动条件已满足，可以启动 Agent"
              : "满足条件后启动首轮求职",
      done: agentStarted,
    },
  ];
  return (
    <div className="page-view">
      <PageHeader
        eyebrow="CAREER AGENT"
        title={`你好，${firstName}`}
        description="把求职交给 Agent，把时间留给更重要的准备。"
      />
      <section className="hero-card">
        <div>
          <div className="eyebrow">YOUR CAREER COPILOT</div>
          <h2>你的下一步</h2>
          <p>
            {agentStatus === "finished"
              ? "目标已达成，查看进度了解完整投递结果。"
              : resume?.parseStatus === "succeeded"
                ? "简历已准备好，可以创建求职目标。"
                : "先上传一份简历，开始准备求职资料。"}
          </p>
          <Link className="button button-primary inline-button" to={nextStep.to}>
            {nextStep.label} <span>→</span>
          </Link>
        </div>
        <div className="hero-orb">✦</div>
      </section>
      <section className="two-col">
        <article className="panel">
          <div className="panel-heading">
            <h2>开始你的求职流程</h2>
            <span className="panel-heading-note">3 个步骤</span>
          </div>
          <div className="guide-step-list">
            {flowSteps.map((step, index) => (
              <div
                className={`guide-step ${step.done ? "is-done" : ""}`}
                key={step.title}
              >
                <span className="guide-step-marker">{step.done ? "✓" : index + 1}</span>
                <div>
                  <strong>{step.title}</strong>
                  <span>{step.description}</span>
                </div>
              </div>
            ))}
          </div>
        </article>
        <article className="panel">
          <div className="panel-heading">
            <h2>当前准备状态</h2>
            <StatusBadge tone={status.tone}>{status.label}</StatusBadge>
          </div>
          <div className="state-list">
            <div
              className={`state-row ${resumeParsed ? "done" : resume ? "active" : ""}`}
            >
              <span className="state-marker">{resumeParsed ? "✓" : "1"}</span>
              <div>
                <strong>简历解析</strong>
                <span>
                  {resume ? resumeStatusMeta[resume.parseStatus].label : "尚未开始"}
                </span>
              </div>
            </div>
            <div
              className={`state-row ${jobGoal ? "done" : resumeParsed ? "active" : ""}`}
            >
              <span className="state-marker">{jobGoal ? "✓" : "2"}</span>
              <div>
                <strong>求职目标</strong>
                <span>{jobGoal ? "已创建" : "等待创建"}</span>
              </div>
            </div>
            <div
              className={`state-row ${agentStatus === "finished" ? "done" : agentStarted || agentStatus === "ready" ? "active" : ""}`}
            >
              <span className="state-marker">
                {agentStatus === "finished" ? "✓" : agentStatus === "running" ? "…" : "3"}
              </span>
              <div>
                <strong>Agent 状态</strong>
                <span>{status.label}</span>
              </div>
            </div>
          </div>
        </article>
      </section>
      <section className="panel guide-summary">
        <div className="panel-heading">
          <h2>产品流程说明</h2>
          <span className="panel-heading-note">Careerpass</span>
        </div>
        <p className="page-subtitle">
          本页面展示从资料准备、求职目标创建到 Agent
          推进求职进度的完整流程。岗位匹配结果和投递数据将在求职进度页面中展示。
        </p>
        <span className="muted-text">当前已有 {applications.length} 条投递记录。</span>
      </section>
    </div>
  );
}
