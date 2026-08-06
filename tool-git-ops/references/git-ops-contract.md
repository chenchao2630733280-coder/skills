# Git 工具层契约 (tool-git-ops)

本文件定义 tool-git-ops skill 的输入/输出契约与安全规则,
供编排总纲(product-pipeline-master / game-forge-master)与各阶段 skill 对齐。

## 一、输入契约

### 通用调用

```
python scripts/git_ops.py <子命令> [选项]
```

### 子命令输入

| 子命令 | 必选参数 | 可选参数 | 说明 |
|--------|---------|---------|------|
| `commit` | `--paths <路径...>` | `--message <msg>`、`--repo <path>` | 路径支持逗号分隔或多次传入;不传 message 则自动生成 |
| `branch` | `--name <分支名>` | `--repo <path>` | 创建并切换到新分支 |
| `push` | (无) | `--repo <path>`、`--remote <名>`、`--confirm` | **必须 `--confirm` 才执行推送** |
| `diff` | (无) | `--repo <path>`、`--paths <路径...>` | 只读 |
| `log` | (无) | `--repo <path>`、`--limit <n>` | 只读,limit 默认 10 |

`--repo` 默认当前目录 `.`。

## 二、输出契约

所有子命令在**当前工作目录**写入 `git-ops-report.json`:

```json
{
  "command": "commit | branch | push | diff | log",
  "files": ["路径列表"],
  "commitHash": "短 hash 或 null",
  "branch": "分支名或 null",
  "pushed": false,
  "error": "错误字符串或 null",
  "timestamp": "ISO8601 带时区"
}
```

| 字段 | 类型 | 说明 |
|------|------|------|
| `command` | string | 实际执行的子命令 |
| `files` | string[] | 实际操作的路径(commit 为通过黑名单过滤后的 add 路径) |
| `commitHash` | string\|null | commit 短 hash;非 commit 为 null |
| `branch` | string\|null | 当前/新建分支;不适用为 null |
| `pushed` | boolean | 是否真正推送;非 push 恒为 false |
| `error` | string\|null | 失败信息;成功为 null |
| `timestamp` | string | ISO8601 带本地时区 |

`diff` / `log` 的文本内容输出到 stdout,报告本身只记录元信息与 error。

## 三、安全规则

### 3.1 黑名单路径表

以下路径**一律不 add、不 commit**,命中即从路径列表剔除:

| 模式 | 说明 |
|------|------|
| `.env` / `*.env` | 环境变量文件 |
| `credentials.json` | 凭证文件 |
| `*.key` | 私钥文件 |
| `*.pem` | PEM 证书/密钥 |
| `id_rsa` / `id_rsa.*` | SSH 私钥 |

### 3.2 确认规则

| 操作 | 是否需确认 | 确认方式 |
|------|-----------|---------|
| `diff` / `log` | 否 | 只读,直接执行 |
| `commit` | 默认执行 | 内容受黑名单过滤;无变更时 error=null |
| `branch` | 默认执行 | 创建并切换新分支 |
| `push` | **必须确认** | 脚本须传入 `--confirm`;否则不推送,pushed=false |

### 3.3 commit message 格式

- 自动生成: `[auto] update {dir_summary} ({n} files)`
  - `dir_summary`:路径公共父目录最末一级名
  - `n`:实际提交文件数
- 显式传入(推荐由编排总纲生成): `[skill:{skill名}] {动作描述} ({产物数量} files)`

### 3.4 add 规则

- **只 add 显式传入的路径**,永不使用 `git add .` / `git add -A`。
- 路径不存在时跳过,提交实际存在的子集。

## 四、失败码定义

脚本不向上抛异常,统一通过 `error` 字段与进程退出码表达:

| 场景 | exit code | error 字段 |
|------|-----------|-----------|
| 成功 | 0 | null |
| 非 git 仓库 | 0 | `not a git repository` |
| 全部路径命中黑名单 | 0 | `all paths blocked by blacklist` |
| 未传任何路径(commit) | 0 | `no paths provided` |
| git 命令失败 | 0 | `git <cmd> failed: <详情>` |
| push 未确认 | 0 | `push requires --confirm to execute` |
| 参数缺失 | 2 | (argparse 报错) |

> 设计原则:除 argparse 参数错误(exit 2)外,所有业务失败均返回 exit 0 并在报告中回填 error,确保不阻塞编排总纲后续阶段。
