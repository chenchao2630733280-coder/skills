# 失败案例库 Schema 定义

本文档定义失败案例库的案例 JSON Schema、索引文件结构与保留策略。

## 一、案例文件 Schema

每个案例存为独立 JSON 文件:`~/.trae-cn/failures/{id}.json`,其中 `id` 为 UUID4 字符串。

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `id` | string (UUID) | 是 | 案例唯一标识,UUID4 字符串 |
| `skill` | string | 是 | 失败的 skill 名,如 `game-code-forge` |
| `code` | string | 是 | 失败码,大写蛇形命名,如 `ASSET_NOT_FOUND` |
| `reason` | string | 是 | 失败原因描述,自然语言 |
| `fix` | string | 是 | 修复方法或规避建议 |
| `timestamp` | string | 是 | 失败发生时间,ISO-8601 带时区(UTC) |
| `project` | string | 否 | 项目名或路径,便于归类;未提供时省略该字段 |
| `severity` | enum | 是 | `error` 或 `warning`,默认 `error` |

### 案例文件示例

```json
{
  "id": "a1b2c3d4-5678-90ef-1234-567890abcdef",
  "skill": "game-code-forge",
  "code": "ASSET_NOT_FOUND",
  "reason": "ASSET_MANIFEST.json 中引用的图片 assets/hero.png 不存在",
  "fix": "回退到 game-asset-forge 重新生成切图,并校验清单完整性",
  "timestamp": "2026-08-06T03:21:00+00:00",
  "project": "my-game",
  "severity": "error"
}
```

## 二、索引文件结构

索引文件:`~/.trae-cn/failures/failure-casebook.json`,记录所有案例的元信息,用于快速查询,避免遍历全量案例文件。

| 字段 | 类型 | 说明 |
|---|---|---|
| `version` | integer | 索引格式版本号,当前为 `1` |
| `cases` | array | 案例元信息数组,按写入顺序追加 |

`cases` 数组中每个元素的结构:

| 字段 | 类型 | 说明 |
|---|---|---|
| `id` | string | 案例唯一标识(UUID) |
| `skill` | string | 失败的 skill 名 |
| `code` | string | 失败码 |
| `severity` | string | `error` 或 `warning` |
| `timestamp` | string | 失败时间,ISO-8601 带时区 |
| `project` | string | 项目名,无则空字符串 `""` |
| `file` | string | 案例文件名,形如 `{id}.json` |

### 索引文件示例

```json
{
  "version": 1,
  "cases": [
    {
      "id": "a1b2c3d4-5678-90ef-1234-567890abcdef",
      "skill": "game-code-forge",
      "code": "ASSET_NOT_FOUND",
      "severity": "error",
      "timestamp": "2026-08-06T03:21:00+00:00",
      "project": "my-game",
      "file": "a1b2c3d4-5678-90ef-1234-567890abcdef.json"
    }
  ]
}
```

## 三、保留策略

- **默认保留期**:案例自写入起保留 **90 天**。
- **可配置**:通过环境变量 `FAILURE_CASEBOOK_RETENTION_DAYS` 设置保留天数,取正整数;未设置或非法时回退默认 90 天。
- **清理时机**:每次执行 `record` 子命令时,顺带清理过期案例。
- **清理动作**:
  1. 计算截止时间 = `now(UTC) - 保留天数`;
  2. 遍历索引,凡 `timestamp` 早于截止时间的案例,删除其案例 JSON 文件;
  3. 从索引 `cases` 数组中移除该条目;
  4. 保存更新后的索引。
- **清理容错**:删除案例文件失败时只打 `WARNING`,不中断清理;索引保存失败时打 `WARNING`,已删除的文件不回滚。
- **无 timestamp 处理**:案例缺少 `timestamp` 或无法解析时,视为不过期,保留在索引中。
