# 指标定义(metrics-definition)

> 本文件定义 skill-usage-tracker 统计的全部指标,供 `scripts/stats.py` 计算时对照,供用户查阅"指标怎么算"。

---

## 一、调用次数(calls)

某 skill 在时间范围内的总调用次数(含成功与失败)。

- **统计口径**:按 `skill` 字段分组计数
- **用途**:识别高频 skill(优化投入回报高)
- **相关命令**:`stats.py top --by calls`

---

## 二、耗时分布(duration_ms)

单次调用的耗时(毫秒),由 `end_time - start_time` 计算。

| 指标 | 含义 | 计算方式 |
|------|------|---------|
| `avg_ms` | 平均耗时 | sum(duration_ms) / calls |
| `p50_ms` | 中位数 | 50% 调用低于此值 |
| `p95_ms` | 95 分位 | 95% 调用低于此值 |
| `p99_ms` | 99 分位 | 99% 调用低于此值 |

- **分位数计算**:对某 skill 的全部 duration_ms 排序后取分位
- **用途**:识别慢 skill(p95 超阈值)
- **相关命令**:`stats.py slow --threshold-ms 60000`

---

## 三、失败率(fail_rate)

- **计算公式**:`fail_rate = fail_count / total_calls`
- **success_rate**:`1 - fail_rate`
- **阈值**:> 10% 标记为"高失败率 skill"(写入 `high_fail_skills`)
- **用途**:关联 failure-casebook 查根因
- **相关命令**:`stats.py top --by failures`

---

## 四、慢 skill 判定

- **默认阈值**:`p95_ms > 60000`(60 秒)
- **可配置**:`--threshold-ms <毫秒>` 参数
- **输出**:超阈值的 skill 列表(写入 `slow_skills`)
- **建议**:慢 skill 关联 failure-casebook 查历史性能问题

---

## 五、未使用 skill(unused_skills)

- **定义**:时间范围内 0 次调用的 skill
- **来源**:工作台全部 skill 目录 - 实际有调用记录的 skill
- **用途**:建议归档(写入 `unused_skills`)
- **相关命令**:`suggest.py`

---

## 六、调用 ID(call_id)

- **格式**:`call-{YYYYMMDD}-{序号}`(如 `call-20260806-001`)
- **生成规则**:未提供 `--call-id` 时自动生成(时间戳 + 当日序号)
- **贯穿链路**:`workflow-runtime` 分配 → `skill-usage-tracker` 记录 → `failure-casebook` 关联
- **用途**:追溯单次调用的完整上下文(耗时/输入/产物/失败原因)

---

## 七、usage-stats.json 字段对照

| 字段 | 指标 | 来源 |
|------|------|------|
| `total_calls` | 总调用数 | 全部记录计数 |
| `success_rate` | 成功率 | 1 - fail_rate |
| `avg_duration_ms` | 平均耗时 | 全部记录的 avg_ms |
| `p95_ms` | 95 分位耗时 | 全部记录的 p95 |
| `p99_ms` | 99 分位耗时 | 全部记录的 p99 |
| `by_skill[].calls` | 单 skill 调用数 | 按 skill 分组 |
| `by_skill[].avg_ms` | 单 skill 平均耗时 | 分组 avg |
| `by_skill[].fail_rate` | 单 skill 失败率 | 分组 fail_count / calls |
| `by_skill[].p95_ms` | 单 skill 95 分位 | 分组 p95 |
| `slow_skills` | 慢 skill 列表 | p95 > 阈值 |
| `high_fail_skills` | 高失败率 skill | fail_rate > 10% |
| `unused_skills` | 未使用 skill | 0 次调用 |
