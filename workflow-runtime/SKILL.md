---
name: "workflow-runtime"
description: "工作流执行引擎 skill。把编排总纲的执行顺序转为可执行 workflow.yaml,支持暂停/恢复/跳过/回退/并行调度。当要把流水线从'文档描述'升级为'可执行工作流',或要驱动 task-tree 执行时调用。本身是执行引擎,不产出业务文件。"
---

# workflow-runtime — 工作流执行引擎

workflow-runtime 是 AI Agent 体系第二阶段升级的 **Workflow 可执行化层 skill**。它把编排总纲
(如 `game-forge-master` §七、`product-pipeline-master` §八)的"执行顺序"文档编译为机读的
`workflow.yaml`,并提供执行器按步骤调度、暂停/恢复/跳过/回退/并行。

- **执行引擎,不产出业务文件**:本 skill 只产出 `workflow.yaml` 与执行轨迹(`workflow-exec-report.json`),
  不产出 PRD/代码/美术等业务产物(那些由被调度的下游 skill 产出)。
- **编译 + 执行分离**:`compile_workflow.py` 负责编译,`run_workflow.py` 负责执行。
- **与人工确认点兼容**:总纲的"⏸ 人工确认点"编译为 `type=pause` 步骤,执行时暂停等用户确认。

## 一、何时调用

满足以下任一条件即调用本 skill:

1. **流水线可执行化**:用户要把流水线从"文档描述的执行顺序"升级为"可执行工作流"。
   - 如:"把 game-forge-master 的执行顺序编译成可执行的 yaml"
   - 如:"给 product-pipeline-master 加一个可运行的工作流"
2. **驱动 task-tree 执行**:`task-planner` 产出 `task-tree.json` 后,要把它转为可执行工作流并调度。
3. **动态调度**:执行中要根据用户选择(暂停点)动态决定下一步,而非固定线性执行。
4. **失败回退编排**:要配置"质量门 FAIL 则回退到某阶段重跑"的回退策略。

**不要**在以下场景调用:
- 用户要直接生成 PRD/代码/美术(走对应阶段 skill,本 skill 只调度不产出业务文件)
- 用户只是问"workflow.yaml 怎么写"(纯咨询,直接读 `references/workflow-yaml-schema.md`)
- 用户要创建新 skill(用 `skill-creator`)
- 用户要拆解任务规划(用 `task-planner`,本 skill 消费其产物而非替代它)

## 二、与编排总纲的关系

| 维度 | 编排总纲(game/product-pipeline-master) | workflow-runtime(本 skill) |
|------|--------------------------------------|--------------------------|
| 职责 | **决策**:引擎选择、阶段裁剪、阶段定义 | **执行**:调度、暂停、恢复、回退 |
| 产出 | 阶段执行序列(文档描述) | workflow.yaml(机读)+ exec-report(轨迹) |
| 何时介入 | 流水线启动时决策"跑哪些阶段" | 决策后把执行顺序编译为可执行工作流 |
| 是否替代对方 | 否(总纲是决策大脑) | 否(本 skill 是执行手脚,不替代总纲) |

**职责分离原则**:
- 总纲决定"做什么、按什么顺序、哪些阶段裁剪"——这是业务决策。
- workflow-runtime 决定"怎么调度执行、何时暂停、失败怎么回退"——这是执行机制。
- 本 skill **不替代编排总纲**:总纲的引擎选择决策树、阶段裁剪规则、失败回退策略仍由总纲定义;
  本 skill 只把总纲的决策结果编译为可执行工作流并按其调度。

调用流程:`用户请求 → 编排总纲决策(裁剪/引擎) → workflow-runtime 编译执行顺序为 workflow.yaml → run_workflow.py 调度执行`

## 三、workflow.yaml 规范

workflow.yaml 是机读的工作流执行计划,顶层字段:`name`(必填) / `source` / `version` / `steps[]`(必填)。
每个 step 含以下字段:

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `id` | string | 是 | 步骤唯一标识(如 `s1-blueprint`/`pause1`) |
| `type` | enum | 否 | `skill`(默认,调用 skill) / `pause`(人工确认暂停点) |
| `skill` | string | type=skill 时必填 | 要调用的 skill 名(如 `game-blueprint`) |
| `args` | object | 否 | 传给 skill 的参数键值对 |
| `outputs` | array | 否 | 预期产物路径列表 |
| `on_fail` | object | 否 | 失败处理:`{action: back_to/skip/abort, target, max_retries}` |
| `next` | string | 否 | 下一步 step id;缺省按数组顺序 |
| `parallel_with` | string | 否 | 并行执行的 step id(双向声明) |
| `runtime` | string | 否 | 引用的 runtime.yaml 路径(skill-runtime 契约) |
| `confirm` | object | type=pause 时必填 | AskUserQuestion 配置:`{question, options[]}` |
| `title` | string | 否 | 步骤标题(人读) |
| `optional` | boolean | 否 | 仅 type=pause 时有意义;默认 false;true 表示可选暂停点(允许跳过);false 表示强制暂停 |

完整字段规范、JSON Schema 与约束见 `references/workflow-yaml-schema.md`。

## 四、workflow.yaml 示例

以下示例由 `game-forge-master` §七的阶段 1~2 编译而来(含 Gate 0 + 人工确认点 1):

```yaml
name: game-forge-pipeline
source: game-forge-master §七执行顺序
version: "1.0"
steps:
  - id: s1-blueprint
    type: skill
    title: 生成游戏蓝图
    skill: game-blueprint
    outputs:
      - docs/GAME_BLUEPRINT.md
    on_fail: { action: abort }
    next: s1-gate0

  - id: s1-gate0
    type: skill
    title: Gate 0 蓝图门
    skill: game-quality-gate
    args: { gate: 0 }
    outputs:
      - docs/GATE_0_REPORT.md
    on_fail: { action: back_to, target: s1-blueprint, max_retries: 3 }
    next: pause1

  - id: pause1
    type: pause
    title: 人工确认点 1
    confirm:
      question: Gate 0 已 PASS,是否进入规格设计?
      options:
        - { label: 进入规格设计, next: s2-spec }
        - { label: 回退修改蓝图, next: s1-blueprint }
        - { label: 终止流水线, next: __end__ }
```

阶段 4 的"并行调用 game-asset-forge 和 game-code-forge"编译为 `parallel_with` 双向声明,
完整并行示例见 `references/workflow-yaml-schema.md` §八。

## 五、执行语义

执行语义定义见 `references/execution-semantics.md`,核心机制:

- **暂停(pause)**:遇到 `type=pause` 步骤时停止,保存状态,等用户确认。
  pause 节点对应一次 AskUserQuestion 调用,选项由 `confirm.options` 定义。
- **恢复(resume)**:用户在暂停点选择后,按 `option.next` 跳转继续执行。
- **跳过(skip)**:裁剪阶段时跳过该 step;或 `on_fail.action=skip` 失败后跳过继续。
- **回退(back_to)**:`on_fail.action=back_to` 失败后回到 `target` 指定的 step 重跑,
  超过 `max_retries`(默认 3)则升级为 abort。典型场景:质量门 FAIL 则回到对应阶段 skill 修复。
- **并行(parallel_with)**:同组步骤同时调度,等全部完成才继续 `next`(汇聚点)。
- **runtime 引用**:step 的 `runtime` 字段引用 skill 的 runtime.yaml(skill-runtime 契约),
  执行前读取 `timeout`/`retry`/`degrade` 等元数据。runtime 层重试与降级用尽后才上升到
  workflow 层的 `on_fail` 处理(两层失败处理关系见 `references/execution-semantics.md` §九)。

状态机:`PENDING → RUNNING → DONE/FAILED/SKIP/PAUSED`,失败回退走 `RETRYING`,超限走 `ABORTED`。

## 六、scripts 调用方式

### 6.1 compile_workflow.py — 编译工作流

```
python scripts/compile_workflow.py compile-from-master \
  --master game-forge-master/SKILL.md --section 七 --output workflow.yaml

python scripts/compile_workflow.py compile-from-tasktree \
  --input task-tree.json --output workflow.yaml

python scripts/compile_workflow.py validate --input workflow.yaml
```

- `compile-from-master`:解析总纲 SKILL.md 的执行顺序章节,识别"调用 `xxx` skill"模式、
  "⏸ 人工确认点"模式、"**并行**调用"模式、"FAIL 则回 N"模式,转为 workflow.yaml 步骤。
  脚本识别基本模式并产出框架;`confirm.next` 与 `back_to.target` 的精确绑定由 AI 在本 SKILL.md
  引导下完成(脚本标 `__TODO__` 占位)。
- `compile-from-tasktree`:把 task-tree 的 tasks 转为 workflow steps,`depends_on` 转为 `next`,
  `parallel_with` 转为 step 的 `parallel_with`(双向绑定)。
- `validate`:校验 workflow.yaml 字段符合 schema(用 PyYAML 解析,引用 `references/workflow-yaml-schema.md`)。

### 6.2 run_workflow.py — 执行工作流

```
python scripts/run_workflow.py run --input workflow.yaml --dry-run
python scripts/run_workflow.py run --input workflow.yaml
python scripts/run_workflow.py resume --state workflow-state.json --workflow workflow.yaml --choice 1
python scripts/run_workflow.py status --state workflow-state.json
```

- `run --dry-run`:干跑模式,只输出执行计划(步骤序列、并行组、暂停点),不实际调用 skill。
- `run`:实际执行,逐 step 调度;遇到 pause 节点输出"暂停点:xxx"并保存状态到 `workflow-state.json`。
- `resume`:从暂停点恢复,`--choice` 指定用户选择的选项序号(1-based),按 `option.next` 跳转。
- `status`:查询当前执行状态(暂停节点、已完成步骤、待确认选项)。
- 执行轨迹写入 `workflow-exec-report.json`(每步完成后追加,暂停时保留,失败不丢失)。

### 6.3 退出码

| 场景 | compile_workflow.py | run_workflow.py |
|------|---------------------|-----------------|
| 成功 | 0 | 0(含正常暂停) |
| 校验失败 | 1 | 1(执行失败/异常) |
| 参数错误 | 2 | 2 |

## 七、与第 1 批 skill 的协作

| skill | 关系 | 协作方式 |
|-------|------|---------|
| `skill-runtime` | 契约消费方 | workflow.yaml 的 step.`runtime` 字段引用 skill 的 runtime.yaml;执行前读 `timeout`/`retry`/`degrade`。runtime.yaml schema 见 `../skill-runtime/references/runtime-schema.md` |
| `task-planner` | 上游消费方 | `compile-from-tasktree` 把 task-planner 的 `task-tree.json` 转为 workflow.yaml;`depends_on`→`next`,`parallel_with`→step.`parallel_with` |
| `skill-usage-tracker` | 数据写入方 | 执行 workflow.yaml 时,每步 skill 调用前后调 `record` 记录调用数据(耗时/状态/产物);分配 call_id 贯穿执行链路,见 §十二 |
| `adaptive-tuner` | 覆盖方 | 执行前可选调 adaptive-tuner 获取 `runtime-overrides.yaml`,把 overrides 中的 timeout/retry 合并到 step 的 runtime 参数(Phase 4 新增,见 §十三) |

调用链示例:
```
task-planner 产出 task-tree.json
  → compile_workflow.py compile-from-tasktree 转为 workflow.yaml
  → run_workflow.py run 调度执行(各 step 调用 assigned_skill)
  → 每个 skill 的 runtime.yaml 提供运行时契约(timeout/retry/degrade)
```

## 八、失败处理

1. **两层失败处理**:
   - runtime 层(skill 内部):`timeout` 超时 / `retry` 重试 / `degrade` 降级 — 由 skill-runtime 定义。
   - workflow 层(步骤间):`on_fail.back_to` / `skip` / `abort` — 由本 skill 定义。
   - runtime 层重试与降级用尽后,才上升到 workflow 层的 `on_fail`。
2. **失败时调 replanner 重规划**:若 `on_fail=abort` 或回退超限,可触发重规划——
   重新评估剩余步骤是否需要调整(如裁剪后续阶段、更换 skill)。重规划由编排总纲或上层 agent 决策。
   (注:replanner 为手动触发工具,`run_workflow.py` 在 `on_fail=abort` 或回退超限时输出提示
   "建议运行 `replanner replan --input task-tree.json --failure <失败信息>`",不自动调用。)
3. **保留执行轨迹**:失败时 `workflow-exec-report.json` 不丢失,写入 ABORTED 记录与失败原因,
   便于复盘与 `failure-casebook` 记录。
4. **failure-casebook 记录**:回退触发后,失败时显式调用 `failure-casebook` record 子命令记录失败码 + 修复方法,
   下次同名 skill 执行前注入预防提示(与 skill-runtime §八 协作)。
5. **失败不阻塞**:workflow 层失败时 `run_workflow.py` 退出码 1,但执行轨迹已保存,
   调用方可根据轨迹决定是否 resume 或重规划,不强制中断整个 agent 会话。

## 九、references 使用指引

| 文件 | 用途 | 何时查 |
|------|------|--------|
| `references/workflow-yaml-schema.md` | workflow.yaml 完整字段规范 + JSON Schema + 示例 | (1) 用户问"workflow.yaml 字段怎么写";(2) `compile_workflow.py validate` 校验时;(3) 编译产物自评时 |
| `references/execution-semantics.md` | 暂停/恢复/跳过/回退/并行语义 + 状态机 + 执行轨迹规范 | (1) `run_workflow.py` 执行时对照行为;(2) 用户问"暂停/回退怎么工作";(3) 配置 `on_fail` 策略时 |

两份 references 均为**懒加载**:仅在需要时读取,不强制调用方一次性全读。
引用文件为只读参考,不得修改;实际产物写入调用方指定的输出目录。

## 十、关键约束

1. **不替代编排总纲**:本 skill 是执行引擎,不做引擎选择/阶段裁剪等业务决策(那是总纲的职责)。
   总纲决策后,本 skill 把决策结果编译为可执行工作流。
2. **与人工确认点兼容**:总纲的"⏸ 人工确认点"是强制暂停点,编译为 `type=pause` 步骤后,
   执行时必须暂停等用户确认,**不允许自动跳过**(即使总纲允许"全流程执行"话术,pause 节点仍强制暂停)。
3. **失败不阻塞**:workflow 层失败时退出码 1 但执行轨迹保留,调用方可 resume 或重规划,
   不强制中断 agent 会话(与 tool-git-ops / skill-runtime 的"失败不阻塞"原则一致)。
4. **保留执行轨迹**:`workflow-exec-report.json` 在运行期间持续更新,暂停时保留,失败不丢失。
5. **不产出业务文件**:本 skill 只产出 workflow.yaml 与执行轨迹,不产出 PRD/代码/美术等业务产物。
6. **"只读不写"声明不适用本 skill**:本 skill 是执行引擎,会写 workflow.yaml / state.json /
   exec-report.json(自身产物),不适用于 skill-runtime / guardrail 等审查类 skill 的"只读不写"约束。
   但本 skill **不修改被调度 skill 的内部文件**——只调用 skill,不改 skill 源码。
7. **PyYAML 可选**:脚本在 PyYAML 缺失时降级为提示(`compile-from-master` 仍可用简易 YAML 输出),
   不强制安装(与 validate_runtime.py 一致)。

## 十一、质量检查清单

### 11.1 产物自评项

- [ ] `python scripts/compile_workflow.py --help` 不报错,三个子命令均可见。
- [ ] `python scripts/compile_workflow.py compile-from-master --help` / `compile-from-tasktree --help` / `validate --help` 子命令 help 正常。
- [ ] `python scripts/run_workflow.py --help` 不报错,`run` / `resume` / `status` 子命令均可见。
- [ ] `compile-from-master` 能识别"调用 `xxx`"/"⏸ 人工确认点"/"**并行**调用"/"FAIL 则回 N"四种模式。
- [ ] `compile-from-tasktree` 能把 task-tree.json 的 `depends_on`/`parallel_with` 转为 workflow steps。
- [ ] `validate` 校验合法 workflow.yaml 时 exit 0,字段缺失/引用错误时 exit 1。
- [ ] `run --dry-run` 只输出执行计划,不调用 skill,不产生 state.json。
- [ ] `run` 遇到 pause 节点时输出"暂停点"并保存 state.json,exit 0(正常暂停)。
- [ ] `resume --choice N` 能按用户选择跳转到对应 step。
- [ ] `status` 能正确显示暂停节点与待确认选项。
- [ ] 执行轨迹 `workflow-exec-report.json` 字段齐全(workflow/started_at/status/steps[])。
- [ ] `references/workflow-yaml-schema.md` 含完整字段规范表 + JSON Schema + 完整示例 + 并行示例。
- [ ] `references/execution-semantics.md` 含状态机图 + 暂停/恢复/跳过/回退/并行语义 + exec-report 字段表。
- [ ] SKILL.md 行数 ≤500,frontmatter 含 name + description。
- [ ] 所有文件 UTF-8 编码,文档与代码注释为中文。
- [ ] 与 skill-runtime 兼容:step.`runtime` 字段引用 runtime.yaml,默认值与 skill-runtime §七 一致。
- [ ] 与 task-planner 兼容:`compile-from-tasktree` 正确消费 task-tree.json 的 tasks/depends_on/parallel_with。

## 十二、数据记录(接入 usage-tracker)

本 skill 执行 workflow.yaml 时,接入 skill-usage-tracker 记录每次 skill 调用数据,形成"执行→统计→优化"数据闭环。

### 12.1 记录时机

每个 type=skill 的 step 执行前后,各调一次 skill-usage-tracker:
- **执行前**:调 `track_usage.py record --skill <skill名> --pipeline <workflow名>`,获取/生成 call_id
- **执行后**:更新该 call_id 的 end_time / duration_ms / status / error_code / outputs

### 12.2 调用 ID 生成规则

- **格式**:`call-{YYYYMMDD}-{序号}`(如 `call-20260806-001`)
- **生成方**:workflow-runtime 在 step 开始时分配,贯穿该 step 的执行链路
- **关联**:failure-casebook 记录失败时关联此 call_id(见 `../failure-casebook/SKILL.md` §五 `related_call_id` 字段),便于追溯单次调用的完整上下文

### 12.3 记录字段对照

| 字段 | 来源 | 说明 |
|------|------|------|
| `call_id` | workflow-runtime 生成 | 调用唯一标识 |
| `skill` | workflow.yaml step.skill | 被调用的 skill 名 |
| `pipeline` | workflow.yaml name | 所属流水线 |
| `start_time` | step 开始时间 | ISO-8601 带时区 |
| `end_time` | step 结束时间 | ISO-8601 带时区 |
| `duration_ms` | end - start | 耗时毫秒 |
| `status` | step 执行结果 | `success` / `fail` |
| `error_code` | on_fail 触发时 | 失败码 |
| `outputs` | step.outputs | 产物路径列表 |
| `caller` | 固定 `workflow-runtime` | 调用方标识 |

### 12.4 失败不阻塞

skill-usage-tracker 的 record 失败时仅打 WARNING,不阻塞 workflow 执行(与 usage-tracker"纯记录不阻塞"原则一致)。调用链:

```
workflow-runtime step 执行
  → 执行前:track_usage.py record (获取 call_id)
  → 执行 skill
  → 执行后:track_usage.py record (更新 call_id 状态)
  → 若失败:failure-casebook record (关联 call_id)
```

## 十三、自适应优化(接入 adaptive-tuner)

本 skill 执行 workflow.yaml 前,可选接入 `adaptive-tuner` 获取数据驱动的运行时参数覆盖,
形成"统计→优化→执行→统计"自适应闭环(Phase 4 新增)。

### 13.1 接入时机

执行 workflow.yaml 前(在 `run_workflow.py run` 的 step 调度循环开始前):
1. 检查是否存在 adaptive-tuner 产出的 `runtime-overrides.yaml`
2. 若存在,读取 overrides 文件,加载各 skill 的优化参数
3. 若不存在或解析失败,标 WARNING 并使用 runtime.yaml 本地值(不阻塞执行)

### 13.2 覆盖优先级

runtime 参数按以下优先级决定最终值(高 → 低):

| 优先级 | 来源 | 说明 |
|--------|------|------|
| 1(最高) | adaptive-tuner 的 `runtime-overrides.yaml` | 基于 skill-usage-tracker 数据自动生成的优化参数 |
| 2 | skill 的 `runtime.yaml` 本地字段 | skill 作者声明的默认运行时参数 |
| 3(最低) | 默认值(timeout=300 等) | 未声明时的兜底值 |

**覆盖规则**:
- overrides 仅覆盖 `timeout` 和 `retry` 字段,不覆盖 `inputs`/`outputs`/`degrade`(后者是 skill 声明契约)。
- overrides 文件中不存在的 skill,使用本地 runtime.yaml 值。
- overrides 中字段类型与本地不一致时,标 WARNING 并回退到本地值。

### 13.3 合并流程

```
run_workflow.py 执行 step 前:
  1. 读取 step.skill 的 runtime.yaml(本地声明)
  2. 检查 runtime.yaml 是否含 external_overrides 字段
     - 是 → 读取 external_overrides 引用的 overrides 文件
     - 否 → 检查 adaptive-tuner 默认产出路径是否有 runtime-overrides.yaml
  3. 从 overrides 文件中筛选当前 step.skill 对应的 overrides
  4. 用 overrides 的 timeout/retry 覆盖本地值
  5. 最终参数用于执行(设超时、决定重试次数)
  6. 若 overrides 文件不存在或解析失败,标 WARNING 并回退到本地值
```

### 13.4 与 skill-runtime 的关系

skill-runtime 的 runtime.yaml 新增了 `external_overrides` 可选字段(Phase 4):
- `external_overrides`: 引用 adaptive-tuner 产出的 overrides 文件路径
- workflow-runtime 执行时若发现该字段,优先读 overrides 文件
- `validate_runtime.py` 校验:external_overrides 引用的文件存在且为合法 YAML

详见 `../skill-runtime/references/runtime-schema.md` §九。

### 13.5 自适应闭环

```
skill-usage-tracker 记录调用数据(耗时/失败率)
  → adaptive-tuner analyze 分析数据,生成 tuning-suggestions.json
  → adaptive-tuner suggest 产出 runtime-overrides.yaml(需用户确认)
  → adaptive-tuner apply 应用覆盖
  → workflow-runtime 执行时读取 overrides,用优化参数调度
  → 执行结果再次被 skill-usage-tracker 记录
  → (循环)
```

### 13.6 失败不阻塞

adaptive-tuner 或 overrides 文件不可用时,workflow-runtime 标 WARNING 并使用本地 runtime.yaml 值,
不阻塞 workflow 执行(与"失败不阻塞"原则一致)。

### 13.7 与 adaptive-tuner apply 的职责分工

- **adaptive-tuner apply 子命令**:**持久化**合并覆盖到 runtime.yaml 本地字段(先备份再覆盖 timeout/retry),适用于离线调优场景。
- **workflow-runtime 运行时合并**:**运行时**合并 external_overrides 引用的 overrides 文件到 step.runtime,不修改 runtime.yaml 本地字段,适用于在线执行场景。
- **两者不冲突**:apply 后 runtime.yaml 本地字段已被优化值覆盖,external_overrides 字段保留(供 workflow-runtime 运行时再做一次合并,值相同不会出 bug)。
- **推荐顺序**:先 adaptive-tuner apply 持久化基线优化 → workflow-runtime 运行时按需合并临时 overrides。
