---
name: "skill-usage-tracker"
description: "Data 层 skill。记录每次 skill 调用数据(名称/耗时/成败/产物),统计高频/慢/失败率 skill,产出优化建议。当 workflow-runtime 执行 skill 时自动记录,或用户要'看 skill 使用统计/优化建议'时调用。纯记录不阻塞执行。"
---

# skill-usage-tracker

## 一、何时调用

满足以下任一条件即调用本 skill:

- 用户说"记录 skill 调用 / usage-tracker record"
- 用户说"看 skill 使用统计 / 调用排名 / 慢 skill / 失败率"
- 用户说"skill 优化建议 / 哪些 skill 需优化"
- `workflow-runtime` 执行 skill 前后,自动调 `record` 记录调用数据
- `failure-casebook` 记录失败时,关联本 skill 的调用 ID

**不要**在以下场景调用:
- 用户只是问"某 skill 怎么用"(直接调该 skill)
- 要修改 skill 逻辑(本 skill 只记录不修改)
- 单次 skill 调用的性能调试(用 debug-fix)

本 skill **纯记录不阻塞**:记录失败不影响 skill 执行,数据写入 `.trae-cn/usage/`(不提交 Git)。

---

## 二、数据模型

每条调用记录追加写入 `.trae-cn/usage/records.jsonl`(JSON Lines 格式,便于追加):

```json
{
  "call_id": "call-20260806-001",
  "skill": "game-asset-forge",
  "pipeline": "game-forge",
  "start_time": "2026-08-06T10:00:00+08:00",
  "end_time": "2026-08-06T10:05:30+08:00",
  "duration_ms": 330000,
  "status": "success | fail",
  "error_code": null,
  "outputs": ["assets/role/hero.png"],
  "caller": "workflow-runtime"
}
```

完整指标定义见 `references/metrics-definition.md`,保留策略见 `references/retention-policy.md`。

---

## 三、scripts 调用方式

### track_usage.py

#### record(记录单次调用)

```
python scripts/track_usage.py record --skill <skill名> [--pipeline <流水线>] [--status success|fail] [--duration-ms <毫秒>] [--call-id <调用ID>] [--outputs <产物路径...>]
```

- 追加一条记录到 `records.jsonl`
- 未提供 `--call-id` 时自动生成(时间戳+序号)
- 未提供 `--duration-ms` 时从 start/end 推算

#### query(查询调用记录)

```
python scripts/track_usage.py query --skill <skill名> [--from <开始日期>] [--to <结束日期>] [--status fail] [--limit 20]
```

- 按条件筛选调用记录
- 输出匹配记录列表

### stats.py

#### summary(汇总统计)

```
python scripts/stats.py summary [--from <开始日期>] [--to <结束日期>]
```

- 输出指定时间范围的汇总:总调用数 / 成功率 / 平均耗时 / P95 / P99
- 产出 `usage-stats.json`

#### top(调用排名)

```
python scripts/stats.py top [--by calls|duration|failures] [--limit 10]
```

- 按 调用次数/总耗时/失败次数 排名

#### slow(慢 skill)

```
python scripts/stats.py slow [--threshold-ms <毫秒>] [--limit 10]
```

- 列出平均耗时超阈值的 skill(P95)

### suggest.py(优化建议)

```
python scripts/suggest.py [--from <开始日期>] [--to <结束日期>]
```

- 基于统计数据生成优化建议
- 高频失败 skill 关联 `failure-casebook` 查询
- 慢 skill 建议优化
- 未使用 skill 建议归档
- 产出 `optimization-suggestions.md`

### 退出码

`0`=成功;`1`=有错误;`2`=参数错误。

---

## 四、references 使用指引

| 文件 | 读取时机 |
|------|---------|
| `references/metrics-definition.md` | (1) 用户问"指标怎么算";(2) stats 计算时对照指标定义 |
| `references/retention-policy.md` | (1) 用户问"数据保留多久";(2) 清理过期数据时查阅 |

两份 references 均为**懒加载**。

---

## 五、关键约束

1. **纯记录不阻塞**:record 失败时仅打印警告,不抛异常;调用方(workflow-runtime)不受影响。
2. **调用 ID 贯穿链路**:workflow-runtime 分配 call_id,failure-casebook 关联该 ID,便于追溯。
3. **数据存储**:`.trae-cn/usage/records.jsonl`(追加写入,不覆盖);统计产物在同目录。
4. **保留 90 天**:过期记录清理(可配置);清理前提示用户。
5. **统计可过滤**:按时间范围 / skill 名 / 流水线 / 状态过滤。
6. **失败不阻塞**:统计/建议生成失败时回填 error 字段返回 exit 1,不中断调用方。

---

## 六、与其他 skill 的关系

| skill | 关系 | 说明 |
|-------|------|------|
| `workflow-runtime` | 写入方 | 执行 skill 前后调 record 记录调用数据 |
| `failure-casebook` | 关联方 | 失败记录关联 call_id,查询时可返回调用上下文 |
| `skill-auditor` | 消费方 | 可读取统计数据辅助评测 skill 质量 |
| `replanner` | 消费方 | 重规划时参考慢 skill / 高失败率 skill 数据 |
| `adaptive-tuner` | 数据消费方 | 读取本 skill 产出的 usage-stats.json 作为调优数据源 |

---

## 七、usage-stats.json schema

```json
{
  "period": "2026-08-01~2026-08-31",
  "total_calls": 320,
  "success_rate": 0.92,
  "avg_duration_ms": 45000,
  "p95_ms": 180000,
  "p99_ms": 300000,
  "by_skill": [
    {
      "skill": "game-asset-forge",
      "calls": 45,
      "avg_ms": 120000,
      "fail_rate": 0.11,
      "p95_ms": 180000
    }
  ],
  "slow_skills": ["game-asset-forge"],
  "high_fail_skills": ["tool-deploy-ops"],
  "unused_skills": ["tool-ci-ops"]
}
```

---

## 八、质量检查清单

### 8.1 纯记录不阻塞约束
- [ ] SKILL.md 已声明"纯记录不阻塞",record 失败仅打印警告,不抛异常。

### 8.2 产物自评项
- [ ] `python scripts/track_usage.py --help` 不报错,`record` / `query` 子命令可见。
- [ ] `python scripts/stats.py --help` 不报错,`summary` / `top` / `slow` 子命令可见。
- [ ] `python scripts/suggest.py --help` 不报错。
- [ ] record 能追加记录到 `records.jsonl`,字段齐全(call_id/skill/start_time/status)。
- [ ] query 能按 skill 名 + 时间范围筛选。
- [ ] summary 能计算调用数/成功率/平均耗时/P95。
- [ ] top 能按调用次数排名。
- [ ] slow 能列出超阈值的 skill。
- [ ] suggest 能生成优化建议 Markdown。
- [ ] `references/metrics-definition.md` 含指标定义(调用数/耗时分布/失败率/P95/P99)。
- [ ] `references/retention-policy.md` 含保留策略(默认 90 天 + 清理规则)。
- [ ] SKILL.md 行数 ≤500,frontmatter 含 name + description。
- [ ] 所有文件 UTF-8 编码,文档与代码注释为中文。
- [ ] 产物自评:本 skill 产出后,按 skill-auditor 执行后评测模式自查(可选)。
