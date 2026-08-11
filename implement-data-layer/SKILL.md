---
name: "implement-data-layer"
description: "Implements production database schemas, migrations, constraints, seed data, repositories, and transaction rules from the system data model and implementation plan. Use when building or updating the persistence layer."
---

# Implement Data Layer — 数据层实现

本 Skill 负责把数据模型和业务规则实现为可迁移、可验证、可回滚的数据层，并遵循当前项目已有 ORM、迁移工具和命名规范。


## 全局约束

遵循 `../_shared/references/engineering-constraints.md`（项目隔离/技术栈沿用/密钥/验证/追溯/增量修改等 10 条通用工程约束，唯一事实来源）。

**本 skill 特有约束**：无。


## 前置输入

优先读取：

- `./output/build/architecture.json`
- `./output/build/implementation-plan.md`
- `./output/spec/data-model.json`
- `./output/spec/business-rules.json`
- `./output/spec/permissions.json`
- 当前项目已有实体、Schema、迁移和数据库配置

若上游没有结构化数据模型，应从 PRD 提取并将推导内容标为 `INFERRED`，同时写入数据库实施报告。

## 实施要求

### 1. Schema 映射

- 使用当前项目既有 ORM 或迁移工具，不并行引入第二套工具。
- 精确定义字段类型、长度、精度、时区、可空性、默认值、唯一约束、外键和检查约束。
- 金额、汇率、比例和计量字段按业务精度分别设计，不机械统一精度。
- 逻辑删除、版本号和审计字段根据表类型决定；日志、关联表和不可变流水不得盲目套模板。
- 枚举需考虑数据库枚举、检查约束或字典表的演进成本。

### 2. 索引与性能

- 根据查询筛选、排序、关联、唯一性和数据权限路径建立索引。
- 避免重复索引、低选择性单列索引和无依据的全字段索引。
- 对关键列表查询记录预期执行计划和分页方式；大数据量优先考虑游标分页。

### 3. 迁移与回滚

- 每次结构变更必须产生有序迁移文件。
- 迁移应支持空库初始化和已有数据升级。
- 破坏性变更采用扩展—迁移—收缩策略，不能一步删除仍被代码使用的字段。
- 提供回滚或前向修复说明；生产数据不可逆时必须明确标记。

### 4. 数据访问和事务

- 实现当前架构约定的实体、模型、Repository 或数据访问层。
- 明确跨表写入事务边界、锁策略、幂等键和并发冲突处理。
- 查询默认避免 N+1、无限列表和未限制的模糊搜索。
- 数据权限过滤必须在可信后端层执行，不能只依赖前端隐藏。

### 5. Seed 与测试数据

- 只生成最小可用字典、角色和演示数据。
- 不写入真实个人信息和固定生产密码。
- 测试账户必须通过环境变量或开发专用初始化脚本创建。

## 验证

尽可能实际执行：

1. Schema/迁移静态校验。
2. 空库迁移到最新版本。
3. 回滚或前向修复验证。
4. 数据层单元或集成测试。
5. 唯一约束、外键、事务和并发关键场景测试。

## 输出

代码写入当前项目既有数据层目录，并更新：

```text
output/build/
├── database-implementation-report.md
├── schema-snapshot.json
└── traceability.json
```

报告必须列出实际修改文件、迁移顺序、执行命令、结果、剩余风险和阻塞项。

---

## 质量检查清单

- [ ] schema 与 PRD 数据模型一致
- [ ] migration 顺序明确且可回滚
- [ ] 约束(主键/外键/唯一/非空)完整
- [ ] 索引覆盖高频查询
- [ ] 产物自评:本 skill 产出后,按 skill-auditor 执行后评测模式自查(可选)
