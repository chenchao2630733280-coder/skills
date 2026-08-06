# 项目知识库 Schema 定义

本文件定义 `project-knowledge-base` skill 的知识条目结构、分类、索引与存储路径规则,
是 `scripts/kb_ops.py` 与 SKILL.md 第五节(schema)的权威参考。

## 一、知识分类说明

| 分类 key | 中文名 | 用途 | 典型内容 |
|----------|--------|------|----------|
| `team-conventions` | 团队规范 | 约束团队协作行为 | 命名约定、分支策略、提交信息格式、Code Review 流程 |
| `adr` | 架构决策记录 | 沉淀技术选型与架构演进决策 | 决策背景、备选方案、决策结果、影响 |
| `postmortems` | 事故复盘 | 记录线上事故/缺陷的根因与改进 | 时间线、影响范围、根因、改进措施、跟踪项 |
| `code-standards` | 代码规范 | 约束代码实现风格 | 目录结构、错误处理、日志规范、测试约定 |

> 分类 key 即存储子目录名,新增时由 `--category` 指定,枚举校验。

## 二、知识条目字段表

| 字段 | 类型 | 必填 | 约束 / 说明 |
|------|------|------|-------------|
| `id` | string | 是 | UUID v4 字符串,由脚本 `add` 时生成,全局唯一;亦为条目文件名 |
| `category` | string | 是 | 枚举值,见第一节;决定存储子目录 |
| `title` | string | 是 | 简明标题,建议 ≤80 字符 |
| `content` | string | 是 | 正文,支持多行;`adr` 建议包含 背景/决策/结果 三段 |
| `tags` | string[] | 否 | 标签数组,无标签时为 `[]`;参与关键词检索 |
| `createdAt` | string | 是 | ISO8601 字符串,新建时写入,后续不变 |
| `updatedAt` | string | 是 | ISO8601 字符串,每次 `update` 刷新 |
| `project` | string | 否 | 所属项目标识,跨项目场景使用,单项目可省略 |

### 条目示例

```json
{
  "id": "f1c2d3e4-5a6b-7c8d-9e0f-1234567890ab",
  "category": "adr",
  "title": "选用 PostgreSQL 作为主库",
  "content": "背景:需要强一致与复杂查询。\n决策:采用 PostgreSQL 16。\n结果:主库统一为 PG。",
  "tags": ["数据库", "选型"],
  "createdAt": "2026-08-06T10:00:00",
  "updatedAt": "2026-08-06T10:00:00"
}
```

## 三、索引结构

索引文件路径:`.trae-cn/knowledge/knowledge-base.json`

```json
{
  "entries": [
    {
      "id": "f1c2d3e4-5a6b-7c8d-9e0f-1234567890ab",
      "category": "adr",
      "title": "选用 PostgreSQL 作为主库",
      "tags": ["数据库", "选型"],
      "createdAt": "2026-08-06T10:00:00",
      "updatedAt": "2026-08-06T10:00:00",
      "path": ".trae-cn/knowledge/adr/f1c2d3e4-5a6b-7c8d-9e0f-1234567890ab.json"
    }
  ]
}
```

说明:

- `entries` 为数组,每个元素为一条知识的元数据。
- 索引项是条目文件的子集,额外包含 `path` 字段,指向条目文件相对项目根的路径,便于快速定位。
- `add` 追加索引项;`update` 同步刷新 `title` / `updatedAt`;`query` / `list` 仅读取索引。

## 四、存储路径规则

| 对象 | 路径 |
|------|------|
| 知识库根目录 | `{项目根}/.trae-cn/knowledge/` |
| 分类子目录 | `{项目根}/.trae-cn/knowledge/{category}/` |
| 条目文件 | `{项目根}/.trae-cn/knowledge/{category}/{id}.json` |
| 索引文件 | `{项目根}/.trae-cn/knowledge/knowledge-base.json` |

规则:

1. 脚本以当前工作目录为项目根(`Path.cwd()`)。
2. `add` 自动创建缺失的根目录与分类子目录(`mkdir parents=True, exist_ok=True`)。
3. 条目文件名即其 `id`,后缀 `.json`,与所属分类子目录共同确定唯一位置。
4. 索引文件与条目文件一一对应;`update` 同步刷新条目文件与索引项。
5. 不提供删除子命令;如需删除,须人工确认后同时移除条目文件与索引项,避免悬挂索引或孤立文件。
6. 所有文件以 UTF-8 编码写入,`json.dump` 使用 `ensure_ascii=False` 以保留中文。
