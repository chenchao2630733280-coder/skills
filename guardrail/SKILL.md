---
name: "guardrail"
description: "安全护栏 skill。在 skill 执行前后做安全检查:敏感路径保护/操作分级/diff 审查。当编排总纲或其他 skill 要执行变更操作时调用。"
---

# 安全护栏 (Guardrail)

## 一、定位与职责

guardrail 是一套**只读不写**的安全护栏,职责:

- **前置拦截**:在编排总纲或任何 skill 执行变更操作(写/删文件、运行命令)之前,检查目标路径是否安全、操作级别是否允许。
- **后置审查**:在 skill 产出之后,对 diff 做风险审查,识别危险变更(删文件、大幅删减、配置/依赖变更)。
- **不改产物**:guardrail 不修改任何被检查的文件,只输出 `guardrail-report.json` 报告供编排总纲决策。

guardrail **绝不**直接修改用户工程文件,所有结论以报告形式返回。

## 二、操作分级表

| 级别 | 含义 | 处置 |
|------|------|------|
| 只读 (read-only) | 读取文件、查询状态、列出目录 | 直接放行 |
| 低风险变更 (low) | 写入非敏感路径、新增普通文件 | 记录到报告,放行 |
| 高风险变更 (high) | 写入/覆盖敏感路径 | 需用户二次确认后才能执行 |
| 禁止 (forbidden) | 删除敏感路径、覆盖密钥、改写核心代码 | 直接拦截,返回 error |

判定依据见 `references/operation-levels.md`。

## 三、敏感路径清单

默认敏感清单(详见 `references/sensitive-paths.md`):

- **生产配置**:`config/production/*.yml`、`*.env.prod`、`.env.production`
- **数据库**:`migrations/`、`schema.sql`、`db/init/`
- **核心代码**:`src/core/`、`main.ts`、`app/main.py`、`cmd/server/main.go`
- **密钥**:`*.key`、`*.pem`、`id_rsa`、`credentials*`、`.env`(纯本地 secret)

项目可通过根目录 `.guardrail.yml` 覆盖默认清单(增删规则)。

## 四、scripts 调用方式

所有脚本相对 guardrail skill 目录执行。脚本只读不写,仅产出 `guardrail-report.json`。

### 4.1 前置路径检查

```bash
python scripts/check_paths.py --paths src/core/auth.ts,config/production/app.yml --operation write
```

参数:
- `--paths`:逗号分隔,或多次传入 `--paths a --paths b`
- `--operation`:`read` / `write` / `delete`
- `--output`:报告输出路径(默认 `guardrail-report.json`)
- `--project-root`:项目根目录(用于加载 `.guardrail.yml`)

示例(多次传入):

```bash
python scripts/check_paths.py --operation delete --paths migrations/001.sql --paths .env.prod
```

### 4.2 后置 diff 审查

```bash
# 方式一:传入 before/after 路径(目录或文件)
python scripts/diff_review.py --before ./old_dir --after ./new_dir

# 方式二:传入 git diff 文本(- 表示从 stdin 读取)
git diff HEAD~1 | python scripts/diff_review.py --diff -
```

参数:
- `--before` / `--after`:目录或文件路径
- `--diff`:git diff 文本文件路径,传 `-` 从 stdin 读取
- `--output`:报告输出路径(默认 `guardrail-report.json`)

## 五、产出契约

`guardrail-report.json` 结构:

```json
{
  "checkType": "path-check | diff-review",
  "operation": "read | write | delete | diff",
  "paths": ["src/core/auth.ts", "config/production/app.yml"],
  "riskLevel": "low | high | forbidden",
  "blocked": false,
  "warnings": ["写入敏感路径需用户二次确认 (匹配规则: config/production/.*\\.ya?ml$)"],
  "timestamp": "2026-08-06T10:00:00+08:00"
}
```

diff-review 额外字段:`riskChanges` 数组,每项形如:

```json
{ "file": "config/production/app.yml", "change": "config-changed", "severity": "medium", "reason": "配置文件发生变更" }
```

`change` 取值:`deleted` / `large-reduction` / `config-changed` / `dependency-changed` / `added-dependency`。

退出码:`0` = 通过;`2` = 存在 forbidden/blocked 项。

## 六、与编排总纲的接入

1. **前置检查**:编排总纲在执行任何 Tool 变更操作(Edit/Write/Delete/RunCommand 写类)之前,先调用 `check_paths.py`,根据 `riskLevel` 决策:
   - `low` → 放行
   - `high` → 暂停,提示用户二次确认
   - `forbidden` → 拦截,不执行
2. **后置审查**:skill 产出后(可选),编排总纲调用 `diff_review.py` 审查变更,若 `riskChanges` 含 forbidden/high 删除项,要求回滚或人工复核。
3. **接入位置**:前置检查在"Tool 调用前"钩子;后置审查在"skill 产出后"钩子,二者均非阻塞式调用脚本,由编排总纲读取报告再决策。

## 七、失败处理

- 检查脚本本身崩溃(异常退出、JSON 解析失败)→ 编排总纲降级为"标记未知风险,放行但标 WARNING",不阻塞主流程,报告中 `warnings` 包含 `guardrail-check-failed: <reason>`。
- 路径不存在 → check_paths 视为 `low`(无对象可破坏),但 warnings 中记录;diff_review 跳过该路径并在 warnings 中记录。
- 敏感清单加载失败(`.guardrail.yml` 解析异常)→ 使用内置默认清单,并在 warnings 中记录降级。
- 退出码非 0/2 → 一律视为脚本失败,按降级策略处理。

## 八、质量检查清单

- [ ] SKILL.md 行数 ≤300
- [ ] 两个 Python 脚本 `--help` 不报错
- [ ] 脚本含 shebang 与 `if __name__ == '__main__': main()`,函数有 docstring
- [ ] 报告 JSON 字段齐全(checkType/operation/paths/riskLevel/blocked/warnings/timestamp)
- [ ] 敏感路径正则覆盖四类(配置/数据库/核心代码/密钥)
- [ ] 操作分级矩阵覆盖 read/write/delete × 敏感级别
- [ ] 失败降级路径有文档说明
- [ ] 中文注释、UTF-8 编码
