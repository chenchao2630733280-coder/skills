# 操作分级规则

定义 read/write/delete 对各路径级别的判定矩阵,供 `check_paths.py` 实现。

## 操作类型

| 操作 | 含义 | 示例 |
|------|------|------|
| `read` | 读取文件、查询、列目录 | Read 工具、Glob、Grep |
| `write` | 新建、覆盖、追加写文件 | Write、Edit |
| `delete` | 删除文件或目录 | DeleteFile |

## 路径敏感级别

| 级别 | 判定 |
|------|------|
| 普通路径 | 不匹配 `sensitive-paths.md` 任一规则 |
| 敏感路径 | 匹配 `sensitive-paths.md` 任一规则 |

## 判定矩阵

| 操作 \ 路径 | 普通路径 | 敏感路径 |
|-------------|----------|----------|
| `read` | 只读放行 (low, blocked=false) | 只读放行 (low, blocked=false) |
| `write` | 低风险 (low, blocked=false) | 高风险 (high, blocked=false,需确认) |
| `delete` | 低风险 (low, blocked=false) | 禁止 (forbidden, blocked=true,拦截) |

## 风险级别处置

| 风险级别 | blocked | 编排总纲处置 | 退出码 |
|----------|---------|-------------|--------|
| `low` | false | 放行,记录到报告 | 0 |
| `high` | false | 暂停,提示用户二次确认 | 0 |
| `forbidden` | true | 直接拦截,不执行 | 2 |

## 升级与汇总规则

- **多路径检查**:取所有路径中的最高风险级别作为总体 `riskLevel`。
- **任一路径 forbidden** → 总体 `blocked=true`,退出码 2。
- **路径不存在**:read/write/delete 均视为 `low`(无对象可破坏),但在 `warnings` 中记录"路径不存在"。
- **未知操作**:降级为 `low`,不阻断。

## 后置审查(diff-review)补充

`diff_review.py` 额外引入 `medium` 级别用于配置文件变更,其 `riskLevel` 汇总顺序为:
`low < medium < high`。仅 `change=deleted` 且 `severity=high` 时 `blocked=true`,其余高风险项由编排总纲决定是否要求人工复核或回滚。
