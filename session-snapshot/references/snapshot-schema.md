# 快照 JSON Schema

> 本文件定义 session-snapshot 产出的 `session-snapshot.json` 的完整结构。

## 一、顶层结构

```json
{
  "snapshot_id": "snap-20260806-001",
  "session_id": "原会话ID",
  "created_at": "2026-08-06T10:30:00+08:00",
  "trigger": "manual",
  "task_tree": { ... },
  "artifacts": [ ... ],
  "context_summary": { ... },
  "workflow_state": { ... }
}
```

## 二、字段说明

### 2.1 元数据字段

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `snapshot_id` | string | 是 | 快照唯一标识，格式 `snap-{YYYYMMDD}-{NNN}` |
| `session_id` | string | 是 | 原会话 ID（若未知则 `unknown`） |
| `created_at` | string(ISO-8601) | 是 | 快照创建时间，带时区 |
| `trigger` | enum | 是 | `manual` / `auto-confirm` / `auto-stage` / `auto-fail` |

### 2.2 任务进度（task_tree）

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `current_task` | string | 否 | 当前正在执行的任务 ID（如 `T3`） |
| `completed` | array | 否 | 已完成任务 ID 列表 |
| `pending` | array | 否 | 待执行任务 ID 列表 |
| `task_tree_file` | string | 否 | 原始 task-tree.json 路径（若存在） |

### 2.3 已产出文件（artifacts）

数组，每项：

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `path` | string | 是 | 文件路径（相对项目根） |
| `hash` | string | 是 | SHA-256 哈希，格式 `sha256:{hex}` |
| `summary` | string | 否 | 文件摘要（一句话） |
| `size` | integer | 否 | 文件大小（字节） |

### 2.4 上下文摘要（context_summary）

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `key_decisions` | array | 否 | 关键决策列表（字符串数组） |
| `user_preferences` | array | 否 | 用户偏好（字符串数组） |
| `failures` | array | 否 | 失败记录，每项含 `skill` / `code` / `case_id`（关联 failure-casebook） |
| `notes` | string | 否 | 其他备注 |

### 2.5 workflow 状态（workflow_state）

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `current_step` | string | 否 | 当前步骤 ID（如 `s3`） |
| `paused_at` | string | 否 | 暂停点 ID（如 `pause1`），无则 null |
| `workflow_file` | string | 否 | workflow.yaml 路径 |
| `exec_report_file` | string | 否 | 执行轨迹文件路径 |

## 三、完整示例

```json
{
  "snapshot_id": "snap-20260806-001",
  "session_id": "sess-abc123",
  "created_at": "2026-08-06T10:30:00+08:00",
  "trigger": "auto-confirm",
  "task_tree": {
    "current_task": "T3",
    "completed": ["T1", "T2"],
    "pending": ["T4", "T5"],
    "task_tree_file": "output/build/task-tree.json"
  },
  "artifacts": [
    {
      "path": "docs/PRD.md",
      "hash": "sha256:a1b2c3d4e5f6...",
      "summary": "产品需求文档",
      "size": 15234
    },
    {
      "path": "docs/TECH_DESIGN.md",
      "hash": "sha256:f6e5d4c3b2a1...",
      "summary": "技术设计文档",
      "size": 8920
    }
  ],
  "context_summary": {
    "key_decisions": [
      "使用 Phaser 3 引擎",
      "目标平台 Web",
      "游戏类型:2D 跑酷"
    ],
    "user_preferences": [
      "每步人工确认",
      "中文沟通"
    ],
    "failures": [
      {
        "skill": "game-asset-forge",
        "code": "TIMEOUT",
        "case_id": "case-uuid-001"
      }
    ],
    "notes": "用户要求在蓝图阶段后暂停确认"
  },
  "workflow_state": {
    "current_step": "s3",
    "paused_at": "pause1",
    "workflow_file": "output/build/workflow.yaml",
    "exec_report_file": "output/build/workflow-exec-report.json"
  }
}
```

## 四、索引文件（snapshots-index.json）

索引文件记录所有快照的元信息，用于快速查询（避免遍历全量快照文件）：

```json
{
  "snapshots": [
    {
      "snapshot_id": "snap-20260806-001",
      "session_id": "sess-abc123",
      "created_at": "2026-08-06T10:30:00+08:00",
      "trigger": "auto-confirm",
      "summary": "任务 T2 完成,暂停于 pause1",
      "file": "snap-20260806-001.json"
    }
  ],
  "updated_at": "2026-08-06T10:30:00+08:00"
}
```

## 五、约束

1. **snapshot_id 全局唯一**：格式 `snap-{YYYYMMDD}-{NNN}`，NNN 为当日序号（001 开始）。
2. **hash 算法**：统一用 SHA-256，前缀 `sha256:`。
3. **时间格式**：ISO-8601 带时区（默认 +08:00）。
4. **artifacts 路径**：相对项目根，正斜杠分隔（跨平台兼容）。
5. **可选字段**：未提供的字段用 `null` 或省略，不强制填空字符串。
