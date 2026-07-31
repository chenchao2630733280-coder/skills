# 产品工作台（Product Workbench）

一套覆盖"从想法到实施"完整产品交付流水线的 Skill 集合，外加文档交付物生成能力。本文件是工作台的总索引。

## 流水线总览

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
        ↓ 原型评审通过
plan-system-implementation   实施规划（可选）：可执行的工程实施蓝图

【旁线：文档交付物】（可并行，不依赖主线顺序）
bid-functional-solution      标书功能建设方案（Word）
ruanzhu-doc-generator        软著产品说明书（DOCX，PC/移动端分离）
screenshot-operation-manual  截图操作手册（DOCX/PDF/Markdown）
```

**总编排入口**：`product-pipeline-master` 是调度中枢，接收用户需求后判定端类型、裁剪阶段、串联下游 skill。用户也可直接调用单个 skill，但端到端生成时建议先经过总纲。

主线 Skill 的顺序是推荐顺序，不是强制依赖；PRD 可从需求、脑暴、原型、HTML、代码或运行系统证据生成或逆向重建（详见 `generate-system-prd/references/prd-stage-boundary.md`）。

## Skill 清单

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

## 编号体系（追溯用）

PRD 产出 `PXX / BR-XXX / VR-XXX(V/S/C/E) / PERM-XXX / SM-XXX / TXX`；原型阶段产出 `SXX / ACT-XXX / OV-XXX / CMP-XXX / CMD-XXX`；各阶段校验产生 `CHK-XXX / TBD-XXX`。完整登记表见 `generate-system-prd/SKILL.md` 第七节"编号体系"。

## _shared 共享参考文件

`_shared/references/` 是多个 Skill 共用文件（PC 管理端规范 `pc_admin_ui_spec.md`、移动端通用 UI 规范 `ui-design-standards.md`、9 个 JSON 结构示例）的**唯一事实来源**，规则见 `_shared/README.md`。各 Skill 内只保留本阶段特有文件。

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
- 新增 `_shared/references/`（9 个共享 schema + 共享 UI 规范 + README），删除四个 skill 内 32 份重复拷贝
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
