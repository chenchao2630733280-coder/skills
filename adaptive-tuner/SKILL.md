---
name: "adaptive-tuner"
description: "Data 自适应优化层 skill。基于 skill-usage-tracker 的调用统计数据，自动生成 skill 参数优化建议（timeout/retry/降级阈值），产出 runtime-overrides.yaml 供 workflow-runtime 应用。当要基于历史数据优化 skill 运行时参数、或用户要'看 skill 调优建议'时调用。不自动应用，需用户确认。"
---

# adaptive-tuner — Data 自适应优化层

adaptive-tuner 是 AI Agent 体系第四阶段升级的 **Data 自适应优化层 skill**。它读取
`skill-usage-tracker` 积累的调用统计数据，分析每个 skill 的运行特征（耗时分布/失败率/降级频率），
自动生成参数优化建议（timeout/retry/降级阈值），产出 `runtime-overrides.yaml` 供
`workflow-runtime` 应用，形成"数据采集 → 分析 → 优化 → 应用"的闭环。

- **数据驱动优化**：所有建议基于 `skill-usage-tracker` 的实际调用数据，非臆测。
- **不自动应用**：建议生成后需用户确认才应用到 `runtime.yaml`，避免破坏稳定性。
- **保守调整**：timeout 调整幅度不超过默认值 2 倍，retry 上限 5 次。
- **白名单机制**：关键 skill（guardrail/skill-auditor）不参与自动调优（安全考虑）。

## 一、何时调用

满足以下任一条件即调用本 skill：

1. **定期调优**：用户要基于历史数据优化 skill 运行时参数。
   - 如："看看哪些 skill 需要调优"
   - 如："生成 runtime-overrides.yaml"
2. **慢 skill 优化**：某 skill 频繁超时或接近超时阈值，要调整 timeout。
3. **高失败率 skill 优化**：某 skill 失败率高，要增加 retry 或调整降级策略。
4. **应用/回退覆盖**：用户要应用调优建议到 runtime.yaml，或回退已应用的覆盖。

**不要**在以下场景调用：
- 用户要记录 skill 调用数据（走 `skill-usage-tracker`，本 skill 只读其数据）
- 用户要定义 runtime.yaml 契约（走 `skill-runtime`，本 skill 只生成覆盖）
- 用户要执行 workflow（走 `workflow-runtime`，本 skill 只产出覆盖文件）

## 二、与其他 skill 的关系

| 维度 | skill-usage-tracker | adaptive-tuner（本 skill） | workflow-runtime |
|------|---------------------|--------------------------|------------------|
| 职责 | **采集**：记录每次调用数据 | **分析+建议**：基于数据生成优化建议 | **应用**：执行时应用覆盖 |
| 产出 | records.jsonl + usage-stats.json | tuning-suggestions.json + runtime-overrides.yaml | workflow-exec-report.json |
| 何时介入 | 每次 skill 调用前后 | 定期或用户主动触发 | 执行 workflow.yaml 前 |
| 是否替代对方 | 否（数据源） | 否（分析层） | 否（应用层） |

**数据闭环**：
```
skill-usage-tracker 记录调用数据
  → adaptive-tuner 分析数据生成建议
  → 用户确认后生成 runtime-overrides.yaml
  → workflow-runtime 执行时应用覆盖
  → 新的调用数据回流到 skill-usage-tracker
```

## 三、分析规则

### 3.1 调优判定规则

| 触发条件 | 建议动作 | 置信度要求 |
|----------|---------|-----------|
| P95 > timeout × 80% | 提高 timeout 至 P95 × 1.5（上限默认值 2 倍） | 样本 ≥ 10 |
| fail_rate > 10% | 增加 retry.max（上限 5）或调整降级策略 | 样本 ≥ 10 |
| fail_rate > 30% | 建议检查 skill 实现或增加降级（不自动调 retry） | 样本 ≥ 10 |
| 频繁降级（degrade_count > calls × 20%） | 建议调整降级阈值或增加资源 | 样本 ≥ 10 |
| 调用次数 < 5 | 标记"数据不足，保持默认" | 不生成建议 |

### 3.2 置信度计算

```
confidence = min(sample_count / 30, 1.0) × (1 - variance_penalty)
```

- `sample_count`：该 skill 的调用次数
- `variance_penalty`：耗时方差惩罚（方差大则置信度降低）
- `confidence < 0.5`：标"低置信度"，建议仅供参考
- `confidence ≥ 0.5`：标"可应用"

### 3.3 白名单（不参与调优）

以下 skill 因安全/稳定性考虑，不参与自动调优：
- `guardrail`（安全护栏，参数变更影响安全策略）
- `skill-auditor`（评测 skill，参数变更影响评测一致性）
- `diff-reviewer`（审查 skill，同上）

## 四、子命令清单

本 skill 通过 `scripts/analyze_usage.py` 提供四个子命令：

### 1. analyze —— 分析统计数据

| 项 | 说明 |
|---|---|
| 输入 | `--stats`(可选，默认读 `~/.trae-cn/usage/usage-stats.json`，否则提示先运行 skill-usage-tracker stats) |
| 输出 | 打印各 skill 的运行特征摘要（调用次数/P95/失败率/是否需调优） |

### 2. suggest —— 生成调优建议

| 项 | 说明 |
|---|---|
| 输入 | `--stats`(可选)、`--output`(可选，默认当前目录) |
| 输出 | `tuning-suggestions.json`(机读建议清单) + `runtime-overrides.yaml`(可应用覆盖) |

### 3. apply —— 应用覆盖（需用户确认）

| 项 | 说明 |
|---|---|
| 输入 | `--overrides`(runtime-overrides.yaml 路径)、`--confirm`(必须传 yes 才执行) |
| 输出 | 各 skill 的 runtime.yaml 备份路径 + 应用结果 |
| 前置 | 必须传 `--confirm yes`，否则拒绝执行 |

### 4. revert —— 回退覆盖

| 项 | 说明 |
|---|---|
| 输入 | `--backup`(apply 时产出的备份路径) |
| 输出 | 各 skill 的 runtime.yaml 恢复结果 |

## 五、scripts 调用方式

脚本路径：`scripts/analyze_usage.py`，使用标准 Python 3，无外部依赖。

### 分析统计数据

```bash
python scripts/analyze_usage.py analyze
python scripts/analyze_usage.py analyze --stats ~/.trae-cn/usage/usage-stats.json
```

### 生成调优建议

```bash
python scripts/analyze_usage.py suggest --output .
```

产出 `tuning-suggestions.json` + `runtime-overrides.yaml`。

### 应用覆盖（需确认）

```bash
python scripts/analyze_usage.py apply --overrides runtime-overrides.yaml --confirm yes
```

应用前自动备份各 skill 的原 runtime.yaml 到 `~/.trae-cn/tuner-backups/{timestamp}/`。

### 回退覆盖

```bash
python scripts/analyze_usage.py revert --backup ~/.trae-cn/tuner-backups/20260806-103000/game-asset-forge.yaml.bak
```

### 查看帮助

```bash
python scripts/analyze_usage.py --help
python scripts/analyze_usage.py suggest --help
```

## 六、产出 schema

### 6.1 tuning-suggestions.json

```json
{
  "generated_at": "2026-08-06T...",
  "data_source": "~/.trae-cn/usage/usage-stats.json",
  "total_skills_analyzed": 15,
  "suggestions_count": 3,
  "suggestions": [
    {
      "skill": "game-asset-forge",
      "current": { "timeout": 600, "retry": { "max": 2 } },
      "suggested": { "timeout": 900, "retry": { "max": 3, "backoff": "exponential" } },
      "reason": "P95=580s 接近 timeout 600s;fail_rate=12% 建议增加重试",
      "confidence": 0.85,
      "sample_count": 45,
      "applied": false
    }
  ],
  "skipped": [
    { "skill": "guardrail", "reason": "白名单（安全 skill 不调优）" },
    { "skill": "game-blueprint", "reason": "数据不足（<5 次调用）", "sample_count": 3 }
  ]
}
```

### 6.2 runtime-overrides.yaml

详见 `references/override-format.md`。

## 七、references 使用指引

| 文件 | 用途 | 何时查 |
|------|------|--------|
| `references/tuning-rules.md` | 调优规则（timeout/retry/降级阈值的调整算法 + 白名单） | (1) 修改调优判定逻辑；(2) 用户问"调优规则是什么"；(3) 新增调优维度时 |
| `references/override-format.md` | runtime-overrides.yaml 格式规范 + 示例 | (1) 生成 overrides 时对照格式；(2) 用户问"overrides 格式"；(3) workflow-runtime 解析时 |

两份 references 均为**懒加载**：仅在需要时读取。

## 八、与其他 skill 的协作

| skill | 关系 | 协作方式 |
|-------|------|---------|
| `skill-usage-tracker` | 数据源 | 本 skill 读取其 `usage-stats.json`；数据不足时提示先运行 `stats` 子命令 |
| `workflow-runtime` | 应用方 | workflow-runtime 执行前可选读本 skill产出的 `runtime-overrides.yaml`，合并到 step.runtime |
| `skill-runtime` | 契约方 | 本 skill 的覆盖遵循 skill-runtime 的 runtime.yaml schema；覆盖优先级见 skill-runtime 的 external_overrides 字段 |
| `failure-casebook` | 关联方 | 高失败率 skill 的调优建议可关联 failure-casebook 的历史失败案例，辅助判断根因 |

## 九、失败处理

本 skill 自身的失败 **不阻断主流程**：

- `usage-stats.json` 不存在 → 打印提示"请先运行 skill-usage-tracker stats 生成统计数据"，exit 1
- 数据解析失败 → 打印 `WARNING: <详情>`，exit 1
- apply 时 runtime.yaml 不存在 → 跳过该 skill，记录到结果，继续处理其他 skill
- apply 时备份失败 → 拒绝应用该 skill，记录错误，继续处理其他 skill
- revert 时备份文件不存在 → 打印错误，exit 1

**设计原则**：建议生成失败只是没有优化建议，不影响 skill 正常运行；apply 失败只影响被调优的 skill，不中断整体。

## 十、关键约束

1. **不自动应用**：suggest 只生成建议文件，apply 必须用户传 `--confirm yes`。
2. **数据驱动**：所有建议基于 usage-tracker 实际数据，样本不足时标"数据不足"。
3. **保守调整**：timeout ≤ 默认值 × 2；retry.max ≤ 5；不删除 skill 已有的降级策略。
4. **白名单**：guardrail / skill-auditor / diff-reviewer 不参与调优。
5. **可回退**：apply 前备份，revert 可恢复。
6. **只读 usage-tracker 数据**：本 skill 不写 usage-tracker 的 records.jsonl。
7. **SKILL.md 行数 ≤ 500**。

## 十一、质量检查清单

- [ ] `python scripts/analyze_usage.py --help` 可正常输出，无报错
- [ ] `analyze` 能读取 usage-stats.json 并打印各 skill 运行特征
- [ ] `suggest` 能生成 tuning-suggestions.json + runtime-overrides.yaml
- [ ] `apply` 无 `--confirm yes` 时拒绝执行
- [ ] `apply --confirm yes` 能备份原 runtime.yaml 并应用覆盖
- [ ] `revert` 能从备份恢复 runtime.yaml
- [ ] 白名单 skill 不出现在建议中
- [ ] 样本不足的 skill 标"数据不足"，不生成建议
- [ ] 仅用标准库，无外部依赖；UTF-8 编码，中文注释
- [ ] SKILL.md 行数 ≤ 500
