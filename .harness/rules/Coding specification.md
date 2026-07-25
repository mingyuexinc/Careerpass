# 编码规范

## API设计规范

- RESTful 风格，资源名用复数
- 版本控制：`/api/v1/{resources}`
- 请求方法：GET查询、POST创建、PUT更新、DELETE删除
- 统一响应格式：`{code: number, msg: string, data: T}`
- 响应描述字段唯一使用 `msg`；禁止使用 `message`。该约定与 `.harness/wiki/Interface protocol.md` 保持一致。
- 错误码：4xx客户端错误，5xx服务端错误
