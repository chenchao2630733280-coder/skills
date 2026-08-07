# AI Agent 系统设计文档

> 面向 AI 基础读者的完整宣讲：从"什么是 AI"到"整套 Agent 系统怎么运转"
>
> 读者：不需要懂编程，但需要能理解"工具""流程""决策"这些日常概念
>
> 文档目标：讲透三件事——**这套系统是什么、为什么这么设计、怎么运转**

---

## 第一章 先搞懂：AI、Skill、Agent 到底是什么

### 1.1 用一个比喻把概念讲透

想象你要开一家餐厅：

| 餐厅角色 | 对应的 AI 概念 | 做什么 |
|---------|--------------|--------|
| 老板 | **人（你）** | 定目标、做关键决策 |
| 餐厅经理 | **Agent** | 接到目标后自己安排怎么干 |
| 厨师 / 服务员 / 收银员 | **Skill** | 每个人只会一件事，被经理调度 |
| 菜谱 / 操作手册 | **references** | 详细说明书，按需翻看 |
| 厨具 / POS 机 | **Tool** | 被技能使用的工具 |
| 菜单 / 流程图 | **编排总纲** | 一道菜从接单到出餐的标准流程 |
| 餐厅记忆本 | **Memory** | 记住老顾客、上次出过什么问题 |
| 厨房监控 | **Evaluation** | 检查出品质量合不合格 |
| 安全规章 | **Guardrail** | 不能做危险的事（比如用坏掉的食材） |

### 1.2 三个核心概念的精确定义

**AI（人工智能）**
> 会"理解语言+推理+生成内容"的程序。你能用自然语言跟它说话，它能听懂并回应。

**Skill（技能）**
> 一个**被动的、专精的能力单元**。它只会做一件事，不会主动启动，必须被"调用"才会工作。
>
> 类比：计算器是个 Skill，你按"=",它才计算；你不按，它就躺着。

**Agent（智能体）**
> 一个**主动的、有目标的执行者**。给它一个目标，它会自己拆任务、调技能、观察结果、调整策略，直到完成。
>
> 类比：你雇的餐厅经理，你说"今晚有 10 桌宴席"，他自己安排谁备菜、谁上菜、谁收银。

### 1.3 最关键的区分：被动 vs 主动

这是最容易混淆的地方，必须讲透：

```
Skill（技能）              Agent（智能体）
─────────────             ─────────────
被动等调用                  主动驱动
被别人调用才动              自己决定调谁
不会自己启动                自己跑起来
做完就结束                  看结果决定下一步
```

**一个 Skill 再强大，它也不会自己变成 Agent。** 就像一个厨师再厉害，没人叫他做菜，他不会自己开始炒菜。

### 1.4 这套工作区是什么

```
c:\Users\26307\.agents\skills\
                     ↑
                 这里全是 Skill 集合
```

**重要结论**：

- 这个工作区是 **61 个 Skill 的集合**，不是 Agent 集合
- 这里的 `agent-orchestrator` / `agent-runtime-exec` / `agent-builder` 都是**关于 Agent 的 Skill**，不是 Agent 本身
- 真正的 Agent 是**宿主**（Trae 这个 AI 助手本身）——它调用这里的 Skill 来完成任务
- 工作台首次使用时调 `rd-init` 扫描全部 skill，生成 `.workbench-index.json` 索引和完整性报告，让 AI 一目了然地掌握工作台全貌（有哪些 skill、分属哪条流水线、frontmatter 是否规范、references 路径是否完整、哪些 skill 已接入 runtime.yaml）

### 1.5 那"Agent 体系"是什么意思

当文档里说"Agent 体系层 skill"，指的是：**这套 skill 集合加起来，构成了一个完整的 Agent 能力底座**。

有了这套底座，任何宿主（Trae / 其他 AI 助手 / 未来的 agent-loop 程序）都可以调用这些 skill，表现出"像一个 Agent"的行为。

类比：厨房里的厨师/服务员/收银员 + 流程手册 + 记忆本 + 监控 = 一整套"开餐厅的能力底座"。谁是经理（Agent），谁就能用这套底座开餐厅。

---

## 第二章 系统全貌：一张图看懂架构

### 2.1 顶层架构图

```
┌─────────────────────────────────────────────────────────────┐
│                    宿主 Agent（决策大脑）                    │
│   Trae AI 助手 / 未来可替换为 agent-loop 程序                │
│   职责：理解用户目标 → 决策 → 调度 skill → 产出结果          │
└───────────────────────────┬─────────────────────────────────┘
                            │ 调用
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                  编排层（流程大脑）                          │
│                                                             │
│   product-pipeline-master                                    │
│   (产研工作台流水线总纲)                                     │
│                                                             │
│   职责：决定"做什么、按什么顺序、哪些阶段跳过"                │
└───────────────────────────┬─────────────────────────────────┘
                            │ 编译为可执行 workflow
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                  执行层（调度引擎）                          │
│                                                             │
│   workflow-runtime   task-planner   replanner                │
│   (执行 workflow)    (拆任务)       (失败重规划)              │
│                                                             │
│   职责：把流程编译成可执行步骤，按步骤调度                    │
└───────────────────────────┬─────────────────────────────────┘
                            │ 调度具体 skill
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                  能力层（61 个 Skill）                       │
│                                                             │
│   ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐       │
│   │ 业务生成 │ │ 工具调用 │ │ 安全护栏  │ │ 记忆系统  │       │
│   │  skill   │ │  skill   │ │  skill   │ │  skill   │       │
│   └──────────┘ └──────────┘ └──────────┘ └──────────┘       │
│   ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐       │
│   │ 运行时    │ │ 数据体系  │ │ 评测体系  │ │ Agent协同│       │
│   │  skill   │ │  skill   │ │  skill   │ │  skill   │       │
│   └──────────┘ └──────────┘ └──────────┘ └──────────┘       │
│                                                             │
│   职责：每个 skill 做一件专精的事，产出具体文件               │
└─────────────────────────────────────────────────────────────┘
```

### 2.2 数据流：一次完整调用怎么走

以"从需求到可部署系统，完整走一遍产研工作台"为例：

```
用户："帮我做一个电商后台，从需求到部署"
  │
  ▼
[1] 宿主理解目标 → 识别这是"产研工作台"场景
  │
  ▼
[2] 调 product-pipeline-master（编排总纲）
    → 决策：端类型=PC 管理后台, 裁剪=跳过移动端阶段
    → 产出执行顺序：需求澄清→PRD→PRD质量检查→原型→HTML生成→门户→工程蓝图→前端→后端→数据层→集成→测试→部署
  │
  ▼
[3] 调 workflow-runtime（执行引擎）
    → 把执行顺序编译成 workflow.yaml
    → 每个阶段对应一个 step, 阶段间插入 pause(人工确认点)
  │
  ▼
[4] 执行 step 1: 调 brainstorm-product-feature skill
    → 澄清早期功能想法, 评估可行性
    → 产出需求澄清文档 docs/FEATURE_BRAINSTORM.md
    → 调 skill-usage-tracker 记录这次调用
  │
  ▼
[5] ⏸ pause: 人工确认点 1
    → AskUserQuestion: "需求已澄清, 进入 PRD 生成? [进入/回退/终止]"
    → 用户选"进入" → 继续
  │
  ▼
[6] 执行 step 2: 调 generate-system-prd skill
    → 逐章生成企业级 PRD（页面规格/权限/状态机/非功能需求）
    → 产出 docs/PRD.md + output/spec/*.json 工件
  │
  ▼
[7] 执行 step 3: 调 prd-quality-checker skill（质量门禁）
    → 审核 PRD 的目标/用户/范围边界/规则/验收等 15+ 维度
    → 产出 Markdown 门禁报告 → PASS
  │
  ▼
[8] ⏸ pause: 人工确认点 2
    → AskUserQuestion: "PRD 已通过质量门禁, 进入原型设计? [进入/回退/终止]"
    → 用户选"进入" → 继续
  │
  ▼
[9] 执行 step 4: 调 generate-prototype skill
     → 消费上游 JSON 工件, 将 PRD 翻译为 ASCII 布局 + 视觉规范
     → 产出原型页面文档 docs/prototype-spec.md
  │
  ▼
[10] ⏸ pause: 人工确认点 3
     → AskUserQuestion: "原型页面文档已生成, 进入 HTML 生成? [进入/回退/终止]"
     → 用户选"进入" → 继续
  │
  ▼
[11] 执行 step 5: 调 generate-html-pages skill
     → 消费原型页面文档, 判定端类型
     → 路由到 generate-html-pc-admin（PC 管理后台风格）
     → 产出 output/site/pc/ + build-report.json
  │
  ▼
[12] ⏸ pause: 人工确认点 4
     → AskUserQuestion: "HTML 原型已生成, 进入总控门户? [进入/回退/终止]"
     → 用户选"进入" → 继续
  │
  ▼
[13] 执行 step 6: 调 generate-portal skill
     → 消费 build-report.json, 产出总控演示门户（跨端预览+标注）
  │
  ▼
[14] ⏸ pause: 人工确认点 5
     → AskUserQuestion: "需求阶段(PRD+原型+门户)全部完成, 进入工程蓝图规划? [进入/回退/终止]"
     → 用户选"进入" → 继续
  │
  ▼
[15] 执行 step 7: 调 plan-system-implementation skill
     → 由 PRD/原型/仓库生成技术实施蓝图（架构/模块/API 契约/交付增量）
     → 产出 docs/IMPLEMENTATION_PLAN.md
  │
  ▼
[16] ⏸ pause: 人工确认点 6
     → AskUserQuestion: "工程蓝图已就绪, 进入工程实现? [进入/回退/终止]"
     → 用户选"进入" → 继续
  │
  ▼
[17] 执行 step 8: 并行调 implement-frontend / implement-backend / implement-data-layer
     → 前端: 原型转生产级前端（类型化API/可访问性/权限/测试）
     → 后端: 实现 API/领域服务/校验/授权/集成测试
     → 数据层: 实现 schema/migration/constraints/seed/repo
     → 三层并行, 汇聚后继续
  │
  ▼
[18] 执行 step 9: 调 integrate-system skill
     → 前后端+DB+认证+权限+文件+异步任务集成
     → 替换 mock 为真实流程
  │
  ▼
[19] 执行 step 10: 调 test-and-harden-system skill
     → 单元/集成/E2E/安全/可访问性/性能/lint/类型/构建检查
     → 修复阻塞缺陷, 产出验收报告
  │
  ▼
[20] ⏸ pause: 人工确认点 7
     → AskUserQuestion: "系统已验收通过, 进入部署? [进入/回退/终止]"
     → 用户选"进入" → 继续
  │
  ▼
[21] 执行 step 11: 调 package-and-deploy-system skill
     → 容器化/CI/CD/迁移/健康检查/可观测/备份/回滚
     → 或调 web-static-deploy（纯静态前端走 GitHub Pages/Vercel/CloudBase）
  │
  ▼
[22] ⏸ pause: 人工确认点 8（可选 Tool）
     → AskUserQuestion: "产物已部署, 是否提交到 Git / 部署到平台 / 跳过? [提交/部署/跳过]"
     → 选"提交到 Git" → 调 tool-git-ops
     → 选"部署到平台" → 调 tool-deploy-ops
     → 选"跳过" → 结束
  │
  ▼
[23] 完成 → 返回部署 URL + 验收报告路径
```

这是完整产研流水线，分两大阶段：

**需求阶段**（step 1~6）：需求澄清→PRD→质量门禁→原型文档→HTML 生成→门户，产出可演示的需求产物
**落地阶段**（step 7~11）：工程蓝图→前端/后端/数据层→集成→测试→部署，产出可运行系统

两个阶段之间有明确转折点：确认点 5（需求阶段全部完成→进入工程蓝图规划）。

共 8 个人工确认点（含 1 个可选 Tool 确认点）。实际使用中可按需裁剪：
- 只做需求阶段：执行到 step 6 停止（产出 PRD+原型文档+HTML+门户）
- 只做工程蓝图：执行到 step 7 停止
- 只做工程实现：从 step 8 开始
- 只做部署：直接调 package-and-deploy-system 或 web-static-deploy

### 2.3 第二条流水线：AI 游戏生成（game-forge）

工作台不仅有产研流水线，还有**AI 游戏生成流水线**（game-forge），覆盖从选题到可运行游戏的完整链路。

```
用户："帮我做一个游戏"
  │
  ▼
[1] game-forge-master（编排总纲）
    → 决策：引擎选择（Phaser 3 / Pixi.js / 纯 Canvas / Godot 4 / Unity）
    → 裁剪：按游戏类型决定哪些阶段跳过
  │
  ▼
[2] game-topic-brainstorm → game-blueprint → game-spec
    → 选题脑暴 → 一页纸蓝图 → 详细 PRD + TECH_DESIGN
  │
  ▼
[3] ⏸ 人工确认
  │
  ▼
[4] game-art-spec → game-asset-forge
    → 美术规范 + 资源清单 → AI 生图 + 图集打包 + 音频占位
  │
  ▼
[5] ⏸ 人工确认
  │
  ▼
[6] game-code-forge
    → 按 5 引擎之一生成完整可运行工程代码
  │
  ▼
[7] game-integrate（质量门 Gate 4 实跑预检）
    → npm 构建或 godot --headless --export-release 或 unity -batchmode
  │
  ▼
[8] ⏸ 人工确认
  │
  ▼
[9] game-polish（可选）→ 完成
```

**五引擎覆盖**：

| 引擎 | 适用场景 | 代码生成 | 构建命令 | 产物路径 |
|------|---------|---------|---------|---------|
| Phaser 3 | 2D Web 游戏 | TypeScript + Vite | `npm run build` | dist/ |
| Pixi.js | 2D Web 游戏（高性能渲染） | TypeScript + Vite | `npm run build` | dist/ |
| 纯 Canvas | 轻量 2D Web 游戏 | TypeScript + Vite | `npm run build` | dist/ |
| Godot 4 | 2D/3D 桌面游戏 | GDScript 4.x | `godot --headless --export-release` | export/ |
| Unity | 3D 游戏 / 跨平台 | C# | `unity -batchmode -executeMethod` | Build/ |

**关键设计**：
- game-forge-master 统一编排，按游戏类型裁剪阶段
- game-quality-gate 在 4 个关键节点介入做契约校验与实跑预检
- 与产研流水线共享 Agent 体系层（workflow-runtime / skill-runtime / guardrail 等）
- 另有 short-drama-game-adapt skill 支持将短剧/影视 IP 改编为游戏机制

### 2.4 关键架构原则

**原则 1：决策与执行分离**
- 编排总纲做决策（做什么、什么顺序）
- workflow-runtime 做执行（怎么调度、怎么暂停）
- 具体 skill 做产出（生成文件）
- 三层互不替代

**原则 2：人工确认是流程的一部分**
- 不是"全自动跑完才告诉你"
- 关键阶段后必须停下，等人确认
- 这是设计选择，不是能力不足

**原则 3：失败不阻塞**
- 任何 skill 失败，不会让整个系统崩
- 失败 → 降级 → 记录 → 继续

---

## 第三章 Skill 的内部结构：一个 skill 长什么样

### 3.1 标准目录结构

```
某个-skill/
├── SKILL.md          ← 主入口（人读+机读）
├── references/        ← 详细文档（懒加载）
├── scripts/           ← 可执行脚本
└── agents/
    └── openai.yaml    ← 平台配置
```

### 3.2 SKILL.md 的 7 个标准章节

每个 SKILL.md 都按这个结构写，保证一致性：

```
1. 何时调用         → 满足什么条件调我 + 什么场景别调我
2. 核心规范/职责    → 速查表，详细内容引用 references
3. 示例             → 一个完整用法示例
4. scripts 调用方式 → 命令行怎么用 + 退出码
5. references 指引  → 哪个文件什么时候读
6. 关键约束         → 必须遵守的规则（如"只读不写"）
7. 与其他 skill 关系 → 我的上游是谁、下游是谁
```

### 3.3 一个具体例子：skill-runtime

以 `skill-runtime` 为例，看它每个章节是什么：

| 章节 | 内容 |
|------|------|
| 何时调用 | "要统一 skill 运行时行为 / 校验 runtime.yaml"时调用 |
| 核心规范 | runtime.yaml 的字段速查表（timeout/retry/inputs/outputs） |
| 示例 | generate-prototype 的 runtime.yaml 完整示例 |
| scripts | `python validate_runtime.py check --skill xxx` |
| references | runtime-schema.md（字段详细规范）+ degrade-patterns.md（降级模式） |
| 关键约束 | 只读不写、失败不阻塞、声明后必符 schema |
| skill 关系 | 被 workflow-runtime 消费、被 skill-auditor 校验 |

### 3.4 行数控制与懒加载

**为什么 SKILL.md 要控制行数？**

因为 AI 的上下文窗口有限（就像人的短期记忆）。SKILL.md 太长，AI 读不完或读混。

**策略**：

```
SKILL.md（≤300 行，优秀）
  ├── 速查表（一眼看全）
  ├── 流程入口（指向 references）
  └── 关键约束（必须记住）

references/（按需读，不强制全读）
  ├── 详细规范 A
  ├── 详细规范 B
  └── 详细规范 C
```

**懒加载原则**：只读当前需要的，不一次性全读。

类比：你不会进厨房就把所有菜谱全背一遍，而是做哪道菜翻哪本。

---

## 第四章 运行逻辑：一次完整执行的全过程

### 4.1 三个运行模式

**模式 1：人机协同模式（当前主用）**

```
你说一句话目标
  → AI（宿主）理解并决策
  → AI 调用对应 skill 执行
  → 产出后，AI 暂停问你"继续吗"
  → 你确认 → AI 调下一个 skill
  → ...直到完成
```

这是你当前的工作模式。AI 是大脑，你是决策者。

**模式 2：半自动模式（workflow-runtime）**

```
你给目标 + 确认执行
  → workflow-runtime 编译 workflow.yaml
  → 自动按 step 执行
  → 遇到 pause 节点停下问你
  → 你选择 → 继续
  → 直到完成
```

把"每步都要手动调"变成"自动跑、关键点问你"。

**模式 3：全自动模式（未来可选）**

```
给个目标 → agent-loop 自己拆任务、调 skill、观察、调整 → 完成
```

适用场景有限（见第 4.5 节分析）。

### 4.2 人工确认机制的运行逻辑

这是整套系统的**核心设计**，不是可有可无的点缀。

**为什么必须人工确认？**

以完整产研流水线的 8 个确认点为例：

| 确认点 | AI 自动可能出错 | 人工确认的价值 |
|--------|----------------|--------------|
| 1. 需求澄清完成 | 理解偏了方向 | 你看一眼就知道对不对 |
| 2. PRD 质量门禁通过 | 漏了关键需求/规则冲突 | 你比 AI 更懂业务 |
| 3. 原型页面文档已生成 | 页面布局/交互逻辑不对 | 你比 AI 更懂用户习惯 |
| 4. HTML 原型已生成 | HTML 渲染异常/页面缺失 | 你点开看一眼就知道 |
| 5. 需求阶段全部完成→进工程蓝图 | 需求没定清楚就开工落地 | 你确认需求闭环了再进入落地阶段 |
| 6. 工程蓝图已就绪→进工程实现 | 架构方案不合理 | 你评估技术方案可行性 |
| 7. 系统验收通过→进部署 | 测试覆盖不全/有隐藏 bug | 你运行一下就知道 |
| 8. 产物已部署→提交 Git/部署平台（可选 Tool） | 误提交/误部署 | 你确认要提交才提交 |

**确认点的标准动作**（三选项）：

```
阶段产出完成 → 质量门禁 PASS → 简报
  │
  ▼
AskUserQuestion:
  [1] 进入下一阶段（推荐）  ← 默认选项,99% 选这个
  [2] 回退修改              ← 发现问题,回到上一步重做
  [3] 终止                  ← 放弃,保留当前状态
  │
  ▼
按选择执行
```

**例外**：阶段 1（需求澄清/脑暴）可选不设确认点，因为产出简单，用户可直接进入下一阶段。

### 4.3 失败处理：两层防御

**第一层：runtime 层（skill 内部）**

```
skill 执行失败
  → 查 runtime.yaml 的 retry 策略
  → 按 backoff 策略重试（fixed/exponential）
  → 重试 max 次后仍失败 → 查 degrade 降级策略
  → 降级（如用占位图代替生图）→ 继续
```

**第二层：workflow 层（workflow-runtime）**

```
skill 重试+降级都失败
  → 查 workflow.yaml 的 on_fail 策略
  → back_to: 回到某一步重跑（最多 max_retries 次）
  → skip: 跳过继续
  → abort: 终止整个流水线
```

**原则**：能重试就重试，能降级就降级，实在不行才 abort。

### 4.4 数据驱动的自适应闭环

这是 Phase 4 的核心创新，讲透：

**问题**：skill 的 timeout/retry 怎么定？写死了不准怎么办？

**解法**：让数据来调。

```
[第1轮] skill 按默认 timeout=300 跑
         → 实际跑了 500 秒,超时失败
         → skill-usage-tracker 记录:"generate-prototype 跑了 500 秒,失败"

[第2轮] adaptive-tuner 分析数据
         → "generate-prototype 经常超时,建议 timeout=900"
         → 产出 runtime-overrides.yaml(需用户确认)

[第3轮] workflow-runtime 执行前
         → 读 external_overrides → 发现 timeout=900
         → 用 900 秒超时跑 → 成功
         → skill-usage-tracker 记录:"跑了 700 秒,成功"

[循环] 数据持续记录 → adaptive-tuner 持续优化 → 参数持续自适应
```

**三层覆盖优先级**（谁说了算）：

```
1. external_overrides（adaptive-tuner 数据驱动产出）  ← 最高优先级
2. runtime.yaml 本地字段（skill 作者声明的默认值）
3. 默认值（未声明时的兜底,如 timeout=300）          ← 最低
```

**失败不阻塞**：overrides 文件缺失或解析失败 → 标 WARNING → 回退到本地值 → 继续跑。

### 4.5 为什么不做全自动（重要分析）

**表面看**：有了 workflow-runtime + 人工确认点，完全可以写个 agent-loop 自动跑。

**实际不做的理由**：

| 理由 | 说明 |
|------|------|
| 每阶段都要确认 | 确认点之间本来就是单个 skill 一次跑完，自动 loop 只省"输入一句话"的负担 |
| 人工决策质量更高 | AI 不知道"这份 PRD 对不对""这个原型风格好不好"——你知道 |
| 失败需要人判断 | AI 失败时可能走错方向，自动重试可能越走越偏 |
| 业务上下文在用户脑子里 | AI 不知道你的真实需求和偏好 |

**真正适合全自动的场景**（少数）：
- 失败自愈（skill 临时失败，自动重试不需要问你）
- 批量任务（一次跑 10 个目标）
- 长时监控（盯某个东西，有变化才通知你）

**结论**：当前的人机协同模式是最优解。Agent Loop 是可选增强，不是必需品。

---

## 第五章 12 维度体系：完整能力地图

### 5.1 为什么是 12 个维度

一个完整的 Agent 需要很多能力。经过 4 个阶段的建设，我们识别出 **12 个不可省略的能力维度**。

如果缺任何一个，Agent 在某些场景就会"卡住"或"出错"。

### 5.2 12 维度总览

| # | 维度 | 中文名 | 一句话职责 | 代表 skill |
|---|------|--------|-----------|-----------|
| 1 | Model | 模型层 | 管理 prompt 模板，版本化 | prompt-registry |
| 2 | Skill | 技能层 | 标准结构，保证一致性 | 全部 skill |
| 3 | Tool | 工具层 | 封装 Git/CI/部署等操作 | tool-git-ops 等 5 个 |
| 4 | Planning | 规划层 | 拆任务，失败重规划 | task-planner / replanner |
| 5 | Memory | 记忆层 | 知识库，失败案例，会话快照 | project-knowledge-base 等 |
| 6 | Context | 上下文层 | 代码库索引，语义检索 | codebase-rag |
| 7 | Workflow | 工作流层 | 编译可执行 workflow | workflow-runtime |
| 8 | Agent Runtime | 运行时层 | runtime.yaml 契约，多 Agent 执行 | skill-runtime / agent-runtime-exec |
| 9 | Evaluation | 评测层 | skill 质量审查 | skill-auditor |
| 10 | Data | 数据层 | 调用统计，自适应优化 | skill-usage-tracker / adaptive-tuner |
| 11 | Guardrail | 安全层 | 前置拦截，diff 审查 | guardrail / diff-reviewer |
| 12 | Human Feedback | 人机协同层 | 人工确认点，checkpoint 回退 | 编排总纲 + session-snapshot |

> 注：另有 Engineering（工程层）3 个 skill（code-review / debug-fix / refactor）作为产研流水线的可选步骤，独立于 12 维度但被 build-working-system 编排。
>
> 另有工作台元 skill 1 个（rd-init）作为工作台加载器，负责扫描全部 skill 目录、生成索引和完整性报告，独立于 12 维度和业务流水线。

### 5.3 每个维度用比喻讲透

**1. Model（模型层）= 菜谱库**
- 管理每道菜的菜谱（prompt），有版本号
- 第1版菜谱不好吃 → 改第2版 → 可以对比两版差异
- skill: prompt-registry

**2. Skill（技能层）= 厨师操作手册**
- 每个厨师按统一标准做事（SKILL.md 结构一致）
- 保证换个人也能做同样的菜
- skill: 全部

**3. Tool（工具层）= 厨具**
- 锅碗瓢盆（Git/CI/部署工具）
- 厨师（skill）用厨具（tool）做菜
- 厨具默认只读，改东西要确认
- skill: tool-git-ops 等

**4. Planning（规划层）= 餐厅经理的排班**
- 来了 10 桌宴席 → 经理拆成：备菜 / 烹饪 / 上菜 / 收银
- 某环节出问题 → 重新排班
- skill: task-planner / replanner

**5. Memory（记忆层）= 餐厅记忆本**
- 记住老顾客偏好（project-knowledge-base）
- 记录上次出过什么问题（failure-casebook）
- 会话中断能恢复（session-snapshot）
- skill: 3 个

**6. Context（上下文层）= 厨房布局图**
- 知道食材在哪、调料在哪（代码库索引）
- 找东西不用翻箱倒柜（语义检索）
- skill: codebase-rag

**7. Workflow（工作流层）= 出餐流程图**
- 一道菜从接单到出餐的标准步骤
- 可以暂停（等食材解冻）、恢复、跳过（没这道菜）、回退（做坏了重做）
- skill: workflow-runtime

**8. Agent Runtime（运行时层）= 厨师工作守则**
- 每个厨师有工作守则（runtime.yaml）：超时多久、重试几次、失败了怎么办
- 多个厨师协同时有调度器（agent-runtime-exec）
- skill: skill-runtime / agent-runtime-exec

**9. Evaluation（评测层）= 品控检查员**
- 检查出品合不合格（skill 质量）
- 6 个维度：结构 / 一致性 / 健壮性 / 扩展性 / 运行时契约 / 执行后评测
- skill: skill-auditor

**10. Data（数据层）= 经营数据分析**
- 记录每道菜做了多久、失败率（skill-usage-tracker）
- 分析数据 → 建议"这道菜要多给 5 分钟"（adaptive-tuner）
- skill: 2 个

**11. Guardrail（安全层）= 厨房安全规章**
- 动刀前确认（操作分级）
- 过期食材不能用（敏感路径保护）
- 改动后检查有没有问题（diff 审查）
- skill: guardrail / diff-reviewer

**12. Human Feedback（人机协同层）= 老板拍板**
- 关键决策必须老板点头（人工确认点）
- 每做完一步都可以存档回退（checkpoint）
- skill: 编排总纲 + session-snapshot

---

## 第六章 4 阶段演进：怎么一步步建起来的

### 6.1 演进路线图

```
Phase 1          Phase 2          Phase 3          Phase 4
工具齐全          自主运行          数据+协作         自适应+协同
┌──────┐        ┌──────┐         ┌──────┐         ┌──────┐
│ 12   │        │  4   │         │  4   │         │  3   │
│skill │  →     │skill │   →     │skill │   →     │skill │
│      │        │      │         │      │         │      │
└──────┘        └──────┘         └──────┘         └──────┘
+3 扩展          +3 扩展          +2 扩展          +3 扩展

平行扩展:产研流水线(22 skill) + 游戏流水线(11 skill,五引擎) + AI短剧(2 skill) + 工作台元(1 skill: rd-init)
```

> 注：以上 Phase 1-4 的 skill 计数仅统计 Agent 体系层（25 个）。产研业务层（22 个）、游戏流水线（11 个）、AI 短剧（2 个）、工作台元 skill（1 个：rd-init）作为平行业务扩展，独立于 Agent 体系层的 4 阶段演进。

### 6.2 每个阶段解决了什么问题

**Phase 1：工具齐全（"有手有脚"）**

问题：AI 想做很多事，但没有专门的能力。

解决：建了 12 个 skill + 3 个扩展
- Tool 层 5 个：Git/CI/部署/DB/监控操作
- 工程层 4 个：code-review / debug-fix / refactor / diff-reviewer
- 安全层 1 个：guardrail
- 记忆层 2 个：project-knowledge-base / failure-casebook
- 评测层扩展：skill-auditor（5 模式 5 维度）

类比：产研团队招齐了产品经理、前端、后端、QA、运维,配上代码审查和发布规章。

**Phase 2：自主运行（"能自己跑流程"）**

问题：每步都要人手动调 skill，太累。

解决：建了 4 个 skill + 3 个扩展
- skill-runtime：定义 runtime.yaml 契约（每个 skill 声明超时/重试/降级）
- task-planner：拆任务为 task-tree
- replanner：失败时重新规划
- workflow-runtime：把流程编译为可执行 workflow.yaml

关键升级：编排总纲的"执行顺序"可以从文档变成可执行程序。

类比：产研团队有了项目管理系统和迭代排期,不用老板手动指挥每个人。

**Phase 3：数据驱动+智能协作（"有记忆、会协作"）**

问题：skill 调用没记录、代码库无法持久化检索、prompt 没版本管理、多 Agent 无法协同。

解决：建了 4 个 skill + 2 个扩展
- codebase-rag：代码库持久化语义索引
- skill-usage-tracker：记录每次 skill 调用数据
- prompt-registry：prompt 模板版本化管理
- agent-orchestrator：多 Agent 协同协议

类比：产研团队有了工时统计、需求版本管理、多团队协同机制。

**Phase 4：智能自适应+协同运行（"会自我优化"）**

问题：skill 参数写死不准、会话中断无法恢复、多 Agent 协议无法实际执行。

解决：建了 3 个 skill + 3 个扩展
- adaptive-tuner：基于调用数据自动生成参数优化建议
- session-snapshot：会话状态快照与跨会话恢复
- agent-runtime-exec：多 Agent 实际调度执行器

扩展：
- skill-runtime 新增 external_overrides（数据驱动参数覆盖）
- workflow-runtime 接入 adaptive-tuner（自适应闭环）
- agent-orchestrator 接入 agent-runtime-exec（协议落地）

类比：产研团队会根据历史数据自动调整每个任务的预估工时,跨会话/跨天也能恢复进度。

### 6.3 关键设计决策回顾

| 决策 | 选择 | 为什么 |
|------|------|--------|
| 编排 vs 执行 | 分离 | 总纲做决策，runtime 做执行，互不替代 |
| 人工确认 | 强制 | AI 决策质量不够，关键点必须人确认 |
| 失败处理 | 两层 | runtime 层先重试降级，workflow 层再回退跳过 |
| 参数配置 | 三层覆盖 | 数据驱动 > 本地声明 > 默认值 |
| 行数控制 | ≤300 行 | AI 上下文有限，长了读不完 |
| references | 懒加载 | 按需读，不强制全读 |
| checkpoint | 每任务提交 | 支持回退，不怕改坏 |
| 全自动 | 不做 | 人工决策质量更高，全自动价值有限 |

---

## 第七章 系统的边界：什么不做

### 7.1 不做的事

**1. 不做全自动 Agent Loop**
- 理由：每个环节都要人确认，全自动只省"输入一句话"的负担
- 保留：作为可选增强，未来批量/监控场景可用

**2. 不做实时多 Agent 运行**
- 理由：协议已定义（agent-orchestrator），执行器已实现（agent-runtime-exec），但实际多 Agent 场景少
- 保留：复杂任务可启用

**3. 不做 skill 自动生成**
- 理由：skill 需要领域知识，AI 凭空生成质量不够
- 保留：agent-builder 提供框架指导，但不替用户写

**4. 不做强制 runtime.yaml**
- 理由：渐进式接入，高风险 skill 先声明，其他可选
- 保留：未声明的走默认值，不标 FAIL

### 7.2 系统的局限

| 局限 | 说明 | 缓解 |
|------|------|------|
| 依赖宿主 AI | 没有 Trae/AI 助手，skill 不会自己跑 | 这是设计前提 |
| 上下文有限 | AI 读不完超长文档 | SKILL.md ≤300 行 + references 懒加载 |
| 人工瓶颈 | 确认点必须人参与 | 关键点才确认，非每步 |
| 单语言 | 文档和注释为中文 | 可扩展 |

---

## 第八章 附录

### 8.1 Skill 完整清单（61 个）

**产研业务生成层**（22 个，按产研工作流全阶段组织）

| 产研阶段 | skill | 作用 |
|---------|-------|------|
| 需求澄清 | brainstorm-product-feature | 早期功能想法的澄清、可行性评估、隐藏假设检查 |
| 系统规划 | generate-system-prd | 生成企业级 PRD（页面规格/权限/状态机/非功能需求） |
| PRD 质量门禁 | prd-quality-checker | 审核 PRD 的目标/用户/范围/规则/验收等 15+ 维度，产出门禁报告 |
| 工程蓝图 | plan-system-implementation | 由 PRD/原型/仓库生成技术实施蓝图（架构/模块/API 契约/交付增量） |
| 原型生成 | generate-prototype | 将 PRD 翻译为原型页面文档（ASCII 布局+视觉规范+交互逻辑） |
| 原型生成 | generate-html-pages | 消费原型页面文档生成 HTML，判定端类型后路由到 mobile/pc-admin 子 skill |
| 原型生成 | generate-html-mobile | 移动端 HTML 原型（任务型页面：入口/发现/检索/详情/交易/个人中心） |
| 原型生成 | generate-html-pc-admin | PC 管理后台 HTML 原型（vue-admin-plus 风格：深色侧栏+工作区页签） |
| 总控门户 | generate-portal | 生成总控演示门户（三栏布局：导航+跨端预览+PRD 动态标注） |
| 前端实现 | implement-frontend | 将原型转为生产级前端（类型化 API/可访问性/校验/权限/测试） |
| 后端实现 | implement-backend | 实现后端 API/领域服务/校验/授权/审计/集成测试 |
| 数据层 | implement-data-layer | 实现数据库 schema/migration/constraints/seed/repo/事务规则 |
| 系统集成 | integrate-system | 前后端+DB+认证+权限+文件+异步任务+外部服务集成 |
| 测试加固 | test-and-harden-system | 单元/集成/E2E/安全/可访问性/性能/lint/类型/构建检查 |
| 部署交付 | package-and-deploy-system | 容器化/CI/CD/迁移/健康检查/可观测/备份/回滚/发布文档 |
| 部署交付 | web-static-deploy | 静态前端部署（GitHub Pages/Vercel/Netlify/CloudBase/COS） |
| 全流程编排 | product-pipeline-master | 产研工作台流水线总纲（决策+裁剪+人工确认点） |
| 全流程编排 | build-working-system | 可运行系统总编排器（端到端转换 PRD→原型→可运行系统） |
| 前端设计 | frontend-design | 视觉设计指导（排版/配色/组件，避免模板化默认风格） |
| 软著文档 | ruanzhu-doc-generator | 软件著作权申请文档生成（由截图生成 DOCX） |
| 标书方案 | bid-functional-solution | 标书功能建设方案生成（由 PRD/截图生成 DOCX） |
| 操作手册 | screenshot-operation-manual | 由截图/录屏生成操作手册（DOCX/PDF/Markdown/HTML） |

**工作台元 skill**（1 个）

| skill | 作用 |
|-------|------|
| rd-init | 工作台加载器。扫描 skills 目录全部 skill，生成 `.workbench-index.json` 索引和完整性报告（frontmatter 规范/references 路径/runtime.yaml 声明），让 AI 快速掌握工作台全貌。不生成业务产物 |

**AI 游戏生成流水线**（11 个，game-forge，支持五引擎）

| 游戏阶段 | skill | 作用 |
|---------|-------|------|
| 选题脑暴 | game-topic-brainstorm | 从0到1结构化脑暴游戏选题 |
| 游戏蓝图 | game-blueprint | 一页纸定义类型/平台/引擎/玩法/范围 |
| 游戏 PRD | game-spec | 详细 PRD + TECH_DESIGN（玩法/数值/UI/关卡/状态机） |
| 美术规范 | game-art-spec | 美术规范 + ASSET_MANIFEST.json 资源清单 |
| 美术资源 | game-asset-forge | AI 生图 + 图集打包 + 音频占位 |
| 代码生成 | game-code-forge | 五引擎代码生成（Phaser/Pixi/Canvas/Godot/Unity） |
| 集成构建 | game-integrate | npm/godot/unity 构建 + 实跑预检 |
| 效果打磨 | game-polish | 可选，视觉/手感/反馈打磨 |
| 质量门禁 | game-quality-gate | 4 节点契约校验 + 实跑预检 |
| 全流程编排 | game-forge-master | 游戏生成总纲（引擎选择决策树+阶段裁剪） |
| IP 改编 | short-drama-game-adapt | 短剧/影视 IP 改编为游戏机制 |

**AI 短剧**（2 个，均已接入 runtime.yaml 并含失败回退章节）

| skill | 作用 | runtime.yaml | 失败回退 |
|-------|------|--------------|---------|
| ai-short-drama-topic-planner | 短剧选题生成与优化 | timeout=600s, retry=2, 含 inputs/outputs/degrade | 5 类场景：相似度过高/趋势缺失/用户不满意/自检未通过/失败记录，L1-L3 分层回退 |
| ai-short-drama-project-development | 短剧项目开发（13 步流程） | timeout=900s, retry=2, 含 inputs/outputs/degrade | 4 类场景：选题复核未通过/大纲集数不匹配/制作可行性未通过/单步质量不达标，L1-L3 分层回退 |

**Agent 体系层**（25 个，12 维度，支撑所有业务 skill 运行）

| 维度 | skill |
|------|-------|
| Model | prompt-registry |
| Skill | agent-builder（元技能） |
| Tool | tool-git-ops / tool-ci-ops / tool-deploy-ops / tool-db-ops / tool-monitor-ops |
| Planning | task-planner / replanner |
| Memory | project-knowledge-base / failure-casebook / session-snapshot |
| Context | codebase-rag |
| Workflow | workflow-runtime |
| Agent Runtime | skill-runtime / agent-runtime-exec / agent-orchestrator |
| Evaluation | skill-auditor |
| Data | skill-usage-tracker / adaptive-tuner |
| Guardrail | guardrail / diff-reviewer |
| Engineering | code-review / debug-fix / refactor |
| Human Feedback | （融入编排总纲 + session-snapshot） |

### 8.2 术语表

| 术语 | 定义 |
|------|------|
| Skill | 被动的能力单元，被调用才工作 |
| Agent | 主动的执行者，自己驱动完成任务 |
| 宿主 | 调用 skill 的 AI 助手（如 Trae） |
| 编排总纲 | 定义"做什么、什么顺序"的 skill |
| workflow.yaml | 机读的工作流执行计划 |
| runtime.yaml | skill 的运行时元数据契约 |
| external_overrides | adaptive-tuner 产出的数据驱动参数覆盖 |
| 人工确认点 | 关键阶段后的强制暂停，等人选择 |
| checkpoint | 每个任务后的 git 提交，支持回退 |
| 降级 | skill 失败时的兜底策略（如用占位图） |
| 懒加载 | references 按需读取，不强制全读 |

### 8.3 关键文件索引

| 文件 | 作用 |
|------|------|
| WORKBENCH.md | 工作台总览，含 Phase 1-4 + changelog |
| README.md | 完整技能清单 + 分类导航 |
| _shared/validate.ps1 | 15 项防回归校验脚本 |
| _shared/references/schemas/design-tokens.default.json | 全局 UI 设计 token v1.3（单点真理源） |
| .trae/documents/agent-system-upgrade-plan.md | 4 阶段升级详细计划 |
| agent-builder/references/agent-architecture-framework.md | 12 维度架构详解 |
| agent-builder/references/skill-creation-patterns.md | 7 大设计模式详解 |
| agent-builder/references/skill-template.md | 标准 skill 结构模板 |

---

## 结语

这套系统的核心理念：

1. **Skill 是能力底座，不是 Agent** —— 22 个产研业务 skill + 11 个游戏流水线 skill + 2 个 AI 短剧 skill + 25 个 Agent 体系 skill + 1 个工作台元 skill（rd-init）= 61 个能力单元，覆盖产研、游戏、短剧三条业务线，任何宿主都能调用
2. **人机协同是最优模式** —— AI 做执行，人做决策，不是全自动才好
3. **12 维度缺一不可** —— 每个维度解决一类问题，少了就会卡住
4. **失败是常态，系统为失败而设计** —— 重试、降级、回退、不阻塞
5. **数据驱动自适应** —— 参数不是写死的，由数据持续优化
6. **经验沉淀为可复用模式** —— 4 阶段建设经验已沉淀到 agent-builder

**一句话总结**：这是一套"人脑决策 + AI 执行 + skill 能力库 + 数据自适应"的 Agent 系统设计，不是"AI 全自动替代人"的幻想。
