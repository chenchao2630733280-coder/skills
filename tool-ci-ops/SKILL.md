---
name: "tool-ci-ops"
description: "CI/CD 工具层 skill。封装'触发 CI''查询构建状态''读取测试报告'操作。当编排总纲或其他 skill 要触发持续集成或查询构建结果时调用。"
---

# CI/CD 工具层 (tool-ci-ops)

## 一、定位与职责

本 skill 是产品流水线中的 **CI/CD 工具层**,职责单一:封装对持续集成平台的操作。

- **触发类操作**(trigger):属于变更类操作,**必须经用户确认**后才能执行;未确认时仅打印命令供用户手动执行。
- **查询类操作**(status / report):只读,**直接执行**,无需确认。
- **失败不阻塞**:无论 CI 平台是否可用、命令是否成功,本 skill 都不阻断上层编排,而是把结果(含 error)写回 `ci-ops-report.json` 交由上层决策。

## 二、子命令清单

| 子命令    | 输入参数                                                          | 输出                          | 是否需确认 |
| --------- | ----------------------------------------------------------------- | ----------------------------- | ---------- |
| `trigger` | `--platform` `--repo` `[--branch]` `[--confirm]`                  | 触发结果 + ci-ops-report.json | 是(变更类)|
| `status`  | `--platform` `--repo` `[--run-id]`                                | 构建(runId/status)+ 报告      | 否         |
| `report`  | `--platform` `--repo` `[--run-id]`                                | 测试结果(testResults)+ 报告   | 否         |

- 不带 `--confirm` 的 `trigger` 视为 **dry-run**:只打印命令,不执行。
- 不带 `--run-id` 的 `status`/`report` 查询最新一次 run。

## 三、安全规则

1. **触发需确认**:`trigger` 是变更类操作。只有显式传入 `--confirm` 才真正调用平台 CLI;否则只打印命令。
2. **查询直接执行**:`status` / `report` 只读,无需 `--confirm`,可直接调用。
3. **平台不可用降级**:当平台 CLI 未安装或环境变量缺失时,不报错中断,而是 **降级为"提示用户手动触发"**,把待执行命令打印出来,并在报告中标记 `status=degraded`。
4. **不泄露密钥**:环境变量中的 token 只用于 CLI 调用,**绝不**写入报告或日志。

## 四、scripts 调用方式

统一入口:`python scripts/ci_ops.py <子命令> [参数]`

```bash
# 触发 CI(dry-run,仅打印命令)
python scripts/ci_ops.py trigger --platform github-actions --repo owner/repo --branch main

# 触发 CI(确认执行)
python scripts/ci_ops.py trigger --platform gitlab-ci --repo owner/repo --branch dev --confirm

# 查询构建状态(最新一次)
python scripts/ci_ops.py status --platform github-actions --repo owner/repo

# 查询指定 run 的状态
python scripts/ci_ops.py status --platform jenkins --repo my-job --run-id 123

# 读取测试报告
python scripts/ci_ops.py report --platform github-actions --repo owner/repo --run-id 88123
```

`--platform` 取值:`github-actions` | `gitlab-ci` | `jenkins`。

## 五、产出契约

每次执行都会在工作目录生成 `ci-ops-report.json`,结构如下:

```json
{
  "command": "trigger | status | report",
  "platform": "github-actions | gitlab-ci | jenkins",
  "repo": "owner/repo",
  "branch": "main",
  "runId": "88123",
  "status": "triggered | running | success | failed | degraded | dry-run",
  "testResults": {
    "total": 120,
    "passed": 118,
    "failed": 1,
    "skipped": 1
  },
  "error": null,
  "timestamp": "2026-08-06T09:11:00"
}
```

- `testResults` 仅 `report` 命令填充,其余命令为 `null`。
- `error` 为字符串或 `null`;非 `null` 表示该次操作出现异常或降级原因。

## 六、失败处理

1. **平台 CLI 不可用**(未安装/不在 PATH):降级为 **输出提示命令供用户手动执行**,报告 `status=degraded`,退出码 0(不阻断)。
2. **环境变量缺失**(如 `GITHUB_TOKEN` 未设置):同上降级处理。
3. **网络失败 / CLI 执行报错**:在报告中记录 `error` 字符串,`status=failed`,退出码 1;**不阻断**上层编排,由编排总纲决定后续动作。
4. **不支持的平台**:写入 `error`,退出码 1。

## 七、与编排总纲的接入

本 skill 被 `product-pipeline-master`(产品流水线编排总纲)在 **Tool 确认点** 调用:

- 在"提交 Git"步骤之后,**可选**触发 CI(由用户确认)。
- 触发后由编排总纲轮询 `status`,待构建完成后调用 `report` 读取测试结果。
- 若 `status` 返回 `degraded` 或 `failed`,编排总纲可选择跳过 CI 门禁并提示用户,而非硬性中断。

## 八、质量检查清单

- [ ] `python scripts/ci_ops.py --help` 不报错,列出三个子命令。
- [ ] `python scripts/ci_ops.py trigger --help` / `status --help` / `report --help` 均可用。
- [ ] `trigger` 不带 `--confirm` 时为 dry-run,只打印命令,不调用 CLI。
- [ ] `trigger` 带 `--confirm` 但 CLI 不可用时降级为提示,退出码 0。
- [ ] `status` / `report` 不需确认即可执行,CLI 不可用时降级。
- [ ] 每次执行都生成 `ci-ops-report.json`,字段与契约一致。
- [ ] 报告中 **不含** 任何 token / 密钥明文。
- [ ] 仅使用 Python 标准库,无外部依赖。
- [ ] 平台取值限定 `github-actions | gitlab-ci | jenkins`,非法值被拒绝。
