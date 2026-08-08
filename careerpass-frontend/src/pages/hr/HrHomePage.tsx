import { Link } from "react-router-dom";
import { PageHeader } from "../../components/PageHeader";
import { LoadingState, StatusBadge } from "../../components/ui";
import { useDemoRefresh } from "../../features/demo/useDemoRefresh";
import { useDemoStore } from "../../stores/demo-store";

export function HrHomePage() {
  useDemoRefresh();
  const { initialized, currentJob, applications, conversations } = useDemoStore(
    (state) => state,
  );
  if (!initialized) return <LoadingState />;
  return (
    <div className="page-view">
      <PageHeader
        eyebrow="HR WORKSPACE"
        title="欢迎使用 HR 工作台"
        description="从岗位准备到候选人沟通，在一个工作台中完成招聘协作。"
      />
      <section className="hero-card">
        <div>
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
      <section className="panel-grid">
        <article className="panel">
          <div className="panel-heading">
            <h2>当前准备状态</h2>
            <StatusBadge tone={currentJob ? "success" : "neutral"}>
              {currentJob ? "已准备" : "待完成"}
            </StatusBadge>
          </div>
          <div className="state-list">
            <div className="state-row">
              <span className="state-marker">{currentJob ? "✓" : "1"}</span>
              <div>
                <strong>岗位 JD</strong>
                <span>{currentJob ? "已准备岗位数据" : "尚未上传"}</span>
              </div>
            </div>
            <div className="state-row">
              <span className="state-marker">{conversations.length ? "✓" : "2"}</span>
              <div>
                <strong>求职者 Agent 沟通</strong>
                <span>
                  {conversations.length ? "已有沟通记录" : "等待求职者启动 Agent"}
                </span>
              </div>
            </div>
            <div className="state-row">
              <span className="state-marker">{applications.length ? "✓" : "3"}</span>
              <div>
                <strong>投递进度更新</strong>
                <span>{applications.length ? "可以查看并更新" : "沟通开始后可用"}</span>
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
            <Link to="/hr/jobs">
              管理岗位 JD <span>→</span>
            </Link>
            <Link to="/hr/conversations">
              查看求职沟通 <span>→</span>
            </Link>
            <Link to="/hr/applications">
              更新投递进度 <span>→</span>
            </Link>
          </div>
        </article>
      </section>
    </div>
  );
}
