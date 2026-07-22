# 编码规范

## API设计规范

- RESTful 风格，资源名用复数
- 版本控制：`/api/v1/{resources}`
- 请求方法：GET查询、POST创建、PUT更新、DELETE删除
- 统—响应格式：`{code: number，message: string,data: T}`
- 错误码：4xx客户端错误，5xx服务端错误