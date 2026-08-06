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

- 这个工作区是 **24 个 Skill 的集合**，不是 Agent 集合
- 这里的 `agent-orchestrator` / `agent-runtime-exec` / `agent-builder` 都是**关于 Agent 的 Skill**，不是 Agent 本身
- 真正的 Agent 是**宿主**（Trae 这个 AI 助手本身）——它调用这里的 Skill 来完成任务

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
│   game-forge-master      product-pipeline-master            │
│   (游戏流水线总纲)        (产品工作台流水线总纲)              │
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
│                  能力层（24 个 Skill）                       │
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

以"用 Phaser 生成一个躲避障碍小游戏"为例：

```
用户："生成一个躲避障碍小游戏"
  │
  ▼
[1] 宿主理解目标 → 识别这是"游戏生成"场景
  │
  ▼
[2] 调 game-forge-master（编排总纲）
    → 决策：引擎=Phaser, 类型=2D, 裁剪=跳过 3D 阶段
    → 产出执行顺序：蓝图→规格→美术→代码→集成→打磨
  │
  ▼
[3] 调 workflow-runtime（执行引擎）
    → 把执行顺序编译成 workflow.yaml
    → 每个阶段对应一个 step, 阶段间插入 pause(人工确认点)
  │
  ▼
[4] 执行 step 1: 调 game-blueprint skill
    → 产出 docs/GAME_BLUEPRINT.md
    → 调 skill-usage-tracker 记录这次调用
  │
  ▼
[5] 执行 step 2: 调 game-quality-gate(Gate 0)
    → 校验蓝图合规性 → PASS
  │
  ▼
[6] ⏸ pause: 人工确认点 1
    → AskUserQuestion: "蓝图已生成, 进入规格设计? [进入/回退/终止]"
    → 用户选"进入" → 继续
  │
  ▼
[7] 执行 step 3: 调 game-spec skill → 产出 PRD + 技术设计
[8] 执行 step 4: 调 game-art-spec → 产出美术规范
[9] 执行 step 5: 调 game-asset-forge + game-code-forge (并行)
    → 产出 assets/ 和 src/
[10] ⏸ pause: 人工确认点 → 用户确认
[11] 执行 step 6: 调 game-integrate → 产出 dist/ 可运行游戏
[12] 完成 → 返回最终产物路径
```

### 2.3 关键架构原则

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
| 示例 | game-asset-forge 的 runtime.yaml 完整示例 |
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

| 场景 | AI 自动可能出错 | 人工确认的价值 |
|------|----------------|--------------|
| 生成蓝图 | 方向跑偏 | 你看一眼就知道对不对 |
| 生成美术规范 | 风格不对 | 你比 AI 更懂审美 |
| 代码集成完成 | 跑不起来 | 你运行一下就知道 |
| PRD 完成 | 漏了关键需求 | 你比 AI 更懂业务 |

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

**例外**：阶段 1（脑暴/蓝图）可选不设确认点，因为产出简单，用户可直接进入下一阶段。

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
         → skill-usage-tracker 记录:"game-asset-forge 跑了 500 秒,失败"

[第2轮] adaptive-tuner 分析数据
         → "game-asset-forge 经常超时,建议 timeout=900"
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
| 人工决策质量更高 | AI 不知道"这个蓝图对不对""这个美术风格好不好"——你知道 |
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
```

### 6.2 每个阶段解决了什么问题

**Phase 1：工具齐全（"有手有脚"）**

问题：AI 想做很多事，但没有专门的能力。

解决：建了 12 个 skill + 3 个扩展
- Tool 层 5 个：Git/CI/部署/DB/监控操作
- 工程层 4 个：code-review / debug-fix / refactor / diff-reviewer
- 安全层 1 个：guardrail
- 记忆层 2 个：project-knowledge-base / failure-casebook
- 评测层扩展：skill-auditor（5 模式 5 维度）

类比：厨房买齐了厨师、服务员、收银员、监控、安全规章。

**Phase 2：自主运行（"能自己跑流程"）**

问题：每步都要人手动调 skill，太累。

解决：建了 4 个 skill + 3 个扩展
- skill-runtime：定义 runtime.yaml 契约（每个 skill 声明超时/重试/降级）
- task-planner：拆任务为 task-tree
- replanner：失败时重新规划
- workflow-runtime：把流程编译为可执行 workflow.yaml

关键升级：编排总纲的"执行顺序"可以从文档变成可执行程序。

类比：餐厅经理有了排班系统，不用老板手动指挥每个厨师。

**Phase 3：数据驱动+智能协作（"有记忆、会协作"）**

问题：skill 调用没记录、代码库无法持久化检索、prompt 没版本管理、多 Agent 无法协同。

解决：建了 4 个 skill + 2 个扩展
- codebase-rag：代码库持久化语义索引
- skill-usage-tracker：记录每次 skill 调用数据
- prompt-registry：prompt 模板版本化管理
- agent-orchestrator：多 Agent 协同协议

类比：餐厅有了数据分析、菜谱版本管理、多经理协同机制。

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

类比：餐厅会根据数据自动调整每道菜的烹饪时间，经理换班也能无缝接手。

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

### 8.1 24 个 skill 完整清单

**业务生成层**（不在 12 维度内，是业务 skill）
- generate-system-prd / generate-prototype / generate-html-pages / generate-portal
- generate-html-mobile / generate-html-pc-admin
- game-blueprint / game-spec / game-art-spec / game-asset-forge / game-code-forge / game-integrate / game-polish / game-quality-gate
- game-forge-master / game-topic-brainstorm / short-drama-game-adapt
- product-pipeline-master / build-working-system
- implement-frontend / implement-backend / implement-data-layer / integrate-system / test-and-harden-system / package-and-deploy-system
- plan-system-implementation / brainstorm-product-feature / frontend-design / ruanzhu-doc-generator / bid-functional-solution / screenshot-operation-manual
- ai-short-drama-topic-planner

**Agent 体系层 24 个**（12 维度）

| 维度 | skill |
|------|-------|
| Model | prompt-registry |
| Skill | agent-builder（元技能） |
| Tool | tool-git-ops / tool-ci-ops / tool-deploy-ops / tool-db-ops / tool-monitor-ops |
| Planning | task-planner / replanner |
| Memory | project-knowledge-base / failure-casebook / session-snapshot |
| Context | codebase-rag |
| Workflow | workflow-runtime |
| Agent Runtime | skill-runtime / agent-runtime-exec |
| Evaluation | skill-auditor |
| Data | skill-usage-tracker / adaptive-tuner |
| Guardrail | guardrail / diff-reviewer |
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
| _shared/validate.ps1 | 14 项防回归校验脚本 |
| _shared/design-tokens.json | 全局 UI 设计 token（单点真理源） |
| .trae/documents/agent-system-upgrade-plan.md | 4 阶段升级详细计划 |
| agent-builder/references/agent-architecture-framework.md | 12 维度架构详解 |
| agent-builder/references/skill-creation-patterns.md | 7 大设计模式详解 |
| agent-builder/references/skill-template.md | 标准 skill 结构模板 |

---

## 结语

这套系统的核心理念：

1. **Skill 是能力底座，不是 Agent** —— 24 个 skill 构成完整能力，任何宿主都能调用
2. **人机协同是最优模式** —— AI 做执行，人做决策，不是全自动才好
3. **12 维度缺一不可** —— 每个维度解决一类问题，少了就会卡住
4. **失败是常态，系统为失败而设计** —— 重试、降级、回退、不阻塞
5. **数据驱动自适应** —— 参数不是写死的，由数据持续优化
6. **经验沉淀为可复用模式** —— 4 阶段建设经验已沉淀到 agent-builder

**一句话总结**：这是一套"人脑决策 + AI 执行 + skill 能力库 + 数据自适应"的 Agent 系统设计，不是"AI 全自动替代人"的幻想。
