import type { ReactNode } from "react";
import { NavLink, useNavigate } from "react-router-dom";
import { useAuthStore } from "../stores/auth-store";
import { useDemoStore } from "../stores/demo-store";
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
  const resetDemo = useDemoStore((state) => state.resetDemo);
  const demoLoading = useDemoStore((state) => state.loading);
  const roleLabel = role === "candidate" ? "求职者工作台" : "HR 工作台";
  const items: NavigationItem[] =
    role === "candidate"
      ? [
          { to: "/candidate", label: "使用指南", icon: "⌂" },
          { to: "/candidate/documents", label: "求职资料", icon: "↥" },
          { to: "/candidate/job-goal", label: "求职任务", icon: "◎" },
          { to: "/candidate/progress", label: "求职进度", icon: "▥" },
        ]
      : [
          { to: "/hr", label: "使用指南", icon: "⌂" },
          { to: "/hr/jobs", label: "岗位 JD", icon: "↥" },
          { to: "/hr/conversations", label: "求职沟通", icon: "□" },
          { to: "/hr/applications", label: "投递进度", icon: "↗" },
        ];

  function handleSignOut() {
    signOut();
    navigate("/login");
  }

  async function handleReset() {
    await resetDemo();
    navigate(`/${role}`);
  }

  return (
    <div className="app-shell">
      <aside className="sidebar" aria-label="主导航">
        <div className="brand-lockup">
          <div className="brand-mark">C</div>
          <div>
            <div className="sidebar-title">Careerpass</div>
            <div className="sidebar-role">{roleLabel}</div>
          </div>
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
          <div>
            <strong>{user?.displayName}</strong>
            <span>演示账号 · {user?.title}</span>
          </div>
          <button type="button" onClick={() => void handleReset()} disabled={demoLoading}>
            重置演示数据
          </button>
          <button type="button" onClick={handleSignOut}>
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
