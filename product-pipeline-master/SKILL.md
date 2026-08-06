---
name: "product-pipeline-master"
description: "产品工作台的总编排调度中枢。当用户要'端到端生成产品原型''从需求到可演示原型''按流水线生成产品交付物'时调用。负责判定端类型、裁剪阶段、串联下游 skill 的执行顺序、提供失败回退策略，本身不直接产出文件。"
---

# Product Pipeline Master — 产品工作台总编排

本 skill 是产品交付流水线的**调度中枢**，本身不直接产出业务文件，职责是：
1. 接收用户需求，判定走哪条交付路径（主线/旁线/混合）
2. 判定终端类型（admin_web / native_app / mobile_web / mini_program / hybrid / multi_end）
3. 裁剪阶段（轻量原型可跳过脑暴/实施规划）
4. 串联下游 6 个主线 skill 与 3 个旁线 skill 的执行顺序
5. 提供失败回退策略与产物路径总表

---

## 一、何时调用

满足以下任一条件即调用本 skill：

- 用户说"用 AI 端到端生成一个产品原型"
- 用户说"从需求到可演示原型，按流水线走"
- 用户给了产品需求，需要完整走完 PRD → 原型 → HTML → 门户
- 用户调用了任意 `generate-*` 系列 skill 但未先经过总纲

**不要**在以下场景调用：
- 用户只要单一阶段产物（直接调对应 skill，如"写 PRD"→ `generate-system-prd`）
- 用户只是咨询产品怎么做（用对话回答即可）
- 用户要修改已有产物的某一处（直接用 Edit/Write）

---

## 二、流水线总览

```
用户需求
       ↓
[本 skill] 路径选择 + 端类型判定 + 阶段裁剪
       ↓
brainstorm-product-feature  (可选) → 功能构想评估摘要
       ↓
generate-system-prd        → 产品设计方案.md + JSON 工件
       ↓
⏸ 人工确认点 1 (AskUserQuestion: 进入原型 / 回退修改 PRD / 终止)
       ↓
generate-prototype         → 页面原型文档.md + annotations.json
       ↓
⏸ 人工确认点 2 (AskUserQuestion: 进入 HTML 生成 / 回退修改原型 / 终止)
       ↓
generate-html-pages        → 判端路由 + 调度子skill + 汇总 build-report.json
  ├─ generate-html-pc-admin    → output/site/pc/
  └─ generate-html-mobile      → output/site/mobile/
       ↓
⏸ 人工确认点 3 (AskUserQuestion: 进入门户生成 / 回退修复 HTML / 终止)
       ↓
generate-portal            → output/site/index.html (三栏演示门户,独占)
       ↓
⏸ 人工确认点 4 (AskUserQuestion: 进入实施规划(可选) / 流水线完成 / 回退修复门户)
       ↓
⏸ 人工确认点 5 (可选 Tool,AskUserQuestion: 提交 Git / 部署平台 / 跳过;Tool 前过 guardrail 前置检查)
       ↓ 原型评审通过
plan-system-implementation → 实施蓝图 + 任务板 + 追溯表

【旁线:文档交付物】(可并行,不依赖主线顺序)
bid-functional-solution      → 标书功能建设方案 .docx
ruanzhu-doc-generator        → 软著说明书 .docx
screenshot-operation-manual  → 操作手册 .docx

[注] 本流水线可由 workflow-runtime 编译为 workflow.yaml 驱动执行(可选),见 §八 末尾说明
```

**阶段性质**：
- 阶段 0-5（脑暴→PRD→原型→HTML→门户）：**主线路径**，产出可演示原型
- 实施规划：**可选**，评审通过后才走
- 旁线文档：**可并行**，任何阶段都能触发，不依赖主线顺序
- **人工确认点 1~4：强制暂停**，每阶段质量门禁 PASS 后用 AskUserQuestion 确认，不允许自动进入下一阶段(见 §九.1)

**关键约束**：每阶段产物的路径与文件名固定，下游 skill 必须按固定路径读取上游产物，不允许自定义路径。

---

## 三、端类型判定决策树

根据用户需求自动判定终端类型，决定 HTML 阶段走哪个子 skill：

```
用户需求
   ├─ "管理后台/PC后台/管理系统/admin" → admin_web → generate-html-pc-admin
   ├─ "移动端/手机端/APP/H5/触屏" → native_app 或 mobile_web → generate-html-mobile
   ├─ "小程序/微信小程序" → mini_program → generate-html-mobile
   ├─ "双端/PC+移动/多端" → multi_end → 两个子 skill 都走
   ├─ 需求中未明确端类型 → 询问用户(见 §九 用户交互)
   └─ 用户明确指定 → 尊重用户选择
```

### 判定细则

| 需求特征 | 端类型 | HTML 子 skill | 理由 |
|---------|--------|--------------|------|
| 企业管理系统、数据后台、配置中心 | admin_web | generate-html-pc-admin | 需要深色侧栏+工作区页签+表格密集布局 |
| 面向 C 端用户的移动应用 | native_app | generate-html-mobile | 任务型单列布局，沉浸式体验 |
| 移动端内嵌网页、H5 营销页 | mobile_web | generate-html-mobile | 移动端布局但浏览器访问 |
| 微信/支付宝小程序 | mini_program | generate-html-mobile | 移动端布局，注意小程序限制 |
| 后台管理 + 移动端用户侧 | multi_end | 两个子 skill 都走 | 双端输出，共用页面编号 |
| 纯内容展示网站 | mobile_web | generate-html-mobile | 优先移动端，除非明确要 PC |

### 判定结果写入

端类型判定结果写入 PRD 的"1.5 终端与使用场景"章节，格式：
```
端类型: admin_web
HTML 子 skill: generate-html-pc-admin
理由: [一句话]
```

---

## 四、阶段裁剪规则

不是所有项目都要走完整 6 阶段。根据复杂度裁剪：

| 复杂度 | 特征 | 裁剪 |
|--------|------|------|
| ★ 极简 | 单页面 + 无交互逻辑 + 纯展示 | 跳过 brainstorm，PRD 极简版，原型直出 HTML |
| ★★ 简单 | 3-5 页 + 简单 CRUD + 单端 | 跳过 brainstorm，PRD 标准版 |
| ★★★ 中等 | 5-15 页 + 多模块 + 单端 | 全流程（含 brainstorm 可选） |
| ★★★★ 复杂 | 15+ 页 + 多端 + 复杂业务规则 | 全流程 + 强烈建议走 brainstorm |
| ★★★★★ 极复杂 | 多端 + 多角色 + 复杂权限 + 工作流 | 全流程 + 建议人工 review |

**实施规划的裁剪规则**（独立判断）：

| 触发条件 | 是否执行 plan-system-implementation |
|---------|----------------------------------|
| 用户明确要求"生成实施计划/任务拆解/排期" | ✓ 执行 |
| 原型评审通过，用户要进入开发阶段 | ✓ 执行 |
| 用户只要原型演示，未提及开发 | ✗ 跳过 |
| 用户明确说"先到原型为止" | ✗ 跳过 |

**旁线文档的触发规则**：

| 用户需求 | 触发旁线 skill |
|---------|--------------|
| "生成标书/投标方案" | bid-functional-solution |
| "生成软著材料/软件著作权" | ruanzhu-doc-generator |
| "生成操作手册/使用说明" | screenshot-operation-manual |

裁剪结果在执行前向用户简报，用户确认后开始执行。

---

## 五、产物路径总表

所有 skill 必须遵守的固定路径：

| 产物 | 路径 | 由哪个 skill 产出 |
|------|------|-----------------|
| 脑暴摘要 | 对话输出 | brainstorm-product-feature |
| PRD 文档 | `output/docs/{产品名称}-{端类型}-产品设计方案-V{版本号}.md` | generate-system-prd |
| PRD 质量门禁报告（可选，非主线产出） | 默认对话输出；用户/工作流指定时写入 `output/build/prd-quality-report.md` + `.json` | prd-quality-checker（**门禁类 skill**，非主线产出者；仅用于 PRD 进入下游前的质量门禁，不产出业务文件，§八确认点 1 依赖其 PASS/FAIL 结论） |
| JSON 工件 | `output/spec/*.json`（pages/data-model/navigation/annotations/actions/overlays/components/permissions/business-rules/state-machines/pipeline-context） | generate-system-prd + generate-prototype（pages.json 富化） |
| design-tokens.json | `output/spec/design-tokens.json` | generate-prototype（唯一产出者；缺失时下游用 `_shared/references/schemas/design-tokens.default.json` 兜底） |
| 页面原型文档 | `output/docs/{系统名称}-页面原型文档.md` | generate-prototype |
| annotations.json | `output/spec/annotations.json` | generate-prototype |
| PC HTML 页面 | `output/site/pc/PXX-*.html` + `common.css` + `sidebar.js` | generate-html-pc-admin |
| 移动端 HTML 页面 | `output/site/mobile/PXX-*.html` + `common.css` + `navbar.js` | generate-html-mobile |
| 构建报告 | `output/site/build-report.json` | generate-html-pages（路由器汇总） |
| 演示门户 | `output/site/index.html` | generate-portal（独占） |
| 实施蓝图 | `output/build/implementation-plan.md` + `architecture.json` | plan-system-implementation |
| 任务板 | `output/build/task-board.json` | plan-system-implementation |
| 追溯表 | `output/build/traceability.json` | plan-system-implementation |
| 风险登记 | `output/build/risk-register.md` | plan-system-implementation |
| 架构决策记录 | `output/build/decisions/ADR-*.md` | plan-system-implementation |
| 标书方案 | 用户指定路径 `.docx` | bid-functional-solution |
| 软著说明书 | 用户指定路径 `.docx` | ruanzhu-doc-generator |
| 操作手册 | 用户指定路径 `.docx` | screenshot-operation-manual |
| workflow.yaml(可选) | `workflow.yaml` | workflow-runtime(编译本总纲执行顺序生成) |
| CI 操作报告(按需) | `output/build/ci-ops-report.json` | tool-ci-ops(由 package-and-deploy-system §4 CI/CD 调用;按需产出,未调用时缺失不视为缺陷) |
| 数据库操作报告(按需) | `output/build/db-ops-report.json` | tool-db-ops(由 package-and-deploy-system §3 数据库发布 或 implement-data-layer 调用;按需产出) |
| 监控操作报告(按需) | `output/build/monitor-ops-report.json` | tool-monitor-ops(由 package-and-deploy-system §5 运维能力 或 debug-fix 调用;按需产出) |

---

## 六、JSON 工件消费链

下游 skill 读取上游 JSON 工件的固定关系：

```
generate-system-prd 产出:
  pages.json ──────────────────→ generate-prototype (富化页面身份)
  data-model.json ─────────────→ generate-prototype (字段约束)
  permissions.json ────────────→ generate-prototype (权限标注)
  business-rules.json ─────────→ generate-prototype (交互规则)
  state-machines.json ─────────→ generate-prototype (状态流转)
  pipeline-context.json ───────→ 所有下游 skill (上下文)

generate-prototype 产出/更新:
  pages.json (富化) ───────────→ generate-html-pages (页面清单+端类型)
  navigation.json ─────────────→ generate-html-pages (页面流转)
  annotations.json ────────────→ generate-portal (标注展示)
  actions.json ────────────────→ generate-html-pages (交互行为)
  overlays.json ───────────────→ generate-html-pages (弹窗规格)
  components.json ─────────────→ generate-html-pages (组件清单)
  design-tokens.json ──────────→ generate-html-pages + generate-portal + implement-frontend (视觉Token；generate-prototype 为唯一产出者)

generate-html-pages 产出:
  build-report.json ───────────→ generate-portal (页面清单+双端对应)
```

**关键约束**：JSON 工件是阶段间数据传递的权威来源，优于从文档中重复提取。

---

## 七、失败回退策略

下游 skill 执行失败时的统一处理：

| 失败场景 | 回退策略 |
|---------|---------|
| PRD 生成中断 | 保存已生成章节，用户可从断点续写 |
| 原型阶段缺少 PRD | 允许从需求文档/截图逆向重建 PRD，标记 `generatedByFallback: true` |
| HTML 生成缺少页面 | 跳过缺失页面，在 build-report.json 的 `openIssues` 记录 |
| HTML 生成缺少标注 | 门户降级运行，显示"暂无标注"，不伪造 SXX |
| 门户 iframe 跨域 | 关闭角标 DOM 定位，明确说明，用严格 sandbox 隔离 |
| 端类型无法判定 | 询问用户，不擅自决定 |
| JSON 工件缺失 | 回退到从 Markdown 文档解析，标记 `sourceLevel: INFERRED` |
| design-tokens.json 缺失 | 使用 `design-tokens.default.json` fallback（已与规范对齐） |

**所有失败都允许继续往下走**，失败项汇总到 `build-report.json` 的 `openIssues` 字段或对应文档的"已知问题"章节，供人工后补。

---

## 八、执行顺序（必须严格遵循，每阶段人工确认）

调用本 skill 后，按以下顺序执行下游 skill。**每个阶段完成后必须暂停，用 AskUserQuestion 向用户确认后再进入下一阶段**(见 §九.1 确认规则)：

### 主线流程

1. （可选）调用 `brainstorm-product-feature`，产出功能构想评估摘要
2. 调用 `generate-system-prd`，读取脑暴摘要（如有）和用户需求，产出 PRD 文档 + JSON 工件
   - （可选）调用 `prd-quality-checker`（**门禁类 skill，非主线产出者**）：基于可定位证据审核 PRD 目标/范围/规则/验收等 15+ 维度，产出 Markdown 门禁报告 + 可选 JSON（默认对话输出，工作流指定时写入 `output/build/prd-quality-report.md`）
   - ⏸ **人工确认点 1**：PRD 质量门禁 PASS 后，简报 PRD 页面数/端类型/JSON 工件路径，AskUserQuestion 询问"进入原型设计 / 回退修改 PRD / 终止流水线"
3. 调用 `generate-prototype`，读取 PRD 和 JSON 工件，产出页面原型文档 + 富化的 JSON 工件
   - ⏸ **人工确认点 2**：原型质量门禁 PASS 后，简报页面原型数/annotations 数，AskUserQuestion 询问"进入 HTML 生成 / 回退修改原型 / 终止流水线"
4. 调用 `generate-html-pages`（路由器）：
   - 读取 `output/spec/pages.json` 的 `devices` 字段判定端类型
   - 按端类型调度子 skill：
     - admin_web → `generate-html-pc-admin`
     - native_app / mobile_web / mini_program → `generate-html-mobile`
     - multi_end → 两个子 skill 都调用
   - 汇总子 skill 产出的 build-report.json
   - ⏸ **人工确认点 3**：HTML 质量门禁 PASS 后，简报 HTML 页面数/build-report 结果，AskUserQuestion 询问"进入门户生成 / 回退修复 HTML / 终止流水线"
5. 调用 `generate-portal`，读取 HTML 页面 + `build-report.json` + `annotations.json`，产出 `output/site/index.html`
   - ⏸ **人工确认点 4**：门户质量门禁 PASS 后，简报门户路径/iframe 预览状态，AskUserQuestion 询问"进入实施规划(可选) / 流水线完成 / 回退修复门户"
   - ⏸ **人工确认点 5（可选 Tool）**：门户完成后(或确认点 4 选"流水线完成"后),若用户明确要"提交/部署",AskUserQuestion 询问"提交产物到 Git / 部署到平台 / 跳过 Tool 操作"
     - 选"提交到 Git" → 调用 `tool-git-ops`(commit 产物目录,默认不 push)
     - 选"部署到平台" → 判定部署目标:
       - 纯静态前端(无后端/无数据库) → 调用 `web-static-deploy`(GitHub Pages / Vercel / Netlify / CloudBase / COS)
       - 含后端/数据库的完整系统 → 调用 `tool-deploy-ops`(需先 git commit)
     - 选"跳过" → 进入阶段 6(若尚未进入)或结束
   - Tool 操作前过 `guardrail` 前置检查(检查 output/ 路径是否在敏感清单)
6. （可选）原型评审通过后，调用 `plan-system-implementation`，**首次产出**实施蓝图（architecture.json / task-board.json / traceability.json）
   - **与 build-working-system 的边界**：本阶段（product-pipeline-master 阶段6）是 plan-system-implementation 的**首次产出**方；后续进入 `build-working-system` 时，其 Stage 1 会**恢复或更新**已有蓝图（不重复首次产出），然后才进入 Stage 3 按 P0 垂直切片按名调用 `implement-data-layer` / `implement-backend` / `implement-frontend`。两个编排器不重复执行同一份蓝图的首次产出。

### 旁线流程（可与主线任意阶段并行）

- 用户要标书 → 调用 `bid-functional-solution`
- 用户要软著 → 调用 `ruanzhu-doc-generator`
- 用户要操作手册 → 调用 `screenshot-operation-manual`

**不允许跳步**：即使某阶段被裁剪，也必须确认上游产物已存在。例如跳过 brainstorm 时，需确认用户需求足够清晰可直接写 PRD。
**人工确认不可跳过**：确认点 1~4 是强制暂停点，即使用户此前已表达"全流程执行"，也必须在每个确认点等待用户明确选择后才继续。旁线流程不参与主线确认点。

**可选:产出 workflow.yaml 交 workflow-runtime 驱动执行**

本总纲的执行顺序(§八)可由 `workflow-runtime` skill 编译为可执行 `workflow.yaml`,支持暂停/恢复/跳过/回退/并行调度。编译命令:
```
python ../workflow-runtime/scripts/compile_workflow.py compile-from-master --master SKILL.md --section "§八" --output workflow.yaml
```
产出 `workflow.yaml`(可选产物)。workflow-runtime 模式下,pause 节点自动触发 AskUserQuestion,与本文 §九.1 的人工确认点一一对应。详见 `../workflow-runtime/SKILL.md`。

---

## 九、用户交互约定

- 默认全程中文输出
- 每阶段完成后向用户简报产物路径与下一步
- 遇到选择（端类型、阶段裁剪、是否进入实施）用 AskUserQuestion 确认，不擅自决定
- 端类型无法判定时，提供选项让用户选择：
  - "PC 管理后台" → admin_web
  - "移动端 APP/H5" → native_app / mobile_web
  - "双端（PC + 移动）" → multi_end
  - "小程序" → mini_program
- 全流程产物纯文本/HTML/JSON，不依赖任何可视化编辑器

### 9.1 人工确认机制（强制，见 §八 确认点 1~4）

每个主线阶段（阶段 2~5）完成且对应质量门禁 PASS 后，**必须暂停流水线**，用 AskUserQuestion 向用户确认下一步。**不允许自动连续执行下一阶段**，即使用户在启动时说过"全流程跑完"或类似话术。

**确认点标准动作**：

1. **简报**：用 2-3 句话汇报本阶段产物路径 + 关键指标（如 PRD 页面数/HTML 文件数/门户是否可独立打开）
2. **AskUserQuestion 询问**，选项固定 3 个（按阶段语义微调文案）：
   - "进入下一阶段：{下一阶段名}"（推荐）
   - "回退修改：回到本阶段修复问题"
   - "终止流水线：停止，保留当前产物"
3. **根据用户选择**：
   - 选"进入下一阶段" → 调用下游 skill
   - 选"回退修改" → 重新执行本阶段 skill（用户可补充修改要求），重跑质量门禁，再次确认
   - 选"终止流水线" → 输出最终简报（已完成阶段 + 产物清单），结束

**例外**：
- 阶段 1（brainstorm）本身可选，不设独立确认点；若执行，用户确认脑暴摘要即进入阶段 2
- 阶段 6（plan-system-implementation）是可选增量，由确认点 4 的用户选择决定是否进入，进入后不再设确认点（直接执行到底）
- 质量门禁 FAIL 时无需确认，直接回退修复（修复后重跑门禁，门禁 PASS 再走确认点）
- 旁线流程（标书/软著/操作手册）独立于主线，不参与确认点，可在任意阶段并行触发
- 确认点 5（可选 Tool）是**可选**的：即使用户在确认点 4 选了"流水线完成"，也可在产物已落地后单独触发 Tool 操作；反之，确认点 5 默认不强制出现，仅在用户明确要"提交/部署"时触发

**workflow-runtime 兼容**:在 workflow-runtime 模式下,本文的人工确认点(确认点 1~5)对应 workflow.yaml 中的 pause 节点,pause 节点自动触发 AskUserQuestion,选项与本文一致("进入下一阶段"/"回退修改"/"终止流水线")。可选 Tool 确认点(确认点 5)对应 workflow.yaml 中 optional=true 的 pause 节点。详见 `../workflow-runtime/references/execution-semantics.md`。

---

## 十、质量门禁

每阶段完成后的质量检查点：

| 阶段 | 质量门禁 |
|------|---------|
| PRD | `prd-quality-checker` 可选审核；JSON 工件 `sourceLevel` 不应为 `INFERRED` |
| 原型 | `pages.json` 的 `archetypeId` 已填充；`annotations.json` 与页面清单对齐 |
| HTML | `build-report.json` 的 `result` 为 `PASS`；`openIssues` 为空或有明确说明 |
| 门户 | `index.html` 可独立打开；iframe 预览正常；标注渲染正确 |
| 实施 | 任务板 `task-board.json` 与 PRD 页面清单可追溯 |
| Tool(可选) | `tool-git-ops` 产出 `git-ops-report.json`；`tool-deploy-ops` 产出 `deploy-ops-report.json`；`guardrail` 前置检查通过 |

**防回归校验**：修改任何共享文件或 skill 引用后，运行：
```powershell
powershell -File _shared/validate.ps1
```

---

## 十一、与 game-forge-master 的差异

本 skill 参考 `game-forge-master` 的编排模式，但针对产品交付场景做了以下调整：

| 维度 | game-forge-master | product-pipeline-master |
|------|------------------|------------------------|
| 引擎选择 | Phaser/Pixi/Canvas 三选一 | 端类型判定（admin_web/native_app/...） |
| 阶段裁剪依据 | 游戏复杂度星级 | 产品复杂度星级 + 端类型 |
| 并行阶段 | asset-forge + code-forge | 旁线文档可与主线任意阶段并行 |
| 可选阶段 | game-polish | brainstorm + plan-system-implementation |
| 失败回退 | 占位图 + 静音音频 | JSON 工件 fallback + 文档逆向重建 |
| 产物消费 | 固定路径读取 | JSON 工件优先于文档提取 |
