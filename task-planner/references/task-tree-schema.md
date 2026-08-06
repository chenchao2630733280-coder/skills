# task-tree.json 规范 (task-planner)

本文件定义 task-planner 产出物 `task-tree.json` 的完整 JSON Schema,可用于校验。
脚本 `scripts/plan_tasks.py` 的 `topology` 子命令会据此校验输入文件。

## 一、顶层结构

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `version` | string | 是 | 固定 `"1.0"` |
| `root` | object | 是 | 根任务,描述整体需求 |
| `tasks` | array | 是 | 子任务数组,每个元素为一个任务节点 |

## 二、root 字段

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `id` | string | 是 | 根任务 id,固定 `"ROOT"` |
| `title` | string | 是 | 需求标题/一句话描述 |
| `complexity` | string | 是 | 整体复杂度:`low` / `medium` / `high` |

## 三、tasks 数组元素字段

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `id` | string | 是 | 任务唯一 id,建议 `T-001` 格式 |
| `title` | string | 是 | 任务标题,动宾结构(如"实现创建文章接口") |
| `priority` | string | 是 | 优先级:`P0`(阻塞关键路径) / `P1`(重要) / `P2`(可延后) |
| `depends_on` | string[] | 否 | 前置依赖任务的 id 数组;无依赖为空数组 `[]` |
| `parallel_with` | string[] | 否 | 可并行的任务 id 数组(无资源冲突) |
| `assigned_skill` | string | 否 | 建议承接的 skill 名(如 `implement-backend`);未定为 `null` |
| `est_complexity` | string | 是 | 预估复杂度:`★` ~ `★★★★★` |
| `est_duration` | string | 否 | 预估耗时(可选),如 `"30min"` / `"2h"` |

## 四、完整 JSON Schema

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "task-tree",
  "type": "object",
  "required": ["version", "root", "tasks"],
  "additionalProperties": false,
  "properties": {
    "version": { "type": "string", "const": "1.0" },
    "root": {
      "type": "object",
      "required": ["id", "title", "complexity"],
      "additionalProperties": false,
      "properties": {
        "id": { "type": "string" },
        "title": { "type": "string" },
        "complexity": { "type": "string", "enum": ["low", "medium", "high"] }
      }
    },
    "tasks": {
      "type": "array",
      "items": {
        "type": "object",
        "required": ["id", "title", "priority", "est_complexity"],
        "additionalProperties": false,
        "properties": {
          "id": { "type": "string" },
          "title": { "type": "string" },
          "priority": { "type": "string", "enum": ["P0", "P1", "P2"] },
          "depends_on": {
            "type": "array",
            "items": { "type": "string" }
          },
          "parallel_with": {
            "type": "array",
            "items": { "type": "string" }
          },
          "assigned_skill": { "type": ["string", "null"] },
          "est_complexity": {
            "type": "string",
            "enum": ["★", "★★", "★★★", "★★★★", "★★★★★"]
          },
          "est_duration": { "type": "string" }
        }
      }
    }
  }
}
```

## 五、字段约束补充

1. `id` 在 `tasks` 内必须唯一;`root.id` 不与 task id 冲突。
2. `depends_on` 中的 id 必须能在 `tasks` 中找到(引用完整性);指向不存在的任务视为校验失败。
3. `depends_on` 不得形成环(拓扑排序会检测并报错)。
4. `parallel_with` 是对称建议:若 A 的 `parallel_with` 含 B,通常 B 的也含 A;脚本不强制对称,但会提示。
5. `assigned_skill` 为 `null` 表示尚未分配承接 skill,需人工或上层编排补充。

## 六、与 plan-system-implementation task-board.json 的兼容

`task-tree.json` 可互转为 `task-board.json`(plan-system-implementation 产物):

| task-tree.json | task-board.json |
|----------------|-----------------|
| `id` (T-001) | `id` (TASK-001) |
| `title` | `title` |
| `depends_on` | `dependencies` |
| `assigned_skill` | (映射到 `targetFiles`/执行说明) |
| (无) | `status` 默认 `todo` |
| (无) | `sourceIds` 可空 |

转换时 `priority` / `est_complexity` 等 task-tree 特有字段保留在扩展字段或备注,不破坏 task-board 结构。
