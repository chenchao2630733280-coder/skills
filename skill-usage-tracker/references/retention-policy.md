# 数据保留策略(retention-policy)

> 本文件定义 skill-usage-tracker 的数据保留与清理规则,供 `scripts/stats.py` 清理过期数据时查阅。

---

## 一、默认保留期

- **90 天**
- 过期记录(`start_time` 早于"当前时间 - 保留期")在清理时删除

---

## 二、清理规则

### 清理时机
- 每次运行 `stats.py summary` 时自动检查过期记录
- 也可手动触发:`stats.py clean`(若实现)

### 清理范围
- `start_time < (当前时间 - 保留期)` 的记录
- 仅清理 `records.jsonl` 中的过期行,不删除统计产物

### 清理前提示
- 默认清理前打印待清理记录数,提示用户确认
- 可配置 `--auto-clean` 跳过确认(自动化场景)

---

## 三、配置方式

按优先级从高到低:

1. **命令行参数**:`--retention-days <天数>`
2. **环境变量**:`USAGE_RETENTION_DAYS`(默认 90)
3. **配置文件**:`.trae-cn/usage/config.json` 的 `retention_days` 字段(可选)
4. **默认值**:90 天

### 配置示例

```json
// .trae-cn/usage/config.json
{
  "retention_days": 180,
  "auto_clean": false,
  "slow_threshold_ms": 60000,
  "high_fail_threshold": 0.1
}
```

---

## 四、存储位置

| 文件 | 用途 | 清理规则 |
|------|------|---------|
| `.trae-cn/usage/records.jsonl` | 调用记录(追加写入) | 按保留期清理过期行 |
| `.trae-cn/usage/usage-stats.json` | 统计产物 | 每次统计时覆盖 |
| `.trae-cn/usage/optimization-suggestions.md` | 优化建议 | 每次生成时覆盖 |
| `.trae-cn/usage/config.json` | 配置(可选) | 不清理 |

**不提交 Git**:整个 `.trae-cn/usage/` 目录加入 `.gitignore`。

---

## 五、数据安全

- **不含敏感信息**:记录仅含 skill 名 / 耗时 / 状态 / 失败码 / 产物路径
- **失败码为枚举值**:不含堆栈详情(堆栈由 failure-casebook 单独管理)
- **产物路径不含内容**:仅记录路径字符串,不记录文件内容
- **连接串/密钥不记录**:由调用方(workflow-runtime)确保不传入敏感字段

---

## 六、保留期调整建议

| 场景 | 建议保留期 | 原因 |
|------|-----------|------|
| 个人开发 | 30 天 | 数据量小,短期够用 |
| 团队协作 | 90 天(默认) | 覆盖一个季度的迭代周期 |
| 长期优化 | 180 天 | 观察长期趋势 |
| 合规要求 | 按合规要求 | 不低于法规最低保留期 |

调整时通过环境变量或配置文件设置,不影响已存记录。
