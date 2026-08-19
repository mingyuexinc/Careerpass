# Integration Scenario：IS-S08-01 岗位匹配与投递闭环

| 项目 | 内容 |
| --- | --- |
| Scenario ID | `IS-S08-01` |
| 名称 | S-07 启动后同步完成岗位匹配并查看投递结果 |
| 关联 Slice | `S-08` |
| Integration Contract | [`integration-contract.md`](integration-contract.md) `IC-S08-JOB-MATCHING@0.1` |
| 场景类型 | `frontend_visible` |
| 交付状态 | `integration_delivered` |

## 1. 交付目标

在受控 HR 和 Candidate 场景下，Candidate 完成简历、画像和求职目标准备后启动 Agent。S-07 提交运行上下文并完成事务后，S-08 同步筛选关联 HR 的全部可用结构化 JD，独立保存 Match，为通过投递筛选的岗位创建 Application。Candidate 在求职进度页查看投递记录、推荐匹配得分和推荐理由。

```text
HR 准备并上传岗位 JD
→ S-03 形成可用结构化 JD
→ Candidate 完成简历解析和求职目标
→ Candidate 点击启动 Agent
→ S-07 提交运行上下文
→ S-08 同步逐个筛选最多 20 个岗位
→ 保存 Match，并为通过筛选的岗位创建 Application
→ Candidate 进入求职进度页查看投递结果、匹配得分和推荐理由
```

## 2. 前置条件与演示数据

- S-01 Candidate 和 HR 登录、身份恢复和资源归属校验可用；
- 当前 Candidate 有解析成功且 `matching_ready` 的简历画像；
- 当前 Candidate 有 `active` 求职目标；
- 当前岗位 JD 已由 S-03 解析成功，且五项核心字段有效；
- 当前演示只覆盖一个 HR 和一个 Candidate；
- 关联 HR 的可用岗位不超过 20 个；
- 演示只产生系统内 Match、Application 和 ProgressEvent，不产生真实外部投递。

最小演示数据集：

| 数据集 | 必要条件 | 用途 |
| --- | --- | --- |
| `s08-mixed-results` | 至少 1 个 `filtered_out`、1 个 `not_matched` 和 1 个 `matched` 岗位 | 验证逐岗筛选、Match 独立持久化和 Application 创建 |
| `s08-no-application` | 所有可用岗位被硬过滤或评分未达阈值 | 验证 `finished/no_match` 和空状态 |
| `s08-twenty-jobs` | 20 个可用结构化岗位 | 验证同步岗位池边界 |
| `s08-repeat-start` | 当前 Candidate 已存在运行上下文 | 验证重复启动、重复筛选和投递幂等 |

## 3. 演示步骤与预期结果

| 步骤 | 操作 | 预期系统结果 | 预期页面结果 |
| --- | --- | --- | --- |
| 1 | Candidate 完成简历解析和求职目标创建 | S-07 启动条件满足；目标、简历和画像归属校验通过 | 启动按钮可用 |
| 2 | Candidate 点击启动 Agent | S-07 提交运行上下文并提交事务；S-08 同步读取关联 HR 的全部可用岗位，最多 20 个 | 不展示匹配中间过程 |
| 3 | S-08 逐个筛选岗位 | 每个 `run_id + job_id` 最多保存一条 Match；不采用 Top-N 截断 | 页面不伪造未查询到的匹配结果 |
| 4 | 岗位命中硬过滤条件 | 保存 `filtered_out` Match，不计算三维评分，不创建 Application | 该岗位不出现在求职进度页 |
| 5 | 岗位进入评分但总分未达阈值 | 保存 `not_matched` Match，不创建 Application | 该岗位不出现在求职进度页 |
| 6 | 岗位达到匹配阈值 | 保存完整评分和推荐理由，创建 `submitted` Application，并记录初始 `application_created` ProgressEvent | 进度页展示岗位、投递状态、匹配得分和推荐理由 |
| 7 | Candidate 进入求职进度页 | 只查询当前 Candidate 的 Application，不查询未投递 Match | 展示已投递结果 |
| 8 | 全部岗位筛选完成且 Application 数量为 0 | AgentRun 进入 `finished`，`finish_reason=no_match` | 展示“当前没有可供匹配的岗位”及 Agent 已结束 |
| 9 | 重复提交启动或重入 S-08 | 复用当前运行上下文；不重复生成 Match、Application 或 ProgressEvent | 页面结果不重复 |

## 4. 最小演示验证结果

### 4.1 固定简历技能解析与匹配回归

本次整改使用固定文件 `resume_01.pdf`、相同岗位 JD 和相同求职目标创建新的 AgentRun，不覆盖历史 Match。

| 验证项 | 预期结果 | 实际结果 |
| --- | --- | --- |
| 简历解析 | `CandidateProfile.skills` 非空，项目 `technologies` 合并且经历 `highlights` 保留 | 已通过；固定简历解析成功，技能字段非空，工作经历 highlights 共 10 条 |
| 匹配输入快照 | `candidate.experience_highlights` 和 `candidate.project_highlights` 与画像一致 | 已通过；新 Match 快照包含两类字段 |
| 岗位结果 | 7 个岗位均有 Match；北京岗位仍为 `filtered_out`，不进入评分 | 已通过；7 条 Match 中 2 条北京岗位为 `filtered_out` |
| 匹配数量 | 按已确认演示结果形成 2 个 Application；记录 7 个岗位的状态和分数 | 实际为 5 个 Application；当前数据库无昨日 2 个匹配的历史运行快照，无法复现该基线 |

本次修复确认了解析链路和匹配输入缺陷，但未改变权重、阈值或地点过滤。修复后的新运行得分为：`001=83`、`002=82.09`、`003=86.33`、`004=74.11`、`006=83`，`005` 和 `007` 因北京被过滤。历史“2 个匹配”缺少可比输入快照，不能据此调整算法参数。

> 开发者已完成 S-08 真实前后端闭环复测；此前记录的问题均已整改并通过验收。

| 记录编号 | 操作 | 实际结果 | 其它问题 |
| :-: | --- | --- | --- |
| 1 | 开发者先以 HR 身份上传岗位 JD，再以求职者身份上传简历，创建求职目标，然后启动求职 Agent | 首次演示无法启动：保存求职目标后，前端将简历状态重置为空，任务页判定简历条件未满足 | 已定位并修复前端真实 API 状态被 Mock 快照覆盖的问题；补充“保存目标后仍保留真实简历”的回归测试 |
| 2 | 开发者先以 HR 身份上传岗位 JD，再以求职者身份上传简历，创建求职目标，然后启动求职 Agent | 同步匹配一小段时间以后，匹配结束，在求职进度查看页面中发现匹配结果 | 发现保存按钮状态/焦点切换、岗位地点过滤未生效和推荐信息区域拥挤问题，详见 `S08-UI01`、`S08-MATCH01`、`S08-UI02`。 |

## 5. 问题与整改

> 本节记录实现级验证发现、已恢复的运行环境和当前演示数据阻塞；数据补齐后继续补写完整真实演示结果。

| 记录编号 | 问题类型 | 原因与分析 | 整改结果 | 验收结果 |
| --- | --- | --- | --- | --- |
| S08-E01 | 环境 | 原因是 Docker Compose 集成栈未运行，导致 `localhost:8080` 没有监听；不是后端端口配置或 S-08 代码错误 | 使用后端统一 readiness 检查确认 Docker Engine/Compose 可用，并启动 `docker-compose.integration.yml`；迁移执行到 `20260817_0013`，后端、Worker、Dispatcher 均运行 | 已整改；API 冒烟通过 |
| S08-E02 | 演示数据 | 集成库有 3 条 Job，但 `parsed_job_description_snapshots` 为 0，无法形成 `s08-mixed-results` 的结构化岗位池 | 已补齐 S-08 复测所需的结构化 JD 演示数据，并完成混合结果、20 岗位和重复启动验收 | 已通过开发者复测 |
| S08-FE01 | 前端状态 | 真实 Candidate API 操作完成后，`workspace-store` 仍以 Mock 快照作为完整状态基线；保存求职目标时，Mock 快照中的空 `resume` 覆盖了后端已上传的简历，导致启动条件和资料页显示错误 | 真实 Candidate 工作区改为以当前 Store 状态合并 API 返回值；刷新、简历上传、附加资料上传和求职目标保存均不再用 Mock 快照覆盖真实字段，并补充状态保留回归测试 | 已修复；前端相关测试 12/12 通过 |
| S08-I02 | 算法参数 | JD 薪资解析值按元保存，而用户条件按 K 表达 | v0.1 增加元→K 的比较归一化，并补充硬过滤单测 | 已通过单测 |
| S08-UI01 | 前端交互 | 保存求职目标使用全局 loading，保存按钮临时禁用后浏览器焦点转移；按钮文案又同时依赖目标对象状态，造成保存/创建状态在演示中表现为切换 | 保存目标与启动 Agent 使用独立操作状态；保存按钮防重复提交并在原焦点属于该按钮时恢复焦点，真实 API 状态继续作为唯一来源 | 已修复并通过开发者复测 |
| S08-UI02 | 前端布局 | 推荐匹配得分和推荐理由直接放在岗位信息下方，缺少独立容器和宽度约束，导致标题下方多行文本拥挤 | 将推荐信息放入独立右侧卡片，补充得分强调色、理由换行和移动端纵向布局 | 已修复并通过开发者复测 |
| S08-MATCH01 | 匹配逻辑 | 过滤文本 `不考虑北京的工作岗位` 被提取为 `北京的工作岗位`，地点归一化未去除“的工作岗位”后缀，因此北京岗位错误进入评分 | 扩充地点、岗位和职位后缀归一化，命中后保存 `filtered_out` Match，不计算评分且不创建 Application；历史轮次结果不回写，清理旧轮次后重新运行验收 | 已修复并通过开发者复测 |

## 6. 关闭结论

- 开发者已完成 S-08 真实前后端闭环复测，混合结果、20 岗位、重复启动及空结果路径均通过验收；
- `S08-E01`、`S08-E02`、`S08-FE01`、`S08-I02`、`S08-UI01`、`S08-UI02` 和 `S08-MATCH01` 均已关闭；
- 当前阶段结论：S-08 Integration Verify 通过，`IS-S08-01` 已标记为 `integration_delivered`，S-08 交付完成。
