import { Link } from "react-router-dom";

export function RegisterPage() {
  return (
    <section className="login-card" aria-labelledby="register-title">
      <div className="eyebrow">CAREERPASS DEMO</div>
      <h1 id="register-title">注册功能暂未启用</h1>
      <p className="page-subtitle">
        本期 Demo 使用固定身份，注册页面保留为后续真实账号体系的扩展入口。
      </p>
      <Link className="button button-primary inline-button" to="/login">
        返回登录
      </Link>
    </section>
  );
}
