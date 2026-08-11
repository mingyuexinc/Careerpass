# MinerU 能力验证

> 本文档只记录 MinerU 接入的真实验证证据和限制，不承担解析 Slice 方案或业务契约职责。

## 1. 当前结论

状态：partial。

- 2026-07-27 使用受控凭证启动同机 stdio MCP Bridge，initialize 和 tools/list 成功。
- 工具发现结果包含 parse_documents 和 get_ocr_languages。
- 该证据只证明 MCP 会话和工具发现，不证明受控 PDF 能稳定得到可用 Markdown。
- 远程 MCP 地址使用现有 Bearer 方式在工具发现阶段返回 401，当前不能作为可用方案。

## 2. 当前首选边界

- Worker 是 MCP Client；受控启动的 mineru-open-mcp 子进程是 MCP Server。
- 命令和参数由配置固定，不接受 API、Agent、模型或文件内容拼接。
- 凭证仅通过子进程环境注入，不进入命令行、日志或响应。
- 本地临时文件由系统创建并在调用后清理，路径不进入业务契约。

## 3. 通过标准

将状态改为 passed 前必须以受控脱敏 PDF 证明：

- MCP 会话建立且 parse_documents 可调用；
- 返回非空、可供后续 Schema 处理的 Markdown；
- 临时文件在成功和失败后均被清理；
- 超时、不可读文件、限流和服务错误映射为受控失败分类；
- 日志与测试证据不包含令牌、正文、内部路径或供应商原始响应。

未满足完整标准前，具体解析 Slice 的 Readiness Check 不得把 MinerU 标记为已通过。
