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

### 补充风险类型:`external-rewrite`(外部改写)

`diff_review.py` 只看"这次改动"的 diff,**看不见"这次改动之外谁还动过交付物"**。
交付物可能被编辑器自动格式化、陈旧缓冲区回写、其他会话或外部脚本改动;这类改动**内容常常依然合规**
(被回退过的旧词是合法词、被重排过的表格不违反任何契约),故常规内容审查**全绿也发现不了**。

- **检出手段**:唯一可靠判据是**与快照逐字节比对**(见 SKILL.md §六),比对判据含三档:
  磁盘缺失 / 内容不一致 / **快照外新增**(只遍历快照内条目会漏掉这一档)。
- **风险级别**:一经发现,`riskLevel` 升至 `high`(不直接 `forbidden`;由编排总纲决定回退或人工复核)。
- **注意事项**:**"字节数相同"不等于"未改动"** —— 等长替换字节数相同但内容已变,必须比首个差异字节位。
