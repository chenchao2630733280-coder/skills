# 冲突解决策略（Conflict Strategies）

> 本文件定义 agent-runtime-exec 合并多 Agent 结果时的冲突解决策略。

## 一、策略总览

| 策略 | 说明 | 适用场景 | 自动化 |
|------|------|---------|--------|
| priority | 按 Agent 优先级取首个非空结果 | 有明确优先级顺序 | 全自动 |
| voting | 相同结果占比 >50% 取胜 | 多 Agent 独立评估同一任务 | 半自动(无多数时转人工) |
| human | 不自动合并,标记待人工裁决 | 结果差异大/高风险决策 | 人工 |
| latest | 取最近完成的结果 | 时间敏感场景 | 全自动 |

## 二、priority（优先级策略）

### 2.1 算法

1. 按 `--priority-order` 指定的 Agent 顺序遍历
2. 取首个 `status=completed` 且 `result` 非空的结果
3. 后续 Agent 的结果忽略(仅记录到 conflicts)

### 2.2 调用

```bash
python scripts/resolve_conflicts.py resolve \
  --exec-id exec-001 --strategy priority \
  --priority-order "sub-1,sub-2,sub-3"
```

### 2.3 示例

```
sub-1: result = { "蓝图": "A方案" }     ← 取此结果(priority 最高)
sub-2: result = { "蓝图": "B方案" }     ← 忽略,记录到 conflicts
sub-3: result = null                    ← 跳过(空结果)
合并结果 = { "蓝图": "A方案", "source": "sub-1" }
```

### 2.4 适用场景

- 各 Agent 有明确能力分级(如专家 Agent 优先)
- 需要确定性结果(不依赖投票)

## 三、voting（投票策略）

### 3.1 算法

1. 提取各 Agent 结果的 `summary` 字段
2. 按 summary 分组统计
3. 占比 >50% 的组取胜
4. 无组过半数时,转人工裁决

### 3.2 调用

```bash
python scripts/resolve_conflicts.py resolve \
  --exec-id exec-001 --strategy voting
```

### 3.3 示例

```
sub-1: summary = "风险等级:高"
sub-2: summary = "风险等级:高"
sub-3: summary = "风险等级:低"
投票: "风险等级:高" 占 2/3 (67% > 50%)
合并结果 = { "summary": "风险等级:高", "votes": 2, "total": 3 }
```

### 3.4 适用场景

- 多 Agent 独立评估同一任务
- 需要多数共识

## 四、human（人工裁决）

### 4.1 算法

1. 收集全部结果
2. 不自动合并
3. 标记 `status=unresolved`
4. 输出全部结果供人工决策

### 4.2 调用

```bash
python scripts/resolve_conflicts.py resolve \
  --exec-id exec-001 --strategy human
```

### 4.3 适用场景

- 结果差异大,无法自动合并
- 高风险决策需人工确认
- 自动策略无法达成一致

## 五、latest（最近优先）

### 5.1 算法

1. 按 `completed_at` 时间倒序排列
2. 取最近完成的结果
3. 之前的忽略

### 5.2 调用

```bash
python scripts/resolve_conflicts.py resolve \
  --exec-id exec-001 --strategy latest
```

### 5.3 适用场景

- 时间敏感(如监控数据)
- 后完成的结果更准确(有更多上下文)

## 六、策略选择建议

| 需求 | 推荐策略 |
|------|---------|
| 有明确优先级 | priority |
| 需要多数共识 | voting |
| 高风险/差异大 | human |
| 时间敏感 | latest |
| 默认 | priority |

## 七、冲突记录

无论哪种策略,合并后均产出 `conflicts` 字段,记录被忽略的结果:

```json
{
  "merge_strategy": "priority",
  "merged_result": { "summary": "A方案", "source": "sub-1" },
  "conflicts": [
    { "agent": "sub-2", "summary": "B方案", "reason": "priority 低于 sub-1" }
  ]
}
```

便于复盘:为什么选了 A 而非 B。
