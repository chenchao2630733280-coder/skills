---
name: "tool-db-ops"
description: "数据库工具层 skill。封装'跑 migration''查询数据''回滚迁移'操作。当 implement-data-layer 或其他 skill 要执行数据库操作时调用。生产环境只读。"
---

# tool-db-ops

数据库工具层 skill,封装 migration / query / rollback 三类操作,提供统一的安全护栏与产物契约。

## 一、定位与职责

- **封装**:数据库操作的执行入口,屏蔽驱动差异(sqlite3 默认,可通过 `DB_URL` 切换)。
- **生产环境只读**:检测到 production 连接串时,仅允许 `query` 子命令;任何写操作(migrate/rollback)直接拒绝。
- **确认机制**:`migrate` 需 `--confirm`;`rollback` 需二次确认(`--confirm` 且在非生产环境)。
- **被调用方**:由 `implement-data-layer` skill 调用,不直接面向最终用户编排。
- **不负责**:迁移文件内容编写、schema 设计、数据模型决策(这些归上游 skill)。

## 二、子命令清单

| 子命令    | 输入                                              | 输出                       | 需确认                |
| --------- | ------------------------------------------------- | -------------------------- | --------------------- |
| `migrate` | `--migration-dir`、`--direction`(up/down,默认 up)、`--repo`(可选) | 执行迁移文件列表、影响行数 | 是(`--confirm`)       |
| `query`   | `--sql`、`--params`(可选,JSON 数组)             | 查询行、行数               | 否(纯只读)          |
| `rollback`| `--migration-dir`、`--target`(回滚到版本)         | 回滚的迁移文件列表         | 是(二次确认,生产拒绝)|

## 三、安全规则

1. **生产环境只读**:连接串(`DB_URL` 或 `DB_HOST`)中含 `production` / `prod` / `prd` 时标记为生产环境,仅放行 `query`。
2. **migrate 需确认**:执行前必须传入 `--confirm`,否则拒绝并提示。
3. **rollback 需二次确认**:即便有 `--confirm`,生产环境也直接拒绝;非生产环境需 `--confirm`。
4. **连接串管理**:从环境变量 `DB_URL` / `DB_HOST` / `DB_USER` / `DB_PASSWORD` 读取,**绝不**写入任何产物文件或日志。
5. **事务保护**:`migrate` / `rollback` 在单事务内执行,失败回滚整个事务。

## 四、scripts 调用方式

统一入口:
```
python scripts/db_ops.py <子命令> [选项]
```

### migrate 示例
```bash
# 向上迁移(需确认)
python scripts/db_ops.py migrate --migration-dir ./migrations --direction up --confirm

# 向下迁移单个版本(需确认)
python scripts/db_ops.py migrate --migration-dir ./migrations --direction down --confirm
```

### query 示例
```bash
# 只读查询(生产环境也允许)
python scripts/db_ops.py query --sql "SELECT id, name FROM users WHERE active = ?" --params '[1]'

# 无参数查询
python scripts/db_ops.py query --sql "SELECT COUNT(*) FROM orders"
```

### rollback 示例
```bash
# 回滚到指定版本(非生产 + 二次确认)
python scripts/db_ops.py rollback --migration-dir ./migrations --target 20240101_0001 --confirm
```

## 五、产出契约

每次执行产出 `db-ops-report.json`,结构如下:

```json
{
  "command": "migrate | query | rollback",
  "direction": "up | down | null",
  "migrationFiles": ["20240101_0001_init.sql"],
  "rows": [{"id": 1, "name": "alice"}],
  "rowCount": 1,
  "error": null,
  "timestamp": "2026-08-06T10:00:00+08:00",
  "environment": "development | production"
}
```

- `rows` / `rowCount`:仅 `query` 必填;`migrate`/`rollback` 留空数组与 0。
- `error`:成功为 `null`;失败为字符串(含失败码,见 references/db-safety.md)。
- `environment`:基于连接串自动判定。

## 六、失败处理

| 场景                     | 行为                                                   |
| ------------------------ | ------------------------------------------------------ |
| 迁移执行失败             | 回滚整个事务,`error` 记录失败 SQL 与异常,`migrationFiles` 列出已尝试文件 |
| 连接失败                 | 返回 `error`(失败码 `DB_CONNECT_FAILED`),不产生副作用 |
| 生产环境检测到写操作     | 直接拒绝,`error` 失败码 `PROD_WRITE_REJECTED`         |
| 缺少 `--confirm`         | 拒绝执行,`error` 失败码 `CONFIRM_REQUIRED`            |
| 迁移文件缺失/格式错误    | `error` 失败码 `MIGRATION_FILE_INVALID`                |

## 七、与编排总纲的接入

- **上游调用方**:`implement-data-layer`(在生成 schema/migration 后调用本 skill 落库)。
- **不主动编排**:本 skill 不调用其他 skill,只产出 `db-ops-report.json` 供上游决策。
- **回退策略**:若上游检测到 `error` 非空,应中止后续步骤并提示人工介入;`rollback` 失败时禁止自动重试。

## 八、质量检查清单

- [ ] 连接串仅来自环境变量,产物与日志中无明文。
- [ ] 生产环境只读规则生效(写操作被拒绝)。
- [ ] `migrate` / `rollback` 在事务内执行,失败回滚。
- [ ] `db-ops-report.json` 字段完整、`timestamp` 为 ISO8601 带时区。
- [ ] `--help` 不报错;三个子命令均可独立运行。
- [ ] 迁移文件按文件名排序执行。
- [ ] 失败码与 references/db-safety.md 一致。
- [ ] Python 脚本无额外第三方依赖(sqlite3 为标准库)。
