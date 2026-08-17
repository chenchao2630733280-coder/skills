# AI Agent Skills 工作台

一套面向 AI 编码助手的 skill 集合，覆盖**产品交付、AI 游戏生成、AI 短剧策划、AI Agent 体系层**四大领域，外加文档交付物生成能力。本文件是工作台的总索引。

> **首次使用工作台**：先运行 `rd-init` 扫描全部 skill 目录，生成 `.workbench-index.json` 索引和完整性报告，让 AI 一目了然地掌握工作台全貌。新增或删除 skill 后建议重跑。

## 流水线总览

### 一、产品交付流水线

```text
【总编排】
product-pipeline-master      调度中枢：端类型判定 + 阶段裁剪 + 串联下游 + 失败回退
        ↓
【主线：产品交付流水线】
brainstorm-product-feature   第0阶段（可选）：脑暴与构想评估
        ↓ 构想、假设和范围已确认
generate-system-prd          第1阶段：系统产品设计文档（PRD）
        ↓
generate-prototype           第2阶段：页面原型文档
        ↓
generate-html-pages          第3/4阶段：HTML原型路由器（判断端类型→调度子skill→汇总build-report）
  ├─ generate-html-pc-admin       PC管理后台HTML原型（深色侧栏+工作区页签）
  └─ generate-html-mobile         移动端HTML原型（任务型：综合入口/详情/交易等）
        ↓
generate-portal              第5阶段：三栏演示门户（output/site/index.html，独占）
        ↓ 原型评审通过，进入生产阶段（交接给 build-working-system）
plan-system-implementation   实施规划（可选）：可执行的工程实施蓝图（首次产出）
        ↓ 控制权交接
build-working-system         生产阶段编排器：恢复/更新蓝图 → 骨架 → implement-* → 集成 → 测试 → 部署

【旁线：文档交付物】（可并行，不依赖主线顺序）
bid-functional-solution      标书功能建设方案（Word）
ruanzhu-doc-generator        软著产品说明书（DOCX，PC/移动端分离）
screenshot-operation-manual  截图操作手册（DOCX/PDF/Markdown）
```

**总编排入口**：`product-pipeline-master` 是调度中枢，接收用户需求后判定端类型、裁剪阶段、串联下游 skill。用户也可直接调用单个 skill，但端到端生成时建议先经过总纲。

主线 Skill 的顺序是推荐顺序，不是强制依赖；PRD 可从需求、脑暴、原型、HTML、代码或运行系统证据生成或逆向重建（详见 `generate-system-prd/references/prd-stage-boundary.md`）。

### 二、AI 游戏生成流水线

```text
【总编排】
game-forge-master            调度中枢：引擎选择（Phaser 3 / Pixi.js / 纯Canvas / Godot 4 / Unity）+ 阶段裁剪 + 失败回退
        ↓
game-topic-brainstorm        阶段0（可选）：游戏选题脑暴
        ↓
game-blueprint               阶段1：一页纸游戏蓝图（类型/平台/引擎/玩法/范围）
        ↓
game-spec                    阶段2：详细 PRD + 技术设计
        ↓
game-art-spec                阶段3：美术规范 + ASSET_MANIFEST.json + 音频规范
        ↓
┌────────────────────┐  ┌────────────────────┐
│ game-asset-forge   │  │ game-code-forge    │  (可并行)
│ 阶段4a：AI 生图    │  │ 阶段4b：工程代码   │
├────────────────────┘  └────────────────────┘
        ↓
game-integrate               阶段5：集成构建 + 浏览器自测 + 验收报告
        ↓
game-polish                  阶段6（可选）：视觉/手感/反馈效果打磨
```

**质量门**：`game-quality-gate` 在 4 个关键节点（规格后/美术后/资源代码后/集成前）介入做契约校验与实跑预检，不通过则阻断流水线。

### 三、AI 短剧策划

```text
ai-short-drama-topic-planner          短剧选题生成与优化（含趋势雷达）
        ↓ 选题确认
ai-short-drama-project-development    短剧项目开发（13 步流程：选题复核→故事发动机→核心规则→人物关系→分集大纲→风险诊断）
```

两个短剧 skill 均已接入 `runtime.yaml`（topic-planner timeout=600s / project-development timeout=900s）并含"失败回退与降级"章节（L1-L3 分层回退）。

### 四、AI 短剧制作流水线（short-drama-*）

```text
【总编排】
short-drama-forge-master      调度中枢：类型判定（全 AI 生成/图文短剧/数字人/实拍辅助）+ 工具链决策 + 阶段裁剪 + 失败回退
        ↓
short-drama-topic-brainstorm  阶段0（可选）：选题脑暴（观看动力/趋势/多样性/评分）
        ↓
short-drama-blueprint         阶段1：一页纸短剧立项蓝图（类型/形式/卖点/工具链/复杂度）
        ↓
short-drama-spec              阶段2：故事规格（发动机/规则/人物/秘密/阶段/情绪曲线）+ 分集大纲
        ↓
short-drama-script            阶段3：竖屏正式剧本（每集一文件，1-3 分钟/集，强卡点）
        ↓
short-drama-storyboard        阶段4：分镜脚本 + 视觉规范（每镜头文生图/图生视频 prompt）
        ↓
┌────────────────────┐  ┌────────────────────┐
│ short-drama-video- │  │ short-drama-audio- │  (可并行)
│   forge            │  │   forge            │
│ 阶段5：manifest+    │  │ 阶段6：配音/BGM/   │
│ 逐镜头 AI 视频      │  │ 字幕              │
└────────────────────┘  └────────────────────┘
        ↓
short-drama-edit              阶段7：剪辑合成成片（ffmpeg 拼接/混音/字幕烧录，内含 Gate 5 成片实跑门）
```

**质量门**：`short-drama-quality-gate` 在 5 个关键节点（立项后/规格后/剧本后/分镜后/生产后）介入做 Gate 0~4 契约校验与实跑预检，FAIL 硬阻断并回原阶段修复；只读业务产物、只写 `docs/GATE_{0..4}_REPORT.md`。

**固定产物契约**：全流水线按 `short-drama-forge-master/SKILL.md` §八 的产物路径总表读写（`docs/` 文档链 → `production/manifest.json` → `shots/` → `audio/`+`subtitles/` → `episodes/EP{XX}.mp4`），每阶段 Gate PASS 后强制人工确认点，不允许自动连续执行。10 个 skill 均已接入 `runtime.yaml`。

## Skill 清单（产品交付流水线）

> 游戏流水线 skill 清单详见 `game-forge-master/SKILL.md`；短剧 skill 清单详见各 skill 的 SKILL.md；Agent 体系层 skill 清单见下文"Agent 体系层"章节。

| Skill | 阶段 | 主要产出 | 默认输出位置 |
|-------|------|---------|-------------|
| `product-pipeline-master` | 总编排 | 调度中枢，不直接产出文件 | - |
| `brainstorm-product-feature` | 0 脑暴 | 功能构想评估摘要 | 对话输出 |
| `generate-system-prd` | 1 PRD | `{产品名称}-{端类型}-产品设计方案-V{版本号}.md`；可选 JSON 工件 | `output/docs/`、`output/spec/` |
| `generate-prototype` | 2 原型 | `{系统名称}-页面原型文档.md`；可选 `annotations.json` 等 | `output/docs/`、`output/spec/` |
| `generate-html-pages` | 3/4 路由 | 端判断 + 调度子skill + 汇总 `build-report.json` | `output/site/` |
| `generate-html-pc-admin` | 3/4 PC | `pc/` 静态页面（深色侧栏+工作区页签） | `output/site/pc/` |
| `generate-html-mobile` | 3/4 移动 | `mobile/` 静态页面（任务型原型） | `output/site/mobile/` |
| `generate-portal` | 5 门户 | `index.html` 三栏演示门户（独占） | `output/site/` |
| `plan-system-implementation` | 实施 | 实施蓝图、架构契约、任务板、追溯表 | `output/build/` |
| `bid-functional-solution` | 旁线 | 标书功能建设方案 `.docx` | 用户指定 |
| `ruanzhu-doc-generator` | 旁线 | 软著说明书 `.docx`（PC/移动端分离） | 用户指定 |
| `screenshot-operation-manual` | 旁线 | 操作手册 `.docx` 等 | 用户指定 |

## Agent 体系层

除流水线 skill 外,工作台新增 AI Agent 体系层 skill(2026-08-06 升级):

### Tool 层（工具调用）

| Skill | 职责 |
|---|---|
| `tool-git-ops` | Git 操作封装(commit/branch/push/diff/log,默认不 push) |
| `tool-ci-ops` | CI/CD 操作(触发/查询/报告,触发需确认) |
| `tool-deploy-ops` | 部署操作(部署/回滚/健康检查,支持 GitHub Pages/Vercel/Netlify/CloudBase/COS) |
| `tool-db-ops` | 数据库操作(migrate/query/rollback,生产环境只读) |
| `tool-monitor-ops` | 监控查询(logs/metrics/trace,纯只读) |

### 工程 skill

| Skill | 职责 |
|---|---|
| `code-review` | 代码审查(4 维度 + 报告,只读不写) |
| `debug-fix` | 调试修复(定位 + 修复,最多重试 3 轮) |
| `refactor` | 代码重构(不改功能,小步保测试) |

### 安全与评测

| Skill | 职责 |
|---|---|
| `guardrail` | 安全护栏(前置拦截,敏感路径保护 + 操作分级) |
| `diff-reviewer` | 变更审查(后置审查 diff 的风险变更,只读不写) |
| `skill-auditor` | 质量审查(5 模式 5 维度,含执行后评测) |

### Memory 层

| Skill | 职责 |
|---|---|
| `project-knowledge-base` | 项目知识库(团队规范/ADR/历史事故/代码规范) |
| `failure-casebook` | 失败案例库(自动记录失败码 + 修复方法,保留 90 天) |

**接入方式**：编排总纲(product-pipeline-master / game-forge-master)末尾的可选 Tool 确认点会按需调用 Tool 层 + guardrail 前置检查。各高频 skill 的质量检查清单末尾含“产物自评”项(可选调用 skill-auditor 执行后评测模式)。

### Phase 2 运行时层（2026-08-06 升级）

| Skill | 职责 |
|---|---|
| `skill-runtime` | Agent Runtime 层(定义 runtime.yaml 契约:timeout/retry/inputs/outputs/degrade) |
| `task-planner` | Planning 层(通用任务规划器,拆解为 task-tree.json) |
| `replanner` | Planning 层(重规划器,失败/变更时动态调整 task-tree) |
| `workflow-runtime` | Workflow 层(工作流执行引擎,编译执行顺序为可执行 workflow.yaml) |

**Phase 2 接入方式**:编排总纲(product-pipeline-master / game-forge-master)的执行顺序可由 workflow-runtime 编译为 workflow.yaml,支持暂停/恢复/跳过/回退/并行调度;runtime.yaml 契约被 skill-auditor 第 6 维度审查;failure-casebook 的 auto-query 子命令供 workflow-runtime 在调用 skill 前注入预防提示。

### Phase 3 数据与协作层（2026-08-06 升级）

| Skill | 职责 |
|---|---|
| `codebase-rag` | Context 层(持久化代码库索引,语义检索,与宿主 SearchCodebase 互补) |
| `skill-usage-tracker` | Data 层(记录 skill 调用数据,统计高频/慢/失败率,纯记录不阻塞) |
| `prompt-registry` | Model 层(集中管理 prompt 模板,版本化+变体管理+对比) |
| `agent-orchestrator` | 多 Agent 协同(定义通信协议+任务委派+结果汇总) |

**Phase 3 接入方式**:workflow-runtime 执行 workflow.yaml 时,每步 skill 调用前后调 skill-usage-tracker record 记录调用数据(分配 call_id 贯穿链路);failure-casebook 记录失败时关联 call_id(related_call_id 字段);codebase-rag 与宿主 SearchCodebase 互补(宿主实时,本 skill 持久化+跨会话);prompt-registry 渐进式接入(先 game-*/implement-* 试点);agent-orchestrator 定义协议,实际多 Agent 运行依赖宿主。详细计划见 `.trae/documents/agent-system-upgrade-plan.md` §十五。

### Phase 4 自适应与执行落地层（2026-08-06 升级）

| Skill | 职责 |
|---|---|
| `adaptive-tuner` | Data 层(基于 skill-usage-tracker 数据自动生成 skill 参数优化建议,产出 runtime-overrides.yaml,需用户确认) |
| `session-snapshot` | Memory 层(会话状态快照与跨会话恢复,save/restore/list/diff/clean) |
| `agent-runtime-exec` | Agent Runtime 执行层(基于 agent-orchestrator 协议实现多 Agent 实际调度执行器,delegate/collect/merge/monitor) |

**Phase 4 扩展的已有 skill**:

| Skill | 扩展内容 |
|---|---|
| `skill-runtime` | runtime.yaml 新增 `external_overrides` 字段,三层覆盖优先级(overrides > 本地 > 默认),引用 adaptive-tuner 产出的 runtime-overrides.yaml |
| `workflow-runtime` | 新增 §十三"自适应优化"章节,执行前读 external_overrides 合并 timeout/retry,形成数据驱动闭环;接入 adaptive-tuner |
| `agent-orchestrator` | 新增 §六.1"执行后端"章节,委托 agent-runtime-exec 实际运行多 Agent;协议定义与执行实现职责分离 |

**Phase 4 接入方式(自适应闭环)**:
```
skill-usage-tracker 记录调用数据(耗时/失败率)
  → adaptive-tuner analyze 分析数据,生成 tuning-suggestions.json
  → adaptive-tuner suggest 产出 runtime-overrides.yaml(需用户确认)
  → workflow-runtime 执行时读取 external_overrides,用优化参数调度
  → 执行结果再次被 skill-usage-tracker 记录 → (循环)
```

覆盖优先级:`external_overrides`(adaptive-tuner 产出) > runtime.yaml 本地字段 > 默认值。失败不阻塞:overrides 文件缺失或解析失败时回退到本地值并标 WARNING。详细计划见 `.trae/documents/agent-system-upgrade-plan.md` §十六。

### 元技能层

| Skill | 职责 |
|---|---|
| `rd-init` | 工作台加载器(扫描 skills 目录全部 skill,生成 `.workbench-index.json` 索引和完整性报告,让 AI 快速掌握工作台全貌) |
| `agent-builder` | Skill 工程化元技能(12 维度架构框架+标准创建流程+7 大设计模式+结构模板,用于新建 Agent 体系层 skill 时指导) |

**元技能层接入方式**:
- **工作台加载**:首次使用工作台时调 `rd-init` 扫描全部 skill,生成机器可读索引和完整性报告(frontmatter 规范/references 路径/runtime.yaml 声明)。
- **新建 Agent skill**:先调 `agent-builder` 确定架构定位和模式选择,再用 `skill-creator` 创建文件骨架。`agent-builder` 提供"怎么设计",`skill-creator` 提供"怎么写"。

## skill 调度归类

工作台的编排总纲(`product-pipeline-master` / `game-forge-master` / `build-working-system`)在调度 skill 时,以下 skill **不在被动调度清单**内,按独立使用或被消费的方式接入:

| Skill | 归类 | 不被动调度的原因 |
|-------|------|-----------------|
| `debug-fix` | 反应式调试工具,独立使用 | 由用户在遇到 Bug 时主动调用,非流水线阶段产物;不参与编排总纲的线性/并行调度链 |
| `prompt-registry` | Model 层基础设施,被消费而非被调度 | 集中管理 prompt 模板,由各 skill 读取引用;本身不产出业务文件,不被编排总纲作为阶段调用 |
| `task-planner` | 通用规划工具,产物被主动读取 | 产出 `task-tree.json`,由 `agent-orchestrator` / `workflow-runtime` 主动读取其上游产物转为执行计划;非被动调度对象,而是规划上游 |
| `diff-reviewer` | 独立深度变更审查工具,guardrail 内置脚本的补充 | guardrail 内置 `diff_review.py` 脚本已覆盖基础变更审查;本 skill 在编排总纲中由人工或编排层按需调用做深度补充审查,不作为流水线阶段被自动调度 |

## Checkpoint 机制

每完成一个 todo 任务后，自动提交本地 git checkpoint：
- commit message 以 "checkpoint(...)" 开头
- 支持回退：`git reset --hard HEAD~1` 回到上一个 checkpoint
- 回退后需重跑相关质量门禁
- 触发时机：每完成一个 todo / 质量门禁 FAIL / 会话上下文丢失时用户主动触发

## 编号体系（追溯用）

PRD 产出 `PXX / BR-XXX / VR-XXX(V/S/C/E) / PERM-XXX / SM-XXX / TXX`；原型阶段产出 `SXX / ACT-XXX / OV-XXX / CMP-XXX / CMD-XXX`；各阶段校验产生 `CHK-XXX / TBD-XXX`。完整登记表见 `generate-system-prd/SKILL.md` 第七节"编号体系"。

## _shared 共享参考文件

`_shared/references/` 是多个 Skill 共用文件（PC 管理端规范 `pc_admin_ui_spec.md`、移动端通用 UI 规范 `ui-design-standards.md`、18 个 JSON 结构示例）的**唯一事实来源**，规则见 `_shared/README.md`。各 Skill 内只保留本阶段特有文件。

**防回归校验**：修改任何共享文件或 Skill 引用后，运行：

```powershell
powershell -File _shared/validate.ps1
```

校验内容：共享文件不得被本地重建拷贝、SKILL.md 引用路径必须存在、全部 JSON 可解析、design-tokens 单点且版本 1.3。

## 单独分发某个 Skill

Skill 内引用 `../_shared/` 的文件需在分发时复制回该 Skill 的 `references/` 并改回本地引用路径，详见 `_shared/README.md` 第 5 条。

## 变更记录

### 2026-07-30 新增 product-pipeline-master 总编排调度 skill
- 参考 game-forge-master 的编排模式，为产品工作台创建总调度中枢
- 含端类型判定决策树、阶段裁剪规则、产物路径总表、JSON 工件消费链、失败回退策略
- 本身不产出文件，负责判定端类型→裁剪阶段→串联下游 6 个主线 skill + 3 个旁线 skill
- WORKBENCH.md 流水线图和 skill 清单同步更新

### 2026-07-30 generate-system-prd 懒加载优化
- §三文档结构规范（369行）抽离到 `references/prd-document-template.md`，SKILL.md §三改为索引表+端专属约束摘要
- SKILL.md 从 610行 缩减到 275行（瘦身55%），references 指引表和生成流程同步指向 template
- 激活时只加载路由+流程+约束，逐章生成时按需读取 template 对应章节

### 2026-07-30 generate-html-pages 优化：冲突修复、架构边界与结构精简
- PC 端 Token 与 DOM 骨架以 `pc-admin-navigation-style.md` 为唯一基准，消除与 `_shared/pc_admin_ui_spec.md` 的双版本漂移
- 剥离 `index.html` 总控台生成职责至 `generate-portal`，引入 `build-report.json` 供下游消费
- 交互代码模板抽离至 `interaction-patterns.md`，SKILL.md 瘦身约 42%
- HTML 输出路径统一从 `outputhtml/` 迁移至 `output/site/`，全工作台引用同步更新
- 删除 generate-html-pages 内 10 份与 `_shared` 重复的 schema 与孤例示例文件
- **总纲路由拆分**：`generate-html-pages` 重构为轻量路由器（232行，原693行），PC 规范下沉至 `generate-html-pc-admin`，移动端规范下沉至 `generate-html-mobile`；端专属 references 迁入对应子skill，`interaction-patterns.md` 作为双端通用资源留总纲由子skill跨目录引用

### 2026-07-24 第三轮：_shared 单点维护改造 + 防回归
- 新增 `_shared/references/`（18 个共享 schema + 共享 UI 规范 + README），删除四个 skill 内 32 份重复拷贝
- 四个 SKILL.md 引用路径切换为 `../_shared/`，并区分"本阶段特有"与"共享"
- html-pages Token 块接入 _shared 同步注释；`--page-bg` 与壳层样式文件兼容性修复
- 新增 `_shared/validate.ps1` 防回归校验脚本与本 `WORKBENCH.md` 总索引

### 2026-07-24 第二轮：格式统一与命名消歧
- `annotations.example.json` 四处统一为 schemaVersion 2.1 结构
- 两份 `pages.example.json` 增加 `_stageNote` 阶段快照说明（PRD 注册态 / 原型富化态）
- prototype 版 `product-design-standards.md` 重命名为 `prototype-design-standards.md`，消除同名不同文
- 补齐 6 个 skill 的 `agents/openai.yaml`（9 个 skill 平台配置齐全）
- PRD 编号体系表补登 `TXX / ACT / OV / CMP / CMD / CHK / TBD / 原型ID`

### 2026-07-24 第一轮：冲突修复与链路打通
- `design-tokens.default.json` 四份拷贝统一为 v1.3（修复 v1.0/v1.1/v1.3 三版并存漂移）
- 重写 `generate-portal/SKILL.md`：移除 Tailwind/FontAwesome/固定蓝色强制，对齐 `annotation-standards.md`
- `output/site/index.html` 归属 generate-portal 独占，html-pages 不再生成总控台
- 输出路径统一：文档 `output/docs/`、JSON 工件 `output/spec/`、HTML `output/site/`
- PRD 新增编号体系（PXX/BR/VR/PERM/SM），移动端页面废弃 MXX 编号
- 四个 SKILL.md 新增 references 使用指引，消灭死资产
- 新增两份 `requirements.txt` 与依赖自检命令；frontmatter 与 description 风格统一

### 2026-08-06 AI Agent 体系升级（第一阶段完成）
- 新增 12 个 Agent 体系层 skill：Tool 层 5 个(tool-git-ops/tool-ci-ops/tool-deploy-ops/tool-db-ops/tool-monitor-ops) + 工程 skill 3 个(code-review/debug-fix/refactor) + Guardrail 层 2 个(guardrail/diff-reviewer) + Memory 层 2 个(project-knowledge-base/failure-casebook)
- 扩展 skill-auditor：新增第 5 模式"执行后评测" + 第 5 维度"执行质量" + references/audit-execution.md
- 9 个高频 skill(generate-system-prd/generate-prototype/generate-html-pages/game-spec/game-art-spec/game-code-forge/implement-backend/implement-frontend/implement-data-layer)质量章节末尾加"产物自评"项
- product-pipeline-master + game-forge-master 末尾加可选 Tool 确认点(确认点 5/6),打通"产出→提交→部署"闭环,Tool 前过 guardrail 前置检查
- _shared/validate.ps1 扩展 3 项检查:Tool skill 必须有 scripts/ 目录 / 审查类 skill 必须声明"只读"约束 / 新 skill frontmatter 必填 name+description
- 详细计划见 `.trae/documents/agent-system-upgrade-plan.md` §十三

### 2026-08-06 AI Agent 体系升级（第二阶段完成）
- 新增 4 个 Phase 2 运行时层 skill：skill-runtime(Agent Runtime 契约) + task-planner/replanner(Planning) + workflow-runtime(Workflow 可执行化)
- 扩展 product-pipeline-master + game-forge-master：执行顺序可由 workflow-runtime 编译为可执行 workflow.yaml，人工确认点对应 pause 节点
- 扩展 skill-auditor：新增第 6 维度"运行时契约"（现 6 模式 6 维度）+ references/audit-runtime.md
- 扩展 failure-casebook：新增 auto-query 子命令（skill 执行前自动查询历史失败，注入预防提示）
- 详细计划见 `.trae/documents/agent-system-upgrade-plan.md` §十四

### 2026-08-06 AI Agent 体系升级（第三阶段完成）
- 新增 4 个 Phase 3 数据与协作层 skill：codebase-rag(Context 持久化索引) + skill-usage-tracker(Data 调用统计) + prompt-registry(Model prompt 版本管理) + agent-orchestrator(多 Agent 协同协议)
- 扩展 workflow-runtime：执行 workflow.yaml 时每步调 skill-usage-tracker record 记录调用数据(分配 call_id 贯穿链路)
- 扩展 failure-casebook：记录失败时关联 call_id(related_call_id 字段)
- _shared/validate.ps1 扩展 2 项检查(检查 10 prompt-registry references / 检查 11 agent-orchestrator references),检查 7 newSkills 加 Phase 3 的 4 个 skill
- 详细计划见 `.trae/documents/agent-system-upgrade-plan.md` §十五

### 2026-08-06 AI Agent 体系升级（第四阶段完成）
- 新增 3 个 Phase 4 自适应与执行落地层 skill：adaptive-tuner(Data 自适应优化) + session-snapshot(Memory 会话快照) + agent-runtime-exec(Agent Runtime 执行器)
- 扩展 skill-runtime：runtime.yaml 新增 `external_overrides` 字段,三层覆盖优先级(overrides > 本地 > 默认),references/runtime-schema.md 新增 §九
- 扩展 workflow-runtime：新增 §十三"自适应优化"章节,接入 adaptive-tuner 形成数据驱动闭环(记录→分析→覆盖→执行→再记录)
- 扩展 agent-orchestrator：新增 §六.1"执行后端"章节,委托 agent-runtime-exec 实际运行多 Agent,协议定义与执行实现职责分离
- _shared/validate.ps1 扩展 3 项检查(检查 12 adaptive-tuner / 检查 13 agent-runtime-exec / 检查 14 session-snapshot references),检查 7 newSkills 加 Phase 4 的 3 个 skill(现 23 个),共 14 项检查全 PASS
- 详细计划见 `.trae/documents/agent-system-upgrade-plan.md` §十六

### 2026-08-06 新增 agent-builder 元技能(经验沉淀)
- 新增 `agent-builder` skill:把 4 阶段升级的 23 个 skill 建设经验沉淀为可复用的元技能
- 含 12 维度架构框架 + 6 步标准创建流程 + 7 大设计模式 + 标准 skill 结构模板
- 3 份 references:`agent-architecture-framework.md`(12 维度详解) + `skill-creation-patterns.md`(7 大模式) + `skill-template.md`(结构模板)
- 与 `skill-creator` 互补:agent-builder 提供"怎么设计 Agent skill",skill-creator 提供"怎么写 skill 文件"
- validate.ps1 检查 7 newSkills 从 23 扩展到 24(加 agent-builder)

### 2026-08-07 rd-init 重构为工作台加载器
- 从项目初始化器(创建目录/project.yaml/project-brief.json)重构为工作台加载器,职责收敛为扫描 skills 目录全部 skill + 生成 `.workbench-index.json` 索引 + 输出完整性报告
- 扫描全部 61 个 skill(含 rd-init 自身),按五大类分类:工作台元 skill(1) / 产研业务层(22) / 游戏流水线(11) / AI 短剧(2) / Agent 体系层(25,含 12 维度细分统计)
- 完整性校验:SKILL.md 存在(CRITICAL) / frontmatter name 存在(CRITICAL) / description 存在(WARNING) / runtime.yaml 声明(INFO) / references 路径存在(WARNING,支持 skill 目录内 + _shared/references/ + 跨 skill 目录三种合法位置)
- 同步修复:ai-short-drama-project-development 的 frontmatter 格式错误(标题在 `---` 前)
- WORKBENCH.md 元技能层新增 rd-init 收录

### 2026-08-07 短剧 skill 接入运行时契约 + 失败回退
- 两个短剧 skill 新增 `runtime.yaml`:`ai-short-drama-topic-planner`(timeout=600s,retry=2) / `ai-short-drama-project-development`(timeout=900s,retry=2),均含 inputs/outputs/degrade 声明
- 两个短剧 SKILL.md 新增"失败回退与降级"章节,定义 L1-L3 分层回退策略:
  - topic-planner:5 类场景(相似度过高/趋势缺失/用户不满意/自检未通过/失败记录)
  - project-development:4 类场景(选题复核未通过/大纲集数不匹配/制作可行性未通过/单步质量不达标)
- runtime.yaml 声明总数从 24 增至 26

### 2026-08-07 build-report.json device 字段写法统一
- `generate-html-mobile` 和 `generate-html-pc-admin` 的 device 字段写法统一为 `device: "mobile"` / `device: "pc"`(原 mobile 用冒号、pc 用等号,下游解析需兼容两种)

### 2026-08-10 新增 AI 短剧制作流水线（short-drama-* 10 个 skill）
- 新增总纲 `short-drama-forge-master`:类型判定（全 AI 生成/图文短剧/数字人/实拍辅助）+ 工具链决策树（可灵/即梦/Runway/Pika/Sora/海螺、Midjourney/SD/Flux、火山/CosyVoice/Edge TTS、Suno、FFmpeg）+ 阶段裁剪 + 固定产物路径表 + 失败回退（硬阻断/软降级）+ 强制人工确认点
- 新增 8 个阶段 skill:topic-brainstorm(0,可选) / blueprint(1) / spec(2) / script(3) / storyboard(4) / video-forge(5) / audio-forge(6) / edit(7,内含 Gate 5 成片实跑门)
- 新增跨阶段质量门 `short-drama-quality-gate`:Gate 0~4 契约校验 + 实跑预检,FAIL 硬阻断回原阶段,只写 `docs/GATE_{0..4}_REPORT.md`
- 设计要点:镜像 game-forge 套件结构(固定路径契约/裁剪/质量门/确认点/失败降级);产出"文档 + 可执行生产工程"(manifest.json + ffmpeg 脚本),视频生成失败降级静态图/图文短剧
- 全部 10 个新 skill 均接入 `runtime.yaml`(runtime.yaml 声明总数 26 → 36)
