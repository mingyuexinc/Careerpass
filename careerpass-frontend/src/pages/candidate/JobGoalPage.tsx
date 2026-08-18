import { NavLink, Outlet, useLocation } from "react-router-dom";
import { PageHeader } from "../../components/PageHeader";
import { LoadingState } from "../../components/ui";
import { useWorkspaceRefresh } from "../../features/workspace/useWorkspaceRefresh";
import { useWorkspaceStore } from "../../stores/workspace-store";

export function JobGoalPage() {
  useWorkspaceRefresh();
  const initialized = useWorkspaceStore((state) => state.initialized);
  const location = useLocation();
  if (!initialized) return <LoadingState />;

  const isViewPage = location.pathname.endsWith("/view");

  return (
    <div className="page-view job-goal-page">
      <PageHeader
        eyebrow="CANDIDATE / JOB GOAL"
        title={isViewPage ? "查看求职目标" : "配置你的求职任务"}
        description={
          isViewPage
            ? "查看当前用户已创建的求职目标记录。"
            : "设置目标 Offer 数量和岗位条件，满足启动条件后即可开始求职 Agent。"
        }
      />
      <nav className="job-goal-section-nav" aria-label="求职目标页面菜单">
        <NavLink to="create" className={({ isActive }) => (isActive ? "is-active" : "")}>
          求职目标创建
        </NavLink>
        <NavLink to="view" className={({ isActive }) => (isActive ? "is-active" : "")}>
          求职目标查看
        </NavLink>
      </nav>
      <Outlet />
    </div>
  );
}
