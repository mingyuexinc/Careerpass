import { Link } from "react-router-dom";
import { PageHeader } from "../../components/PageHeader";
import { DebugResetPanel } from "../../components/DebugResetPanel";
import {
  LoadingState,
  StatusBadge,
  StepListItem,
  type StepMarkerStatus,
} from "../../components/ui";
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
  const resumeStepStatus: StepMarkerStatus = resumeParsed
    ? "completed"
    : resume
      ? "active"
      : "waiting";
  const goalStepStatus: StepMarkerStatus = jobGoal
    ? "completed"
    : resumeParsed
      ? "active"
      : "waiting";
  const agentStepStatus: StepMarkerStatus =
    agentStatus === "finished"
      ? "completed"
      : agentStatus === "running" || agentStatus === "ready"
        ? "active"
        : "waiting";
  const agentActiveSymbol = agentStatus === "running" ? "…" : undefined;
  const nextStep =
    agentStatus === "finished"
      ? { to: "/candidate/progress", label: "查看求职进度" }
      : resumeParsed
        ? { to: "/candidate/job-goal", label: "进入求职任务" }
        : { to: "/candidate/documents", label: "上传求职资料" };
  const flowSteps: Array<{
    title: string;
    description: string;
    status: StepMarkerStatus;
    activeSymbol?: string;
  }> = [
    {
      title: "上传求职资料",
      description: resumeParsed
        ? "简历解析成功，画像已就绪"
        : resume?.parseStatus === "processing" || resume?.parseStatus === "uploading"
          ? "简历正在解析，请稍候"
          : resume?.parseStatus === "failed"
            ? "简历解析未完成，请重新上传"
            : "上传一份简历，完成资料准备",
      status: resumeStepStatus,
    },
    {
      title: "创建求职目标",
      description: jobGoal ? "求职目标已创建" : "设置目标岗位与筛选条件",
      status: goalStepStatus,
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
      status: agentStepStatus,
      activeSymbol: agentActiveSymbol,
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
        <article className="panel guide-panel">
          <div className="panel-heading">
            <h2>开始你的求职流程</h2>
            <span className="panel-heading-note">3 个步骤</span>
          </div>
          <div className="step-list">
            {flowSteps.map((step, index) => (
              <StepListItem
                key={step.title}
                step={index + 1}
                status={step.status}
                title={step.title}
                description={step.description}
                activeSymbol={step.activeSymbol}
              />
            ))}
          </div>
        </article>
        <article className="panel guide-panel">
          <div className="panel-heading">
            <h2>当前准备状态</h2>
            <StatusBadge tone={status.tone}>{status.label}</StatusBadge>
          </div>
          <div className="step-list">
            <StepListItem
              step={1}
              status={resumeStepStatus}
              title="简历解析"
              description={
                resume ? resumeStatusMeta[resume.parseStatus].label : "尚未开始"
              }
            />
            <StepListItem
              step={2}
              status={goalStepStatus}
              title="求职目标"
              description={jobGoal ? "已创建" : "等待创建"}
            />
            <StepListItem
              step={3}
              status={agentStepStatus}
              activeSymbol={agentActiveSymbol}
              title="Agent 状态"
              description={status.label}
            />
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
      <DebugResetPanel />
    </div>
  );
}
