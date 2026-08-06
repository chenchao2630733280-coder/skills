---
name: "replanner"
description: "重规划器 skill。当子任务失败或上下文变化时,动态调整 task-tree(重排/跳过/拆分/合并)。当 workflow-runtime 检测到任务失败或用户变更需求时调用,产出调整后的 task-tree 与变更说明。"
---

# replanner — 重规划器

replanner 是 AI Agent 体系第二阶段升级的 **Planning 层 skill**。它依赖 `task-planner` 产出的
`task-tree.json` 格式,在子任务失败或上下文变化时**动态调整**任务树(重排/跳过/拆分/合并/降级),
产出符合 `task-tree-schema` 的 `task-tree.v2.json` 与人读的 `replan-report.md`。

- **只调整规划不执行**:本 skill 不调用下游 skill 执行任务,只产出调整后的任务树与变更说明。
- **依赖 task-planner 格式**:输入与输出均符合 `task-planner` 的 `task-tree-schema`,可无缝替换原任务树。
- **最多 3 轮**:同一失败链路重规划不超过 3 轮,超过转人工接管。
- **可回退**:原 `task-tree.json` 保留,`task-tree.v2.json` 为新版本,失败可回退。

## 一、何时调用

满足以下任一条件即调用本 skill(由 `workflow-runtime` 或上层编排触发):

1. **子任务执行失败**:`workflow-runtime` 检测到某 task 执行失败(异常退出/质量门 FAIL/超时),
   需评估是否调整后续任务树。
2. **用户变更需求**:用户在执行中途修改需求范围/目标,原 task-tree 部分任务失效或需新增。
3. **质量门 FAIL**:质量门(`quality-gate` 类 skill)判定某阶段产物不达标,需重做或降级。
4. **依赖链断裂**:某任务的前置产物缺失或结构不符,下游任务无法承接。

> 若仅是单次可重试的瞬时错误(如网络抖动),由 `workflow-runtime` 直接重试即可,不进入本 skill。
> 本 skill 处理的是**需要改变规划本身**的失败。

## 二、与 task-planner 的关系

| 维度 | task-planner(初始规划) | replanner(本 skill,动态调整) |
|------|----------------------|------------------------------|
| 时机 | 需求开始前,一次性规划 | 执行过程中,失败/变更时触发 |
| 输入 | 任意需求文本 | 原 `task-tree.json` + 失败信息 |
| 产出 | `task-tree.json` + `task-plan.md` | `task-tree.v2.json` + `replan-report.md` |
| 格式 | 符合 `task-tree-schema` | **同样符合 `task-tree-schema`**(兼容) |
| 性质 | 从 0 到 1 构建 | 在已有树上做局部调整 |

**核心约定**:
- 两者产出格式**完全一致**,都符合 `task-planner` 的 `../task-planner/references/task-tree-schema.md`。
- `task-tree.v2.json` 可直接作为 `workflow-runtime` 的新执行输入,无需格式转换。
- replanner **不重新规划全局**,只对受影响局部做最小调整,保持未受影响任务的稳定性。

## 三、重规划流程

```
接收原 task-tree + 失败信息 → 影响分析 → 生成调整方案 → 产出 task-tree.v2 + replan-report
```

### 3.1 接收输入
- 读取原 `task-tree.json`(由 `task-planner` 产出或上一轮 replanner 产出)。
- 读取失败信息 JSON,字段:
  - `failed_task_id`(必填):失败任务 id。
  - `error_code`(可选):错误分类码。
  - `error_message`(必填):错误描述。
  - `suggested_action`(可选):调用方建议的策略(重排/跳过/拆分/合并/降级/人工接管)。
  - `round`(可选):当前重规划轮次,默认 1;≥3 时强制转人工接管。
- 失败信息来源:`workflow-runtime` 的执行报告、`failure-casebook` 的历史案例、质量门报告。

### 3.2 影响分析
- 调用 `scripts/replan.py impact` 或在脑内执行影响分析算法(见第四节)。
- 找出所有**直接依赖**与**间接依赖**失败任务的任务,分级为阻断/降级/无影响。

### 3.3 生成调整方案
- 对照第五节策略表,结合影响分级与 `suggested_action` 选择策略。
- 脚本 `replan.py replan` 会给出框架性建议,实际策略选择与任务改写由 AI 在本 SKILL.md 引导下完成。

### 3.4 产出
- 写 `task-tree.v2.json`(机读,符合 schema,见第九节)。
- 写 `replan-report.md`(人读,含影响分析、策略、变更说明)。
- 原 `task-tree.json` 保留不覆盖,支持回退。

## 四、影响分析

影响分析用于判断"一个任务失败后,还有哪些任务受牵连"。算法详见 `references/impact-analysis.md`。

### 4.1 依赖图构建
- 从 task-tree 的 `depends_on` 字段构建**反向依赖图**:若 B 的 `depends_on` 含 A,则 A 失败会影响 B。
- 反向图 `reverse[A] = [B, C, ...]` 表示 A 的所有直接下游。

### 4.2 传播算法
- **BFS 分层遍历**:从失败任务出发,第 1 层为直接依赖者,第 2 层为间接依赖者,依此类推。
- 遍历收集所有受影响任务 id(不含失败任务本身)。

### 4.3 影响分级

| 分级 | 判定 | 处置倾向 |
|------|------|---------|
| 阻断 | 失败任务为 P0,或受影响任务中含 P0 | 必须处理(拆分/降级),否则关键路径停滞 |
| 降级 | 受影响任务仅 P1/P2 | 可跳过/降级,不阻塞主路径 |
| 无影响 | 无任何任务依赖失败任务 | 仅记录,不影响后续 |

> 示例:T-001(设计表结构,P0)失败 → T-003(创建接口)直接受影响 → T-004(列表页)间接受影响。
> 因 T-001 为 P0,分级为"阻断"。

## 五、重规划策略

5 种核心调整策略 + 1 种兜底(人工接管),详见 `references/replan-strategies.md`:

| 策略 | 适用场景 | 操作 | 风险 |
|------|---------|------|------|
| 重排 | 失败任务非关键路径,可后置 | 调整 `depends_on`/执行顺序,先做其他 | 低 |
| 跳过 | 失败任务为可选阶段(P1/P2) | 从 tasks 移除,清理下游引用并标注 | 中(下游可能缺产物) |
| 拆分 | 失败任务过大/根因不明 | 把失败任务拆为多个更小子任务重试 | 中(需重新估复杂度) |
| 合并 | 多个小任务频繁失败 | 合并为一个较大任务统一处理 | 中(并行度降低) |
| 降级 | 失败任务可用降级方案替代 | 换用 `skill-runtime` 的降级策略,产物降级 | 高(质量折损,需用户确认) |
| 人工接管 | 同一失败链路重规划达 3 轮 | 停止自动重规划,转人工审查 | —(兜底) |

**策略选择优先级**:重排 > 跳过 > 拆分 > 合并 > 降级 > 人工接管。
- 优先选对规划扰动最小的策略。
- 降级因涉及质量折损,需用户确认后才执行。
- 人工接管是硬兜底:第 3 轮失败后**必须**转人工,不再自动重规划。

## 六、scripts 调用方式

脚本 `scripts/replan.py`,argparse 双子命令:

### 6.1 replan — 重规划

```
python scripts/replan.py replan --input <原task-tree.json> --failure <失败信息.json> --output <输出路径>
```

- `--input`:原 `task-tree.json` 路径(必填)。
- `--failure`:失败信息 JSON 路径,含 `failed_task_id`/`error_code`/`error_message`/`suggested_action`/`round`(必填)。
- `--output`:输出路径,可为目录(写入 `task-tree.v2.json` + `replan-report.md`)或具体 `.json` 文件(报告写同目录),默认当前目录。
- 脚本完成:Schema 校验 → 失败信息校验 → 影响分析 → 策略建议 → 产出 `task-tree.v2.json`(原树副本脚手架)+ `replan-report.md`。
- **实际任务改写由 AI 在本 SKILL.md 引导下完成**:脚本只产出脚手架与影响分析报告,AI 据此修改 `task-tree.v2.json` 并回填报告"变更说明"。

### 6.2 impact — 影响分析

```
python scripts/replan.py impact --input <task-tree.json> --task-id <失败任务ID>
```

- 读取 `task-tree.json`,校验 Schema,分析指定任务的影响传播。
- 输出:失败任务信息、影响分级、直接/间接受影响任务清单、不受影响任务数。

### 6.3 退出码

| 场景 | exit code |
|------|-----------|
| 成功 | 0 |
| 校验失败(Schema/失败信息/任务不存在) | 1 |
| 参数错误 | 2 |

## 七、references 使用指引

| 文件 | 用途 | 何时查 |
|------|------|--------|
| `references/impact-analysis.md` | 影响传播分析方法(依赖图/BFS/分级) | 第四节"影响分析"阶段 |
| `references/replan-strategies.md` | 5 种策略 + 人工接管的触发条件/操作/示例 | 第五节"选择策略"阶段 |

引用文件为只读参考,不得修改;实际产物写入调用方指定的输出目录。

## 八、关键约束

1. **只调整规划不执行**:本 skill 不调用下游 skill 执行任务,只产出调整后的任务树与变更说明。执行由 `workflow-runtime` 承接。
2. **最多 3 轮**:同一失败链路重规划不超过 3 轮;第 3 轮仍失败**必须**转人工接管,不再自动重规划。
3. **保留原版本可回退**:原 `task-tree.json` 不覆盖,`task-tree.v2.json` 为新版本;回退时直接恢复原文件。
4. **格式兼容**:产出 `task-tree.v2.json` 必须符合 `task-planner` 的 `task-tree-schema`,不额外加字段(顶层仅 `version`/`root`/`tasks`,task 字段同 schema)。
5. **失败信息来源可信**:失败信息来自 `workflow-runtime` 执行报告、`failure-casebook` 历史案例或质量门报告,不臆造失败原因。
6. **最小扰动**:优先调整受影响局部,不重写未受影响任务;能重排就不跳过,能跳过就不拆分。
7. **降级需确认**:`降级`策略涉及质量折损,产出前需用户确认;未经确认不写入降级方案。
8. **中文产出**:`task-tree.v2.json` 的 title、`replan-report.md` 正文用中文。

## 九、产物规范

### 9.1 task-tree.v2.json

- 顶层字段:`version`("1.0") / `root`(id/title/complexity) / `tasks`(数组)。
- 每个 task 字段:`id`/`title`/`priority`/`depends_on`/`parallel_with`/`assigned_skill`/`est_complexity`/`est_duration`(可选)。
- **与 task-planner 产出完全同构**,详见 `task-planner` 的 `../task-planner/references/task-tree-schema.md`。
- 调整后需通过 `replan.py` 的 Schema 校验(脚本产出时已校验,AI 改写后建议再跑 `task-planner` 的 `topology` 子命令校验无环)。
- 拆分产生的新任务 id 建议沿用原 id 加后缀(如 `T-003` 拆为 `T-003a`/`T-003b`),便于追溯。

### 9.2 replan-report.md

字段/章节:

| 章节 | 内容 |
|------|------|
| 头部元信息 | 生成时间、原 task-tree 根、失败任务、错误码/信息、调用方建议、重规划轮次、影响分级 |
| 一、影响分析 | 直接/间接受影响任务数与清单(id/title/priority)、不受影响任务数 |
| 二、策略建议 | 建议策略 + 引用 `references/replan-strategies.md` |
| 三、变更说明(AI 填充) | 调整类型、变更任务 id、变更内容、回退方案 |
| 四、人工接管提示 | 仅当轮次≥3 时出现 |
| 五、产物 | 列出 `task-tree.v2.json`/`replan-report.md` 与回退说明 |

## 十、质量检查清单

产出 `task-tree.v2.json` + `replan-report.md` 后逐项自评,全部通过方可交付:

- [ ] `task-tree.v2.json` 的 `version` 为 `"1.0"`,`root` 含 id/title/complexity。
- [ ] 每个 task 含必填字段:id/title/priority/est_complexity。
- [ ] `id` 在 tasks 内唯一,不与 root.id 冲突;拆分新 id 可追溯(含原 id 前缀)。
- [ ] `depends_on` 中所有 id 都能在 tasks 中找到(引用完整);跳过的任务已从所有 `depends_on`/`parallel_with` 清理。
- [ ] `depends_on` 无环(可跑 `task-planner` 的 `topology` 子命令复核)。
- [ ] 未受影响任务保持原样,未被误改。
- [ ] 策略选择与影响分级一致:阻断级不选"跳过";降级策略已经用户确认。
- [ ] 重规划轮次 ≤3;第 3 轮产物含人工接管提示。
- [ ] 原 `task-tree.json` 保留未覆盖,可回退。
- [ ] `replan-report.md` 的"变更说明"已回填,含调整类型/变更任务/变更内容/回退方案。
- [ ] 产出格式与 `task-planner` 兼容,可直接作为 `workflow-runtime` 的新执行输入。
