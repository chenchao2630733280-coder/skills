---
name: "tool-git-ops"
description: "Git 工具层 skill。封装 git add/commit/branch/push/diff/log 操作,支持'只提交产物目录''自动生成 commit message''创建 PR 分支'。当编排总纲或其他 skill 要把产物提交到 Git 时调用。"
---

# tool-git-ops

## 一、定位与职责

tool-git-ops 是产品/游戏生成流水线的 Git 工具层 skill,封装所有对 Git 仓库的读写操作。

- **只读优先**:`diff` / `log` 为只读命令,可安全执行,无需人工确认。
- **变更需确认**:`commit` / `branch` / `push` 属于变更操作;其中 `push` 默认禁用,必须显式确认(脚本 `--confirm` 参数)后才执行。
- **失败不阻塞**:git 命令失败时,脚本捕获异常并在 `git-ops-report.json` 的 `error` 字段回填错误信息,不向上抛异常,不阻塞编排总纲后续阶段。
- **只 add 指定路径**:永不使用 `git add .` 或 `git add -A`,只 add 调用方显式传入的产物路径,避免误提交敏感文件。

## 二、子命令清单

| 子命令 | 输入 | 输出 | 是否需确认 |
|--------|------|------|-----------|
| `commit` | `--paths`(路径列表)、`--message`(可选)、`--repo` | `git-ops-report.json`(含 commitHash) | 默认执行,内容受黑名单过滤 |
| `branch` | `--name`(分支名)、`--repo` | `git-ops-report.json`(含 branch) | 默认执行(创建新分支) |
| `push` | `--repo`、`--remote`(默认 origin)、`--confirm` | `git-ops-report.json`(含 pushed) | **必须 `--confirm` 才执行** |
| `diff` | `--repo`、`--paths`(可选) | `git-ops-report.json`(diff 文本输出到 stdout) | 否(只读) |
| `log` | `--repo`、`--limit`(默认 10) | `git-ops-report.json`(log 文本输出到 stdout) | 否(只读) |

## 三、安全规则

1. **默认不 push**:`push` 子命令必须显式传入 `--confirm` 参数才真正执行 `git push`,否则仅在报告中标记 `pushed=false` 并回填提示。
2. **黑名单路径过滤**:以下路径一律不 add、不 commit,命中时从路径列表剔除并在报告中记录:
   - `.env` / `*.env`
   - `credentials.json`
   - `*.key`
   - `*.pem`
   - `id_rsa` / `id_rsa.*`
3. **commit message 格式**:
   - 自动生成:`[auto] update {dir_summary} ({n} files)`,其中 `dir_summary` 为路径公共目录摘要,`n` 为实际提交文件数。
   - 显式传入(推荐由编排总纲生成):`[skill:{skill名}] {动作描述} ({产物数量} files)`。
4. **不 add 全部**:仅 add 调用方显式传入的路径,绝不使用 `git add .` / `git add -A`。

## 四、scripts 调用方式

通用调用格式(概念示意,实际参数以脚本 argparse 定义为准):

```
python scripts/git_ops.py <子命令> --paths <路径列表> [--message <msg>] [--branch <名>] [--push]
```

### commit
```
python scripts/git_ops.py commit --paths dist/,assets/manifest.json --message "[skill:game-asset-forge] add assets (12 files)" --repo .
```
不传 `--message` 时自动生成:
```
python scripts/git_ops.py commit --paths dist/ --repo .
```

### branch
```
python scripts/git_ops.py branch --name feat/game-assets-20260806 --repo .
```

### push
```
python scripts/git_ops.py push --repo . --remote origin --confirm
```
不加 `--confirm` 时脚本不执行 push,仅在报告中提示。

### diff
```
python scripts/git_ops.py diff --repo . --paths dist/
```

### log
```
python scripts/git_ops.py log --repo . --limit 10
```

## 五、产出契约

所有子命令执行后,在当前工作目录写入 `git-ops-report.json`,结构如下:

```json
{
  "command": "commit",
  "files": ["dist/index.html", "assets/manifest.json"],
  "commitHash": "a1b2c3d",
  "branch": "main",
  "pushed": false,
  "error": null,
  "timestamp": "2026-08-06T10:00:00+08:00"
}
```

字段说明:
- `command`:实际执行的子命令名。
- `files`:本次操作的路径列表(commit 时为通过黑名单过滤后的实际 add 路径)。
- `commitHash`:commit 子命令返回的短 hash;非 commit 命令为 `null`。
- `branch`:当前所在分支或新建分支名;不适用时为 `null`。
- `pushed`:push 子命令是否真正推送;非 push 命令为 `false`。
- `error`:失败时回填错误字符串;成功为 `null`。
- `timestamp`:ISO8601 带时区时间戳。

## 六、失败处理

- **git 命令失败**:脚本捕获 `subprocess.CalledProcessError` 及通用 `Exception`,在 `error` 字段回填错误信息,进程退出码仍返回 0,不向上抛异常、不阻塞流水线。
- **非 git 仓库**:`git rev-parse --is-inside-work-tree` 失败时,`error` 回填 `"not a git repository"`,`files/commitHash/branch/pushed` 置空。
- **路径不存在**:`commit` 时对不存在路径直接跳过,继续提交其余路径。
- **黑名单命中**:剔除命中路径,继续提交其余路径;若全部命中导致无文件可提交,`error` 回填 `"all paths blocked by blacklist"`。

## 七、与编排总纲的接入

- 被以下编排总纲在 **Tool 确认点**调用:
  - `product-pipeline-master`:产物阶段产出后,由总纲确认是否提交到 Git。
  - `game-forge-master`:`game-integrate` 产出到 `dist/` / `export/` 后,由总纲触发提交。
- **执行前过 guardrail**:总纲调用本 skill 前,须先经过对应 Gate 的 guardrail 校验(如产物存在性、黑名单预检),guardrail 不通过则不调用本 skill。
- **默认不 push**:总纲如需推送,须显式在调用指令中要求传入 `--confirm`,并由用户确认。

## 八、质量检查清单

- [ ] `python scripts/git_ops.py --help` 不报错,五个子命令均可见。
- [ ] `python scripts/git_ops.py commit --help` 等子命令 help 正常。
- [ ] `generate_commit_message.py` 可被 `git_ops.py` import,单独运行返回 `[auto] update ... (n files)`。
- [ ] commit 黑名单路径被过滤且记录于报告。
- [ ] push 缺少 `--confirm` 时不执行真实推送。
- [ ] 非 git 仓库时返回 `error` 且不抛异常。
- [ ] 所有报告写入当前目录 `git-ops-report.json`,字段齐全。
- [ ] 所有文件 UTF-8 编码,代码注释为中文。

## references 使用指引

| 文件 | 用途 |
|------|------|
| `references/git-ops-contract.md` | 输入/输出契约与安全规则,供编排总纲与各阶段 skill 对齐 |
