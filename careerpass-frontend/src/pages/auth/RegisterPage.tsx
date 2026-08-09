import { Link } from "react-router-dom";

export function RegisterPage() {
  return (
    <section className="login-card" aria-labelledby="register-title">
      <div className="eyebrow">CAREERPASS</div>
      <h1 id="register-title">注册功能暂未启用</h1>
      <p className="page-subtitle">
        注册服务正在完善，当前可先返回登录页进入对应工作台。
      </p>
      <Link className="button button-primary inline-button" to="/login">
        返回登录
      </Link>
    </section>
  );
}
