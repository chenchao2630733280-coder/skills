# 结果冲突解决 (conflict-resolution)

> agent-orchestrator 的多 Agent 结果冲突解决策略参考。merge 时查阅。

## 一、四种冲突解决策略

### 1. 优先级(priority,默认)

**规则**:按 Agent 优先级序列,取首个非空(非 failed)结果。

**适用**:主从模式,各 Agent 有明确优先级(如"主 Agent 信任度 > 备份 Agent")。

**命令**:
```bash
python scripts/orchestrate.py merge --correlation-id T1 \
  --strategy priority --priority-order "sub-1,sub-2,sub-3"
```

**示例**:
```
sub-1 结果:failed
sub-2 结果:ok  <- 取这个(优先级序列中首个非 failed)
sub-3 结果:ok
```

**退化场景**:全部 failed 时,默认取首个结果(sub-1),并提示。

---

### 2. 投票(voting)

**规则**:按 result.payload.summary 投票,相同 summary 占比 >50% 取胜。

**适用**:对等模式,多 Agent 独立产出,需多数共识(如"多 Agent 评审方案")。

**命令**:
```bash
python scripts/orchestrate.py merge --correlation-id T1 --strategy voting
```

**示例**:
```
sub-1 summary: "方案A"
sub-2 summary: "方案A"  <- 2/3 一致,取胜
sub-3 summary: "方案B"
```

**退化场景**:无多数(最高占比 <=50%)时,不自动合并,转人工裁决。

---

### 3. 人工裁决(human)

**规则**:不自动合并,列出全部结果,等待人工标注 chosen=true。

**适用**:冲突无法自动解决,或结果重要性高需人工确认。

**命令**:
```bash
python scripts/orchestrate.py merge --correlation-id T1 --strategy human
```

**示例输出**:
```
待人工裁决的任务 T1:
  [1] from=sub-1  status=ok
      summary: 方案A
  [2] from=sub-2  status=ok
      summary: 方案B
  请人工选择最终结果(在 agent-messages.json 中标注 chosen=true)
```

**人工标注**:在 agent-messages.json 中,对选中的 result 消息加 `"chosen": true` 字段。

---

### 4. 最新优先(latest)

**规则**:保留 timestamp 最大的结果,丢弃其他结果。适用于幂等性写入场景(如配置更新、状态覆盖),最后写入者胜出。

**适用**:多 Agent 并发写入同一资源且操作幂等时(对齐 agent-runtime-exec/references/conflict-strategies.md §一第 12 行 latest 策略)。

**命令**:
```bash
python scripts/orchestrate.py merge --correlation-id T1 --strategy latest
```

**示例**:
```
sub-1 result: timestamp=2026-08-06T10:00:00+08:00  summary: "配置=v1"
sub-2 result: timestamp=2026-08-06T10:05:00+08:00  summary: "配置=v2"  <- 取这个(timestamp 最大)
sub-3 result: timestamp=2026-08-06T09:58:00+08:00  summary: "配置=v1"
```

**退化场景**:无任何 ok 结果时,转人工裁决。

---

## 二、策略选择速查

| 场景 | 推荐策略 | 说明 |
|------|---------|------|
| 主从模式,有明确优先级 | priority | 取首个非空 |
| 对等模式,需多数共识 | voting | >50% 一致取胜 |
| 冲突无法自动解决 | human | 转人工 |
| 结果重要性高 | human | 强制人工确认 |
| 幂等写入/最后写入者胜出 | latest | 取 timestamp 最大 |
| 不确定 | priority | 默认最稳 |

---

## 三、与委派模式的关系

| 委派模式 | 常用冲突策略 |
|---------|------------|
| 扇出(Fan-out) | priority(各 Agent 有优先级) |
| 扇入(Fan-in) | voting(多 Agent 独立产出) |
| 管道(Pipeline) | 通常无冲突(串行单结果) |
| 协商(Negotiation) | voting / human |
| 并发写入(幂等) | latest(最后写入者胜出) |

---

## 四、与超时的关系

- 委派超时(默认 300s)未收到 result:status=failed
- merge 时跳过 failed 结果(priority 取首个非 failed)
- 全部 failed 时:
  - priority:取首个(并提示)
  - voting:无法投票,转人工
  - human:已转人工,等待标注
  - latest:无可用结果,转人工

**超时转人工流程**:
```
delegate -> 超时(300s) -> status=failed
  -> collect 输出 WARN
  -> merge --strategy human 转人工裁决
```

---

## 五、人工裁决标注规范

人工裁决后,在 agent-messages.json 中对选中的 result 消息加字段:

```json
{
  "msg_id": "M005",
  "type": "result",
  "from": "sub-2",
  "to": "master-agent",
  "correlation_id": "T1",
  "payload": { "summary": "方案B", "status": "ok" },
  "chosen": true,
  "chosen_by": "human",
  "chosen_at": "2026-08-06T11:00:00+08:00"
}
```

字段说明:
- `chosen`:boolean,是否为最终选定结果
- `chosen_by`:string,标注方(如 "human" / "auto-priority" / "auto-voting")
- `chosen_at`:string,标注时间(ISO8601)

---

## 六、与 failure-casebook 的协作

- 委派超时或结果失败时,显式调用 `failure-casebook` record 子命令记录失败码 + 修复方法
- 下次同名任务委派前,注入预防提示(类似 skill-runtime §八 协作)
- 失败码格式:`AGENT_TIMEOUT_<correlation_id>` / `AGENT_CONFLICT_<correlation_id>`
