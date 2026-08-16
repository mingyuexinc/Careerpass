# Integration Contract：S-DBG 当前账号数据恢复

| 字段 | 值 |
| --- | --- |
| Contract ID | `IC-SDBG-RESET` |
| Version | `0.1` |
| Status | `locked` |
| Authentication | Bearer Token；当前身份由服务端解析 |

## Endpoint

```http
POST /api/v1/debug/reset/current-account
```

请求无 Body。客户端不得提交 `user_id`、`candidate_id`、`hr_profile_id` 或资源 ID。

## Success

```json
{
  "code": 200,
  "msg": "debug data reset",
  "data": {
    "reset": true,
    "scope": "current_account"
  }
}
```

## Errors

| HTTP | `code` | 语义 |
| --- | --- | --- |
| 401 | 401 | 未登录或身份无效 |
| 403 | 403 | 调试恢复能力未开启 |
| 409 | 409 | 当前账号存在活动任务或无法安全删除的关联数据 |
| 500 | 500 | 服务端未预期失败 |

错误响应中的 `data` 为 `null`，不得包含 SQL、内部路径、令牌或异常堆栈。

## Client Behavior

前端在 Vite 开发模式默认显示按钮；非开发模式仅在 `VITE_DEBUG_RESET_ENABLED=true` 时显示。后端开关是最终权限边界。成功后清空本地工作区、清除登录态并跳转 `/login`；失败时保留页面和登录态。
