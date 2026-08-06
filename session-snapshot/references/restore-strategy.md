# 恢复策略（Restore Strategy）

> 本文件定义 session-snapshot 的恢复策略与文件冲突处理。

## 一、恢复模式

### 1.1 全量恢复（默认）

恢复快照的全部状态：
- 任务进度（task_tree）
- 已产出文件清单（artifacts）
- 上下文摘要（context_summary）
- workflow 状态（workflow_state）

**适用场景**：新会话完全接续上次工作，无任何已有状态。

**调用**：
```bash
python scripts/snapshot_ops.py restore --snapshot-id snap-20260806-001 --confirm yes
```

### 1.2 选择性恢复

只恢复指定部分（通过 `--only` 参数）：
- `--only task_tree`：只恢复任务进度
- `--only artifacts`：只恢复文件清单（用于校验文件是否被修改）
- `--only context`：只恢复上下文摘要
- `--only workflow`：只恢复 workflow 状态

**适用场景**：新会话已有部分状态，只需补充特定部分。

**调用**：
```bash
python scripts/snapshot_ops.py restore --snapshot-id snap-001 --confirm yes --only task_tree
```

### 1.3 增量恢复（未来版本）

基于 diff 结果，只恢复与当前状态不同的部分。当前版本暂不支持，后续基于 `diff` 子命令实现。

## 二、文件 hash 校验

### 2.1 校验流程

恢复 artifacts 时，对每个文件：
1. 读取快照中记录的 `hash`（如 `sha256:a1b2c3...`）
2. 计算当前文件的实际 SHA-256
3. 对比：
   - **一致**：文件未被修改，正常恢复
   - **不一致**：文件已被修改，标 `CONFLICT`
   - **文件不存在**：文件已删除，标 `MISSING`

### 2.2 冲突处理

| 情况 | 处理 | 用户提示 |
|------|------|---------|
| 文件 hash 一致 | 正常恢复 | 无 |
| 文件被修改（hash 不一致） | 标 CONFLICT，不自动覆盖 | "文件 X 已被修改，请确认是否用当前版本继续" |
| 文件不存在 | 标 MISSING | "文件 X 已删除，可能需要重新生成" |
| 文件存在但快照无记录 | 忽略（非本次恢复范围） | 无 |

**原则**：不自动覆盖用户修改的文件，由用户决定如何处理冲突。

### 2.3 冲突报告

恢复后产出 `restore-result.json`，记录每个文件的校验结果：

```json
{
  "snapshot_id": "snap-20260806-001",
  "restored_at": "2026-08-06T11:00:00+08:00",
  "artifacts_check": [
    { "path": "docs/PRD.md", "status": "ok", "snapshot_hash": "sha256:...", "current_hash": "sha256:..." },
    { "path": "docs/TECH_DESIGN.md", "status": "conflict", "snapshot_hash": "sha256:...", "current_hash": "sha256:..." }
  ],
  "context_injected": true,
  "task_tree_restored": true
}
```

## 三、恢复后的上下文注入

### 3.1 注入内容

恢复后，把快照的 `context_summary` 注入到新会话的上下文中：
- `key_decisions`：作为"上次会话的关键决策"提示
- `user_preferences`：作为"用户偏好"提示
- `failures`：作为"历史失败记录"提示（关联 failure-casebook）
- `notes`：作为"备注"提示

### 3.2 注入格式

注入到新会话的提示（示例）：

```
【会话恢复】来自快照 snap-20260806-001(2026-08-06 10:30)

任务进度:
  当前任务: T3
  已完成: T1, T2
  待执行: T4, T5

关键决策:
  - 使用 Phaser 3 引擎
  - 目标平台 Web
  - 游戏类型:2D 跑酷

用户偏好:
  - 每步人工确认
  - 中文沟通

历史失败:
  - game-asset-forge: TIMEOUT(案例 case-uuid-001)

备注: 用户要求在蓝图阶段后暂停确认

文件校验:
  docs/PRD.md: OK
  docs/TECH_DESIGN.md: CONFLICT(文件已被修改)
```

## 四、恢复限制

1. **恢复需用户确认**：`restore` 必须传 `--confirm yes`。
2. **不自动覆盖文件**：文件冲突时只提示，不自动覆盖。
3. **不恢复对话历史**：本 skill 只恢复状态，不恢复对话历史（那是宿主记忆的职责）。
4. **不恢复 skill 内部状态**：只恢复 task-tree/workflow 等外部状态，skill 内部变量不恢复。
5. **一次只恢复一个快照**：不支持合并多个快照（冲突复杂，留给用户决策）。

## 五、与 workflow-runtime 的协作

workflow-runtime 恢复执行时：
1. 调 `session-snapshot restore` 恢复 workflow_state
2. 读取快照中的 `current_step` 和 `paused_at`
3. 从 `paused_at` 节点继续执行 workflow.yaml
4. 恢复 task-tree 状态，供 replanner 评估是否需要重规划
