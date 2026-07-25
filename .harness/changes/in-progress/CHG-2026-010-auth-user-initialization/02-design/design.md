# 设计说明

注册请求先经 Pydantic 校验，再由应用服务调用 Repository，在一个事务中创建 User 与 Candidate。登录校验密码后，通过可信 `user_id` 解析唯一 Candidate。受保护接口统一通过 Bearer Token 校验及 Repository 复核获取当前身份。

所有接口经统一响应包装返回，认证失败使用统一错误语义。
