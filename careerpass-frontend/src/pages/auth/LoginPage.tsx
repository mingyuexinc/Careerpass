import { useState, type FormEvent } from "react";
import { Link, useNavigate } from "react-router-dom";
import type { UserRole } from "../../domain/types";
import { useAuthStore } from "../../stores/auth-store";

export function LoginPage() {
  const navigate = useNavigate();
  const login = useAuthStore((state) => state.login);
  const error = useAuthStore((state) => state.error);
  const submitting = useAuthStore((state) => state.submitting);
  const [role, setRole] = useState<UserRole>("candidate");

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    const username = String(form.get("username") ?? "");
    const password = String(form.get("password") ?? "");
    try {
      const user = await login(username, password, role);
      navigate(`/${user.role}`);
    } catch {
      // The store keeps a safe, user-facing error message.
    }
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
      <div className="eyebrow">CAREERPASS</div>
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
          <input name="username" key={role} placeholder="请输入账号" />
        </label>
        <label>
          密码
          <input name="password" type="password" placeholder="请输入密码" />
        </label>
        <button className="button button-primary" type="submit" disabled={submitting}>
          {submitting ? "登录中…" : "登录"}
        </button>
        {error ? <p role="alert">{error}</p> : null}
      </form>
      <Link className="login-register-link" to="/register">
        了解注册流程
      </Link>
    </section>
  );
}
