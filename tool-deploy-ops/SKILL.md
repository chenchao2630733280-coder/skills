---
name: "tool-deploy-ops"
description: "部署工具层 skill。封装'部署到各平台''回滚''健康检查'操作,支持 GitHub Pages / Vercel / Netlify / CloudBase / COS。当编排总纲或其他 skill 要部署产物时调用。"
---

# tool-deploy-ops 部署工具层

## 一、定位与职责

本 skill 是**部署操作封装层**,位于编排总纲(product-pipeline-master / game-forge-master)之下、
具体平台 CLI 之上。它不决定"部署到哪个平台"(那是上层编排的职责),只负责把已构建好的产物
(`dist/`、`build/`、`export/`)可靠地推到目标平台,并在部署后做一次健康检查。

核心职责三件:

1. **deploy** — 把产物部署到 github-pages / vercel / netlify / cloudbase / cos 之一。
2. **rollback** — 回滚到上一版本(平台支持时)。
3. **healthcheck** — 对部署后的 URL 做 HTTP GET,记录状态码与响应时间。

行为约束(很重要):

- **部署与回滚都需用户确认**(`--confirm`);未带 `--confirm` 时只打印将要执行的命令,不实际执行。
- **健康检查失败不阻断流水线**——只把结果标为 WARNING 写入报告,由上层决定是否继续。
- **平台 CLI 不可用时降级**:不报错中断,而是把"该执行的部署指令"原样输出给用户手动执行。

## 二、子命令清单

| 子命令 | 输入 | 输出 | 需用户确认 |
|--------|------|------|-----------|
| `deploy` | `--platform`、`--source`(产物路径)、`--target`(可选)、`--confirm`(可选) | `deploy-ops-report.json` | 是(无 `--confirm` 仅打印命令) |
| `rollback` | `--platform`、`--target`、`--confirm`(可选) | `deploy-ops-report.json` | 是(无 `--confirm` 仅打印命令) |
| `healthcheck` | `--url` | `deploy-ops-report.json`(含 healthStatus) | 否 |

说明:

- `deploy` 的 `--source` 必须是已存在的产物目录;若不存在直接返回 error,不降级。
- `rollback` 依赖平台自身的版本历史(GitHub Pages 走 git revert / Vercel、Netlify 走各自 rollback API)。
  平台不支持回滚时,报告里写明并降级为输出手动回滚指令。
- `healthcheck` 可单独运行(部署后验证),也可由 `deploy` 在成功后自动接一次。

## 三、安全规则

1. **部署需用户确认**:未带 `--confirm` 一律只打印命令,不调用任何平台 CLI、不推送任何文件。
2. **回滚需用户确认**:同上,回滚是高风险操作(会让线上回到旧版本),必须显式 `--confirm`。
3. **健康检查失败标 WARNING 不阻断**:HTTP 非 2xx 或超时,只写 `healthStatus.ok=false` 与
   `error`,**不**抛阻断异常,由上层编排总纲决定后续动作。
4. **平台 CLI 不可用时降级**:检测到 `gh` / `vercel` / `netlify` / `tcb` / `coscli` 不在 PATH 或
   未登录时,不报错,而是把对应平台的部署命令原样输出到 stdout 与报告,提示用户手动执行。
5. **凭证安全**:本 skill **不存储任何 token / SecretId / SecretKey**。需要凭证的步骤一律交给
   平台 CLI 自身的登录态(`gh auth`、`vercel login`、`tcb login`)或由用户在本地手动执行降级命令。
   绝不把密钥写进 `deploy-ops-report.json` 或日志。
6. **产物校验**:部署前确认 `--source` 目录存在且非空;空产物直接返回 error。

## 四、scripts 调用方式

统一入口 `scripts/deploy_ops.py`,三个子命令:

```bash
# 部署(未带 --confirm 仅打印命令)
python scripts/deploy_ops.py deploy \
  --platform <github-pages|vercel|netlify|cloudbase|cos> \
  --source <产物路径> \
  [--target <目标名>] \
  [--confirm]

# 回滚(未带 --confirm 仅打印命令)
python scripts/deploy_ops.py rollback \
  --platform <github-pages|vercel|netlify|cloudbase|cos> \
  --target <目标名> \
  [--confirm]

# 健康检查(无需确认)
python scripts/deploy_ops.py healthcheck \
  --url <URL>
```

示例:

```bash
# 1) 预演部署到 Vercel(只看会执行什么)
python scripts/deploy_ops.py deploy --platform vercel --source ./dist --target my-app

# 2) 确认部署到 GitHub Pages
python scripts/deploy_ops.py deploy --platform github-pages --source ./dist --target user/repo --confirm

# 3) 部署到 CloudBase 后做健康检查
python scripts/deploy_ops.py deploy --platform cloudbase --source ./dist --target envId --confirm
python scripts/deploy_ops.py healthcheck --url https://xxx.tcloudbase.com

# 4) 回滚 Vercel 到上一版本
python scripts/deploy_ops.py rollback --platform vercel --target my-app --confirm
```

参数约定:

- `--platform` 枚举值:`github-pages`、`vercel`、`netlify`、`cloudbase`、`cos`。
- `--source`:产物目录路径(仅 deploy 需要)。
- `--target`:目标名(仓库名 / 项目名 / envId / 桶名),可选,各平台语义不同。
- `--confirm`:存在才真正执行;不存在只打印。
- `--url`:健康检查目标 URL(仅 healthcheck)。

## 五、产出契约

每次调用产出(覆盖写)`deploy-ops-report.json`,结构如下:

```json
{
  "command": "deploy|rollback|healthcheck",
  "platform": "github-pages|vercel|netlify|cloudbase|cos|null",
  "source": "产物路径或null",
  "target": "目标名或null",
  "url": "部署/检查的URL或null",
  "version": "本次部署版本标识或上一版本标识或null",
  "healthStatus": {
    "ok": true,
    "statusCode": 200,
    "responseTimeMs": 123
  },
  "error": "错误信息或null",
  "timestamp": "2026-08-06T12:00:00+08:00"
}
```

字段说明:

- `command`:实际执行的子命令。
- `platform`:目标平台;`healthcheck` 单独跑时可为 `null`。
- `version`:部署时为本次版本标识(如 git short SHA / 时间戳);回滚时为回退到的版本标识;不支持时为 `null`。
- `healthStatus`:`deploy` 成功后会尽力推断 URL 并自动接一次健康检查填入(推断不到则留 `null`,由上层另跑 `healthcheck` 子命令);`healthcheck` 子命令只填本字段;`rollback` 不填(可为 `null`)。
- `error`:任何阶段的错误信息(降级输出命令时也写明"CLI 不可用,已输出手动指令");正常为 `null`。
- `timestamp`:ISO8601 带时区,使用本机时区。

报告固定写入当前工作目录的 `deploy-ops-report.json`(同名覆盖)。

## 六、失败处理

| 失败场景 | 处理方式 | 是否阻断 |
|---------|---------|---------|
| `--source` 目录不存在或为空(仅 `--confirm` 执行时校验) | 返回 error,不执行 | 阻断(返回非零退出码) |
| 平台 CLI 未安装 / 未登录 | **降级**:输出该执行的手动命令到 stdout 与报告 | 不阻断(退出码 0) |
| 部署命令执行失败(非零返回) | 写 error 到报告 | 不阻断(退出码 0,交上层判断) |
| 回滚平台不支持 | 降级输出手动回滚指令 | 不阻断 |
| 健康检查 HTTP 非 2xx / 超时 | `healthStatus.ok=false`,标 WARNING | **不阻断** |
| 参数缺失 / 枚举非法 | argparse 报错 | 阻断(退出码 2) |

原则:**只有参数错误和空产物这类"输入不合法"才阻断;运行期失败一律写报告交上层决策**,
这样编排总纲可以拿到结构化结果而不是一个崩溃的子进程。

## 七、与编排总纲的接入

本 skill 由 `product-pipeline-master` / `game-forge-master` 在其 **Tool 确认点** 调用:

- 调用前提:**产物必须已经 `git commit`**(部署/回滚需要可追溯的版本基线;健康检查不需要)。
  编排总纲在调用本 skill 前应已完成 commit。
- 调用顺序通常是:`build → commit → deploy(--confirm) → healthcheck`。
- 编排总纲负责"选平台"(基于仓库可见性、是否国内访问、是否需 DB 等决策),本 skill 只接收
  `--platform` 参数执行,不做平台选择。
- 健康检查失败时,本 skill 不阻断;编排总纲可据 `healthStatus.ok=false` 决定是否触发 `rollback`
  或提示用户。
- 平台 CLI 不可用降级时,编排总纲应把降级命令呈现给用户,由用户手动执行后再次跑 `healthcheck`。

接入约定:编排总纲读取本 skill 产出的 `deploy-ops-report.json` 作为该阶段的结构化结果。

## 八、质量检查清单

部署前自检(全部为是才执行 `--confirm` 部署):

- [ ] 产物目录 `--source` 存在且非空,`index.html`(或平台入口)存在。
- [ ] 已 `git commit`(部署/回滚需要版本基线)。
- [ ] `--platform` 在枚举值内。
- [ ] 用户已显式 `--confirm`(否则只打印命令)。
- [ ] 目标平台 CLI 已安装且已登录(否则走降级路径,不阻断)。
- [ ] 凭证不落盘:不把任何 token / SecretKey 写进报告或日志。

部署后自检:

- [ ] `deploy-ops-report.json` 已生成且字段完整。
- [ ] `deploy` 成功后自动跑了 `healthcheck`,`healthStatus` 已填。
- [ ] 健康检查失败时仅 WARNING,未抛阻断异常。
- [ ] 降级路径下,手动命令已完整输出(可复制即跑)。
- [ ] 报告 `timestamp` 带时区,`error` 字段在正常时为 `null`。

## references 使用指引

| 文件 | 用途 |
|------|------|
| `references/deploy-platforms.md` | 部署平台差异说明(GitHub Pages / Vercel / Netlify / CloudBase / COS 的命令与配置) |
