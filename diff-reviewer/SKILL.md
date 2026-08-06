---
name: "diff-reviewer"
description: "变更审查 skill。审查产物变更的 diff,标红'删除核心文件''大幅删减''配置变更'等风险操作。当 skill 产出后或用户要'审查变更/检查 diff'时调用。只读不写。"
---

# diff-reviewer - 变更后置审查

## 一、定位与职责

diff-reviewer 是**变更后置审查** skill,职责是在 skill 产出或代码变更**已经发生之后**,
对 diff 进行只读审查,标红可能带来风险的操作(删除文件、大幅删减、配置/依赖/密钥变更)。

**只读不写**:diff-reviewer 不修改任何被审查的产物,仅产出审查报告
(`diff-review-report.md` 人读 + `diff-review-report.json` 机读)。

与 guardrail 的区别:
- **guardrail 是前置拦截**:在操作执行前判断是否为禁止级操作,命中则阻断,不让操作发生。
- **diff-reviewer 是后置审查**:在操作已经执行后,对实际产生的 diff 做风险标注与提醒,
  不阻断、不回滚,只给出风险清单与处置建议。

二者互补:guardrail 把危险操作挡在门外,diff-reviewer 把已发生的危险变更暴露在报告里。

## 二、风险变更识别规则

diff-reviewer 识别 5 类风险变更,严重级别从高到低:

| 风险类型 | 触发条件 | 严重级别 |
| --- | --- | --- |
| 删除文件 | diff 中出现 `deleted file mode`,或 before 存在而 after 缺失 | high |
| 大幅删减 | 单文件行数减少 > 30%(按 hunk header 的 old/new 行数估算) | high |
| 配置文件变更 | 路径匹配 `*.yml`/`*.yaml`/`*.json`/`*.toml` 等 | medium |
| 依赖变更 | 路径为 `package.json`/`requirements.txt`/`go.mod`/`pom.xml` 等 | high |
| 密钥文件变更 | 路径匹配 `*.key`/`*.pem`/`.env*` 等 | critical |

详细判定条件与示例见 `references/diff-risk-rules.md`。

## 三、scripts 调用方式

通过 `scripts/diff_review.py` 执行审查,支持三种输入模式:

### 1. 对比两个目录或文件(--before / --after)

```bash
python scripts/diff_review.py --before ./before_dir --after ./after_dir
python scripts/diff_review.py --before ./old.txt --after ./new.txt
```

### 2. 直接传入 diff 文本文件(--diff)

```bash
git diff > my.diff
python scripts/diff_review.py --diff my.diff
```

### 3. 审查已 staged 的变更(--git-staged)

```bash
git add -A
python scripts/diff_review.py --git-staged
```

脚本仅使用 Python 标准库,无外部依赖。产出 `diff-review-report.md` 与
`diff-review-report.json` 于当前工作目录。

## 四、产出契约

每次审查产出两份报告,置于执行目录:

- **diff-review-report.md**(人读):含风险变更清单(类型/文件/严重级别/详情)、
  汇总统计、处置建议。
- **diff-review-report.json**(机读),结构如下:

```json
{
  "riskChanges": [
    {"type": "deleted_file", "file": "src/core.py", "severity": "high", "detail": "删除文件: src/core.py"}
  ],
  "summary": {"total": 1, "high": 1, "medium": 0, "critical": 0},
  "timestamp": "2026-08-06T10:00:00"
}
```

## 五、与编排总纲的接入

在编排总纲(如 product-pipeline-master / game-forge-master)中,skill 产出后可**可选**地
串入 diff-reviewer 做后置审查:

```
skill 产出 → (可选)diff-reviewer 后置审查 → 输出报告
```

接入要点:
- 可选环节,不强制阻断流水线;报告供人工或下游决策。
- 与 guardrail 互补:guardrail 在 skill 执行前拦截禁止操作,diff-reviewer 在 skill 执行后审查实际变更。
- 若 diff-reviewer 报告出现 critical(密钥变更),建议人工立即介入。

## 六、失败处理

- diff 解析失败(格式无法识别、文件不存在、git 不可用):**降级处理**,在报告中标记
  "无法自动审查,建议人工 review",不抛异常中断。
- `--before`/`--after` 路径无效:报错并提示正确用法,退出码非 0。
- `--git-staged` 在非 git 仓库执行:降级为"无法审查,建议人工 review"。

## 七、与 guardrail 的协作

| 维度 | guardrail | diff-reviewer |
| --- | --- | --- |
| 时机 | 前置(执行前) | 后置(执行后) |
| 行为 | 拦截/阻断 | 标注/报告 |
| 对象 | 即将执行的操作 | 已发生的 diff |
| 密钥/删除 | 禁止级,直接挡掉 | critical/high,写入报告待处置 |

协作流程:
1. 操作发起 → guardrail 前置检查 → 命中禁止级则阻断。
2. 操作执行通过 → 产生 diff → diff-reviewer 后置审查 → 输出风险报告。
3. 人工或编排层根据报告决定是否回滚/修复。

## 八、质量检查清单

- [ ] SKILL.md 行数 ≤ 300
- [ ] `python scripts/diff_review.py --help` 正常输出,不报错
- [ ] 三种调用模式(--before/--after、--diff、--git-staged)均可运行
- [ ] 5 类风险变更均能正确识别并标注严重级别
- [ ] 同时产出 .md 与 .json,且 json 结构符合契约
- [ ] 脚本仅依赖标准库
- [ ] 中文注释,UTF-8 编码
- [ ] diff 解析失败时降级,不中断
- [ ] 只读不写:不修改任何被审查文件
