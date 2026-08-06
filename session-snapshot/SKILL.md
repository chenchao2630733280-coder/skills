---
name: "session-snapshot"
description: "会话持久化层 skill。把当前会话的关键状态（任务进度/已产出文件/上下文摘要）快照保存，支持跨会话恢复。当会话上下文将丢失、或要在新会话继续未完成任务时调用。与宿主内置记忆互补（宿主会话级，本 skill 显式快照+跨会话恢复）。"
---

# session-snapshot — 会话持久化层

session-snapshot 是 AI Agent 体系第四阶段升级的 **会话持久化层 skill**。它把当前会话的关键状态
（任务进度/已产出文件/上下文摘要/workflow 执行状态）序列化为快照文件，支持跨会话恢复，
解决"会话上下文丢失后无法继续"的问题。

- **显式快照**：用户主动或自动触发，把会话状态写入 `session-snapshot.json`。
- **跨会话恢复**：在新会话中读取快照，注入上下文，继续未完成任务。
- **与宿主记忆互补**：宿主负责会话级记忆，本 skill 负责显式快照 + 跨会话。
- **文件 hash 校验**：恢复时校验已产出文件的 hash，检测文件是否被修改。

## 一、何时调用

满足以下任一条件即调用本 skill：

1. **会话将丢失**：上下文窗口将满或会话即将终止，要保存当前进度。
   - 如："保存当前会话状态"
   - 如："快照当前进度"
2. **跨会话继续**：要在新会话继续未完成任务，需恢复上次状态。
   - 如："恢复上次的会话"
   - 如："读取快照 snap-20260806-001"
3. **对比快照**：要查看两个快照之间的状态差异。
   - 如："对比快照 snap-001 和 snap-002"
4. **清理过期快照**：要清理过期的快照文件。
   - 如："清理 30 天前的快照"

**不要**在以下场景调用：
- 用户要记录 skill 调用数据（走 `skill-usage-tracker`，本 skill 只存会话状态）
- 用户要持久化代码库索引（走 `codebase-rag`，本 skill 不索引代码）
- 用户要保存失败案例（走 `failure-casebook`，本 skill 不记录失败码）

## 二、与其他 skill 的关系

| 维度 | 宿主记忆 | session-snapshot（本 skill） | failure-casebook |
|------|---------|---------------------------|------------------|
| 范围 | 会话级 | 跨会话 | 跨会话 |
| 内容 | 对话历史 | 任务进度+文件+上下文摘要 | 失败码+原因+修复 |
| 触发 | 自动 | 用户主动/自动节点 | 失败时自动 |
| 存储 | 宿主内部 | `.trae-cn/sessions/` | `.trae-cn/failures/` |

**互补关系**：
- 宿主记忆：会话内的对话历史，会话结束即丢失。
- session-snapshot：显式快照关键状态，跨会话可用，恢复时注入新会话。
- failure-casebook：记录失败案例，session-snapshot 的 context_summary 可引用其失败记录。

## 三、快照内容

每个快照包含以下四部分状态：

### 3.1 任务进度（task_tree）

来自 `task-planner` 的 `task-tree.json` 当前状态：
- `current_task`：当前正在执行的任务 ID
- `completed`：已完成任务 ID 列表
- `pending`：待执行任务 ID 列表

### 3.2 已产出文件（artifacts）

会话中产出的关键文件清单：
- `path`：文件路径（相对项目根）
- `hash`：SHA-256 哈希（用于恢复时校验是否被修改）
- `summary`：文件摘要（一句话描述）

### 3.3 上下文摘要（context_summary）

- `key_decisions`：关键决策列表（如"使用 Phaser 3 引擎"）
- `user_preferences`：用户偏好（如"每步人工确认"）
- `failures`：失败记录（关联 failure-casebook）
- `notes`：其他备注

### 3.4 workflow 状态（workflow_state）

来自 `workflow-runtime` 的执行状态：
- `current_step`：当前步骤 ID
- `paused_at`：暂停点 ID（若有）
- `workflow_file`：workflow.yaml 路径

## 四、子命令清单

本 skill 通过 `scripts/snapshot_ops.py` 提供五个子命令：

### 1. save —— 保存快照

| 项 | 说明 |
|---|---|
| 输入 | `--session-id`(可选)、`--trigger`(manual/auto-confirm/auto-stage/auto-fail)、`--artifacts`(文件路径列表)、`--context`(JSON 字符串)、`--task-tree`(task-tree.json 路径)、`--workflow-state`(JSON) |
| 输出 | 新快照的 `snapshot_id` 与写入路径；顺带清理过期快照 |

### 2. restore —— 恢复快照

| 项 | 说明 |
|---|---|
| 输入 | `--snapshot-id`(必填)或`--latest`(取最新)、`--confirm`(必须 yes) |
| 输出 | 快照内容 + 文件 hash 校验结果（若文件被修改则提示冲突） |

### 3. list —— 列出快照

| 项 | 说明 |
|---|---|
| 输入 | `--limit`(默认 20)、`--session-id`(可选,按会话过滤) |
| 输出 | 快照列表（ID/时间/触发/任务摘要） |

### 4. diff —— 对比快照

| 项 | 说明 |
|---|---|
| 输入 | `--snapshot-a`(必填)、`--snapshot-b`(必填) |
| 输出 | 两快照的差异（任务进度/文件/上下文变化） |

### 5. clean —— 清理过期快照

| 项 | 说明 |
|---|---|
| 输入 | `--retention-days`(默认 30) |
| 输出 | 清理的快照数量 |

## 五、scripts 调用方式

脚本路径：`scripts/snapshot_ops.py`，使用标准 Python 3，无外部依赖。

### 保存快照

```bash
python scripts/snapshot_ops.py save \
  --trigger manual \
  --artifacts docs/PRD.md docs/TECH_DESIGN.md \
  --context '{"key_decisions":["使用 Phaser 3"],"user_preferences":["每步人工确认"]}'
```

### 恢复快照

```bash
python scripts/snapshot_ops.py restore --snapshot-id snap-20260806-001 --confirm yes
python scripts/snapshot_ops.py restore --latest --confirm yes
```

### 列出快照

```bash
python scripts/snapshot_ops.py list
python scripts/snapshot_ops.py list --session-id abc123 --limit 10
```

### 对比快照

```bash
python scripts/snapshot_ops.py diff --snapshot-a snap-001 --snapshot-b snap-002
```

### 清理过期快照

```bash
python scripts/snapshot_ops.py clean --retention-days 30
```

### 查看帮助

```bash
python scripts/snapshot_ops.py --help
python scripts/snapshot_ops.py save --help
```

## 六、存储规则

- **快照目录**：所有快照 JSON 文件存到 `~/.trae-cn/sessions/`（脚本自动创建）。
- **单快照文件**：每个快照一个独立 JSON 文件，文件名 `{snapshot_id}.json`。
- **索引文件**：`~/.trae-cn/sessions/snapshots-index.json`，记录所有快照元信息（ID/session_id/created_at/trigger/summary），用于快速查询。
- **保留策略**：快照默认保留 **30 天**，可通过环境变量 `SESSION_SNAPSHOT_RETENTION_DAYS` 配置；每次 `save` 时顺带清理过期快照。
- **编码**：所有文件 UTF-8 编码，JSON 以缩进 2 写出，timestamp 为 ISO-8601 带时区。

## 七、产出 schema

详见 `references/snapshot-schema.md`。

**session-snapshot.json schema 摘要**：
```json
{
  "snapshot_id": "snap-20260806-001",
  "session_id": "原会话ID",
  "created_at": "2026-08-06T...",
  "trigger": "manual | auto-confirm | auto-stage | auto-fail",
  "task_tree": { "current_task": "T3", "completed": ["T1","T2"], "pending": ["T4"] },
  "artifacts": [
    { "path": "docs/PRD.md", "hash": "sha256:...", "summary": "产品需求文档" }
  ],
  "context_summary": {
    "key_decisions": ["使用 Phaser 3 引擎", "目标平台 Web"],
    "user_preferences": ["每步人工确认"],
    "failures": [{"skill": "game-asset-forge", "code": "TIMEOUT"}]
  },
  "workflow_state": { "current_step": "s3", "paused_at": "pause1" }
}
```

## 八、自动快照触发点

session-snapshot 支持在关键节点自动触发快照（由 workflow-runtime 或编排总纲调用）：

| 触发点 | trigger 值 | 调用方 |
|--------|-----------|-------|
| 人工确认点 | `auto-confirm` | workflow-runtime 在 pause 节点前调 save |
| 阶段完成 | `auto-stage` | 编排总纲在阶段完成时调 save |
| 失败回退 | `auto-fail` | workflow-runtime 在 on_fail 触发时调 save |
| 用户手动 | `manual` | 用户显式调 save |
| agent-runtime-exec | 执行状态持久化 | agent-runtime-exec 的执行状态可被 session-snapshot 快照保存 |

**注入机制**：workflow-runtime 调用 save 后，把 `snapshot_id` 写入执行轨迹，便于后续恢复。

## 九、references 使用指引

| 文件 | 用途 | 何时查 |
|------|------|--------|
| `references/snapshot-schema.md` | 快照 JSON schema（任务/文件/上下文/workflow 状态） | (1) 修改快照结构时对照；(2) 用户问"快照格式"；(3) 恢复时校验字段 |
| `references/restore-strategy.md` | 恢复策略（全量恢复/选择性恢复/增量恢复 + 文件冲突处理） | (1) 恢复时选择策略；(2) 文件 hash 冲突处理；(3) 用户问"怎么恢复" |

两份 references 均为**懒加载**：仅在需要时读取。

## 十、与其他 skill 的协作

| skill | 关系 | 协作方式 |
|-------|------|---------|
| `workflow-runtime` | 触发方 | workflow-runtime 在 pause/on_fail 节点前调 save 保存快照；恢复时调 restore |
| `task-planner` | 数据源 | save 时读取 task-tree.json 的当前状态写入快照 |
| `failure-casebook` | 关联方 | context_summary.failures 引用 failure-casebook 的案例 ID |
| 宿主记忆 | 互补 | 宿主负责会话级对话历史，本 skill 负责跨会话状态快照 |

## 十一、失败处理

本 skill 自身的失败 **不阻断主流程**：

- 快照目录创建失败、文件写入失败、索引损坏等异常，脚本捕获后只在 stderr 打印 `WARNING: <详情>`，并以 exit code 0 退出（save）或返回空结果（restore/list/diff）。
- workflow-runtime 调用本 skill 时，应忽略其退出码与 stderr 中的 WARNING，继续主流程。
- 文件 hash 校验失败（恢复时检测到文件被修改）：标 `CONFLICT`，提示用户手动处理，不自动覆盖。
- **设计原则**：快照是辅助记忆，不是关键路径，宁可丢快照也不能拖垮主流程。

## 十二、关键约束

1. **与宿主记忆互补**：宿主负责会话级，本 skill 负责跨会话显式快照。
2. **快照不提交 Git**：存储在 `~/.trae-cn/sessions/`（本地或团队共享盘）。
3. **恢复需用户确认**：restore 必须传 `--confirm yes`。
4. **文件 hash 校验**：恢复时校验 artifacts 的 hash，冲突则提示不自动覆盖。
5. **保留 30 天**：过期清理（可配置 `SESSION_SNAPSHOT_RETENTION_DAYS`）。
6. **失败不阻塞**：快照读写失败只打 WARNING，不阻断主流程。
7. **SKILL.md 行数 ≤ 500**。

## 十三、质量检查清单

- [ ] `python scripts/snapshot_ops.py --help` 可正常输出，无报错
- [ ] `save` 能生成快照 ID、写入快照 JSON、更新索引
- [ ] `restore` 能读取快照并校验文件 hash
- [ ] `restore` 无 `--confirm yes` 时拒绝执行
- [ ] `list` 按时间倒序、limit 生效
- [ ] `diff` 能对比两快照差异（任务/文件/上下文）
- [ ] `clean` 能清理过期快照（>30 天）
- [ ] `~/.trae-cn/sessions/` 目录不存在时自动创建
- [ ] 快照读写失败时只打 WARNING，不阻断主流程，exit code 0
- [ ] 仅用标准库，无外部依赖；UTF-8 编码，中文注释
- [ ] SKILL.md 行数 ≤ 500
