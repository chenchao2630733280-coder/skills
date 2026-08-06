# 调优规则（Tuning Rules）

> 本文件定义 adaptive-tuner 的调优判定规则、置信度计算与白名单。

## 一、调优判定规则

### 1.1 timeout 调优

| 触发条件 | 建议动作 | 约束 |
|----------|---------|------|
| P95 > timeout × 80% | 提高 timeout 至 `P95 × 1.5`（向上取整到 30 秒倍数） | 新 timeout ≤ 原 timeout × 2 |
| P99 > timeout | 提高 timeout 至 `P99 × 1.2`（向上取整到 30 秒倍数） | 新 timeout ≤ 原 timeout × 2 |
| P95 < timeout × 30% | 降低 timeout 至 `P95 × 2`（节省资源） | 新 timeout ≥ 60s |

**默认值**：未声明 runtime.yaml 的 skill，默认 timeout=300s。

### 1.2 retry 调优

| 触发条件 | 建议动作 | 约束 |
|----------|---------|------|
| fail_rate > 10%（可重试类失败） | 增加 retry.max +1 | retry.max ≤ 5 |
| fail_rate > 30%（不可重试类失败） | 不增加 retry，建议检查 skill 实现 | - |
| retry 后仍失败 > 50% | 建议调整降级策略而非增加 retry | - |

**退避策略**：默认 `exponential`（指数退避），不修改原有 backoff 策略。

### 1.3 降级阈值调优

| 触发条件 | 建议动作 |
|----------|---------|
| degrade_count > calls × 20% | 建议检查降级触发条件是否过于敏感 |
| degrade_count = 0 且 fail_rate > 10% | 建议增加降级策略（当前无降级但有失败） |

**注意**：降级策略调整风险较高，只生成建议，不自动修改 degrade 字段。

## 二、置信度计算

### 2.1 公式

```
confidence = min(sample_count / 30, 1.0) × (1 - variance_penalty)
```

### 2.2 参数说明

- `sample_count`：该 skill 的调用次数（来自 usage-tracker 的 by_skill.calls）
- `variance_penalty`：耗时方差惩罚
  - 计算方式：`variance = var(durations) / mean(durations)^2`
  - `variance_penalty = min(variance / 2, 0.5)`（上限 0.5）
  - 方差大（耗时波动大）则置信度降低

### 2.3 置信度分级

| 范围 | 级别 | 处理 |
|------|------|------|
| ≥ 0.7 | 高置信度 | 生成建议，可应用 |
| 0.5 ~ 0.7 | 中置信度 | 生成建议，标"建议验证" |
| < 0.5 | 低置信度 | 生成建议，标"低置信度，仅供参考" |
| 样本 < 10 | 数据不足 | 不生成建议，标"数据不足" |

## 三、白名单（不参与调优）

以下 skill 因安全/稳定性考虑，不参与自动调优：

| skill | 原因 |
|-------|------|
| guardrail | 安全护栏，参数变更影响安全策略一致性 |
| skill-auditor | 评测 skill，参数变更影响评测基准一致性 |
| diff-reviewer | 审查 skill，同上 |
| adaptive-tuner | 自身，避免自指调优 |

**扩展**：用户可通过 `--whitelist-add` / `--whitelist-remove` 自定义白名单（未来版本）。

## 四、保守调整原则

1. **不删除已有字段**：调优只增加/修改 timeout/retry，不删除 skill 已有的 degrade/inputs/outputs。
2. **不突破上限**：timeout ≤ 默认 × 2；retry.max ≤ 5。
3. **保留原 backoff**：若 skill 已声明 backoff 策略，不修改。
4. **单次调整幅度**：timeout 单次调整不超过原值的 50%（避免剧烈变化）。

## 五、特殊场景处理

### 5.1 无 runtime.yaml 的 skill

未声明 runtime.yaml 的 skill，使用默认值（timeout=300/retry=0）作为基准分析。
若建议调整，生成的 overrides 会包含完整字段（相当于新建 runtime.yaml 的覆盖）。

### 5.2 并行 skill（parallel_with）

并行执行的 skill（如 game-asset-forge ∥ game-code-forge），取两者中较慢的 P95 作为
timeout 调优基准，确保两者都不会因对方慢而超时。

### 5.3 冷启动 skill

调用次数 < 5 的 skill，标"数据不足，保持默认"，不生成建议。
建议用户先运行更多任务积累数据。
