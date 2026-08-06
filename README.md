# AI Agent Skills 技能集合

> 一套面向 AI 编码助手的 skill 集合，覆盖 **AI 游戏生成、产品需求与系统交付、前端原型、文档/标书生成、短剧策划** 等场景。每个 skill 目录内含 `SKILL.md` 作为技能定义；`_shared/` 为公共引用与校验脚本，本身不是独立 skill。

---

## 一、技能总览（按领域分组）

### 1. AI 游戏生成流水线（game-*）
由一句话需求端到端生成可运行游戏工程，纯文本产物、零编辑器依赖。
`game-forge-master`(调度) → `game-blueprint` → `game-spec` → `game-art-spec` → (`game-asset-forge` ∥ `game-code-forge`) → `game-integrate` → `game-polish`(可选)
详见 [第三节](#三ai-游戏生成流水线详情)。

### 2. 产品交付流水线（product-pipeline / system-prd / implement-* / generate-*）
由需求生成系统 PRD、工程实施蓝图、前后端与数据层实现、集成测试到部署交付的完整软件交付链路；另含前端原型与演示门户生成。
`product-pipeline-master`(调度) → `generate-system-prd` → `plan-system-implementation` → (`implement-data-layer` / `implement-backend` / `implement-frontend`) → `integrate-system` → `test-and-harden-system` → `package-and-deploy-system`
旁线：`generate-prototype` → `generate-html-pages`(→ `generate-html-pc-admin` / `generate-html-mobile`) → `generate-portal`；质量门禁 `prd-quality-checker`。
详见 [第四节](#四产品交付流水线详情)。

### 3. 文档与标书（doc / bid）
- `bid-functional-solution`：将 PRD/需求/截图/原型转为投标用「标书功能建设方案」Word 文档。
- `ruanzhu-doc-generator`：由产品截图生成中文软著产品说明书 DOCX（区分 PC 后台与移动端）。
- `screenshot-operation-manual`：由截图/录屏生成 PC 后台与移动端操作手册（DOCX/PDF/MD/HTML）。

### 4. 短剧策划（ai-short-drama-*）
- `ai-short-drama-topic-planner`：AI 短剧高概念选题策划，生成/筛选/评估/发散差异化选题并叠加趋势雷达。
- `ai-short-drama-project-development`：选题确认后的项目开发总监，将选题转化为可拍摄的项目开发方案。

### 5. 其他 / 垂直
- `frontend-design`：为新建/重构 UI 提供独特、有意图的视觉设计指导（配色、排版、布局、签名元素）。
- `brainstorm-product-feature`：编写 PRD 前的产品功能脑暴与构想评估（第零阶段），不写 PRD。
- `build-working-system`：可运行系统总编排器，将 PRD/页面规格/原型转为可运行、已测试、可部署系统。
- `rd-init`：由初步需求从 GitLab 拉取 AI 产研模板并初始化新项目。
- `pet-health-product-simulator`：模拟/测试中文宠物主人健康分诊对话机器人产品交互（非兽医诊断）。

### 6. AI Agent 体系层（2026-08-06 升级）
- **Tool 层**：`tool-git-ops` / `tool-ci-ops` / `tool-deploy-ops` / `tool-db-ops` / `tool-monitor-ops`——封装 Git/CI/部署/DB/监控操作,默认只读优先,变更类需用户确认。
- **工程 skill**：`code-review` / `debug-fix` / `refactor`——补齐研发链路的审查/调试/重构能力。
- **安全与评测**：`guardrail`(前置拦截) / `diff-reviewer`(后置审查) / `skill-auditor`(已扩展为 5 模式 5 维度,含执行后评测)。
- **Memory 层**：`project-knowledge-base`(团队规范/ADR/事故) / `failure-casebook`(失败案例自动记录,保留 90 天)。
- **接入方式**：编排总纲(product-pipeline-master / game-forge-master)末尾的可选 Tool 确认点会按需调用 Tool 层 + guardrail 前置检查;各高频 skill 质量检查清单末尾含“产物自评”项(可选调 skill-auditor 执行后评测)。详细计划见 `.trae/documents/agent-system-upgrade-plan.md`。
- **Phase 2 运行时层**（2026-08-06 升级）：`skill-runtime`(runtime.yaml 契约) / `task-planner`(任务规划) / `replanner`(重规划) / `workflow-runtime`(工作流执行引擎)——把编排总纲的执行顺序升级为可执行 workflow.yaml，支持暂停/恢复/跳过/回退/并行调度。详细计划见 `.trae/documents/agent-system-upgrade-plan.md` §十四。
- **Phase 3 数据与协作层**（2026-08-06 升级）：`codebase-rag`(Context 持久化索引) / `skill-usage-tracker`(Data 调用统计) / `prompt-registry`(Model prompt 注册) / `agent-orchestrator`(多 Agent 协同协议)——补齐 Context/Data/Model/协同四大能力,从"自主运行"升级为"数据驱动+智能协作"。详细计划见 `.trae/documents/agent-system-upgrade-plan.md` §十五。

---

## 二、完整技能清单

| 技能目录 | 职责(一句话) | 输入 | 输出 |
|---|---|---|---|
| ai-short-drama-project-development | 短剧选题确认后的项目开发总监，将选题转化为可拍摄、可进入剧本创作的项目开发方案 | 已确认短剧选题/高概念/故事梗概/人物设定/世界规则 | 项目理解、选题复核、故事发动机、人物关系、整剧阶段大纲、情绪曲线、分集大纲、风险诊断、评分等文本 |
| ai-short-drama-topic-planner | AI 短剧高概念选题策划师，生成/筛选/评估/发散差异化选题并叠加趋势雷达 | 目标平台/市场/用户/题材偏好/选题模式/数量/多样性/趋势雷达配置 | 创意策略、趋势雷达、候选选题(含评分)、变量分布、推荐结论、结构化 JSON |
| bid-functional-solution | 将 PRD/需求/截图/原型转化为投标用「标书功能建设方案」Word 文档 | PRD/需规/Word/PDF/截图文件夹/原型图/已有 DOCX | `.docx` 标书功能建设方案(图片/功能说明/功能描述三段式) |
| brainstorm-product-feature | 编写 PRD 前的产品功能脑暴与构想评估（第零阶段），不写 PRD | 功能名称/草案概念/开发原因/用户流程/目标用户/约束/参考资料 | 功能构想评估摘要(定义、场景、价值、最小闭环、方案对比、假设、风险、下一步) |
| build-working-system | 可运行系统总编排器，将 PRD/页面规格/原型转为可运行、已测试、可部署系统 | 现有 PRD、页面规格、原型、部分代码、技术栈 | 实施计划、任务板、追溯矩阵、各层实现报告、集成/测试/发布清单(`output/build/`) |
| frontend-design | 为新建/重构 UI 提供独特、有意图的视觉设计指导 | 设计 brief / 产品主题、受众、页面单一任务 | 设计计划(Token 系统:色板/字体/布局/签名元素)与最终前端代码 |
| game-art-spec | AI 游戏流水线阶段3：由 PRD+技术设计产出美术规范与机读资源清单 | `docs/PRD.md`、`docs/TECH_DESIGN.md` | `docs/ART_SPEC.md`、`docs/ASSET_MANIFEST.json`、`docs/AUDIO_SPEC.md` |
| game-asset-forge | AI 游戏流水线阶段4a：消费资源清单生成图片/图集打包/音频占位 | `docs/ASSET_MANIFEST.json`、`docs/ART_SPEC.md` | `assets/`(role/ui/bg/atlases/audio)、`docs/ASSET_ISSUES.md` |
| game-blueprint | AI 游戏流水线阶段1：由一句话需求生成一页纸游戏蓝图 | 用户一句话需求(可选参考游戏/截图/素材) | `docs/GAME_BLUEPRINT.md` |
| game-code-forge | AI 游戏流水线阶段4b：消费 PRD+设计+清单生成完整可运行工程代码 | `docs/GAME_BLUEPRINT.md`、`docs/PRD.md`、`docs/TECH_DESIGN.md`、`docs/ASSET_MANIFEST.json` | `src/**/*.ts`、`index.html`、`package.json`、`tsconfig.json`、`vite.config.ts`、`README.md` |
| game-forge-master | AI 游戏生成总纲调度中枢(引擎选择/阶段裁剪/串联下游)，本身不产出文件 | 用户一句话游戏需求 | 调度下游各阶段产物(固定路径)，本 skill 不直接产出业务文件 |
| game-integrate | AI 游戏流水线阶段5：集成构建与浏览器自测，产出可运行构建与验收报告 | `assets/`、`src/`、`index.html`、`docs/ASSET_MANIFEST.json` | `dist/`、`docs/BUILD_REPORT.md`(含数值平衡实测) |
| game-polish | AI 游戏流水线阶段6(可选)：在可运行游戏上叠加视觉/手感/反馈效果打磨 | `docs/POLISH_REQUEST.md`、可运行工程、`GameConfig.ts`(只读) | `src/effects/` 增量效果代码、`docs/POLISH_REPORT.md` |
| game-spec | AI 游戏流水线阶段2：由蓝图生成详细 PRD 与技术设计 | `docs/GAME_BLUEPRINT.md` | `docs/PRD.md`、`docs/TECH_DESIGN.md` |
| generate-html-mobile | 任务型移动端静态 HTML 原型页面生成器(generate-html-pages 子 skill) | 系统 PRD、页面原型文档、UI 规范、上游 JSON 工件 | `output/site/mobile/`(common.css、navbar.js、PXX-*.html) |
| generate-html-pages | 多端静态原型生成路由器，判端并调度 PC/移动端子 skill，汇总构建报告 | 系统 PRD、页面原型文档、UI 规范、上游 JSON 工件 | `output/site/pc/`、`output/site/mobile/`、`output/site/build-report.json` |
| generate-html-pc-admin | PC 管理后台静态 HTML 原型页面生成器(generate-html-pages 子 skill) | 系统 PRD、页面原型文档、UI 规范、上游 JSON 工件 | `output/site/pc/`(common.css、sidebar.js、PXX-*.html) |
| generate-portal | 原型演示与标注总控台生成器(三栏布局+iframe 预览+PRD 标注) | 产品设计方案.md、页面原型文档.md、annotations.json、build-report.json、已生成 HTML | `output/site/index.html`(独立门户，独占) |
| generate-prototype | 由系统 PRD 生成终端感知的标准化页面原型文档(UI/UX 交互规格) | 系统产品设计文档(PRD) | `{系统名称}-页面原型文档.md` + 可选 `output/spec/annotations.json` 等 JSON |
| generate-system-prd | 由需求生成标准化系统产品设计文档(13章+附录，多端适配) | 产品名称/目标/端类型/范围/目标用户/核心场景等(可来自脑暴结论) | `{产品名称}-产品设计方案-V{版本号}.md` + 可选 `output/spec/*.json` |
| implement-backend | 按垂直切片实现生产级后端 API/服务/校验/权限/测试 | 架构文件、business-rules.json、permissions.json、data-model.json、已实现数据层 | 后端源码、API 契约、测试、backend-implementation-report.md、更新追溯表 |
| implement-data-layer | 实现可迁移/可验证/可回滚的数据层(Schema/迁移/Repository) | architecture.json、实施计划、data-model.json、business-rules.json、现有 Schema/迁移 | 数据层代码、database-implementation-report.md、schema-snapshot.json、更新追溯表 |
| implement-frontend | 将页面规格与静态原型实现为生产级前端(集成真实 API/类型/权限/测试) | pages.json、annotations.json、design-tokens.json、原型 HTML、架构与后端契约 | 前端源码、主题配置、API 客户端、测试、frontend-implementation-report.md、更新追溯表 |
| integrate-system | 将前后端/数据层/认证/权限/外部服务联调成可运行端到端系统 | API 契约、各已实现层、环境配置 | integration-report.md、environment-matrix.md、contract-drift.json、更新追溯表 |
| package-and-deploy-system | 将已测系统整理为可重复构建/可运维的交付物(容器/CI/回滚文档) | 发布门禁文件、测试报告、构建产物 | 基础设施文件(infra/deploy/.github)、release-manifest.json、deployment-report.md、operations-runbook.md、handoff-checklist.md |
| pet-health-product-simulator | 模拟/测试中文宠物主人健康分诊对话机器人产品交互(非兽医诊断) | 交互模式(模拟/脚本/QA/场景/交接)+ 参考契约/协议/风险模型 | 对话流程脚本、QA 报告、场景用例、状态机/API/UI 需求(实现交接) |
| plan-system-implementation | 由 PRD/原型/仓库生成可执行的工程实施蓝图(架构/切片/任务板) | output/spec/*.json、PRD、原型、当前代码仓库 | implementation-plan.md、architecture.json、task-board.json、traceability.json、risk-register.md、ADR 决策记录 |
| prd-quality-checker | 在下游工作前基于证据审核 PRD 质量，输出门禁报告(Audit/Improve) | 主 PRD/需求基线、关联清单、产品配置、可选上下文 | Markdown 门禁报告(READY/CONDITIONAL/NOT_READY)+ 可选 JSON + AI 开发准备度附录 |
| product-pipeline-master | 产品工作台总编排调度中枢(端判定/阶段裁剪/串联下游)，本身不产出文件 | 用户需求 | 调度下游 6 主线 + 3 旁线 skill 产物(固定路径)，本 skill 不直接产出业务文件 |
| rd-init | 由初步需求从 GitLab 拉取 AI 产研模板并初始化新项目 | "初步需求如下："后的需求文本 | .rd-init-brief.md、project.yaml、workflow_state.yaml、asset_map.json、项目说明(不生成 PRD/代码) |
| ruanzhu-doc-generator | 由产品截图生成中文软著产品说明书 DOCX(区分 PC 后台与移动端) | 截图文件夹 + 可选 PRD/README/产品事实 | `(管理后台)产品说明书.docx`/`(移动端)产品说明书.docx`(混合时两份) |
| screenshot-operation-manual | 由截图/录屏生成 PC 后台与移动端操作手册(DOCX/PDF/MD/HTML) | 截图/录屏/截图文件夹、平台分类 | manual_spec.json + 操作手册.docx(封面、目录、模块说明、步骤、FAQ) |
| skill-runtime | Agent Runtime 层(定义 runtime.yaml 契约:timeout/retry/inputs/outputs/degrade) | skill 目录 | runtime-contract-report.json(校验结果) |
| test-and-harden-system | 运行并提升单元/集成/端到端/安全/性能等检查，修复阻塞缺陷并出验收报告 | 已实现系统、PRD、各层报告、测试配置 | acceptance-matrix.json、test-report.md、security-review.md、performance-smoke.md、release-blockers.json |
| code-review | 代码审查(4 维度:正确性/安全性/性能/可维护性,只读不写) | git diff / PR 链接 | code-review-report.md + code-review-report.json |
| debug-fix | 调试修复(定位根因 + 修复,最多重试 3 轮) | 错误日志 + 堆栈 + 复现步骤 | debug-report.md(根因 + 修复方案 + diff) |
| diff-reviewer | 变更审查(后置审查 diff 的风险变更,只读不写) | 变更前后的路径或 git diff | diff-review-report.md(风险变更清单 + 建议) |
| failure-casebook | 失败案例库(自动记录失败码 + 修复方法,保留 90 天) | skill 名 + 失败码 + 原因 + 修复方法 | failure-casebook.json(索引) + 案例文件 |
| guardrail | 安全护栏(前置拦截:敏感路径保护 + 操作分级) | 目标路径 + 操作类型 | guardrail-report.json(检查结果 + 风险级别) |
| project-knowledge-base | 项目知识库(团队规范/ADR/历史事故/代码规范) | 知识分类 + 查询关键词 | knowledge-base.json(索引) + 各知识文件 |
| refactor | 代码重构(不改功能,小步保测试) | 目标文件/模块 + 重构目标 | 重构方案 + 重构 diff |
| replanner | 重规划器(失败/变更时动态调整 task-tree,最多 3 轮) | 原 task-tree.json + 失败信息 | task-tree.v2.json + replan-report.md |
| task-planner | 通用任务规划器(拆解为子任务树+依赖+优先级) | 需求描述 + 可选上下文 | task-tree.json + task-plan.md |
| tool-ci-ops | CI/CD 工具层(触发/查询/报告,触发需确认) | 仓库 + CI 平台(github-actions/gitlab-ci/jenkins) | ci-ops-report.json |
| tool-db-ops | 数据库工具层(migrate/query/rollback,生产环境只读) | 迁移文件 + 数据库连接配置 | db-ops-report.json |
| tool-deploy-ops | 部署工具层(部署/回滚/健康检查,支持 GitHub Pages/Vercel/Netlify/CloudBase/COS) | 产物路径 + 目标平台 | deploy-ops-report.json(部署 URL + 版本号 + 健康检查) |
| tool-git-ops | Git 工具层(commit/branch/push/diff/log,默认不 push) | 产物路径列表 + 可选 commit message | git-ops-report.json(文件清单 + commit hash + branch) |
| tool-monitor-ops | 监控工具层(logs/metrics/trace 查询,纯只读) | 服务名 + 时间范围 | monitor-ops-report.json |
| workflow-runtime | 工作流执行引擎(编译执行顺序为可执行 workflow.yaml,支持暂停/恢复/跳过/回退/并行) | 编排总纲 SKILL.md 或 task-tree.json | workflow.yaml + workflow-exec-report.json |
| codebase-rag | Context 层(持久化代码库索引,语义检索,与宿主 SearchCodebase 互补) | 项目路径 + 分块策略 | codebase-index.json + 检索结果 |
| skill-usage-tracker | Data 层(记录 skill 调用数据,统计高频/慢/失败率,纯记录不阻塞) | skill 名 + 耗时 + 状态 | records.jsonl + usage-stats.json + optimization-suggestions.md |
| prompt-registry | Model 层(集中管理 prompt 模板,版本化+变体管理+对比) | skill 名 + prompt 模板 + 版本 | prompt-registry.json + prompts/{skill}/{version}.md |
| agent-orchestrator | 多 Agent 协同(定义通信协议+任务委派+结果汇总) | 任务 + Agent 列表 | orchestration-protocol.md + agent-messages.json |

---

## 三、AI 游戏生成流水线（详情）

通过 8 个 skill 串联成一条流水线，让 AI 基于一句话需求端到端生成可一键运行的游戏工程。所有产物纯文本/二进制资源，**零编辑器依赖**。可选阶段 6 在可玩游戏基础上叠加视觉效果打磨。

### 3.1 Skill 清单

| 序号 | Skill 名 | 职责 | 输入 | 输出 |
|---|---|---|---|---|
| 0 | game-forge-master | 总纲/调度/引擎决策树/失败回退 | 用户一句话需求 | 调度下游 skill |
| 1 | game-blueprint | 游戏蓝图(类型/平台/引擎/范围) | 一句话需求 | `docs/GAME_BLUEPRINT.md` |
| 2 | game-spec | PRD + 技术设计 | 蓝图 | `docs/PRD.md` + `docs/TECH_DESIGN.md` |
| 3 | game-art-spec | 美术规范 + 资源清单 + 音频规范 | PRD + TECH_DESIGN | `docs/ART_SPEC.md` + `docs/ASSET_MANIFEST.json` + `docs/AUDIO_SPEC.md` |
| 4a | game-asset-forge | AI 生图 + 切图 + 音频占位 | ASSET_MANIFEST + ART_SPEC | `assets/**` |
| 4b | game-code-forge | 工程代码(三引擎) | PRD + TECH_DESIGN + ASSET_MANIFEST | `src/**` + 工程配置 |
| 5 | game-integrate | 集成构建联调 + 验收报告 | assets + src | `dist/**` + `docs/BUILD_REPORT.md` |
| 6 | game-polish(可选) | 视觉/手感/反馈效果打磨 | 可运行工程 + POLISH_REQUEST(可选) | `src/effects/**` + `docs/POLISH_REPORT.md` |

### 3.2 流水线总览

```
用户一句话需求
       ↓
[0] game-forge-master(调度)
       ↓ 引擎选择 + 阶段裁剪
[1] game-blueprint       → docs/GAME_BLUEPRINT.md
       ↓
[2] game-spec            → docs/PRD.md + docs/TECH_DESIGN.md
       ↓
[3] game-art-spec        → docs/ART_SPEC.md + docs/ASSET_MANIFEST.json + docs/AUDIO_SPEC.md
       ↓
┌────────────────────┐  ┌────────────────────┐
│ [4a] game-asset-   │  │ [4b] game-code-    │  (可并行)
│      forge         │  │      forge         │
│  assets/**         │  │  src/**            │
└────────────────────┘  └────────────────────┘
       ↓
[5] game-integrate       → dist/** + docs/BUILD_REPORT.md
       ↓
[6] game-polish (可选)   → src/effects/** + docs/POLISH_REPORT.md
```

### 3.3 使用方式

- **完整流程(推荐)**：直接说「用 AI 生成一个游戏：…」或「按流水线生成游戏工程」，总纲 skill 自动调度后续阶段。
- **单阶段调用**：跳过总纲直接调用某阶段 skill（适用于已有部分产物的增量生成）：
  - 「生成游戏蓝图」→ game-blueprint
  - 「生成游戏 PRD」→ game-spec
  - 「生成美术规范」→ game-art-spec
  - 「生成游戏资源」→ game-asset-forge
  - 「生成游戏代码」→ game-code-forge
  - 「集成构建游戏」→ game-integrate
  - 「优化游戏效果/加特效/打磨动画」→ game-polish

### 3.4 关键设计点

1. **ASSET_MANIFEST.json 是中枢契约**：美术 skill 与代码 skill 的唯一桥梁。代码 skill 只读 JSON，不读美术文档；美术 skill 只产出 JSON。两阶段完全解耦。
2. **三引擎支持**：默认 Phaser 3，总纲根据游戏类型自动选择：
   - Phaser 3：2D 跑酷/平台/塔防/卡牌/消除(默认)
   - Pixi.js：大量粒子/特效/自定义渲染
   - 纯 Canvas：极简游戏(2048/几何)
3. **失败不阻塞**：所有失败都允许继续，降级方案：
   - 生图失败 → 占位图(纯色 + 文字标识)
   - 切图失败 → 散图降级
   - 音频失败 → 静音占位
   - typecheck 失败 → 降级 strict:false
   - 失败项汇总到 `docs/ASSET_ISSUES.md` 和 `docs/BUILD_REPORT.md`，供人工后补。
4. **固定路径契约**：所有 skill 必须按固定路径读写，不允许自定义。详见 game-forge-master 的「产物路径总表」。

### 3.5 产物路径总表

```
{项目根}/
├── docs/
│   ├── GAME_BLUEPRINT.md       # [1] 产出
│   ├── PRD.md                  # [2] 产出
│   ├── TECH_DESIGN.md          # [2] 产出
│   ├── ART_SPEC.md             # [3] 产出
│   ├── ASSET_MANIFEST.json     # [3] 产出(中枢)
│   ├── AUDIO_SPEC.md           # [3] 产出
│   ├── ASSET_ISSUES.md         # [4a] 失败时产出
│   ├── BUILD_REPORT.md         # [5] 产出
│   ├── POLISH_REQUEST.md       # [6] 用户填写(可选)
│   ├── POLISH_REPORT.md        # [6] 产出(可选)
│   └── screenshots/            # [5] 浏览器自测截图
├── assets/
│   ├── role/{role}/{state}_{frame:03}.png   # [4a]
│   ├── ui/{page}/{element}.png              # [4a]
│   ├── bg/{scene}_{variant}.png             # [4a]
│   ├── atlases/{atlas_id}.png + .json       # [4a]
│   └── audio/*.{wav,mp3}                     # [4a]
├── src/                        # [4b]
│   ├── main.ts
│   ├── config/
│   ├── scenes/
│   ├── objects/
│   ├── managers/
│   ├── ui/
│   ├── effects/                # [6] game-polish 增量产出(可选)
│   ├── net/  (可选)
│   ├── utils/
│   └── types/
├── dist/                       # [5] 构建产物
├── index.html                  # [4b]
├── package.json                # [4b]
├── tsconfig.json               # [4b]
├── vite.config.ts              # [4b]
└── README.md                   # [4b]
```

### 3.6 典型场景示例

**场景 1：新春赛马跑酷游戏**
```
用户:用 AI 生成一个新春赛马跑酷小游戏,带 6 套皮肤和抽奖
[0] 总纲:复杂度 ★★★★,引擎 Phaser 3,音频走静音占位
[1] 蓝图:跑酷+皮肤+抽奖,Web H5,Phaser 3
[2] PRD:跳跃/障碍/计分/复活/抽奖状态机;TECH_DESIGN:6 场景+15 模块
[3] 美术:6 皮肤×16 帧=96 图 + UI + 背景,共 ~150 张;音频 6 个静音占位
[4a] 资源:AI 生图(首帧 reference)+ TexturePacker 打包 6 个图集
[4b] 代码:BootScene/HomeScene/GameScene + Horse/Obstacle/Popup
[5] 集成:npm install → typecheck → 浏览器自测 → build → dist/
```

**场景 2：极简消除游戏**
```
用户:做个三消游戏
[0] 总纲:复杂度 ★★,引擎 Phaser 3,跳过 audio
[1] 蓝图:网格消除,无网络,无皮肤
[2] PRD:8x8 网格,3 消除规则;TECH_DESIGN:单场景
[3] 美术:6 种宝石图 + 背景 + UI,共 ~20 张
[4a] 资源:AI 生图(快速)
[4b] 代码:BootScene + GameScene
[5] 集成:构建完成
```

### 3.7 约束与限制

1. **不支持的类型**：3D 游戏；强物理引擎游戏(如真实刚体碰撞)；MMORPG 等大型多人游戏。
2. **AI 生图限制**：逐帧动画跨帧风格一致性是主要难点；复杂场景(多角色同框 + 复杂光影)成功率低；单游戏美术资源上限 200 张图。
3. **AI 音频限制**：默认全部静音占位；BGM 不建议 AI 生成。
4. **网络与签名**：网络层需用户提供接口契约；复杂签名需用户给参考实现；私有 SDK 需用户提供 .d.ts 类型定义。

---

## 四、产品交付流水线（详情）

由 `product-pipeline-master` 总编排，覆盖「需求 → PRD → 工程实施 → 实现 → 集成 → 测试 → 部署」的完整软件交付链路，并提供前端原型与演示门户生成、PRD 质量门禁等旁线能力。

### 4.1 主链路

```
用户需求
   ↓
[master] product-pipeline-master(调度)
   ↓
generate-system-prd        → {产品}-产品设计方案-Vx.md + output/spec/*.json
   ↓
plan-system-implementation → implementation-plan.md / architecture.json / task-board.json / traceability.json
   ↓  (三实现可并行)
┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐
│ implement-data-  │  │ implement-backend│  │ implement-front- │
│   layer          │  │                  │  │   end            │
└──────────────────┘  └──────────────────┘  └──────────────────┘
   ↓
integrate-system          → integration-report.md / contract-drift.json
   ↓
test-and-harden-system    → test-report.md / security-review.md / acceptance-matrix.json
   ↓
package-and-deploy-system → release-manifest.json / deployment-report.md / operations-runbook.md
```

### 4.2 旁线（前端原型与演示）

```
generate-prototype        → {系统}-页面原型文档.md + output/spec/annotations.json
   ↓
generate-html-pages(路由)
   ├─ generate-html-pc-admin   → output/site/pc/
   └─ generate-html-mobile     → output/site/mobile/
   ↓
generate-portal            → output/site/index.html (演示门户,独占)
```

### 4.3 质量门禁

- `prd-quality-checker`：在下游工作前基于证据审核 PRD 质量，输出 `READY / CONDITIONAL / NOT_READY` 门禁报告。
- `frontend-design`：在生成/重构前端前提供视觉设计 Token 系统（色板/字体/布局/签名元素）。
- `brainstorm-product-feature`：PRD 前的功能脑暴与构想评估（第零阶段）。
- `build-working-system`：可运行系统总编排器，将 PRD/页面规格/原型一次性转为可运行、已测试、可部署系统（与 product-pipeline-master 互补的另一种编排视角）。

---

## 五、各 Skill 详细规范

详见各 skill 目录下的 `SKILL.md`：

**AI 游戏生成流水线**
- [game-forge-master](./game-forge-master/SKILL.md)
- [game-blueprint](./game-blueprint/SKILL.md)
- [game-spec](./game-spec/SKILL.md)
- [game-art-spec](./game-art-spec/SKILL.md)
- [game-asset-forge](./game-asset-forge/SKILL.md)
- [game-code-forge](./game-code-forge/SKILL.md)
- [game-integrate](./game-integrate/SKILL.md)
- [game-polish](./game-polish/SKILL.md)

**产品交付流水线**
- [product-pipeline-master](./product-pipeline-master/SKILL.md)
- [generate-system-prd](./generate-system-prd/SKILL.md)
- [plan-system-implementation](./plan-system-implementation/SKILL.md)
- [implement-data-layer](./implement-data-layer/SKILL.md)
- [implement-backend](./implement-backend/SKILL.md)
- [implement-frontend](./implement-frontend/SKILL.md)
- [integrate-system](./integrate-system/SKILL.md)
- [test-and-harden-system](./test-and-harden-system/SKILL.md)
- [package-and-deploy-system](./package-and-deploy-system/SKILL.md)
- [generate-prototype](./generate-prototype/SKILL.md)
- [generate-html-pages](./generate-html-pages/SKILL.md)
- [generate-html-pc-admin](./generate-html-pc-admin/SKILL.md)
- [generate-html-mobile](./generate-html-mobile/SKILL.md)
- [generate-portal](./generate-portal/SKILL.md)
- [prd-quality-checker](./prd-quality-checker/SKILL.md)
- [frontend-design](./frontend-design/SKILL.md)
- [brainstorm-product-feature](./brainstorm-product-feature/SKILL.md)
- [build-working-system](./build-working-system/SKILL.md)
- [rd-init](./rd-init/SKILL.md)

**文档与标书**
- [bid-functional-solution](./bid-functional-solution/SKILL.md)
- [ruanzhu-doc-generator](./ruanzhu-doc-generator/SKILL.md)
- [screenshot-operation-manual](./screenshot-operation-manual/SKILL.md)

**短剧策划**
- [ai-short-drama-topic-planner](./ai-short-drama-topic-planner/SKILL.md)
- [ai-short-drama-project-development](./ai-short-drama-project-development/SKILL.md)

**其他 / 垂直**
- [pet-health-product-simulator](./pet-health-product-simulator/SKILL.md)

**AI Agent 体系层**（2026-08-06 升级）
- [tool-git-ops](./tool-git-ops/SKILL.md) - [tool-ci-ops](./tool-ci-ops/SKILL.md) - [tool-deploy-ops](./tool-deploy-ops/SKILL.md) - [tool-db-ops](./tool-db-ops/SKILL.md) - [tool-monitor-ops](./tool-monitor-ops/SKILL.md)
- [code-review](./code-review/SKILL.md) - [debug-fix](./debug-fix/SKILL.md) - [refactor](./refactor/SKILL.md)
- [guardrail](./guardrail/SKILL.md) - [diff-reviewer](./diff-reviewer/SKILL.md) - [skill-auditor](./skill-auditor/SKILL.md)（已扩展为 5 模式 5 维度）
- [project-knowledge-base](./project-knowledge-base/SKILL.md) - [failure-casebook](./failure-casebook/SKILL.md)
- [skill-runtime](./skill-runtime/SKILL.md) - [task-planner](./task-planner/SKILL.md) - [replanner](./replanner/SKILL.md) - [workflow-runtime](./workflow-runtime/SKILL.md)（Phase 2 运行时层）
- [codebase-rag](./codebase-rag/SKILL.md) - [skill-usage-tracker](./skill-usage-tracker/SKILL.md) - [prompt-registry](./prompt-registry/SKILL.md) - [agent-orchestrator](./agent-orchestrator/SKILL.md)（Phase 3 数据与协作层）

**公共引用**
- [_shared/](./_shared/)（公共 schema、UI 设计标准、校验脚本，非独立 skill）
