# 变更包管理

`.harness/changes` 用于记录每一项可追溯的设计、实现、验证和发布变更；它不存放业务源码、Alembic revision 或测试代码的副本。

## 状态与目录

变更包按状态存放，并按以下顺序流转：

`proposed` → `ready` → `in-progress` → `released` → `archived`

- `proposed`：待评审的需求、设计或契约提案。
- `ready`：已批准、等待开发的变更。
- `in-progress`：正在实现、测试或评审的变更。
- `released`：已上线、尚需保留近期追溯信息的变更。
- `archived`：已完成的历史变更、废弃提案或仅文档决策。

变更包目录格式为 `CHG-YYYY-NNN-english-kebab-case`。其中 `CHG-YYYY-NNN` 是不可变的全局唯一标识；slug 可在不改变标识的前提下随主题澄清而调整。包所在的一级状态目录是其权威状态，`change.yaml` 的 `status` 必须与之相同。

## 创建与维护

1. 从 `_templates/` 复制所需模板，在 `proposed/` 中创建新变更包。
2. 填写 `change.yaml` 与必填的 `summary.md`，标明受影响业务模块、风险、依赖和替代关系。
3. 评审通过后移动到 `ready/`；开始开发时移动到 `in-progress/`。
4. 实现、测试和发布过程只在对应阶段目录补充说明与证据；业务源码、测试代码和 Alembic revision 仍存放在正式工程目录。
5. 上线后移动到 `released/`，完成追溯周期或确认不再需要活动维护后移动到 `archived/`。

## 阶段产物

- 所有变更：根目录 `change.yaml`、`summary.md`，以及 `01-analysis/impact-analysis.md`。
- `contract`：至少包含概述和影响分析；进入实施前补充 `03-plan/task-breakdown.md`。
- `feature`、`business-module`：必须具备设计、任务拆分、实现说明和测试计划。
- 涉及数据库 Schema、约束、函数或触发器：必须在 `04-data/` 提供 `db-migrations.sql`、`rollback.sql` 与 `alembic-revisions.md`。SQL 是审阅产物；运行时迁移的唯一入口是工程中的 Alembic revision。
- 发布变更：在 `07-release/release-plan.md` 记录 API、数据库、Redis、异步任务、权限、可观测性和回滚影响。

## 校验

执行 `python .harness/changes/tools/validate_changes.py` 校验目录命名、编号唯一性、状态一致性、必填元数据和按变更类型要求的阶段文件。该校验不替代代码测试、迁移审查或发布审批。
