# 部署验证技能

## 概述

规范化部署流程和验证步骤，确保上线安全可控

## 触发条件

当代码通过集成测试，准备部署到预发/生产环境时，自动激活此技能

## 环境清单

| Env        | URL                             | Purpose  | Access   |
| ---------- | ------------------------------- | -------- | -------- |
| dev        | http://dev.careerpass.loacl     | 开发联调 | 开发团队 |
| test       | http://test.careerpass.loacl    | 集成测试 | 测试团队 |
| staging    | http://staging.careerpass.loacl | 预发验证 | 全员     |
| production | http://www.careerpass.com       | 线上生产 | 运维团队 |

## 部署前检查清单

### 代码检查

- [ ] 所有代码已合并到发布分支
- [ ] CI流水线已经全部通过
- [ ] 代码评审已完成，无🔴问题
- [ ] 单元测试覆盖率达标



### 数据库检查

- [ ] SQL变更脚本已准备（forward + rollback）
- [ ] 数据迁移已在test环境验证
- [ ] 大表变更评估影响



### 配置检查

- [ ] 新增配置已在目标环境配置
- [ ] 环境变量已更新