---
name: "package-and-deploy-system"
description: "Prepares a verified application for reproducible local and production deployment with containers, environment contracts, CI/CD, migrations, health checks, observability, backup, rollback, and release documentation."
---

# Package and Deploy System — 打包、部署与交付

本 Skill 将已通过测试的系统整理为可重复构建和可运维的交付物。它不会写入真实生产凭据，也不会在没有部署权限时声称已上线。


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


## 发布前置门禁

- 读取 `./output/build/release-blockers.json` 和测试报告。
- 存在未豁免的阻塞项时，不标记生产就绪；仍可完成部署文件和演练文档。
- 检查许可证、构建产物、数据库迁移、静态资源和运行时版本。

## 实施内容

### 1. 可重复构建

- 固定运行时和包管理器版本，维护锁文件。
- 提供本地开发、测试和生产构建命令。
- 容器采用多阶段构建、非 root 用户、最小运行镜像和健康检查。
- `.dockerignore` / `.gitignore` 排除密钥、缓存和无关产物。

### 2. 环境契约

- 创建或更新 `.env.example`，记录变量用途、是否必填和安全要求。
- 区分开发、测试、预发布、生产配置。
- 秘密通过部署平台或 Secret Manager 注入，不写进镜像和仓库。
- 验证启动时缺失关键变量会快速失败并给出安全错误。

### 3. 数据库发布

- 明确迁移执行者、执行顺序、超时和失败策略。
- 提供备份、恢复和破坏性迁移审批步骤。
- 应用与 Schema 变更需要兼容滚动发布或明确停机窗口。
- **调用 `tool-db-ops` skill 执行迁移**：生产环境迁移通过 `tool-db-ops migrate --migration-dir <从 architecture.json 的 commands.migrationDir 或项目 migrations/ 解析> --confirm` 执行（生产环境只读规则自动生效，写操作需 `--confirm`）；迁移失败时调用 `tool-db-ops rollback --migration-dir <同上> --target <回滚版本> --confirm` 回滚；验证阶段可用 `tool-db-ops query --sql <验证 SQL> --params <JSON 数组>` 只读查询验证数据正确性。产出 `db-ops-report.json` 纳入交付证据。

### 4. CI/CD

按现有平台生成流水线：

- 安装依赖、lint、类型检查、测试和构建。
- 依赖或镜像安全扫描（平台可用时）。
- 产物版本和镜像标签。
- 部署前审批、迁移、部署后健康检查和回滚。

不同时生成多套互相冲突的 CI 平台配置。

**调用 `tool-ci-ops` skill**：生成 CI 配置后，通过 `tool-ci-ops trigger --platform <从 .github/workflows 等 CI 配置识别> --repo <从 Git remote 或 architecture.json modules[].repo 解析> --branch <当前分支> --confirm` 触发构建（需用户确认，属变更类操作）；通过 `tool-ci-ops status --platform <同上> --repo <同上> [--run-id <runId>]` 轮询构建状态；构建完成后通过 `tool-ci-ops report --platform <同上> --repo <同上> --run-id <runId>` 读取测试结果。若 `status` 返回 `degraded` 或 `failed`，不硬性中断，提示用户手动介入。产出 `ci-ops-report.json` 纳入交付证据。

### 5. 运维能力

- `/health`、`/ready` 或等价探针。
- 结构化日志、请求关联 ID、错误监控和关键业务指标。
- 数据备份、保留期、恢复演练和灾难恢复目标。
- 回滚版本、数据库兼容和应急联系人占位。
- **调用 `tool-monitor-ops` skill 验证监控接入**：部署后通过 `tool-monitor-ops logs --service <从 architecture.json modules[].name 取已部署 P0 模块> [--keyword <关键词>] [--limit 100] [--time-range 1h]` 查询服务日志确认启动正常；通过 `tool-monitor-ops metrics --service <同上> --metric cpu [--time-range 1h]` 查询 CPU/内存/QPS/错误率指标验证监控埋点生效；通过 `tool-monitor-ops trace --service <同上> [--trace-id <id>] [--limit 10]` 查询链路确认分布式追踪接入。若平台不可用降级为提示手动验证，不阻塞部署流程。产出 `monitor-ops-report.json` 纳入运维验证证据。

### 6. 交付文档

必须提供：

- 本地启动说明。
- 环境变量说明。
- 部署步骤。
- 数据迁移步骤。
- 验证与冒烟步骤。
- 回滚与恢复步骤。
- 已知限制和未完成项。

## 输出

基础设施文件写入当前项目既有 `infra/`、`deploy/`、`.github/` 等目录，并生成：

```text
output/build/
├── release-manifest.json
├── deployment-report.md
├── operations-runbook.md
├── handoff-checklist.md
├── db-ops-report.json          # tool-db-ops 产出（若执行了数据库迁移）
├── ci-ops-report.json          # tool-ci-ops 产出（若触发了 CI）
└── monitor-ops-report.json     # tool-monitor-ops 产出（若执行了监控验证）
```

后三个文件为按需产出：仅当本 skill 实际调用了对应 tool-* skill 时才生成，未调用时缺失不视为缺陷。

若未实际连接部署环境，报告状态必须是“部署文件已准备 / 未实际部署”，不得写“部署成功”。
