# 执行语义(权威)

本文件定义 workflow.yaml 的执行语义,是 `run_workflow.py` 执行步骤时的行为依据。
`workflow-runtime/SKILL.md` §五 引用本文件。`compile_workflow.py validate` 校验语义一致性时也参照本文件。

## 一、执行状态机

每个 step 在执行过程中经历以下状态:

```
                    ┌──────────┐
        start ─────►│ PENDING  │
                    └────┬─────┘
                         │ 调度执行
                         ▼
                    ┌──────────┐  pause 节点
                    │ RUNNING  │────────────►┌──────────┐
                    └────┬─────┘              │ PAUSED   │
                         │                    └────┬─────┘
              ┌──────────┼──────────┐              │ 用户确认
              │成功      │失败      │              ▼
              ▼          ▼          ▼         ┌──────────┐
        ┌──────────┐ ┌──────────┐ ┌──────┐   │ RESUMING │──► RUNNING(下一步)
        │  DONE    │ │ FAILED   │ │SKIP  │   └──────────┘
        └────┬─────┘ └────┬─────┘ └──┬───┘
             │            │          │
             │ on_fail:   │ on_fail: │ 裁剪跳过,直接到 next
             │ 进入下一步 │ back_to  │
             │           │ 回退重跑 │
             ▼           ▼          
        ┌──────────┐ ┌──────────┐
        │  NEXT    │ │ RETRYING │──► RUNNING(目标 step)
        └──────────┘ └──────────┘
                          │ 超过 max_retries
                          ▼
                    ┌──────────┐
                    │ ABORTED  │──► 结束
                    └──────────┘
```

状态定义:
- **PENDING**:已加载,等待调度
- **RUNNING**:正在执行(调用 skill 或等待用户确认)
- **PAUSED**:遇到 pause 节点,已保存状态,等待用户确认
- **RESUMING**:用户已确认,准备从暂停点继续
- **DONE**:执行成功,产物已产出
- **FAILED**:执行失败
- **SKIP**:被裁剪跳过,不执行
- **RETRYING**:失败后按 on_fail.back_to 回退,准备重跑目标 step
- **ABORTED**:失败次数超限或 on_fail=abort,工作流终止

## 二、暂停(pause)

触发条件:step 的 `type=pause`。

执行动作:
1. `run_workflow.py` 执行到 pause 节点时**停止**,不自动继续
2. 输出"暂停点:{title}"与 `confirm.question` 提问文本
3. 把当前执行状态保存到 `state.json`(含当前 step id、已完成步骤、产物路径)
4. 等待用户通过 AskUserQuestion 选择 `confirm.options` 中的某一项

约束:
- 暂停点不可跳过:即使 step 有 `next`,也必须先暂停等用户确认
- 一个 pause 节点对应一次 AskUserQuestion 调用
- 暂停时 `run_workflow.py` 退出码为 0(正常暂停,非失败)
- **optional pause**(`optional: true`):该暂停点可选,允许跳过。执行动作:
  1. 若上游条件满足(如用户已明确要"提交/部署"),正常暂停并 AskUserQuestion
  2. 若上游条件不满足(如用户未提及 Tool 操作),自动跳过该 pause 节点,按 `next` 继续执行(等价于 SKIP)
  3. 典型场景:可选 Tool 确认点(如 product-pipeline-master 确认点 5),默认不强制出现

## 三、恢复(resume)

触发条件:用户在暂停点做出选择后,调用 `run_workflow.py resume --state state.json`。

执行动作:
1. 读取 `state.json`,定位到暂停的 step id
2. 读取用户选择的 option(通过状态文件中的 `user_choice` 字段)
3. 按 `option.next` 跳转到对应 step 继续执行
4. 若 `option.next` 为 `__end__`,标记工作流完成并输出最终简报

约束:
- 恢复前必须存在有效的 `state.json`
- 恢复后从用户选择的 step 开始,不重跑已 DONE 的步骤(除非显式 back_to)

## 四、跳过(skip)

两种跳过场景:

1. **裁剪跳过**:编排总纲裁剪某阶段时,对应 step 从 steps 数组中移除(编译时裁剪)
   - 由编排总纲在编译时决定(直接从 steps 中移除该 step,workflow.yaml 不保留被裁剪的 step)
   - `run_workflow.py` 执行时不遇到被裁剪的 step,直接按数组顺序执行保留下来的步骤

2. **失败跳过(on_fail.action=skip)**:step 失败后跳过本步,继续执行 next
   - 适用于非关键步骤(如可选的 game-polish)
   - 跳过时在执行轨迹记录失败原因

约束:
- 质量门(Gate)步骤**不可**用 on_fail=skip(质量门失败必须 back_to 或 abort)
- 可选阶段(如 game-topic-brainstorm、game-polish)允许 skip

## 五、回退(back_to)

触发条件:step 失败且 `on_fail.action=back_to`。

执行动作:
1. step 执行失败
2. 读取 `on_fail.target`,定位回退目标 step
3. 检查当前 step 的累计回退次数;若 < `on_fail.max_retries`(默认 3),状态置 RETRYING
4. 重新调度目标 step 执行(回到 back_to 指向的步骤重跑)
5. 回退次数累加;超过 `max_retries` 时升级为 abort,工作流终止

典型场景:质量门 FAIL 则回退到对应阶段 skill 修复(如 Gate 0 FAIL → 回到 game-blueprint 修复)。

约束:
- `on_fail.target` 必须指向 steps 内已存在的 step id
- 回退不消除已产出的产物(skill 自行覆盖或增量更新)
- 回退次数计入执行轨迹,便于 failure-casebook 记录

## 六、并行(parallel_with)

触发条件:step 声明了 `parallel_with` 字段。

执行动作:
1. `run_workflow.py` 遇到声明 `parallel_with` 的 step 时,识别为一组并行步骤
2. 同组步骤(A.parallel_with=B 且 B.parallel_with=A)同时调度执行
3. 等待同组**全部**步骤完成后,才继续执行 `next` 指向的步骤
4. 任一并行步骤失败:按该步骤自身的 `on_fail` 处理(通常 back_to 回退整组)

典型场景:game-forge-master §七 阶段 4 的 `game-asset-forge` 与 `game-code-forge` 并行。

约束:
- `parallel_with` 必须双向声明(A 指向 B,B 指向 A)
- 同组步骤的 `next` 应指向同一个 step(汇聚点,如 Gate 3)
- dry-run 模式下并行步骤按顺序打印(标注"并行组")

## 七、失败处理(on_fail)汇总

| action | 行为 | 适用场景 | 是否终止 |
|--------|------|---------|---------|
| `back_to` | 回退到 target step 重跑,超 max_retries 则 abort | 质量门 FAIL、关键步骤失败 | 否(重跑);超限是 |
| `skip` | 跳过本步,继续 next | 可选阶段失败、非关键步骤 | 否 |
| `abort` | 立即终止工作流 | 关键步骤失败且无回退意义 | 是 |

## 八、执行轨迹(exec-report)

每步执行结果写入 `workflow-exec-report.json`,字段:

| 字段 | 类型 | 说明 |
|------|------|------|
| `workflow` | string | 工作流名称 |
| `started_at` | string | 开始时间(ISO8601) |
| `finished_at` | string | 结束时间(ISO8601) |
| `status` | string | `running` / `paused` / `done` / `aborted` |
| `current_step` | string | 当前 step id(暂停时为 pause 节点 id) |
| `steps` | array | 每步执行记录 |
| `steps[].id` | string | step id |
| `steps[].status` | string | `done` / `failed` / `skipped` / `pending` |
| `steps[].retries` | integer | 回退重跑次数 |
| `steps[].outputs` | array | 实际产出路径 |
| `steps[].error` | string | 失败原因(失败时) |
| `steps[].duration` | string | 耗时 |

约束:
- 执行轨迹在工作流运行期间持续更新(每步完成后追加)
- 暂停时轨迹保留,恢复后继续追加
- 失败时轨迹不丢失(写入 ABORTED 记录)

## 九、与 runtime.yaml 的协作

`run_workflow.py` 执行 `type=skill` 的 step 前:
1. 读取 step 的 `runtime` 字段(若声明),获取该 skill 的 runtime.yaml
2. 按 `timeout` 设定执行超时(超时则视为失败,触发 on_fail)
3. 按 `retry` 决定是否在 skill 内部重试(runtime 层重试,区别于 on_fail.back_to 的工作流层回退)
4. 失败时若 runtime.yaml 声明了 `degrade`,优先尝试降级策略;降级仍失败才走 on_fail

两层失败处理关系:
- **runtime 层**(skill 内部):timeout / retry / degrade — 由 skill-runtime 定义
- **workflow 层**(步骤间):on_fail.back_to / skip / abort — 由本文件定义
- runtime 层重试与降级用尽后,才上升到 workflow 层的 on_fail 处理
