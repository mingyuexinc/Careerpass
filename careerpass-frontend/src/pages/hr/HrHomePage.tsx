import { Link } from "react-router-dom";
import { PageHeader } from "../../components/PageHeader";
import { LoadingState, StatusBadge } from "../../components/ui";
import { useWorkspaceRefresh } from "../../features/workspace/useWorkspaceRefresh";
import { useAuthStore } from "../../stores/auth-store";
import { useWorkspaceStore } from "../../stores/workspace-store";

export function HrHomePage() {
  useWorkspaceRefresh();
  const user = useAuthStore((state) => state.user);
  const { initialized, currentJob, applications, conversations } = useWorkspaceStore(
    (state) => state,
  );
  if (!initialized) return <LoadingState />;
  const firstName = user?.displayName.split(" ")[0] ?? "HR";
  const hasConversations = conversations.length > 0;
  const hasApplications = applications.length > 0;
  const processStarted = hasConversations || hasApplications;
  const flowSteps = [
    {
      title: "上传岗位 JD",
      description: currentJob
        ? "岗位信息已准备，可以查看岗位摘要"
        : "准备供求职者 Agent 匹配的岗位信息",
      done: Boolean(currentJob),
    },
    {
      title: "参与岗位沟通",
      description: hasConversations
        ? "已有沟通记录，可以继续交流"
        : "求职者 Agent 发起沟通后进行交流",
      done: hasConversations,
    },
    {
      title: "更新投递进度",
      description: hasApplications
        ? "根据实际情况推进指定投递记录"
        : "沟通开始后可查看并更新",
      done: hasApplications,
    },
  ];
  return (
    <div className="page-view">
      <PageHeader
        eyebrow="CAREER AGENT"
        title={`你好，${firstName}`}
        description="通过 Careerpass，清晰了解岗位沟通与投递进度。"
      />
      <section className="hero-card">
        <div>
          <div className="eyebrow">HR WORKSPACE</div>
          <h2>{currentJob ? "岗位已经准备就绪" : "先准备一个岗位 JD"}</h2>
          <p>
            {currentJob
              ? `${currentJob.title} · ${currentJob.company}，现在可以查看沟通和投递进度。`
              : "上传岗位资料，为求职者 Agent 准备可匹配的岗位。"}
          </p>
          <Link
            className="button button-primary inline-button"
            to={currentJob ? "/hr/applications" : "/hr/jobs"}
          >
            {currentJob ? "查看投递进度" : "上传岗位 JD"} <span>→</span>
          </Link>
        </div>
        <div className="hero-orb">⌁</div>
      </section>
      <section className="two-col">
        <article className="panel">
          <div className="panel-heading">
            <h2>HR 标准流程</h2>
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
            <StatusBadge tone={processStarted ? "info" : "neutral"}>
              {processStarted ? "进行中" : "待完成"}
            </StatusBadge>
          </div>
          <div className="state-list">
            <div className={`state-row ${currentJob ? "done" : "active"}`}>
              <span className="state-marker">{currentJob ? "✓" : "1"}</span>
              <div>
                <strong>岗位 JD</strong>
                <span>{currentJob ? "已准备岗位数据" : "尚未上传"}</span>
              </div>
            </div>
            <div
              className={`state-row ${hasConversations ? "done" : currentJob ? "active" : ""}`}
            >
              <span className="state-marker">{hasConversations ? "✓" : "2"}</span>
              <div>
                <strong>求职者 Agent 沟通</strong>
                <span>{hasConversations ? "已有沟通记录" : "等待求职者启动 Agent"}</span>
              </div>
            </div>
            <div
              className={`state-row ${hasApplications ? "done" : hasConversations ? "active" : ""}`}
            >
              <span className="state-marker">{hasApplications ? "✓" : "3"}</span>
              <div>
                <strong>投递进度更新</strong>
                <span>{hasApplications ? "可以查看并更新" : "沟通开始后可用"}</span>
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
          本页面展示 HR 从岗位信息准备、候选人 Agent
          沟通到投递进度更新的完整流程。具体岗位和投递数据将在对应功能页面中展示。
        </p>
        <span className="muted-text">当前已有 {applications.length} 条投递记录。</span>
      </section>
    </div>
  );
}
