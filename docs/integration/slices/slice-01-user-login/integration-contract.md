# Integration Contract：S-01 用户登录

> 本契约只定义登录页面与后端认证 API 的跨端交换。业务语义引用业务基线和后端 Slice 规格，不在此重复定义。

## 1. 基本信息

| 项目 | 内容 |
| --- | --- |
| Contract ID | `IC-S01-USER-LOGIN` |
| 版本 | `1.0` |
| 关联 Slice | `S-01` 用户登录 |
| 关联 Integration Scenario | `IS-S01-01` |
| Producer | 后端 `S-01` 认证 API |
| Consumer | 前端 `/login` 登录页 |
| 状态 | `locked` |

## 2. 用户场景与边界

- 求职者和 HR 都作为 `User` 登录主体，通过 `active_role` 进入对应工作区。
- 用户在登录页选择身份、输入账号密码并提交；服务端确认账号、密码和所选身份后返回 Access Token 及可信身份摘要。
- 成功结果是进入与服务端确认身份一致的 `/candidate` 或 `/hr` 工作区。
- 注册、退出登录、Refresh Token、资源级授权和下游业务不属于本契约。
- 业务依据：[`business-baseline.md`](../../../business/business-baseline.md) 中 `BF-FLOW-002`、`BF-RULE-001`、`BF-RULE-003`、`BF-SCOPE-005`；Slice 依据：[`slice-spec.md`](../../../../careerpass-backend/docs/development/slices/slice-01-user-login/slice-spec.md)。

## 3. 请求契约

### 3.1 登录

`POST /api/v1/auth/login`

- 无需认证；请求体为 `application/json`。
- 前端发送的角色值必须是 `candidate` 或 `hr`；服务端必须再次校验该角色属于当前账号。

| 字段 | 类型 | 必填 | 约束 |
| --- | --- | --- | --- |
| `username` | string | 是 | 去除首尾空白后长度 3–64；只允许 `A-Z`、`a-z`、数字、`_`、`.`、`-` |
| `password` | string | 是 | 长度 1–128；仅作为密码输入，不在日志或响应中回显 |
| `active_role` | string | 是（当前前端） | `candidate` 或 `hr`；由服务端确认账号确实拥有该身份 |

请求示例：

```json
{
  "username": "candidate_01",
  "password": "123",
  "active_role": "candidate"
}
```

受控演示账号和账号初始化方式以 [`backend-delivery-scope.md`](../../../../careerpass-backend/docs/product/backend-delivery-scope.md) 为准：`candidate_01 / 123`、`hr_01 / 123`。前端不得将账号密码写入正式接口适配器之外的业务事实或日志。

## 4. 响应契约

所有响应遵循 `{code, msg, data}`。

### 4.1 成功

HTTP `200`，`code` 为 `200`：

```json
{
  "code": 200,
  "msg": "success",
  "data": {
    "access_token": "<token>",
    "token_type": "Bearer",
    "expires_in": 1800,
    "user": {
      "user_id": "<uuid>",
      "roles": ["candidate"],
      "active_role": "candidate",
      "candidate_id": "<uuid>",
      "hr_profile_id": null,
      "profile_status": null
    }
  }
}
```

`hr` 登录时 `roles` 和 `active_role` 为 `hr`，`hr_profile_id` 为对应身份 ID，`candidate_id` 为 `null`。`access_token` 仅用于后续认证请求；前端不得依赖 JWT 内部字段形成角色事实。

### 4.2 失败

| 场景 | HTTP / `code` | `data` | 前端表现 |
| --- | --- | --- | --- |
| 请求字段校验失败 | `400 / 400` | `null` | 保留登录页并显示可理解的输入错误 |
| 账号、密码、角色或身份关系不匹配 | `401 / 401` | `null` | 显示统一登录失败信息，不泄露具体失败原因 |
| 缺少或无效 Bearer Token（后续 `/auth/me`） | `401 / 401` | `null` | 清理本地登录状态并回到登录页 |

认证失败统一使用安全错误信息；不得区分“账号不存在”“密码错误”或“角色不匹配”。

### 4.3 当前身份查询

`GET /api/v1/auth/me`，请求头：`Authorization: Bearer <access_token>`。

成功响应仍遵循 `{code, msg, data}`，`data` 至少包含 `user_id`、`username`、`roles`、`active_role`、`candidate_id`、`hr_profile_id` 和 `profile_status`。该接口用于恢复当前登录身份，不扩大为资源授权接口。

## 5. 状态与兼容性

- 登录是同步请求；前端提交期间禁用重复提交，成功后保存 Token 和服务端确认的活动身份。
- 登录成功不会创建业务资源，也不触发异步任务。
- `1.0` 允许新增可选响应字段；删除字段、修改字段含义、改变角色值或改变错误语义必须升级 Major 版本，并回退到 Slice Design 重新评审。

## 6. 安全边界

- 密码、密码哈希和 Token 不进入日志、追踪或错误响应。
- Token 只在成功响应中返回；前端仅将其用于认证请求。
- `User` 身份模型只解决登录身份和角色交接，不代表资源级归属或权限校验已实现。
