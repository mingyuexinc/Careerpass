# `updated_at` 数据库触发器策略

## 变更概述

为所有声明 `updated_at` 的表规定由 PostgreSQL `BEFORE UPDATE` 触发器统一维护时间戳。当前迁移覆盖 `users` 与 `candidates` 表。

## 影响模块

- 用户管理
- 求职者管理
- Repository 数据更新路径
- 数据库基础设施

## 数据库变更

- 新增共用触发器函数 `set_updated_at()`。
- 为 `users` 和 `candidates` 绑定 `BEFORE UPDATE FOR EACH ROW` 触发器。
- 迁移前校验两个目标表及其 `updated_at` 列均存在；不满足时终止迁移，避免在错误的 Schema 上执行。

## API变更

无。

## Redis变更

无。

## 关键约束

- `created_at` 仅由插入默认值初始化，不在更新时修改。
- `updated_at` 的最终值由数据库触发器写入；Repository、Service 和 Agent 不得手动设置或信任外部输入。
- 后续新增 `updated_at` 字段的表必须在同一迁移中绑定该触发器。

## 回滚方案

先解绑本次新增的表级触发器，再在确认不存在其他依赖后删除 `set_updated_at()` 函数；不修改任何既有业务数据。

## 验证方案

- 分别插入 `users` 和 `candidates` 记录，确认 `created_at` 与 `updated_at` 均由数据库初始化。
- 分别更新两个表的业务字段，确认 `created_at` 保持不变且 `updated_at` 刷新。
- 通过 Repository 与直接 SQL 两种路径更新，确认均触发时间戳刷新。
- 执行回滚脚本，确认仅移除本次触发器和函数，且不修改既有业务数据。

## 关联与实施状态

- 关联需求/变更包：CHG-2026-002（数据模型一致性）。
- 当前状态：已确认，待实现。

## 验收标准

- 受影响表的 `updated_at` 在任何更新路径中均由数据库触发器维护。
- 正向迁移与回滚仅影响本次声明的触发器和函数。
