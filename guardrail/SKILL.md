---
name: "guardrail"
description: "安全护栏 skill。在 skill 执行前后做安全检查:敏感路径保护/操作分级/diff 审查/交付集快照挂钩(改前刷快照、改后比快照、外部改写取证)。当编排总纲或其他 skill 要执行变更操作时调用。"
---

# 安全护栏 (Guardrail)

## 一、定位与职责

guardrail 是一套**只读不写**的安全护栏,职责:

- **前置拦截**:在编排总纲或任何 skill 执行变更操作(写/删文件、运行命令)之前,检查目标路径是否安全、操作级别是否允许。
- **后置审查**:在 skill 产出之后,对 diff 做风险审查,识别危险变更(删文件、大幅删减、配置/依赖变更)。
- **快照挂钩**:批量改动交付集时,联动 `snapshot-guard` 做"**改前刷快照 / 改后比快照**",识别常规审查**看不见**的风险 —— **外部改写**(编辑器格式化、陈旧缓冲区回写、其他会话)。详见 §六。
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

`change` 取值:`deleted` / `large-reduction` / `config-changed` / `dependency-changed` / `added-dependency` / `external-rewrite`。

> **`external-rewrite`（外部改写）** 是一类特殊风险:**文件被本工具集之外的力量改动了**
> —— 编辑器自动格式化、陈旧缓冲区回写、其他会话、外部脚本。它的特殊之处在于:
> **常规内容审查查不出来**(被回退过的文件、被重排过的表格，内容依然"合规")。
> 唯一能发现它的判据是**与快照逐字节比对**(见 §六)。一经发现,`riskLevel` 升至 `high`。

退出码:`0` = 通过;`2` = 存在 forbidden/blocked 项。

---

## 六、交付集快照挂钩(改前刷 / 改后比)

guardrail 的路径检查与 diff 审查都**只看"这次改动"本身**,看不见**"这次改动之外谁还动过交付物"**。
交付物一旦被外部工具污染,常规审查全绿也发现不了 —— 故在**批量改动交付集**时,挂两个快照挂钩:

### 6.1 前置挂钩:改前必刷快照

在**任何批量改写/删除交付物**的操作之前:

1. 把"当前已验收快照"滚动为"上一轮快照"(`current` → `current.prev`)。
2. 重建"当前快照"(`current`)。
3. **不留快照就动手 = 没有回滚兜底、也没有后置比对基准**。

具体动作交 `snapshot-guard`(快照三态:历史基线 / 当前 / 上一轮)。

### 6.2 后置挂钩:改后必比快照

在改动落盘、门禁全绿之后:

1. 做**"磁盘 vs 快照"逐字节比对**(只读,退出码非 0 = 有差异)。
2. 比对判据含**三档**,缺一不可:
   - **磁盘缺失**(快照里有、磁盘没有)
   - **内容不一致**(首个差异字节位)
   - **快照外新增**(快照没有、磁盘有 —— 只遍历快照内条目会漏掉这一档)
3. 有差异 → `riskLevel` 升 `high`,触发 §6.3 取证;**不要急着重刷快照**(那等于把污染"洗白"成基线)。

> ⚠️ **"字节数相同"不能当"未改动"**:等长替换(同样是 8 个字符的两个词)字节数相同,
> 但内容已变。必须比**首个差异字节位**,不能比大小。

### 6.3 外部改写取证(发现 `external-rewrite` 后)

1. **定位范围**:列出 `mtime` 晚于快照 `mtime` 的文件(候选集)。
2. **保全现场**:差异文件先备份(备份用 **`.txt`** 后缀 —— 用 `.md`/`.py` 会被文档扫描器/门禁误扫)。
3. **逐条还原**:按快照逐条覆写(**不用 `extractall`** —— 它会静默跳过已存在的文件,等于没还原)。
4. **复跑门禁 + 复核比对**(应回到 N/N 全一致)。

### 6.4 反身自检(挂钩本身要有牙齿)

拿**上一轮快照**(`current.prev`)喂后置比对,应能报出**本轮改动过的那些文件**;
报不出 = 挂钩在空转。

---

## 七、与编排总纲的接入

1. **前置检查**:编排总纲在执行任何 Tool 变更操作(Edit/Write/Delete/RunCommand 写类)之前,先调用 `check_paths.py`,根据 `riskLevel` 决策:
   - `low` → 放行
   - `high` → 暂停,提示用户二次确认
   - `forbidden` → 拦截,不执行
2. **后置审查**:skill 产出后(可选),编排总纲调用 `diff_review.py` 审查变更,若 `riskChanges` 含 forbidden/high 删除项,要求回滚或人工复核。
3. **接入位置**:前置检查在"Tool 调用前"钩子;后置审查在"skill 产出后"钩子,二者均非阻塞式调用脚本,由编排总纲读取报告再决策。
4. **交付集快照挂钩(批量改动时)**:批量写/删交付物时,除上述两检查外,再挂两个额外钩子 —— **改动前调 `snapshot-guard` 刷快照**(§6.1)、**改动后调其逐字节比对**(§6.2)。比对报出差异 ⇒ 按 `external-rewrite` 升 `high` 并走取证(§6.3)。

## 八、失败处理

- 检查脚本本身崩溃(异常退出、JSON 解析失败)→ 编排总纲降级为"标记未知风险,放行但标 WARNING",不阻塞主流程,报告中 `warnings` 包含 `guardrail-check-failed: <reason>`。
- 路径不存在 → check_paths 视为 `low`(无对象可破坏),但 warnings 中记录;diff_review 跳过该路径并在 warnings 中记录。
- 敏感清单加载失败(`.guardrail.yml` 解析异常)→ 使用内置默认清单,并在 warnings 中记录降级。
- 退出码非 0/2 → 一律视为脚本失败,按降级策略处理。

## 九、质量检查清单

- [ ] SKILL.md 行数 ≤300
- [ ] 两个 Python 脚本 `--help` 不报错
- [ ] 脚本含 shebang 与 `if __name__ == '__main__': main()`,函数有 docstring
- [ ] 报告 JSON 字段齐全(checkType/operation/paths/riskLevel/blocked/warnings/timestamp)
- [ ] 敏感路径正则覆盖四类(配置/数据库/核心代码/密钥)
- [ ] 操作分级矩阵覆盖 read/write/delete × 敏感级别
- [ ] 失败降级路径有文档说明
- [ ] 中文注释、UTF-8 编码
- [ ] **批量改交付集时,前置挂钩已刷快照(current → current.prev,再重建 current)**
- [ ] **改动后置挂钩已做"磁盘 vs 快照"逐字节比对,且三档判据(缺失/不一致/快照外新增)齐全**
- [ ] **发现差异时按 §6.3 取证(保全 `.txt` 现场 → 逐条还原,不用 `extractall`),未直接重刷快照**
- [ ] **反身自检通过:拿上一轮快照跑比对,能报出本轮改动集,否则挂钩空转**
