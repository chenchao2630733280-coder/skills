---
name: "agent-runtime-exec"
description: "Agent Runtime 执行层 skill。基于 agent-orchestrator 定义的通信协议，实现多 Agent 实际调度执行器（委派/收集/合并/冲突解决）。当要把多 Agent 协同从'协议定义'升级为'实际运行'，或要并行调度多个子 Agent 执行任务时调用。本身是执行器，依赖宿主提供 Agent 实例。"
---

# agent-runtime-exec — Agent Runtime 执行层

agent-runtime-exec 是 AI Agent 体系第四阶段升级的 **Agent Runtime 执行层 skill**。它基于
`agent-orchestrator` 定义的通信协议，实现多 Agent 的实际调度执行（委派/收集/合并/监控）,
把"协议定义"升级为"实际运行"。

- **执行器非协议**：本 skill 实现实际调度，`agent-orchestrator` 定义协议规范。
- **依赖宿主提供 Agent 实例**：本 skill 不创建 Agent，只调度已存在的 Agent。
- **协议兼容**：严格遵循 `agent-orchestrator` 的消息格式（msg_id/from/to/type/payload）。
- **失败不阻塞**：单个子 Agent 失败不中断整体，标记失败后继续 collect 其他结果。

**与 agent-orchestrator 的区别**：
- `agent-orchestrator`：定义协议（消息格式/委派模式/冲突规则）—— 是"规则"
- `agent-runtime-exec`：实现执行器（实际调度/收集/合并）—— 是"运行"
- 关系：agent-orchestrator 是"宪法"，agent-runtime-exec 是"政府"

## 一、何时调用

满足以下任一条件即调用本 skill：

1. **实际运行多 Agent**：要把多 Agent 协同从"协议定义"落地为"实际执行"。
   - 如："并行调度前端 Agent + 后端 Agent + 测试 Agent 执行任务"
   - 如："实际运行多 Agent 协同"
2. **并行委派子任务**：主 Agent 要把多个子任务并行委派给多个子 Agent。
   - 如："委派 3 个子任务给 3 个子 Agent 并行执行"
3. **收集合并结果**：收集多个子 Agent 的执行结果，按策略合并解决冲突。
   - 如："收集所有子 Agent 结果并按优先级合并"
4. **监控执行状态**：监控运行中的 Agent 状态，支持取消超时任务。
   - 如："监控当前执行的 Agent 状态"
   - 如："取消超时的子 Agent"

**不要**在以下场景调用：
- 只需定义 Agent 通信协议（走 `agent-orchestrator`，本 skill 消费其协议）
- 编排 skill 调用顺序（走 `workflow-runtime`，它编排 skill；本 skill 编排 Agent）
- 任务拆解规划（走 `task-planner`，本 skill 消费其 task-tree）
- 保存会话状态（走 `session-snapshot`，本 skill 不持久化会话）

## 二、与 agent-orchestrator 的关系

| 维度 | agent-orchestrator | agent-runtime-exec（本 skill） |
|------|-------------------|-------------------------------|
| 角色 | 协议定义 | 执行实现 |
| 产出 | orchestration-protocol.md + agent-messages.json | agent-exec-state.json + agent-exec-report.json |
| 调用 | 定义"怎么通信" | 实现"怎么执行" |
| 运行 | 不启动 Agent | 调度已存在的 Agent（不创建） |
| 粒度 | Agent 协同 | Agent 执行轨迹 |

**调用链**：
```
agent-orchestrator 定义协议 + 首次 delegate 生成 orchestration-protocol.md
  → agent-runtime-exec 读取协议,实际调度(delegate/collect/merge/monitor)
  → 产出 agent-exec-state.json(执行状态) + agent-exec-report.json(执行报告)
```

## 三、核心职责与执行模式

### 3.1 核心职责

| 职责 | 说明 |
|------|------|
| 委派执行 | 把子任务实际分配给子 Agent,记录 deadline 与状态 |
| 结果收集 | 收集所有子 Agent 的执行结果,处理超时/失败 |
| 冲突合并 | 聚合结果,按 conflict-strategies 解决冲突 |
| 状态监控 | 监控运行中 Agent 的状态,支持取消超时任务 |
| 执行轨迹 | 持久化执行轨迹,保留 30 天,便于复盘 |

### 3.2 执行模式

| 模式 | 结构 | 适用场景 |
|------|------|---------|
| 主从模式 | 一主多从,主 Agent 委派 + 收集 | 任务可拆分的并行场景 |
| 对等模式 | 多 Agent 协商,无固定主 | 需要多方观点汇总/投票决策 |
| 管道模式 | 串行接力,前一个输出作后一个输入 | 流水线式处理(如 PRD→设计→实现) |
| 扇出扇入 | 一主扇出多从,扇入收集 | 并行处理 + 结果聚合 |

执行模式详见 `references/execution-modes.md`。

## 四、scripts 调用方式

### 4.1 execute_agents.py — 执行调度

#### delegate(委派执行)

```bash
python scripts/execute_agents.py delegate \
  --from master-agent --to sub-agent-1,sub-agent-2,sub-agent-3 \
  --tasks '[{"task":"生成蓝图","skill":"game-blueprint"},{"task":"生成PRD","skill":"game-spec"}]' \
  --mode master-slave --timeout 300
```

- 读取 `orchestration-protocol.md`(若存在,遵循协议)
- 为每个子任务创建委派记录,分配 deadline(now + timeout)
- 写入 `agent-exec-state.json`(执行状态)
- 返回 `exec_id`

#### collect(收集结果)

```bash
python scripts/execute_agents.py collect --exec-id exec-001 [--timeout 300]
```

- 从 `agent-exec-state.json` 读取委派记录
- 检查每个委派的状态(completed/failed/timeout/pending)
- 超时委派标记 timeout,转人工裁决
- 输出已收集/失败/超时数量

#### merge(合并结果)

```bash
python scripts/execute_agents.py merge --exec-id exec-001 \
  --strategy priority --priority-order "sub-1,sub-2,sub-3"
```

- 聚合 exec_id 关联的全部结果
- 调用 `resolve_conflicts.py` 按策略解决冲突
- 产出 `agent-exec-report.json`

#### monitor(监控状态)

```bash
python scripts/execute_agents.py monitor --exec-id exec-001
```

- 打印当前执行状态(各 Agent 状态/进度)
- 支持 `--cancel <agent>` 取消指定 Agent

### 4.2 resolve_conflicts.py — 冲突解决

```bash
python scripts/resolve_conflicts.py resolve \
  --exec-id exec-001 --strategy priority --priority-order "sub-1,sub-2"
```

- 四种策略:`priority`(优先级)/`voting`(投票)/`human`(人工裁决)/`latest`(最近优先)
- 详见 `references/conflict-strategies.md`

### 4.3 退出码

| 场景 | execute_agents.py | resolve_conflicts.py |
|------|-------------------|---------------------|
| 成功 | 0 | 0 |
| 有错误(无结果/超时/部分失败) | 1 | 1 |
| 参数错误 | 2 | 2 |

## 五、references 使用指引

| 文件 | 读取时机 |
|------|---------|
| `references/execution-modes.md` | (1) 选择主从/对等/管道/扇出扇入模式时;(2) 设计并行/串行编排时;(3) 用户问"有哪些执行模式" |
| `references/conflict-strategies.md` | (1) 多 Agent 结果冲突时;(2) 选择 priority/voting/human/latest 策略时;(3) `merge` 配置策略时 |
| `references/timeout-handling.md` | (1) 子 Agent 超时时;(2) 选择取消/降级/转人工策略时;(3) 配置 timeout 时 |

三份 references 均为**懒加载**:仅在需要时读取。

## 六、产出 schema

### 6.1 agent-exec-state.json(执行状态)

```json
{
  "exec_id": "exec-20260806-001",
  "created_at": "2026-08-06T10:00:00+08:00",
  "mode": "master-slave",
  "master": "master-agent",
  "delegations": [
    {
      "msg_id": "M001",
      "correlation_id": "T1",
      "type": "delegate",
      "from": "master-agent",
      "to": "sub-agent-1",
      "payload": { "task": "生成游戏蓝图", "skill": "game-blueprint" },
      "ack_required": true,
      "timestamp": "2026-08-06T10:00:00+08:00",
      "task": "生成游戏蓝图",
      "assigned_skill": "game-blueprint",
      "deadline": "2026-08-06T10:05:00+08:00",
      "status": "pending",
      "started_at": null,
      "completed_at": null,
      "result": null
    }
  ],
  "status": "running",
  "summary": null
}
```

**delegations 字段说明**:

协议必填字段(来自 agent-orchestrator 消息):

- `msg_id`(string,必填):消息 ID
- `correlation_id`(string,必填):来自 agent-orchestrator 消息,同任务全部消息共享
- `type`(string,必填):消息类型(delegate/collect/merge 等)
- `from`(string,必填):消息发送方
- `to`(string,必填):消息接收方
- `payload`(object,必填):消息负载
- `ack_required`(boolean,必填):是否需要确认
- `timestamp`(string,必填):ISO8601 时间戳

执行器扩展字段(本 skill 维护):

- `task`(string):任务描述
- `assigned_skill`(string):委派给的 skill
- `deadline`(string):截止时间(ISO8601)
- `status`(string):pending/running/completed/failed/timeout
- `started_at`(string|null):实际开始时间
- `completed_at`(string|null):实际完成时间
- `result`(object|null):执行结果

### 6.2 agent-exec-report.json(执行报告)

```json
{
  "exec_id": "exec-20260806-001",
  "created_at": "2026-08-06T10:00:00+08:00",
  "completed_at": "2026-08-06T10:04:30+08:00",
  "mode": "master-slave",
  "total_delegations": 3,
  "completed": 2,
  "failed": 1,
  "timeout": 0,
  "results": [
    { "agent": "sub-1", "status": "completed", "summary": "蓝图已生成" }
  ],
  "merge_strategy": "priority",
  "merged_result": { "summary": "蓝图已生成", "source": "sub-1" },
  "conflicts": []
}
```

## 七、与其他 skill 的协作

| skill | 关系 | 协作方式 |
|-------|------|---------|
| `agent-orchestrator` | 协议来源 | 读取其 `orchestration-protocol.md` 遵循协议;由 agent-orchestrator 通过 delegate 命令的 --tasks 参数传入委派任务(agent-runtime-exec 不直接读取 agent-messages.json,而是通过命令参数接收委派) |
| `workflow-runtime` | 互补 | workflow-runtime 编排 skill(细粒度),本 skill 编排 Agent(粗粒度);Agent 内部可用 workflow-runtime |
| `task-planner` | 上游 | task-planner 产出 task-tree.json;本 skill 把多任务委派给多 Agent |
| `skill-runtime` | 契约消费方 | 委派的 `assigned_skill` 引用 skill,该 skill 的 runtime.yaml 提供 timeout/retry/degrade |
| `failure-casebook` | 协作方 | 执行失败/超时时显式调用 failure-casebook record 子命令记录失败码,下次同名任务委派前注入预防提示 |
| `session-snapshot` | 持久化 | 执行状态可被 session-snapshot 快照保存,支持跨会话恢复 |

调用链示例:
```
task-planner 产出 task-tree.json
  → agent-orchestrator 定义协议 + 首次 delegate 生成协议文档
  → agent-runtime-exec 实际调度(delegate/collect/merge)
  → 各 Agent 内部用 workflow-runtime 调度 skill
  → agent-runtime-exec 收集合并(merge + resolve_conflicts)
  → 产出 agent-exec-report.json
```

## 八、失败处理

本 skill 的失败 **不阻断主流程**:

- 单个子 Agent 失败:标记 `failed`,继续 collect 其他结果,不中断整体;调 failure-casebook record 子命令记录失败码。
- 子 Agent 超时:标记 `timeout`,转人工裁决(merge --strategy human);调 failure-casebook record 子命令记录失败码。
- 执行状态文件读写失败:只打 WARNING,返回空结果,exit code 0(delegate)或 1(collect/merge)。
- 冲突无法自动解决:标 `unresolved`,提示人工裁决,不强制合并。
- **设计原则**:执行器是辅助调度,不是关键路径,宁可降级到人工也不能拖垮主流程。
- **标准动作**:任何失败/超时均显式调用 `failure-casebook record` 子命令记录失败码 + 修复方法,供下次同名任务委派前注入预防提示。

超时处理详见 `references/timeout-handling.md`。

## 九、关键约束

1. **依赖宿主提供 Agent 实例**:本 skill 是执行器,不创建 Agent,只调度已存在的 Agent。
2. **协议兼容**:严格遵循 `agent-orchestrator` 的消息格式(msg_id/from/to/type/payload/correlation_id)。
3. **超时默认 300s**:子 Agent 超时后转人工裁决,不无限等待。
4. **冲突默认按优先级**:可配置投票(`voting`)/人工裁决(`human`)/最近优先(`latest`)。
5. **执行轨迹保留 30 天**:超过保留期的轨迹在下次写入时自动清理。
6. **失败不阻塞**:单个子 Agent 失败不中断整体,标记失败后继续 collect。
7. **不创建 Agent**:只调度,不实例化;Agent 的创建由宿主负责。
8. **SKILL.md 行数 ≤ 500**。

## 十、质量检查清单

- [ ] `python scripts/execute_agents.py --help` 不报错,delegate/collect/merge/monitor 子命令可见
- [ ] `python scripts/resolve_conflicts.py --help` 不报错,resolve 子命令可见
- [ ] delegate 能创建 exec_id、写入 agent-exec-state.json、为每个子任务分配 deadline
- [ ] collect 能读取执行状态、检查超时、输出已收集/失败/超时数量
- [ ] merge 能聚合结果、调用 resolve_conflicts、产出 agent-exec-report.json
- [ ] monitor 能打印执行状态、支持 --cancel 取消指定 Agent
- [ ] resolve_conflicts 四种策略(priority/voting/human/latest)均能正确处理
- [ ] 单个子 Agent 失败不中断整体(failed 标记后继续 collect)
- [ ] 超时委派标记 timeout 并转人工裁决
- [ ] 执行轨迹超 30 天的记录在下次写入时自动清理
- [ ] `references/execution-modes.md` 含主从/对等/管道/扇出扇入四类模式
- [ ] `references/conflict-strategies.md` 含优先级/投票/人工裁决/最近优先四种策略
- [ ] `references/timeout-handling.md` 含取消/降级/转人工三种处理
- [ ] `agents/openai.yaml` 含 interface(display_name/short_description/default_prompt)
- [ ] SKILL.md 行数 ≤ 500,frontmatter 含 name + description
- [ ] 所有文件 UTF-8 编码,文档与代码注释为中文
- [ ] 产物自评:本 skill 产出后,按 skill-auditor 执行后评测模式自查(可选)
