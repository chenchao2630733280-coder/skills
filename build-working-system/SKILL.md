---
name: "build-working-system"
description: "Orchestrates the complete conversion of existing PRD, page specifications, and prototypes into a runnable, tested, and deployable system. Use when the user asks to generate, build, implement, or finish the whole system rather than one technical layer."
---

# Build Working System — 可运行系统编排器

本 Skill 是开发阶段总入口。它按项目现状执行实施规划、数据层、后端、前端、集成、测试和部署准备，目标是交付**当前环境中可运行并有验证证据的系统**，而不是只输出代码样例。

## 全局安装、项目隔离与执行真实性

1. 当前项目根目录是 TRAE 当前打开的目标工作区根目录；所有相对路径均从该目录解析。
2. 禁止读取或修改当前工作区之外的其他项目、TRAE 安装目录、全局 Skill 目录和 Skill 自带 `references/`。
3. Skill 自带参考文件只读；项目实际文档写入 `./output/build/`，业务代码写入当前项目既有源码目录。
4. 修改前必须检查目录结构、包管理器、框架、版本文件、环境变量示例、现有测试和 Git 工作区状态。
5. 优先扩展现有技术栈和编码约定；未经用户明确要求，不得擅自重建项目、替换框架或删除既有功能。
6. 禁止写入真实密钥、密码、Token 或生产凭据；只允许创建安全的 `.env.example` 和占位值。
7. 每次执行后必须运行当前环境可用的 lint、类型检查、测试、构建或迁移验证；未实际运行的检查不得声称通过。
8. 遇到外部服务、凭据、网络或基础设施缺失时，完成可离线完成的部分，并在报告中记录准确阻塞项，不得伪造成功。
9. 所有实现必须可追溯到 `PXX / BR-XXX / VR-XXX / PERM-XXX / SM-XXX / SXX`；映射写入 `./output/build/traceability.json`。
10. 不覆盖无关文件；对高风险变更采用增量修改、兼容迁移和可回滚方案。
11. 高风险变更（如删除文件、修改配置、数据库迁移）前，调用 guardrail 前置检查（检查 output/ 路径是否在敏感清单）。

## 适用场景

- 用户已有 PRD、页面规格和原型，要求“生成系统”“开始开发”“做成可运行项目”。
- 项目已有部分代码，需要继续实现直到形成可验收版本。
- 用户未指定单一技术层，需要自动决定合理执行顺序。

如果用户只要求某一层，应使用对应专用 Skill，避免无关改动。

## 编排阶段

### Stage 0：恢复与盘点

- 检查 `./output/build/task-board.json`、报告和当前 Git 状态。
- 已验证完成的阶段不重复重写；发现代码与报告不一致时以代码和实际检查为准。
- 确认目标项目根目录和现有启动方式。

### Stage 1：实施规划

调用 `plan-system-implementation` skill，**恢复或更新**已有架构、任务板和追溯矩阵（若 product-pipeline-master 阶段6已首次产出实施蓝图，本阶段为更新；若直接从 build-working-system 启动，本阶段为首次产出）。

### Stage 2：基础可运行骨架

- 新项目建立与技术决策一致的最小工作区、配置、环境示例和健康检查。
- 现有项目只补缺失基础设施，不重建目录。
- 确保最小应用能够安装依赖并启动，随后再实现业务。

### Stage 3：按垂直切片实现（按名调用 implement-* skill）

对每个 P0 切片**按名调用以下三个专用 skill** 完成各层实现，本 skill 自身不直接写代码：

1. **数据层** — 调用 `implement-data-layer` skill：按 `output/build/architecture.json` 与领域模型产出 schema/migration/constraints/seed/repo。
2. **后端** — 调用 `implement-backend` skill：基于 API 契约实现领域服务、校验、授权、审计与集成测试。
3. **前端** — 调用 `implement-frontend` skill：将已批准的页面规格与 HTML 原型转译为生产级前端（类型化 API、可访问性、权限、测试）。

每层调用完毕后，对当前切片补齐：

4. 权限、审计和错误处理（跨层一致）。
5. 自动化测试和手工验收步骤。

**调用约束**：
- 三个 implement-* skill 的输入为上游产物（PRD / 原型 / implementation-plan / architecture.json / JSON 工件），输出写入项目源码目录与本 skill 的 `output/build/*-implementation-report.md`。
- 优先完成一条端到端主流程，再扩展其他模块，避免各层都只有半成品。
- implement-* skill 之间允许并行（数据层无前后端依赖时），但必须共享同一份 architecture.json 与 API 契约。

### Stage 4：系统集成

调用 `integrate-system` skill 替换关键 Mock、接通认证权限、文件/任务/外部服务，并运行端到端烟雾测试。

### Stage 5：测试与加固

调用 `test-and-harden-system` skill 运行质量门禁、修复阻塞缺陷并输出证据。

### Stage 6：部署准备与交付

调用 `package-and-deploy-system` skill 生成可重复构建、容器/CI、部署文档、运维手册和发布清单。

**前置门禁输入**（来自上游 Stage，必须已存在）：
- `output/build/release-blockers.json` — 由 Stage 5 `test-and-harden-system` 产出，发布前置门禁读取
- `output/build/test-report.md` — 由 Stage 5 `test-and-harden-system` 产出，发布前置门禁读取
- `output/build/architecture.json` — 由 Stage 1 `plan-system-implementation` 产出，含 existingStack/targetStack/modules/dataStores/commands 等技术决策
- `output/build/traceability.json` — 由 Stage 1 产出，交付文档需引用

**tool-* 调用参数来源**（package-and-deploy-system 调用三个 tool-* skill 时，参数来源约定）：
- `tool-db-ops migrate --migration-dir`：migration 目录由 Stage 3 `implement-data-layer` 产出，路径从 `architecture.json` 的 `commands.migrationDir` 或项目既有 `migrations/` 目录解析
- `tool-ci-ops trigger --platform --repo`：platform 从项目既有 CI 配置（`.github/workflows/` / `.gitlab-ci.yml` / `Jenkinsfile`）自动识别；repo 从 Git remote 或 `architecture.json` 的 `modules[].repo` 解析
- `tool-monitor-ops logs/metrics/trace --service`：service 名从 `architecture.json` 的 `modules[].name` 解析，取已部署的 P0 模块

**guardrail 前置检查**：Stage 6 涉及数据库迁移（tool-db-ops）和 CI 触发（tool-ci-ops trigger）等高风险变更操作，调用 package-and-deploy-system 前必须先过 `guardrail` 前置检查（检查 `output/` 路径是否在敏感清单，确认 `--confirm` 参数已显式传入）。

## 自动决策规则

- 存在成熟代码库：沿用技术栈和目录。
- 空项目且用户未指定技术栈：根据 PRD、部署环境和团队约束选择常见稳定方案，并写 ADR；选择仍有重大影响时标为 `TBD`，但可用合理默认值继续构建最小版本。
- 时间或上下文不足：优先完成一个可运行的 P0 垂直切片、真实测试结果和清晰任务板，不生成大量不可运行占位代码。
- 外部凭据缺失：使用接口适配器和本地假实现完成离线链路，并准确标记生产集成阻塞。

## 完成定义

系统只有同时满足以下条件才可标记为“可运行交付”：

- 安装和启动命令已实际验证。
- 数据库可从空库迁移。
- 至少一条 P0 主流程端到端通过。
- 权限拒绝和关键校验已验证。
- lint、类型检查、阻塞测试和生产构建通过，或剩余失败被明确记录为外部阻塞。
- `.env.example`、README、迁移、测试和回滚说明完整。
- `traceability.json` 可从需求追到代码和测试。

## 最终输出

除实际源码外，最终至少生成：

```text
output/build/
├── architecture.json                 # Stage 1 plan-system-implementation 产出
├── implementation-plan.md            # Stage 1
├── task-board.json                   # Stage 1
├── traceability.json                 # Stage 1
├── database-implementation-report.md # Stage 3 implement-data-layer 产出
├── backend-implementation-report.md  # Stage 3 implement-backend 产出
├── frontend-implementation-report.md # Stage 3 implement-frontend 产出
├── integration-report.md             # Stage 4 integrate-system 产出
├── test-report.md                    # Stage 5 test-and-harden-system 产出
├── release-blockers.json             # Stage 5 产出（package-and-deploy-system 读取）
├── release-manifest.json             # Stage 6 package-and-deploy-system 产出
├── deployment-report.md              # Stage 6 产出
├── operations-runbook.md            # Stage 6 产出
├── handoff-checklist.md              # Stage 6 产出
├── db-ops-report.json                # Stage 6 tool-db-ops 产出（按需）
├── ci-ops-report.json                # Stage 6 tool-ci-ops 产出（按需）
└── monitor-ops-report.json           # Stage 6 tool-monitor-ops 产出（按需）
```

后三个文件为按需产出：仅当 Stage 6 实际调用了对应 tool-* skill 时才生成。

最终回复必须说明：实际完成范围、启动命令、验证命令、通过情况、未完成项和下一阻塞，不得仅说“系统已生成”。

## 可选：产出 workflow.yaml 交 workflow-runtime 驱动执行

本 skill 的编排阶段（Stage 1-6）可由 workflow-runtime skill 编译为可执行 workflow.yaml。编译命令：
python ../workflow-runtime/scripts/compile_workflow.py compile-from-master --master SKILL.md --section "编排阶段" --output workflow.yaml

产出 workflow.yaml（可选产物）。详见 ../workflow-runtime/SKILL.md。

