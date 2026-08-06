# Agent 通信协议规范 (agent-protocol)

> agent-orchestrator 的 Agent 间通信协议参考。设计 Agent 协同时查阅。

## 一、消息格式

所有 Agent 间通信均采用以下 JSON 消息格式:

```json
{
  "msg_id": "M001",
  "from": "master-agent",
  "to": "sub-agent-1",
  "type": "delegate",
  "correlation_id": "T0",
  "payload": { "task": "...", "assigned_skill": "...", "deadline": "..." },
  "ack_required": true,
  "timestamp": "2026-08-06T10:00:00+08:00",
  "status": "pending"
}
```

### 字段说明

| 字段 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| msg_id | string | 是 | - | 消息唯一标识,格式 M001/M002/...(脚本自动生成) |
| from | string | 是 | - | 发送方 Agent 标识(如 master-agent / sub-agent-1) |
| to | string | 是 | - | 接收方 Agent 标识 |
| type | enum | 是 | - | delegate/ack/result/query/notify/heartbeat |
| correlation_id | string | 是 | - | 关联任务 ID,同一任务的全部消息共享 |
| payload | object | 是 | - | 消息负载,结构随 type 而变(见 §二) |
| ack_required | boolean | 否 | false | 是否需要接收方回 ack |
| timestamp | string | 是 | - | ISO8601 带时区时间戳(脚本自动填) |
| status | enum | 否 | pending | pending/delivered/acknowledged/completed/failed |

### status 状态机

```
pending -> delivered -> acknowledged -> completed
                ↓             ↓
              failed        failed
```

- pending:消息已发送,未被拉取
- delivered:接收方已拉取(receive 标记)
- acknowledged:接收方已回 ack(ack 消息触发)
- completed:结果已回传(result 消息触发)
- failed:超时或执行失败

---

## 二、消息类型与 payload

| type | 方向 | 用途 | payload 关键字段 |
|------|------|------|----------------|
| delegate | 主->从 | 任务委派 | task, assigned_skill, deadline |
| ack | 从->主 | 收到确认 | ack_for(对应 delegate 的 msg_id) |
| result | 从->主 | 结果回传 | result, summary, status |
| query | 任一方 | 澄清询问 | question, about |
| notify | 任一方 | 通知(无需 ack) | event, detail |
| heartbeat | 任一方 | 心跳保活 | agent_state |

### payload 示例

#### delegate
```json
{
  "task": "生成游戏蓝图",
  "assigned_skill": "game-blueprint",
  "deadline": "2026-08-06T12:00:00+08:00"
}
```

#### ack
```json
{
  "ack_for": "M001",
  "note": "已收到,开始执行"
}
```

#### result
```json
{
  "result": "docs/GAME_BLUEPRINT.md",
  "summary": "蓝图已生成,含类型/平台/引擎/玩法",
  "status": "ok"
}
```

#### query
```json
{
  "question": "目标平台是 Web 还是移动?",
  "about": "task T1 的 assigned_skill 配置"
}
```

#### notify
```json
{
  "event": "agent_online",
  "detail": "sub-agent-2 已就绪"
}
```

#### heartbeat
```json
{
  "agent_state": "running",
  "progress": "60%"
}
```

---

## 三、握手流程

### 3.1 标准握手(含 ack)

```
主 Agent                     子 Agent
   |                            |
   |--- delegate (ack_req=true)-->|
   |                            |
   |<-- ack (ack_for=M001) -----|
   |                            |
   |                            | (执行任务)
   |                            |
   |<-- result (correlation_id) -|
   |                            |
   |--- (collect + merge) ----->|
```

步骤:
1. 主 Agent 发 delegate 消息(ack_required=true),status=pending
2. 子 Agent receive 拉取消息,status->delivered
3. 子 Agent 回 ack 消息(ack_for=delegate 的 msg_id),delegate 的 status->acknowledged
4. 子 Agent 执行完毕,回 result 消息(correlation_id 一致),delegate 的 status->completed
5. 主 Agent collect 收集 result,按 merge 策略合并

### 3.2 简化握手(无 ack)

对低风险或通知类消息,ack_required=false,跳过 ack 步骤:

```
主 Agent --- delegate (ack_req=false) --> 子 Agent
主 Agent <-- result (correlation_id) ---- 子 Agent
```

---

## 四、确认机制(ack)

### 4.1 何时需要 ack

| 场景 | ack_required | 说明 |
|------|-------------|------|
| 任务委派(delegate) | true | 确保子 Agent 已收到任务 |
| 结果回传(result) | false | 结果即终态,无需再确认 |
| 通知(notify) | false | 单向通知,无需确认 |
| 询问(query) | true | 确保对方收到问题 |

### 4.2 ack 超时

- 发出 ack_required=true 的消息后,主 Agent 等待 ack
- ack 超时默认 60s(可配置),超时后主 Agent 重发一次
- 重发后仍未收到 ack,标记 status=failed,转人工裁决

---

## 五、超时机制

### 5.1 委派超时

- 默认超时 300s,可在 delegate 的 payload.deadline 显式指定
- 超时判断:`collect` 时检查 委派时间 + timeout 是否已过
- 超时且结果数 < 委派数:输出 WARN,建议转人工裁决

### 5.2 超时处理流程

```
委派(delegate)
  -> 等待 result(最长 timeout)
  -> 超时未收到 result
  -> 标记 status=failed
  -> collect 输出 WARN
  -> merge --strategy human 转人工裁决
```

### 5.3 心跳机制(长任务)

- 长任务(预计 >300s)子 Agent 应定期发 heartbeat
- 心跳间隔建议 60s
- 超过 2 个间隔(120s)未收到心跳,主 Agent 视为子 Agent 掉线
- 掉线后标记 status=failed,转人工裁决

---

## 六、日志保留

- 消息日志(agent-messages.json)保留 30 天
- 超过保留期的消息在下次写入时自动裁剪(_prune_expired)
- 无 timestamp 的消息保留(避免误删)
- 协议规范文件(orchestration-protocol.md)持久保留,不自动删除

---

## 七、与 skill-runtime 的协作

delegate 消息的 payload.assigned_skill 引用具体 skill,该 skill 的 runtime.yaml(skill-runtime 契约)
提供:
- timeout:单 skill 执行超时(本 skill 的 delegate 超时是 Agent 级,粒度更大)
- retry:失败重试策略
- degrade:降级策略

两层超时关系:
- skill-runtime 层:单 skill 执行超时(细粒度,如 600s 生图)
- agent-orchestrator 层:Agent 协同超时(粗粒度,如 300s 等待 Agent 回 result)

skill-runtime 层重试与降级用尽后,才上升到 agent-orchestrator 层的委派超时处理。
