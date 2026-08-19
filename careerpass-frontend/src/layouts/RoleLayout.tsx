import type { ReactNode } from "react";
import { NavLink, useNavigate } from "react-router-dom";
import { useAuthStore } from "../stores/auth-store";
import { useWorkspaceStore } from "../stores/workspace-store";
import type { UserRole } from "../domain/types";

interface NavigationItem {
  to: string;
  label: string;
  icon: string;
}

export function RoleLayout({ role, children }: { role: UserRole; children: ReactNode }) {
  const navigate = useNavigate();
  const user = useAuthStore((state) => state.user);
  const signOut = useAuthStore((state) => state.signOut);
  const clearLocalState = useWorkspaceStore((state) => state.clearLocalState);
  const roleLabel = role === "candidate" ? "求职者工作台" : "HR 工作台";
  const items: NavigationItem[] =
    role === "candidate"
      ? [
          { to: "/candidate", label: "使用指南", icon: "⌂" },
          { to: "/candidate/documents", label: "求职资料上传", icon: "↥" },
          { to: "/candidate/job-goal", label: "求职任务", icon: "◎" },
          { to: "/candidate/progress", label: "求职进度查看", icon: "▥" },
        ]
      : [
          { to: "/hr", label: "使用指南", icon: "⌂" },
          { to: "/hr/jobs", label: "岗位 JD 上传", icon: "↥" },
          { to: "/hr/conversations", label: "求职沟通", icon: "□" },
          { to: "/hr/applications", label: "投递进度更新", icon: "↗" },
        ];

  function handleSignOut() {
    void clearLocalState();
    signOut();
    navigate("/login");
  }

  return (
    <div className="app-shell">
      <aside className="sidebar" aria-label="主导航">
        <div className="brand-lockup">
          <div className="brand-mark">C</div>
          <div>
            <div className="sidebar-title">Careerpass</div>
          </div>
        </div>
        <div className="role-badge" aria-label={`当前身份：${roleLabel}`}>
          <span className="dot" aria-hidden="true" />
          <span>{roleLabel}</span>
        </div>
        <nav className="sidebar-nav" aria-label={`${roleLabel}导航`}>
          {items.map((item) => (
            <NavLink key={item.to} to={item.to} end={item.to === `/${role}`}>
              <span className="nav-icon">{item.icon}</span>
              {item.label}
            </NavLink>
          ))}
        </nav>
        <div className="sidebar-footer">
          <div className="profile-mini">
            <div className="avatar" aria-hidden="true">
              {user?.displayName.charAt(0) ?? "U"}
            </div>
            <div>
              <strong>{user?.displayName}</strong>
              <span>{user?.title}</span>
            </div>
          </div>
          <button className="logout" type="button" onClick={handleSignOut}>
            退出登录
          </button>
        </div>
      </aside>
      <main className="content-area">
        <div className="page-container">{children}</div>
      </main>
    </div>
  );
}
