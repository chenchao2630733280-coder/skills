---
name: "task-planner"
description: "通用任务规划器 skill。把复杂需求拆解为子任务树+依赖关系+优先级,产出 task-tree.json。当编排总纲外有复杂需求需规划、或用户要'拆解任务/规划执行步骤'时调用。区别于编排总纲的'流水线阶段裁剪',本 skill 面向任意任务的通用规划。"
---

# task-planner — 通用任务规划器

task-planner 是 AI Agent 体系第二阶段升级的 **Planning 层 skill**。它把任意复杂需求拆解为
**子任务树 + 依赖关系 + 优先级**,产出机读的 `task-tree.json` 和人读的 `task-plan.md`。

- **只规划不执行**:本 skill 只产出任务树,不真正调用下游 skill 完成任务。
- **通用面向**:不绑定固定流水线,任意需求都能拆。
- **产物可互转**:`task-tree.json` 与 `plan-system-implementation` 的 `task-board.json` 结构兼容,可互转。

## 一、何时调用

满足以下任一条件即调用本 skill:

1. **复杂需求需规划**:用户给出一个难以一次完成的需求,需要先拆解再执行。
2. **用户要"拆解任务/规划执行步骤"**:用户明确要求把需求拆成步骤、子任务、执行计划。
3. **编排总纲外的任务**:需求不属于产品流水线(product-pipeline-master)或游戏流水线(game-forge-master)的固定阶段,需动态规划。
4. **多 skill 协同的前置规划**:一个需求要串联多个 skill,需先规划依赖与并行关系再分发。

> 若需求本身就是产品/游戏流水线的一个固定阶段(如"生成 PRD""生成游戏代码"),直接走对应阶段 skill,**不**经本 skill 规划。

## 二、与相关 skill 的分工

| 维度 | task-planner(本 skill) | plan-system-implementation | 编排总纲(product/game-pipeline-master) |
|------|----------------------|----------------------------|------------------------------------|
| 面向 | **任意任务**通用规划 | **工程实施**专精规划 | **固定流水线**阶段裁剪 |
| 输入 | 任意需求文本 | PRD/页面规格/原型/代码仓库 | 流水线请求(端类型/范围) |
| 产出 | task-tree.json + task-plan.md | implementation-plan + task-board.json | 阶段执行序列 |
| 是否执行 | 只规划,不执行 | 规划+技术决策,不执行代码 | 裁剪并串联阶段 skill 执行 |
| 依赖知识 | 通用 WBS/依赖规则 | 工程技术栈/架构/ADR | 流水线阶段定义 |

**核心区分**:
- 本 skill 与 `plan-system-implementation` 都做"规划",但前者**任意任务**(可含非工程任务,如运营、迁移、内容生产),后者**专精工程实施**(必须有 PRD/代码仓库作输入,产出含技术栈决策与 ADR)。
- 本 skill 与编排总纲都做"任务编排",但总纲是**固定流水线裁剪**(阶段已预定义),本 skill 是**任意需求动态拆解**(WBS 模式按需求特征动态选择)。

## 三、拆解流程

```
接收需求 → 识别任务类型 → 选择 WBS 模式 → 拆解为子任务 → 标注依赖 → 标注优先级 → 产出
```

### 3.1 接收需求
- 读取需求文本(用户直接给出或 `plan --requirement` 传入)。
- 可选读取上下文文件(`--context`),补充背景。

### 3.2 识别任务类型
- 判断属于:产品功能开发 / 系统建设 / 流程类任务 / 内容生产 / 迁移运维 / 其他。
- 任务类型决定 WBS 模式选择(见第四节)。

### 3.3 选择 WBS 模式
- 对照 `references/wbs-patterns.md` 的决策表选择主模式。
- 混合特征时选主模式,局部混合(如按层为主、层内按功能)。

### 3.4 拆解为子任务
- 按所选模式从根逐层向下拆,直到叶子任务。
- **粒度红线**:叶子任务必须能在 **1 次 skill 调用**内完成;否则继续拆。

### 3.5 标注依赖
- 对照 `references/dependency-rules.md` 识别数据依赖 / 控制依赖 / 资源依赖。
- 写入每个任务的 `depends_on`;无资源冲突的同层任务互写 `parallel_with`。

### 3.6 标注优先级
- P0:关键路径,阻塞后续任务。
- P1:重要但非阻塞。
- P2:可延后/锦上添花。

### 3.7 产出
- 写 `task-tree.json`(机读,见第六节规范)。
- 写 `task-plan.md`(人读 Markdown,含任务树视图与执行顺序)。
- 运行 `topology` 子命令校验依赖无环、引用完整。

## 四、WBS 拆解模式

三种主模式,详见 `references/wbs-patterns.md`:

| 模式 | 适用 | 树形 |
|------|------|------|
| 按功能拆解 | 产品功能开发 | 根 → 功能模块 → 子功能 → 实现任务 |
| 按层拆解 | 系统建设 | 根 → 数据层 → 后端层 → 前端层 → 集成层 |
| 按时序拆解 | 流程类任务 | 根 → 阶段1 → 阶段2 → 阶段N |

选择决策:
- 多个独立功能可并行 → 按功能拆解。
- 涉及多层技术架构 → 按层拆解。
- 有严格先后阶段 → 按时序拆解。
- 混合 → 选主模式,局部混合。

> 选错模式会导致依赖混乱、并行度低;若拆解后发现大量跨层回依赖,回退重选。

## 五、依赖识别规则

三类依赖,详见 `references/dependency-rules.md`:

1. **数据依赖**:B 需要 A 的产物作输入 → `depends_on` 加 A。
2. **控制依赖**:B 必须等 A 完成(质量门/决策门) → `depends_on` 加 A。
3. **资源依赖**:B 与 A 共用独占资源不能并行 → 串行(标 `depends_on` 或移出 `parallel_with`)。

识别顺序:先数据依赖(最常见),再控制依赖,最后资源依赖。未命中任何依赖的任务可与同层并行。

> 环状依赖会导致拓扑排序失败,需拆出公共前置任务打破环。

## 六、task-tree.json 规范

完整 Schema 见 `references/task-tree-schema.md`。核心字段:

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `version` | string | 是 | 固定 `"1.0"` |
| `root` | object | 是 | `{ id, title, complexity }` |
| `tasks` | array | 是 | 子任务数组 |

每个 task 元素:

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `id` | string | 是 | 唯一 id,建议 `T-001` |
| `title` | string | 是 | 任务标题(动宾结构) |
| `priority` | string | 是 | `P0` / `P1` / `P2` |
| `depends_on` | string[] | 否 | 前置依赖 id 数组 |
| `parallel_with` | string[] | 否 | 可并行任务 id 数组 |
| `assigned_skill` | string | 否 | 建议承接 skill 名 |
| `est_complexity` | string | 是 | `★` ~ `★★★★★` |
| `est_duration` | string | 否 | 预估耗时(可选) |

约束:`id` 唯一;`depends_on` 必须引用已存在任务;不得成环。

## 七、scripts 调用方式

脚本 `scripts/plan_tasks.py`,argparse 双子命令:

### 7.1 plan — 拆解任务

```
python scripts/plan_tasks.py plan --requirement "需求描述" [--context 上下文文件] [--output 输出目录]
```

- 读取需求文本,基于 WBS 模式生成 `task-tree.json` 脚手架与 `task-plan.md`。
- **实际拆解由 AI 在本 SKILL.md 引导下完成**:脚本提供框架与模板,负责格式校验。
- `--output` 默认当前目录,产物写入该目录的 `task-tree.json` 与 `task-plan.md`。

### 7.2 topology — 拓扑排序

```
python scripts/plan_tasks.py topology --input task-tree.json
```

- 读取 `task-tree.json`,校验 Schema、引用完整性、依赖无环。
- 按 `depends_on` 做拓扑排序,输出分层执行顺序(同层可并行)。
- 检测到环时退出码 1 并报错。

### 7.3 退出码

| 场景 | exit code |
|------|-----------|
| 成功 | 0 |
| 校验失败(Schema/引用/环) | 1 |
| 参数错误 | 2 |

## 八、references 使用指引

| 文件 | 用途 | 何时查 |
|------|------|--------|
| `references/wbs-patterns.md` | WBS 拆解模式定义与决策表 | 第三节"选择 WBS 模式"阶段 |
| `references/dependency-rules.md` | 依赖识别规则与流程 | 第五节"标注依赖"阶段 |
| `references/task-tree-schema.md` | task-tree.json 完整 Schema | 校验产出物时 |

引用文件为只读参考,不得修改;实际产物写入调用方指定的输出目录。

## 九、关键约束

1. **拆解粒度**:叶子任务可在 **1 次 skill 调用**内完成;超出则继续拆。这是硬约束。
2. **只规划不执行**:本 skill 不调用下游 skill 完成任务,只产出任务树。执行由上层编排或用户分发。
3. **产物格式兼容**:`task-tree.json` 与 `plan-system-implementation` 的 `task-board.json` 兼容可互转(字段映射见 schema 文件第六节)。
4. **不臆造依赖**:依赖必须能追溯到"数据/控制/资源"之一的具体依据;无依据不标依赖。
5. **不重复 plan-system-implementation**:本 skill 不做技术栈决策、ADR、接口契约设计;这些属于工程实施规划。
6. **需求不清先澄清**:需求模糊时先向用户澄清范围与目标,不强行拆解。
7. **中文产出**:task-tree.json 的 title、task-plan.md 正文用中文。

## 十、task-tree.json schema 摘要

示例(完整 Schema 见 `references/task-tree-schema.md`):

```json
{
  "version": "1.0",
  "root": {
    "id": "ROOT",
    "title": "搭建博客系统",
    "complexity": "medium"
  },
  "tasks": [
    {
      "id": "T-001",
      "title": "设计文章表结构",
      "priority": "P0",
      "depends_on": [],
      "parallel_with": ["T-002"],
      "assigned_skill": "implement-data-layer",
      "est_complexity": "★★",
      "est_duration": "30min"
    },
    {
      "id": "T-002",
      "title": "设计用户表结构",
      "priority": "P0",
      "depends_on": [],
      "parallel_with": ["T-001"],
      "assigned_skill": "implement-data-layer",
      "est_complexity": "★★"
    },
    {
      "id": "T-003",
      "title": "实现创建文章接口",
      "priority": "P0",
      "depends_on": ["T-001"],
      "parallel_with": [],
      "assigned_skill": "implement-backend",
      "est_complexity": "★★★"
    },
    {
      "id": "T-004",
      "title": "实现文章列表页",
      "priority": "P1",
      "depends_on": ["T-003"],
      "parallel_with": [],
      "assigned_skill": "implement-frontend",
      "est_complexity": "★★★"
    }
  ]
}
```

## 十一、质量检查清单

产出 `task-tree.json` 后逐项自评,全部通过方可交付:

- [ ] `version` 为 `"1.0"`,`root` 含 id/title/complexity。
- [ ] 每个 task 含必填字段:id/title/priority/est_complexity。
- [ ] `id` 在 tasks 内唯一,不与 root.id 冲突。
- [ ] `depends_on` 中所有 id 都能在 tasks 中找到(引用完整)。
- [ ] `depends_on` 无环(`topology` 子命令通过)。
- [ ] 叶子任务粒度符合"1 次 skill 调用可完成"红线。
- [ ] 优先级合理:关键路径任务标 P0,非阻塞任务不误标 P0。
- [ ] `parallel_with` 仅用于确实无资源冲突的可并行任务。
- [ ] `assigned_skill` 指向真实存在的 skill,或显式为 `null` 待分配。
- [ ] task-plan.md 与 task-tree.json 内容一致(人读视图无遗漏任务)。
- [ ] 与 plan-system-implementation 的 task-board.json 字段可互转,无结构冲突。
