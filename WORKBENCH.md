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
generate-portal              第5阶段：演示门户（端切换+标注跟随，output/site/index.html，独占）
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
game-forge-master            调度中枢：引擎选择（Phaser 3 / Pixi.js / 纯Canvas / Godot 4 / Unity / Three.js）+ 阶段裁剪 + 失败回退
        ↓
game-topic-brainstorm        阶段0（可选）：游戏选题脑暴（无参考对象时）
        ↓
game-teardown                阶段0.5（可选·复刻专线）：12 维产品系统逆向拆解 → 复刻矩阵 + 数值模型 + 灰盒 MVP
        ↓                         （与阶段0互斥：有参考对象走此路，无参考对象走选题脑暴）
game-blueprint               阶段1：一页纸游戏蓝图（类型/平台/引擎/玩法/范围；存在拆解产物时进复刻模式）
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
short-drama-storyboard        阶段4：分镜脚本 + 视觉规范 + 资产需求清册（每镜头文生图/图生视频 prompt）
        ↓
short-drama-asset-forge       阶段4.5：资产定妆与基线锁定（★ 不可裁剪）
                              ← 人工确认点 4.5 定妆确认
                              → assets/{char,scene,prop,voice,style}/ + docs/ASSET_BASELINE.md
                              → 回写 docs/ASSET_MANIFEST.json（status=locked + hash）
        ↓
┌────────────────────┐  ┌────────────────────┐
│ short-drama-video- │  │ short-drama-audio- │  (可并行)
│   forge            │  │   forge            │
│ 阶段5：manifest+    │  │ 阶段6：配音/BGM/   │
│ 逐镜头 AI 视频      │  │ 字幕（取 voice 资产）│
└────────────────────┘  └────────────────────┘
        ↓
short-drama-edit              阶段7：剪辑合成成片（ffmpeg 拼接/混音/字幕烧录，内含 Gate 5 成片实跑门）
```

**资产层（一致性基线）**：阶段 4 声明 `docs/ASSET_MANIFEST.json`（角色/变体/场景/道具/音色/风格基线，五类，`status=declared`）→ 阶段 4.5 出定妆图并**人工确认后锁定**到 `assets/**` + `docs/ASSET_BASELINE.md`（hash/版本/变更记录/豁免签字）→ Gate 3.5 校验（文件存在 + 已锁定 + hash 一致 + 变体齐全）→ 阶段 5/6 **只消费 `locked` 资产**。资产定义是**唯一真源**，`production/manifest.json` 只准引用（复制定义会被 Gate 4.9 阻断）。

**质量门**：`short-drama-quality-gate` 在 **6 个关键节点**（立项后/规格后/剧本后/分镜后/**资产定妆后**/生产后）介入做 Gate 0~4 + **Gate 3.5 资产门**的契约校验与实跑预检，FAIL 硬阻断并回原阶段修复；只读业务产物、只写 `docs/GATE_{0..4}_REPORT.md` 与 `docs/GATE_3.5_REPORT.md`。**Gate 3.5 是唯一"资源类也硬阻断"的门**（资产缺陷会被全剧镜头放大），豁免须用户在 `ASSET_BASELINE.md` 签字。

**固定产物契约**：全流水线按 `short-drama-forge-master/SKILL.md` §八 的产物路径总表读写（`docs/` 文档链 + `docs/ASSET_MANIFEST.json` → `assets/**` → `production/manifest.json` → `shots/` → `audio/`+`subtitles/` → `episodes/EP{XX}.mp4`），每阶段 Gate PASS 后强制人工确认点（含 **4.5 定妆确认**与 4.6），不允许自动连续执行。short-drama 侧 **10 个 skill 接入 `runtime.yaml`**（`short-drama-forge-master` 与 `short-drama-game-adapt` 为纯 SOP/方法论，无运行时契约）。

### 五、个人商业机会评估（独立方法论）

不属于产品交付流水线，独立使用。

```text
opportunity-screening        四层漏斗：底层逻辑 → 四维筛子 → 自身可达性体检 → 最小验证协议
  ├─ references/business-logic.md           L1 商业底层逻辑（交易创造财富/省时间/价值≠成本）
  ├─ references/screening-dimensions.md     L2 四维筛子（购买力·空位·启动投入·获客门槛）
  ├─ references/self-fit-assessment.md      L3 可达性体检（人脉盘·获客机制·三条换法）
  ├─ references/validation-protocol.md      L4 最小验证（带付费点的作品 + 4 周时间盒）
  ├─ references/case-example.md             实盘案例（10 个机会的裁决 + 打分锚点标定）
  └─ scripts/score_opportunities.py         确定性四维评分器（含「个人不可达」硬伤规则）
```

**核心判据**：「高客单 + 低获客门槛」的象限几乎不存在；获客门槛是唯一不可靠努力弥补的维度，个人的唯一杠杆是用作品替代人脉。**市场价值与个人可达性必须分开评估——前者高后者为零时，正确答案是「不做」。**

**何时用**：用户问"我该做什么副业""这个机会值不值得做""没人脉能不能做""XX 是不是红海了""帮我评估这几个方向"。

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
| `generate-portal` | 5 门户 | `index.html` 演示门户（端切换/标注跟随，独占） | `output/site/` |
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

### 2026-11-09 复刻专线第五批：可编译性审查（workflow-runtime 兼容 + 追踪链补键）

第三轮审查换了个角度：不看文档自洽，而是**真的把 master §七 编译一遍**，看新阶段能否被机读。结果发现 4 个实质问题：

- **`RE_BACK_TO` 把"回 0.5"截成"回 0"（最严重）**：`FAIL\s*则\s*回\s*(\d+)` 只吃整数，Gate 0.5 的失败回退被编译成 `__TODO_stage_0__`，即"拆解门失败 → 重跑选题脑暴"——而这两条线在 master 里明确互斥。若不修，按提示绑定占位的人会得到一个语义相反的 workflow。修复：抽出 `RE_STAGE_NO = (\d+(?:\.\d+)?)`，供 `RE_PAUSE` / `RE_BACK_TO` / `stage_match` 共用。
- **同行多产物只收第一个**：`产出 \`A.md\` + \`B.json\` + \`C.csv\`` 只捕获 A。复刻专线的 `TEARDOWN_MATRIX.json`（跨阶段追踪唯一键）与 `NUMERIC_MODEL.csv` 全部丢失，产物声明形同虚设。修复：新增 `RE_OUTPUT_EXTRA` 收集 `+ \`path\`` 续接项；art-spec（3 份）、game-spec（2 份）、integrate（2 份）同时受益。
- **暂停点标题与编号错位**：title 用计数器（1..7），question 保留原文（0.5/1/…/6），同一个节点两套编号。修复：title 取捕获到的原文编号。
- **"最后一项即终止"的语义倒置**：代码无条件把末选项绑 `__end__`，导致确认点 5 的"回退修复构建问题"= 结束流水线，"流水线完成"= 待绑定。修复：新增 `_is_terminal_label()`，只在文案含"终止/结束/完成/跳过"时绑 `__end__`。
- **追踪链在蓝图处断了一环**：Gate 0.8 只要求"M 项按名称或 matrix_id 找到"，但蓝图 §5 机制清单模板没有承载 ID 的列，于是只能退化成人读的名称匹配。修复：§5 表增 `来源` 列，格式 `(M/原作·D2-01)`，硬约束 2 同步；Gate 0.8 改为"标注 matrix_id，无 ID 可标的才按名称匹配"。
- **交接契约的悬空字段**：蓝图按"§0 摘要"读复刻档位，但档位只写在文档头部元信息里，§0 没有该字段。修复：§0 增 `复刻档位` 一行；Gate 0.5.8 的"与 §0 一致"改为"与报告头部证据覆盖一致"（覆盖率数字同样不在 §0）。
- 另修：master 三处"确认点 1~5"表述（新增 0.5 后不自洽）；`workflow-runtime/SKILL.md` 补三条编译行为说明。
- **回归验证**：`product-pipeline-master §八` 重新编译 22 步、暂停选项语义正确、产物多收 2 项，无破坏；`validate.ps1` 16 项全 PASS。
- **教训（已进本文件）**：**"文档自洽"不等于"机器可编译"**。新增阶段/确认点后必须实跑编译器；正则里的 `(\d+)` 就是一条隐形的"只支持整数"契约，改文档的人看不见它。

### 2026-11-09 复刻专线第四批：接线审查修复（commit 待记）

- **审查发现的时序缺陷（最重要）**：Gate 0.5 的 L2 检查（M 项进蓝图 / X 隔离）引用蓝图，但按 master 流程 Gate 0.5 跑在蓝图**之前**——这些检查永远不会在正确时机执行。修复：**Gate 0.5 收敛为纯 L1（9 项，只查拆解产物自身）**，下游消费检查下沉到对应 Gate：
  - Gate 0 新增 0.7~0.9（复刻条件）：一句话定义两半 / M 项进蓝图 / X 项隔离
  - Gate 1 新增 1.17~1.18：PRD 数值表带 matrix_id 且与 CSV 一致 / M 项落地 + 状态机三套
  - Gate 2 新增 2.15：manifest 无 X 项 + ART_SPEC 风格坐标对齐 §7
  - Gate 3 新增 3.27：GameConfig 字段名与 CSV parameter 同名 + high 敏感参数无硬编码
  - Gate 4 沿用 game-integrate §10.4（数值区间 + 确定性回归）
- **过期引用清理**：game-forge-master §七 的 "game-teardown §十一 交接映射" → §15.1（v2 重排后未同步）。
- **契约补齐**：teardown SKILL §14.2 顶层字段清单补 `sample_coverage`；§15.2 quality-gate 行改为新分工；quality-gate §七 注明 Gate 0.5 报告文件名为 `GATE_0_5_REPORT.md`（不套 {N} 模式）。
- **索引补齐**：README 完整技能清单与 §五 链接列表补 `game-quality-gate` 行（历史遗留缺失）；game-asset-forge / game-polish / game-integrate 的 description 补复刻模式触发词（路由完整）。
- **教训**：跨 skill 声明"会被某 Gate 判 FAIL"时，必须当场在 Gate 的检查表里加对应项——否则就是下游 skill 的"自我声明"，质量门根本不查（和 quality-gate 立项时批判的问题同构：自检宽松无阻断权）。

### 2026-11-09 复刻专线全链路接线审查（第三批）

- **审查结论**：前两批只接了一根线——`game-teardown` 三份产物中只有 `GAME_TEARDOWN.md` §0 被 `game-blueprint` 消费；`TEARDOWN_MATRIX.json` 与 `NUMERIC_MODEL.csv` **无任何下游读取**，下游 7 个 skill 的输入契约全部不知道复刻模式存在。
- **本批把三份产物接到每一个下游阶段**：
  | 阶段 | 新增消费 | 硬约束 |
  |---|---|---|
  | game-spec | TEARDOWN §2/3/5/6 + MATRIX + CSV | 数值只能来自 CSV 且带 `matrix_id`；状态机拆对象/容器/场景三套 |
  | game-art-spec | TEARDOWN §7 风格坐标系 + S/X | X 项禁入 ASSET_MANIFEST，按 replacement 原创 |
  | game-asset-forge | MATRIX X 清单（负面参照） | 生图 prompt 禁原作专名/角色名/商标 |
  | game-code-forge | CSV + 判定基准 | 参数零硬编码且字段名对齐 CSV；四维状态分离；事务式更新；重置确定性 |
  | game-integrate | CSV + high 敏感项 | Gate 4 追加：数值区间核对 + 重置 10 次确定性回归（§10.4） |
  | game-polish | TEARDOWN §6 反馈清单 | 反馈总时长偏离 ≤±20%，时序结构不变 |
  | game-quality-gate | 三份产物全部 | **新增 Gate 0.5 拆解门**（L1 8 项 + L2 3 项，FAIL 不进蓝图） |
- **追溯 ID 契约**：MATRIX `items[].id`（如 `D4-03`）为全链路追踪键；CSV 新增 `matrix_id` 列（10 列），孤立参数视为未拆解支撑；`in_mvp` 的 M 项在蓝图/PRD 中找不到引用即 Gate FAIL——"拆了但没落地"从此可机检。
- **Gate 0.5 检查要点**：三产物齐全可解析 / 12 维覆盖（T0/T1 可裁剪但须标注）/ X 全有 replacement（任何档位不可裁）/ 推断全有 falsifier / 差异点非空 / CSV 无孤儿参数 / 覆盖率如实 / M 项被蓝图消费 / X 项未泄漏进蓝图 / 修正史存在。
- **同步**：game-forge-master（流程图/执行顺序/硬阻断表/路径表新增 GATE_0_5_REPORT.md）、各下游 skill 的 description 与质量清单各加复刻模式条目、quality-gate runtime.yaml 新增 Gate 0.5 输出、README §3.4 新增"复刻专线消费链"设计点。

### 2026-11-09 game-teardown 沉淀《打个螺丝》四步实拆复盘（skill v2）

- **输入**：用户真实的四步拆解过程（步骤一 定位与循环 → 步骤二 研发规格 → 步骤三 修正三个机制 → 步骤四 单帧逆向成数据）。最大价值不是"拆得全"，而是**记录了一次范式修正**：v1 的"螺丝直接进盒/板件随螺丝消失/层级决定可交互"被第 1 秒与第 55 秒画面逐个推翻。
- **沉淀出的六条通用知识**（都不在 v1 里，且与具体游戏无关）：
  1. **拆解是收敛过程**（SKILL §六）：首轮产出是假设集；三条修正触发器（反例/走不通/交叉源冲突）；每条假设必须带 `falsifier`（什么观测能推翻它），没有 falsifier 的结论不许进报告；报告新增第 15 章「修正史」，不删旧结论。经验库收录四种典型修正形态：中间有缓冲层 / 对象消失但有残留态 / 层级其实是多正交维度 / 一次操作触发连锁更新。
  2. **可复刻性三问**（§七）：能写伪代码？能写断言？能算出解？三问全过才算拆清；过 1 问及以下只是"感觉像"，不得进 MVP。附带硬约束：求解器必须复用游戏规则函数。
  3. **状态建模纪律**（§九 + `references/state-modeling.md`）：四概念不许合并成一个 `layer`（归属/渲染层/遮挡/可交互）；可见≠可交互，用"看得见点不了"的实例证伪；残留态（空孔/坑/已解锁槽位）必须独立建模；权威态与派生态分离（能算的不要存）；逻辑与表现分离四条硬约束；遮挡必须写判定基准（中心点/碰撞区/多边形/人工）。
  4. **解空间与难度**（§十 + `references/solvability-and-difficulty.md`）：先找瓶颈资源（容量/步数/时间/次数/费用/血量，四要素：上限·单次占用·释放条件·扩容闸门）；难度用分支因子分布/死路率/步数冗余度/解数表达，**等权加权分只作排序占位**；求解器三种用途（验关/反推难度曲线/生成筛选）；内容产能模式决定成本结构。
  5. **证据形态匹配 + 样本覆盖 + 三类陈述**（§八）：结论类型决定证据形态（存在性→单帧；顺序因果→连续帧；概率→≥30 次；规则→对照实验；隐藏关系→"移除上层后露出"的对照帧）；样本覆盖矩阵（关卡阶段 × 状态，缺格即盲区）；`【观察】/【推断】/【设计】` 三类陈述必须分离，对应矩阵新字段 `kind`。
  6. **审计路径**（§二）：用户自带拆解稿时不重写，只做提级（kind+E）、补缺（12 维）、证伪（falsifier）、补测（待验证清单），给出"先补哪三条最划算"。
- **契约升级**：`TEARDOWN_MATRIX.json` 新增 `kind`（observed/inferred/design，必填）、`falsifier`（kind=inferred 时必填）、`revisions[]`（修正史，字段不许缺）、`mvp.determinism_checks[]`、`sample_coverage`；报告模板扩为 15 章（新增修正史、瓶颈资源表、解空间指标、确定性用例）。
- **新增 references 2 份**：`state-modeling.md`（三套状态机、四维分离、残留态、权威/派生、逻辑表现分离、状态迁移表含副作用列）、`solvability-and-difficulty.md`（瓶颈资源、四指标、求解器与状态哈希、难度落位四档、内容产能管线）。
- **同步**：README 清单行、WORKBENCH 本条目、game-forge-master 模板索引（references 数 3→5）、runtime.yaml（新增"已有拆解稿"输入与审计降级）。

### 2026-11-09 新增 game-teardown（游戏复刻拆解·阶段0.5）

- **背景**：原游戏流水线只支持"从 0 设计"，用户给参考游戏/录屏时只能靠 `game-blueprint` 顺手参考，拆解深度全凭自觉，典型后果是"只拆画面和玩法"——做出来看着像、玩着不像。
- **新增 skill**：`game-teardown`（SKILL.md + runtime.yaml + 4 份 references），把参考游戏当**产品系统**逆向，12 维：定位 / 循环 / 规则 / 数值 / 内容 / 交互 / 表现 / 技术 / 工具链 / 测试 / 合规 / 商业化。
- **四个原创机制（不止是清单化你的 12 条）**：
  1. **复刻档位 × 拆解深度**：T0 学习原型 / T1 玩法克隆 / T2 高保真 / T3 商业产品，对应 L1 结构 / L2 区间 / L3 公式三级深度——**档位决定拆多深**，避免对 T0 也做公式级拆解。
  2. **三色判定 M/S/X**：M 必须复刻（去掉就不像）、S 可替换（表现层，差异化主战场）、X 禁止复制（受保护表达，**必须给替代方案**，空即 Gate FAIL）。
  3. **证据分级 E0~E3 + 可观测性 O1~O3**：进蓝图的数值必须 ≥E2，O3 只写"行为等效设计"，每条数值必须带可复查 source（帧号/样本数/链接）——堵住 AI"把推断写成事实"这个最大失效模式。
  4. **敏感度排序**：拆完再收一刀，只挑 3~5 个决定"像不像"的变量，MVP 只保 high 项，low 项允许大改并**顺势变成差异化锚点**（同时降低换皮混淆风险）。
- **产物 3 份**：`docs/GAME_TEARDOWN.md`（12 维报告，14 章固定结构）+ `docs/TEARDOWN_MATRIX.json`（机读三色矩阵，含 dimensions_covered 全 12 维校验、X 项 replacement 条件必填、L3 仅限 high 敏感） + `docs/NUMERIC_MODEL.csv`（9 列固定，可直接 Excel 调参）。
- **references**：`teardown-dimensions.md`（12 维逐维观察点/方法/记录字段/三色倾向/常见坑）、`numeric-reverse-engineering.md`（帧测/控制变量/区间采样/公式族反解 + 公式族假设库 + 样本量下限 + 7 个陷阱）、`legal-clone-boundary.md`（思想表达二分 / 三档清单 / 换皮混淆 5 条自检 / 8 类合法替代手法 / 发布前 checklist）、`teardown-matrix.schema.json`。
- **流水线接线**：`game-forge-master` 新增阶段 0.5 路由（与阶段 0 互斥）、深度裁剪表、确认点 0.5、产物路径 3 行；`game-blueprint` 新增"§三.0 复刻模式"（交接映射 8 行 + 3 条硬约束 + description 触发词）；`game-topic-brainstorm` 新增复刻分支路由与判据。
- **校验**：`_shared/validate.ps1` 全绿（新增 JSON 可解析、references 路径可达、frontmatter 双引号、runtime.yaml schema）。

### 2026-09-30 新增 opportunity-screening 个人商业机会评估方法论 skill
- 独立方法论 skill（不属于任何交付流水线）：四层漏斗 `底层逻辑 → 四维筛子 → 自身可达性体检 → 最小验证协议`
- 沉淀自一次真实的副业方向评估过程：从「交易创造财富」的底层逻辑，到「客户购买力 · 竞争空位 · 启动投入 · 获客门槛」四维筛选，到「市场价值与个人可达性必须分开评估」的适配层判断
- 核心判据：**获客门槛是唯一不可靠努力弥补的维度**；「高客单 + 低获客门槛」象限几乎不存在，个人唯一杠杆是用作品替代人脉
- 配确定性评分脚本 `scripts/score_opportunities.py`（固定权重 + 「获客门槛=5 → 个人不可达」硬伤规则，避免情绪化打分）
- references 含 4 篇分册（business-logic / screening-dimensions / self-fit-assessment / validation-protocol）+ 1 篇实盘案例标定（case-example，10 个机会的裁决记录）
- WORKBENCH.md 新增「五、个人商业机会评估」章节，README.md 技能总览与完整清单同步更新

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

### 2026-09-30 短剧流水线补上「资产层」（一致性基线）
- **问题**：流水线缺资产概念 —— `char/linwan.png` 被 STORYBOARD/manifest/VISUAL_SPEC 反复引用，但**没有任何阶段产出它**；项目骨架无 `assets/` 目录；角色形象到阶段 5 第一次出图才被"确定"，60-100 集全跑完才发现不像即全量返工（成本后置到最贵环节）
- **新增阶段 4.5** `short-drama-asset-forge`（**不可裁剪**）：把角色（含变体）/场景/剧情道具/音色/风格基线一次性定妆并**锁定为基线**；产出 `assets/{char,scene,prop,voice,style}/**` + `docs/ASSET_BASELINE.md`（锁定表/变更记录/已知风险签字），回写 `docs/ASSET_MANIFEST.json`
- **新增契约** `docs/ASSET_MANIFEST.json`（v1.0，资产**唯一真源**）：阶段 4 storyboard 声明（`status=declared`）→ 阶段 4.5 回写（`status=locked` + `assetVersion`/`hash`/`lockedAt`/`lockedBy`）；五类资产 schema + 状态机见 `short-drama-asset-forge/references/asset-manifest-schema.md`
- **新增 Gate 3.5 资产门**（13 项）：清册合法/被引用资产全 locked/锁定字段无空值/定妆图存在/hash 与实体文件一致/基线表对账/变体完整性(seed 互异)/风格基线唯一/定妆图技术达标/音色齐备/降级已签字/影响面报告齐备 —— **唯一"资源类也硬阻断"的门**（资产缺陷会被全剧 800+ 镜头放大），豁免须用户在 ASSET_BASELINE.md 签字
- **新增人工确认点 4.5（★定妆确认）与 4.6**：候选图生成 → 用户选定才 lock（每批 ≤4 角色，重出 ≤3 轮）；4.5 是"内容锁定确认"，语义区别于其它"阶段推进确认"
- **变体机制**：同角色多 look（年龄跨度/换装伪装/战损/身份反转造型）走 `variantId`，各变体 **seed 必须互异**、`derivedFrom=default`；镜头用 `角色id(变体id)` 标记；禁止在同变体内临时改服装描述（漂移主因）
- **资产变更流程**：unlock → 影响面分析（扫 STORYBOARD 列受影响镜头）→ `docs/ASSET_IMPACT.md` → 用户决策（全量重生成/保留+标记/回退）→ `assetVersion+1`；**禁止静默改图**
- **单一真源收紧**：`production/manifest.json` 改为只写 `assets` 引用块（id+variant+assetVersion+hash）+ 镜头级 `charVariants`/`props`/`assetSnapshot`；新增 Gate 4.7~4.11（引用块存在/hash 一致/**禁止资产定义副本**/引用可解析/音色一致）
- **下游改造**：video-forge 改"消费锁定资产"（资产未锁定/文件缺失/hash 不符 → 报错退出，不再逐镜头硬凑）；audio-forge 音色走 `voiceId`（不选音色）；blueprint 新增"资产数"为第 6 个复杂度维度 + 资产规模/出图张数估算 + `asset-forge` 裁剪行（Gate 0 新增 0.8/0.9）
- **顺手修复的契约漂移**：`short-drama-edit` 的最小读取契约（原 `episode`/`shot_id`/`file`）与 `build_episodes.py`、模板 `manifest.example.json` 统一为 video-forge 实际 schema（`ep`/`id`/`outputPath`，脚本保留旧字段回退）
- 新增 `short-drama-asset-forge`（SKILL.md + runtime.yaml + 3 references + 2 templates）；runtime.yaml 声明总数 36 → 37；同步 `README.md`（目录/清单/链接）、`WORKBENCH.md`、`short-drama-forge-master` 总纲（流程图/裁剪/回退/执行顺序/路径表/模板骨架）与项目模板骨架（`assets/` + ASSET_MANIFEST/ASSET_BASELINE 模板）

### 2026-09-30 清理 _shared/validate.ps1 的 13 项既有 FAIL（回归全绿）
- **背景**：上一轮新增 `opportunity-screening` 时跑防回归校验，新 skill 零 FAIL，但暴露出 13 项与本次改动无关的历史遗留 FAIL；本次一并清理，`validate.ps1` 从 **13 FAIL → 全部通过**（exit 0）
- **① slides/SKILL.md 引用不存在的路径**：Routing 里写的是模板占位 `references/{subcommand}.md`，静态校验无法解析 → 改为指向 Subcommands 表中真实存在的 `references/create.md`
- **② 前端/设计类 11 个 skill 的 frontmatter `name` 未加双引号风格**：`banner-design` / `bing-image-harvest` / `brand` / `coupon-batch-create` / `design` / `design-system` / `html-single-file-pack` / `slides` / `ui-styling` / `ui-ux-pro-max` / `weekly-report-formatter`
- **③ workflow.yaml 无法解析**：根因不是文件坏，而是 `research_delivery_workflow` 是**外部导入包**（自带 `manifest.txt` / `SHA256SUMS.txt` / `scripts/validate_skill.py`，自带校验 19 个必需文件 PASS），它的 `workflow.yaml` 用的是**自有 stages 格式**，而 `validate.ps1` §9 会 glob 全仓 `workflow.yaml` 并一律套用 `workflow-runtime` 的 steps 规范 → 给 §9 加 `$workflowAllowList` 显式声明例外（与 §1 的 `$allowList` 同一思路），由该包自带校验器负责
- **新增维护脚本** `_shared/fix-frontmatter-name.py`：把 frontmatter `name` 批量规范为 `name: "<value>"`，幂等、可指定 skill
- **踩坑（重要，已写进脚本注释）**：本仓库部分 `SKILL.md` 是 **CRLF** 换行且 `core.autocrlf=true`。用 `.split('\n')` 或 `splitlines(keepends=True)` 配 `r'^name:[ \t]*(.+?)[ \t]*$'` 时，尾部 `\r` 会被 `(.+?)` 吃掉，导致两种静默损坏：CRLF 未加引号 → `name: "xxx<CR>"`（CR 被塞进引号里、悄悄丢换行）；CRLF 已加引号 → `name: ""xxx"<CR>"`（畸形）。**正确做法**：先切出「行体 + 终止符」，只在行体上取值，回写保留原终止符；批量脚本务必先核查目标文件的换行风格
- **校验**：`validate.ps1` 全部通过（frontmatter 双引号 86/86、references 引用 108 处、workflow.yaml 1 个外部格式已声明豁免）


### 2026-10-15 generate-portal 对齐门户交互现状（端切换 / 标注跟随）

- 门户 `output/site/index.html` 已由「页面树三栏 + 设备切换」演进为 **端切换驱动的评审台**：
  顶部工具栏按 `projectMap` 模块切端并加载入口页；**画幕外本端页面列表仅移动端渲染**（PC 端沿用原型自带菜单，画幕占满）；
  右侧标注随**任意来源**的页面切换同步（含画幕内导航）。
- 同步更新：`SKILL.md` 第五/六节重写 + 概述与行动指令对齐；新增 `references/portal-interaction-contract.md`（布局与交互权威口径、
  `syncFromFile` 双通道、三条硬约束、验收清单）；`references/annotation-standards.md` §5 明确「`file://` 只降级 DOM 角标定位，
  页面级标注跟随仍须可用」；`agents/openai.yaml` 与 README/WORKBENCH 技能表去「三栏」表述。
- 依据：乌海项目 2026-10-15 的端切换 / 画幕外列表 / 标注跟随改造（含 `file://` 与 `http://` 行为分叉的实测结论）。


### 2026-10-16 四个工程 skill 沉淀乌海项目 10-15/16 轮次教训

- **delivery-consistency-gate**：新增第五节「门禁与被测对象的隐式契约」——固定列索引（`td[N]`/`children[N]`）、
  元素 id、文案正则三类假设随 UI 改动必须同改；**改 UI 前先 grep 门禁源码建「门禁同步清单」**；断言重排换健壮锚点
  （行识别别绑易下线列）；「静默取 0 行」判失败；有副作用的门禁显式标注（审查轮禁跑）。checklist +2，description 补词。
- **state-label-surgery**：新增第五节「概念整体退役八件套」——贯穿多页+共享库+规则的领域概念下线：先接替代源、
  样本改型不留 remap、**同批删完防半下线**、门禁断言按新口径重写（非同步数字）、作废 BR 登记勿删号。
  拓扑判定表加「概念退役」档；标准流程/checklist 同步；`pitfalls.md` 补 S11（半下线事故形态，附渠道下线实战）。
- **snapshot-guard**：`forensics.md` 差异形态表补「瞬时写回（自愈型）」行（首跑差异/复跑自愈/行级 diff=0）；
  取证五步之「性质判定」前插**复跑确认**——自愈型只记档勿还原（还原可能覆盖正在写入的会话）。checklist +1。
- **engineering-ledger-hygiene**：新增 M6「并发会话红项归属判定（基线复现法）」——起点快照解包复跑，
  基线同样红 ⇒ 既有问题不修（属在建轮次收口）；日志记并发窗口；勿顺手修他线红项。
  M1 补「明细外置伴生文件」表述；五条机制改六条；收工仪式与 checklist 同步。
- 依据：乌海项目 b149~b161 界面收敛（门禁三连踩）、2026-10-16 需求轮（渠道概念整体下线）、
  当日一致性审查轮（快照瞬时写回实测）。全库扫引用：README/WORKBENCH 无这四 skill 的旧口径复述，
  product-pipeline-master 引用的门禁分类法（A~H/I~K）未变，无需联动。
