---
name: "plan-system-implementation"
description: "Creates an executable technical implementation plan from existing PRD, page specifications, prototype, and repository. Use before coding a production system or when architecture, stack, module boundaries, API contracts, and delivery increments must be decided."
---

# Plan System Implementation — 系统实施规划

本 Skill 将已有 PRD、页面规格、原型和当前代码仓库转换为**可执行的工程实施蓝图**。它不以泛化技术方案代替代码事实，也不在缺少依据时强行换技术栈。


## 全局约束

遵循 `../_shared/references/engineering-constraints.md`（项目隔离/技术栈沿用/密钥/验证/追溯/增量修改等 10 条通用工程约束，唯一事实来源）。

**本 skill 特有约束**：无（纯规划 skill，不涉及高风险操作）。


## 输入优先级

1. 用户明确指定的文档或目录。
2. `./output/spec/`：`pages.json`、`data-model.json`、`business-rules.json`、`permissions.json`、`annotations.json` 等（由 `generate-system-prd` / `generate-prototype` 按需产出）。
3. `./output/docs/`：PRD、页面规格、原型说明；工作区根目录下的 `{系统名称}-产品设计方案-*.md`、`{系统名称}-页面原型文档.md` 视为同等输入。
4. `./output/site/`：HTML 原型页面（`pc/`、`mobile/`）和演示门户 `index.html`（由 `generate-html-pages` / `generate-portal` 产出）。
5. 当前项目已有源码、配置、测试、CI 和基础设施。

至少存在需求文档或现有代码之一才可执行。资料不足时，用 `TBD` 和风险项表达，不得补造确定事实。

## 核心流程

### 1. 仓库与需求盘点

- 识别单体、多包、前后端分离或微服务结构。
- 识别语言、框架、运行时、包管理器、数据库、认证、测试与部署方式。
- 建立需求覆盖表：页面、业务规则、校验、权限、状态机、异常场景。
- 标记原型与 PRD 的冲突、缺口和不可实现交互。

### 2. 技术决策

- 现有项目存在技术栈时，默认沿用并说明限制。
- 新项目才进行技术选型；选型必须基于团队能力、交付周期、数据规模、安全要求和部署环境。
- 对数据库、缓存、对象存储、消息队列、认证、审计、可观测性分别给出“采用 / 暂不采用 / TBD”。
- 重大决策用 ADR 记录备选项、选择理由、后果和回滚条件。

### 3. 架构与契约

必须定义：

- 模块边界和依赖方向。
- 前端路由、页面与组件边界。
- 后端 API、服务、领域和数据访问边界。
- 数据库迁移策略与事务边界。
- 认证、RBAC、数据权限和审计链路。
- 错误码、幂等、分页、文件上传、异步任务和外部集成策略。
- 本地、测试、预发布和生产环境差异。

### 4. 垂直切片计划

不要按“先写完全部数据库，再写全部后端”组织总计划。将系统拆成可验证的垂直切片，每个切片包含：

- 对应需求 ID 和页面 ID。
- 数据迁移或模型。
- API 与权限。
- 前端页面及状态。
- 自动化测试和验收步骤。
- 完成定义与回滚方式。

基础设施 Skill 可按技术层执行，但 `task-board.json` 必须保留垂直业务切片。

## 输出

```text
output/build/
├── implementation-plan.md
├── architecture.json
├── task-board.json
├── traceability.json
├── risk-register.md
└── decisions/
    ├── ADR-001-stack.md
    ├── ADR-002-auth.md
    └── ...
```

`architecture.json` 至少包含：`projectRoot`、`existingStack`、`targetStack`、`modules`、`dataStores`、`auth`、`integrations`、`environments`、`commands`。

`task-board.json` 每个任务至少包含：`id`、`sliceId`、`title`、`sourceIds`、`dependencies`、`targetFiles`、`verificationCommands`、`status`。

输出文件的结构可参考 `../_shared/references/schemas/` 下的共享示例（唯一事实来源，不要在本地重建拷贝）：`architecture.example.json`、`task-board.example.json`、`traceability.example.json`、`acceptance-matrix.example.json`、`release-manifest.example.json`。

## 质量门禁

- 不得出现“待后续实现”但没有任务 ID 的悬空项。
- 所有 P0 页面、规则和权限必须映射到实施任务或明确标记阻塞。
- 所有命令必须来自仓库事实或明确标记为建议命令。
- 计划必须包含测试、迁移、回滚、安全和部署工作。
