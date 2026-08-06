# runtime-overrides.yaml 格式规范

> 本文件定义 adaptive-tuner 产出的 runtime-overrides.yaml 的格式。

## 一、顶层结构

```yaml
# 由 adaptive-tuner 生成，供 workflow-runtime 应用
generated_at: "2026-08-06T10:30:00+08:00"
data_source: "~/.trae-cn/usage/usage-stats.json"
tuner_version: "1.0"
overrides:
  - skill: <skill名>
    timeout: <秒>
    retry:
      max: <次数>
      backoff: <exponential | linear | fixed>
    reason: "<调优原因>"
    confidence: <0.0~1.0>
    sample_count: <样本数>
  # ... 更多 skill 的覆盖
```

## 二、字段说明

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `generated_at` | string(ISO-8601) | 是 | 生成时间 |
| `data_source` | string | 是 | 数据来源（usage-stats.json 路径） |
| `tuner_version` | string | 是 | 生成器版本 |
| `overrides` | array | 是 | 覆盖列表 |
| `overrides[].skill` | string | 是 | 目标 skill 名 |
| `overrides[].timeout` | integer | 否 | 覆盖的 timeout 值（秒） |
| `overrides[].retry` | object | 否 | 覆盖的 retry 配置 |
| `overrides[].retry.max` | integer | 否 | 最大重试次数（≤5） |
| `overrides[].retry.backoff` | enum | 否 | 退避策略 |
| `overrides[].reason` | string | 是 | 调优原因（含数据依据） |
| `overrides[].confidence` | float | 是 | 置信度（0.0~1.0） |
| `overrides[].sample_count` | integer | 是 | 样本数 |

## 三、覆盖优先级

应用覆盖时，优先级如下（高 → 低）：

1. **external_overrides**（adaptive-tuner 产出，最高）
2. **runtime.yaml 本地字段**（skill 声明）
3. **默认值**（timeout=300 / retry=0）

workflow-runtime 执行 step 时：
- 若 step.runtime 引用了 runtime.yaml，且该 runtime.yaml 的 external_overrides 指向了
  adaptive-tuner 的 overrides 文件，则先加载 overrides，再合并本地字段。

## 四、完整示例

```yaml
generated_at: "2026-08-06T10:30:00+08:00"
data_source: "~/.trae-cn/usage/usage-stats.json"
tuner_version: "1.0"
overrides:
  - skill: game-asset-forge
    timeout: 900
    retry:
      max: 3
      backoff: exponential
    reason: "P95=580s 接近 timeout 600s;fail_rate=12% 建议增加重试"
    confidence: 0.85
    sample_count: 45

  - skill: tool-deploy-ops
    timeout: 600
    reason: "P95=280s 接近 timeout 300s"
    confidence: 0.72
    sample_count: 18

  - skill: game-code-forge
    retry:
      max: 2
    reason: "fail_rate=8%,增加 1 次重试提升成功率"
    confidence: 0.68
    sample_count: 22
```

## 五、应用与回退

### 5.1 应用（apply）

执行 `apply --overrides runtime-overrides.yaml --confirm yes` 时：
1. 备份每个目标 skill 的原 runtime.yaml 到 `~/.trae-cn/tuner-backups/{timestamp}/{skill}.yaml.bak`
2. 合并覆盖到 runtime.yaml（不删除已有字段，只覆盖 timeout/retry）
3. 记录应用结果到 `apply-result.json`

### 5.2 回退（revert）

执行 `revert --backup <备份路径>` 时：
1. 读取备份目录下的各 skill 备份文件
2. 用备份内容覆盖当前 runtime.yaml
3. 记录回退结果到 `revert-result.json`

## 六、约束

1. **不生成空 overrides**：若无 skill 需调优，overrides 为空数组 `[]`，文件仍生成。
2. **不包含白名单 skill**：guardrail/skill-auditor/diff-reviewer 不出现在 overrides 中。
3. **置信度标注**：每条 override 必须含 confidence 字段。
4. **reason 必须含数据依据**：如"P95=580s"、"fail_rate=12%"，非笼统描述。
