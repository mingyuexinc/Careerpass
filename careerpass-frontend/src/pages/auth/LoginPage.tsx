import { useState, type FormEvent } from "react";
import { Link, useNavigate } from "react-router-dom";
import type { UserRole } from "../../domain/types";
import { useAuthStore } from "../../stores/auth-store";

export function LoginPage() {
  const navigate = useNavigate();
  const signIn = useAuthStore((state) => state.signIn);
  const [role, setRole] = useState<UserRole>("candidate");
  const [submitting, setSubmitting] = useState(false);

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSubmitting(true);
    signIn(role);
    window.setTimeout(() => navigate(`/${role}`), 220);
  }

  return (
    <section className="login-card" aria-labelledby="login-title">
      <div className="brand-lockup login-brand">
        <div className="brand-mark">C</div>
        <div>
          <strong>Careerpass</strong>
          <span>求职 Agent</span>
        </div>
      </div>
      <div className="eyebrow">CAREERPASS DEMO</div>
      <h1 id="login-title">开始你的求职旅程</h1>
      <p className="page-subtitle">
        选择身份进入对应工作台，体验从资料准备到求职 Agent 推进的完整流程。
      </p>
      <div className="role-switcher" aria-label="选择登录身份">
        <button
          type="button"
          className={role === "candidate" ? "is-active" : ""}
          onClick={() => setRole("candidate")}
        >
          求职者
        </button>
        <button
          type="button"
          className={role === "hr" ? "is-active" : ""}
          onClick={() => setRole("hr")}
        >
          HR
        </button>
      </div>
      <form onSubmit={handleSubmit} className="login-form">
        <label>
          账号
          <input
            name="username"
            defaultValue={role === "candidate" ? "candidate.demo" : "hr.demo"}
            key={role}
          />
        </label>
        <label>
          密码
          <input name="password" type="password" defaultValue="demo-only" />
        </label>
        <button className="button button-primary" type="submit" disabled={submitting}>
          {submitting ? "登录中…" : "登录 Demo"}
        </button>
      </form>
      <Link className="login-register-link" to="/register">
        了解注册流程（演示扩展）
      </Link>
    </section>
  );
}
