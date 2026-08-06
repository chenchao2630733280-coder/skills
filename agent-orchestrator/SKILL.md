---
name: "agent-orchestrator"
description: "多 Agent 协同 skill。定义 Agent 间通信协议(消息格式/任务委派/结果汇总),支持主从与对等模式。当任务超出单 skill 范围需多 Agent 协作、或要编排多个子 Agent 并行/串行时调用。本身定义协议与编排逻辑,实际多 Agent 运行依赖宿主。"
---

# agent-orchestrator — 多 Agent 协同编排

agent-orchestrator 是 AI Agent 体系的 **Agent 协同层 skill**。它定义 Agent 间通信协议
(消息格式 / 任务委派 / 结果汇总 / 冲突解决),支持主从模式(一主多从)与对等模式(多 Agent 协商)。

- **定义协议不运行**:本 skill 提供协议规范与编排逻辑,实际多 Agent 调度依赖宿主执行。
- **与 workflow-runtime 区别**:workflow-runtime 编排"skill 调用"(粒度=单个 skill),
  agent-orchestrator 编排"Agent 协同"(粒度=Agent,一个 Agent 可包含多 skill)。
- **失败不阻塞**:操作失败返回 error 字段,不抛异常阻断调用方。

## 一、何时调用

满足以下任一条件即调用本 skill:

1. **任务超出单 skill 范围**:任务需要多个 Agent 协作(如"前端 Agent + 后端 Agent + 测试 Agent")。
2. **编排多子 Agent**:要并行/串行调度多个子 Agent,并收集汇总结果。
3. **定义 Agent 间协议**:需要统一 Agent 间的消息格式、握手、确认、超时机制。
4. **结果冲突解决**:多 Agent 产出结果有冲突,需要按优先级/投票/人工裁决合并。

**不要**在以下场景调用:
- 单 skill 能完成的任务(直接调对应 skill,无需 Agent 协同)
- 要编排 skill 调用顺序(用 `workflow-runtime`,它编排 skill;本 skill 编排 Agent)
- 要创建新 skill(用 `skill-creator`)
- 要做任务拆解规划(用 `task-planner`,本 skill 消费其产物而非替代它)
- 用户只是问"Agent 协议怎么写"(纯咨询,直接读 `references/agent-protocol.md`)

本 skill **定义协议不运行**:提供协议规范 + 编排逻辑,实际多 Agent 调度由宿主执行。

---

## 二、核心职责与通信协议

### 2.1 核心职责

| 职责 | 说明 |
|------|------|
| 定义通信协议 | 消息格式(发送方/接收方/类型/负载/关联 ID) |
| 任务委派 | 主 Agent 把子任务委派给子 Agent,收集结果 |
| 协同模式 | 主从模式(一主多从)/ 对等模式(多 Agent 协商) |
| 结果汇总 | 聚合多 Agent 结果,处理冲突/合并 |
| 消息日志 | 持久化消息记录,保留 30 天,可追溯 |

### 2.2 通信协议概览

完整协议规范见 `references/agent-protocol.md`,核心消息格式:

```json
{
  "msg_id": "M001",
  "from": "master-agent",
  "to": "sub-agent-1",
  "type": "delegate",
  "correlation_id": "T0",
  "payload": { "task": "...", "assigned_skill": "...", "deadline": "..." },
  "ack_required": true
}
```

消息类型:`delegate`(委派)/ `ack`(确认)/ `result`(结果)/ `query`(询问)/ `notify`(通知)/ `heartbeat`(心跳)。

### 2.3 协同模式

| 模式 | 结构 | 适用 |
|------|------|------|
| 主从模式 | 一主多从,主 Agent 委派 + 收集 | 任务可拆分的并行/串行场景 |
| 对等模式 | 多 Agent 协商,无固定主 | 需要多方观点汇总/投票决策 |

委派模式详见 `references/delegation-patterns.md`(扇出/扇入/管道/协商)。

---

## 三、scripts 调用方式

通用调用格式:

```
python scripts/orchestrate.py <子命令> [选项]
python scripts/message_bus.py <子命令> [选项]
```

### 3.1 orchestrate.py — 协同编排

#### delegate(委派任务)

```
python scripts/orchestrate.py delegate \
  --from master-agent --to sub-agent-1 \
  --task "生成游戏蓝图" --skill game-blueprint --ack \
  [--correlation-id T1] [--deadline 2026-08-06T12:00:00+08:00] [--timeout 300]
```

- 生成 msg_id(M001/M002/...),type=delegate,写入 `agent-messages.json`
- 首次委派时自动生成 `orchestration-protocol.md`(协议规范文档)
- deadline 缺省时按 `--timeout` 推算(now + timeout)

#### collect(收集结果)

```
python scripts/orchestrate.py collect --correlation-id T1 [--timeout 300]
```

- 从 `agent-messages.json` 筛选 type=result 且 correlation_id 匹配的消息
- 判断超时:委派时间 + timeout 已过且结果数 < 委派数,标记超时转人工
- 控制台输出委派数/已收集/失败数

#### merge(合并结果)

```
python scripts/orchestrate.py merge --correlation-id T1 \
  [--strategy priority|voting|human] [--priority-order "sub-1,sub-2"]
```

- 聚合 correlation_id 关联的全部 result 消息
- `priority`(默认):按 `--priority-order` 取首个非空结果
- `voting`:相同结果摘要占比 >50% 取胜,否则转人工
- `human`:不自动合并,标记待人工裁决

### 3.2 message_bus.py — 消息总线

#### send(发送消息)

```
python scripts/message_bus.py send \
  --from sub-agent-1 --to master-agent --type result \
  --correlation-id T1 --payload '{"summary":"蓝图已生成","status":"ok"}' [--ack]
```

- 生成 msg_id,追加到 `agent-messages.json`
- payload 必须是合法 JSON 字符串

#### receive(拉取消息)

```
python scripts/message_bus.py receive [--to sub-agent-1] [--correlation-id T1] [--type delegate] [--limit 10] [--peek]
```

- 拉取 status 为 pending/delivered 的消息(按 to/correlation_id/type 过滤)
- 默认标记为 delivered(不删除,便于追溯);`--peek` 只看不标记

#### history(查询历史)

```
python scripts/message_bus.py history [--from master-agent] [--to sub-agent-1] \
  [--correlation-id T1] [--type delegate] [--since 2026-08-06T00:00:00+08:00] [--limit 50]
```

- 查询全部历史消息(含已完成/失败),支持多维过滤

### 3.3 退出码

| 场景 | orchestrate.py | message_bus.py |
|------|----------------|----------------|
| 成功 | 0 | 0 |
| 有错误(无结果/超时/失败) | 1 | 1 |
| 参数错误 | 2 | 2 |

---

## 四、references 使用指引

| 文件 | 读取时机 |
|------|---------|
| `references/agent-protocol.md` | (1) 用户问"Agent 消息格式怎么写";(2) 设计握手/确认/超时机制时;(3) `orchestrate.py delegate` 生成协议文档时对照 |
| `references/delegation-patterns.md` | (1) 用户问"怎么委派多 Agent";(2) 选择扇出/扇入/管道/协商模式时;(3) 设计并行/串行编排时 |
| `references/conflict-resolution.md` | (1) 多 Agent 结果冲突时;(2) 选择 priority/voting/human 策略时;(3) `orchestrate.py merge` 配置策略时 |

三份 references 均为**懒加载**:仅在需要时读取,不强制调用方一次性全读。

---

## 五、关键约束

1. **定义协议不运行**:本 skill 提供协议规范 + 编排逻辑,实际多 Agent 调度依赖宿主执行,
   本 skill 不直接启动 Agent 进程。
2. **与 workflow-runtime 区别**:workflow-runtime 编排"skill 调用"(粒度=单个 skill),
   agent-orchestrator 编排"Agent 协同"(粒度=Agent,一个 Agent 可包含多 skill)。
3. **委派有超时**:默认 300s,超时转人工裁决(`merge --strategy human`)。
4. **结果冲突默认按优先级**:可配置投票(`voting`)或人工裁决(`human`)。
5. **消息日志保留 30 天**:超过保留期的消息在下次写入时自动裁剪。
6. **失败不阻塞**:操作失败返回 error 字段并 exit 1,不抛异常阻断调用方(与 tool-git-ops / skill-runtime 一致)。
7. **消息日志不删除**:receive 拉取后只标记 delivered,不删除消息,便于历史追溯。

---

## 六、与其他 skill 的关系

| skill | 关系 | 说明 |
|-------|------|------|
| `workflow-runtime` | 互补 | workflow-runtime 编排 skill 调用(细粒度),本 skill 编排 Agent 协同(粗粒度);一个 Agent 可包含多 skill,workflow-runtime 可被 Agent 内部使用 |
| `task-planner` | 上游 | task-planner 产出 task-tree.json;本 skill 可把多任务委派给多 Agent |
| `skill-runtime` | 契约消费方 | Agent 委派的 `assigned_skill` 引用 skill,该 skill 的 runtime.yaml 提供 timeout/retry/degrade |
| `failure-casebook` | 协作方 | 委派超时/失败时显式调用 `failure-casebook` record 子命令记录失败码,下次同名任务委派前注入预防提示 |
| `agent-runtime-exec` | 执行后端 | 本 skill 定义协议(规则),agent-runtime-exec 实现执行器(运行);用户要"实际运行多 Agent"时,本 skill 委托 agent-runtime-exec 执行(Phase 4 新增,见 §六.1) |
| `skill-creator` | 上游 | 新建 Agent 配置(agents/openai.yaml)时参考本 skill 的协议 |

调用链示例:
```
task-planner 产出 task-tree.json
  → agent-orchestrator 把多任务委派给多 Agent(delegate)
  → 各 Agent 内部用 workflow-runtime 调度 skill
  → Agent 回传 result 消息(message_bus send)
  → agent-orchestrator 收集合并(collect + merge)
```

### 6.1 执行后端:接入 agent-runtime-exec(Phase 4 新增)

本 skill **定义协议不运行**(§五约束 1):提供消息格式、委派模式、冲突解决策略等规范,
但实际多 Agent 调度执行依赖宿主。Phase 4 起引入 `agent-runtime-exec` 作为本协议的执行实现,
补齐"协议定义 → 实际运行"的最后一公里。

**协议与执行器的职责分工**:

| 维度 | agent-orchestrator(本 skill) | agent-runtime-exec(执行器) |
|------|------------------------------|---------------------------|
| 角色 | 协议定义方(规则) | 执行实现方(运行) |
| 产出 | 协议规范、委派模式、合并策略 | 执行轨迹、委派状态、合并结果 |
| 关心 | "Agent 怎么通信"(消息格式/握手/确认) | "Agent 怎么执行"(进程调度/结果收集) |
| 文件 | `references/agent-protocol.md` 等 | `scripts/execute_agents.py` 等 |
| 是否替代对方 | 否 | 否(实现协议,不重新定义协议) |

**调用方式**:

- 用户要"设计 Agent 通信协议 / 多 Agent 编排逻辑"→ 只调本 skill(delegate/collect/merge 生成消息与合并结果)
- 用户要"实际运行多 Agent / 跑一次多 Agent 调度"→ 本 skill 委托 `agent-runtime-exec` 执行:
  1. 本 skill 用 `orchestrate.py delegate` 生成委派消息(写 `agent-messages.json`)
  2. 调 `agent-runtime-exec delegate` 把委派转为实际子 Agent 调用,子 Agent 执行后回写 result
  3. 调 `agent-runtime-exec collect` 收集执行结果
  4. 调 `agent-runtime-exec merge` 合并结果(复用本 skill 定义的 priority/voting/human 策略)
  5. 必要时调 `agent-runtime-exec monitor` 监控多 Agent 执行状态
- 失败回退:agent-runtime-exec 执行失败不阻塞本 skill,错误回填 error 字段;调用方可选择
  回退到本 skill 的 `merge --strategy human` 转人工裁决

**与 workflow-runtime 的层级关系**:

```
编排总纲(决策) → workflow-runtime(skill 调用编排,粒度=skill)
                  → agent-orchestrator(Agent 协同编排,粒度=Agent,一个 Agent 含多 skill)
                    → agent-runtime-exec(实际执行多 Agent 调度,Phase 4 新增)
```

> **注意**:agent-runtime-exec 是本协议的"参考实现",不是唯一实现。宿主或第三方仍可
> 基于本 skill 定义的协议实现自己的执行器。本 skill 的协议规范优先级高于执行器实现。

---

## 七、消息格式与协议规范

### 7.1 消息格式

所有 Agent 间通信均采用以下 JSON 消息格式:

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `msg_id` | string | 是 | 消息唯一标识(M001/M002/...) |
| `from` | string | 是 | 发送方 Agent 标识 |
| `to` | string | 是 | 接收方 Agent 标识 |
| `type` | enum | 是 | delegate/ack/result/query/notify/heartbeat |
| `correlation_id` | string | 是 | 关联任务 ID(同一任务的全部消息共享) |
| `payload` | object | 是 | 消息负载,结构随 type 而变 |
| `ack_required` | boolean | 否 | 是否需要接收方回 ack,默认 false |
| `timestamp` | string | 是 | ISO8601 带时区时间戳(脚本自动填) |
| `status` | enum | 否 | pending/delivered/acknowledged/completed/failed |

### 7.2 消息类型与 payload

| type | 方向 | 用途 | payload 关键字段 |
|------|------|------|----------------|
| delegate | 主→从 | 任务委派 | task, assigned_skill, deadline |
| ack | 从→主 | 收到确认 | ack_for(对应 msg_id) |
| result | 从→主 | 结果回传 | result, summary, status |
| query | 任一方 | 澄清询问 | question, about |
| notify | 任一方 | 通知(无需 ack) | event, detail |
| heartbeat | 任一方 | 心跳保活 | agent_state |

### 7.3 握手流程

1. 主 Agent 发 delegate 消息(ack_required=true)
2. 子 Agent 收到后回 ack 消息(ack_for=delegate 的 msg_id)
3. 子 Agent 执行完毕回 result 消息(correlation_id 一致)
4. 主 Agent collect 收集 result,按 merge 策略合并

### 7.4 产物文件

| 产物 | 路径 | 说明 |
|------|------|------|
| 消息日志 | `agent-messages.json`(当前工作目录) | 全部消息记录,保留 30 天 |
| 协议规范 | `orchestration-protocol.md`(当前工作目录) | 首次委派时自动生成,持久保留 |

---

## 八、质量检查清单

### 8.1 协议定义约束

- [ ] SKILL.md 已声明"定义协议不运行",脚本只读写消息日志与协议文档,不启动 Agent 进程。

### 8.2 产物自评项

- [ ] `python scripts/orchestrate.py --help` 不报错,`delegate` / `collect` / `merge` 子命令均可见。
- [ ] `python scripts/orchestrate.py delegate --help` / `collect --help` / `merge --help` 子命令 help 正常。
- [ ] `python scripts/message_bus.py --help` 不报错,`send` / `receive` / `history` 子命令均可见。
- [ ] `python scripts/message_bus.py send --help` / `receive --help` / `history --help` 子命令 help 正常。
- [ ] delegate 能生成 msg_id 并写入 `agent-messages.json`,首次委派时生成 `orchestration-protocol.md`。
- [ ] collect 能按 correlation_id 筛选 result 消息,超时时输出 WARN。
- [ ] merge 三种策略(priority/voting/human)均能正确处理冲突。
- [ ] send 能追加消息到 `agent-messages.json`,payload 为非法 JSON 时 exit 1。
- [ ] receive 能按 to/correlation_id/type 过滤,默认标记 delivered,`--peek` 不标记。
- [ ] history 能按多维过滤查询,`--since` 时间过滤生效。
- [ ] 消息日志超 30 天的消息在下次写入时自动裁剪。
- [ ] `references/agent-protocol.md` 含消息格式表 + 握手流程 + 确认/超时机制。
- [ ] `references/delegation-patterns.md` 含扇出/扇入/管道/协商四类委派模式。
- [ ] `references/conflict-resolution.md` 含优先级/投票/人工裁决三种策略。
- [ ] `agents/openai.yaml` 含 interface(display_name/short_description/default_prompt)。
- [ ] SKILL.md 行数 ≤500,frontmatter 含 name + description。
- [ ] 所有文件 UTF-8 编码,文档与代码注释为中文。
- [ ] 产物自评:本 skill 产出后,按 skill-auditor 执行后评测模式自查(可选)。
