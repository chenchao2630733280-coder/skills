# 超时处理（Timeout Handling）

> 本文件定义 agent-runtime-exec 处理子 Agent 超时的策略。

## 一、超时判定

### 1.1 判定规则

| 条件 | 判定 |
|------|------|
| 当前时间 > deadline 且 status=pending/running | timeout |
| collect 时委派时间 + timeout 已过且结果数 < 委派数 | partial-timeout |

### 1.2 默认超时

- **默认 300s**(5 分钟)
- 可通过 `--timeout` 参数配置
- deadline = 委派时间 + timeout

## 二、超时处理策略

### 2.1 cancel（取消）

**行为**:标记超时 Agent 为 `timeout`,不再等待其结果。

**适用**:
- 任务有时效性(过期结果无意义)
- Agent 可能已卡死

**调用**:
```bash
python scripts/execute_agents.py monitor --exec-id exec-001 --cancel sub-agent-2
```

**效果**:
- Agent 状态标记为 `timeout`
- 继续收集其他 Agent 的结果
- 合并时忽略 timeout 的 Agent

### 2.2 degrade（降级）

**行为**:超时后降级为简化结果或默认值。

**适用**:
- 有降级方案的任务(如复杂分析降级为简单检查)
- 可接受部分结果

**实现**:
- 调用方在 delegate 时指定 `degrade_to`(降级后的默认结果)
- 超时后,merge 阶段使用 `degrade_to` 替代实际结果

**示例**:
```json
{
  "task": "深度代码审查",
  "assigned_skill": "code-review",
  "timeout": 300,
  "degrade_to": { "summary": "审查超时,建议人工复核", "status": "degraded" }
}
```

### 2.3 human（转人工）

**行为**:超时后不自动处理,标记待人工裁决。

**适用**:
- 高风险任务(自动决策可能出错)
- 超时原因不明(需人工诊断)

**实现**:
- Agent 状态标记为 `timeout`
- 合并策略自动设为 `human`
- 输出提示:"子 Agent X 超时,请人工裁决"

## 三、策略选择

| 场景 | 推荐策略 |
|------|---------|
| 任务有时效性 | cancel |
| 有降级方案 | degrade |
| 高风险/原因不明 | human |
| 默认 | cancel + 转人工合并 |

## 四、超时与失败的区别

| 维度 | timeout | failed |
|------|---------|--------|
| 原因 | 时间超过 deadline | Agent 执行报错 |
| 结果 | 无结果(或降级结果) | 有错误信息 |
| 处理 | cancel/degrade/human | 记录错误,继续 collect |
| 重试 | 可选(重新 delegate) | 可选(重新 delegate) |

## 五、重试机制

### 5.1 自动重试

- **默认不自动重试**:超时后直接标记,不自动重新委派
- **可配置重试**:调用方在 delegate 时指定 `retry.max`(来自 skill-runtime 的 runtime.yaml)
- **重试上限**:最多 5 次(防无限重试)

### 5.2 重试流程

1. 首次委派,deadline = now + timeout
2. 超时后,标记 `timeout`
3. 若 retry.max > 0,重新委派(新 msg_id,新 deadline)
4. 重试次数耗尽后,转人工裁决

### 5.3 重试记录

每次重试记录到执行轨迹:
```json
{
  "msg_id": "M001",
  "retry_count": 2,
  "retry_history": [
    { "attempt": 1, "deadline": "...", "status": "timeout" },
    { "attempt": 2, "deadline": "...", "status": "timeout" },
    { "attempt": 3, "deadline": "...", "status": "completed" }
  ]
}
```

## 六、与 failure-casebook 的协作

超时/失败时,自动记录失败案例到 `failure-casebook`:

```json
{
  "skill": "agent-runtime-exec",
  "code": "AGENT_TIMEOUT",
  "reason": "子 Agent sub-2 超时(300s)",
  "fix": "检查 sub-2 是否卡死,或增加 timeout"
}
```

下次同名任务委派前,注入预防提示:"上次 sub-2 超时,建议增加 timeout 或检查 Agent 状态"。
