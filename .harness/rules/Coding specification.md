# 编码规范

## API设计规范

- RESTful 风格，资源名用复数
- 版本控制：`/api/v1/{resources}`
- 请求方法：GET查询、POST创建、PUT更新、DELETE删除
- 统一响应格式：`{code: number, msg: string, data: T}`
- 响应描述字段唯一使用 `msg`；禁止使用 `message`。该约定与 `.harness/wiki/Interface protocol.md` 保持一致。
- 错误码：4xx客户端错误，5xx服务端错误

## 异常处理与错误码规范

- 业务异常必须引用统一的 `ErrorCode` 枚举或等价的受控错误码定义；禁止在业务代码中直接使用面向用户的错误字符串作为错误码或异常标识。
- 每个 `ErrorCode` 必须集中定义并映射唯一的 HTTP 状态、响应体 `code` 和 `msg`；异常处理器是该映射生成 `{code, msg, data}` 的唯一入口，业务代码不得自行设置 HTTP 状态或 `msg`。
- `msg` 由统一的错误码映射生成，必须使用受控、脱敏的场景文案；不得拼接文件路径、异常堆栈、供应商原始错误或其他敏感信息。

```python
# ✔ 正确：使用受控错误码
raise BusinessException(ErrorCode.FILE_NOT_FOUND)

# × 错误：直接以自然语言字符串表示业务错误
raise BusinessException("文件未找到")
```
